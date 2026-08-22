# Seed base images so nested podman builds work offline

**Status:** proposed — needs go-ahead. Gap identified 2026-08-22; **not yet attempted on the offline
system** (maintainer builds the client image offline fine, but has done no nested-podman work there).
**Priority:** 4
**Difficulty:** 5
**Started:** 2026-08-22

## Goal

Make a project's own container build/run work **nested inside the Crush client on an offline/airgapped
system**. Today nested podman is verified only where a registry is reachable; offline, the first thing
any project build does — `FROM registry.fedoraproject.org/fedora:44` (or whatever base it pins) — has
nothing to pull from and fails ("looked for it and couldn't find it", at the *image* level this time,
not the doc level).

## Why it fails offline (the mechanism)

- The nested inner image store is `--tmpfs /var/lib/containers:rw,size=$(NESTED_PODMAN_TMPFS_SIZE)`
  (`client/Makefile`) — **RAM-backed and empty at every `--rm` launch**. `nested-podman-design.md`
  states it outright: *"The inner store is RAM … Images don't survive the session."*
- Nothing seeds base images into that store — no `podman load`, no `skopeo copy`, no
  `additionalimagestores` (grepped `client/`, 2026-08-22).
- So an inner `podman build`/`podman run <base>` must **pull the base from a registry**. Online this
  "works" but silently re-pulls every session (the tmpfs is wiped by `--rm`), which masked the
  dependency. **Offline the pull can never succeed even once.**
- This also violates the repo's own **"self-contained image runs offline in 5 years"** convention: the
  client image bakes *Crush* in, but not the images its nested builds depend on.

Separate from — and discovered alongside — the doc-reachability bug fixed in
`tasks/archive/2026/08/22/add-nested-podman-to-client.md`. That was "can't find the doc *describing*
nested podman"; this is "can't find the *base image* nested podman needs." Same offline trigger, two
different missing artifacts.

## Approach (candidates — decide in Open questions)

1. **Read-only additional image store baked into the client image (recommended).** At client
   image-build, `skopeo copy` / `podman pull` the base image(s) into a directory baked into a committed
   layer, e.g. `/var/lib/shared-images`; add `additionalimagestores = ["/var/lib/shared-images"]` to
   the baked `storage.conf`. Inner podman then *sees* `fedora:44` with **zero pull and zero RAM copy**,
   offline. Cleanest fit with the self-contained-image convention; the base rides in the image itself.
   - Caveat: `additionalimagestores` is read-only; new/built inner images still land in the RW tmpfs
     store (fine — those are the project's own build outputs, and are ephemeral by design).
2. **`podman load` from a baked-in tar on startup**, gated on `NESTED_PODMAN=1` (e.g. in `shell.sh`).
   Works, but re-copies into RAM each launch and costs tmpfs space — worse than (1).
3. **Dir-backed persistent inner store**, pre-seeded once (mirrors runClaude's open thread
   `tasks/dir-backed-nested-podman-storage.md`). Bigger change; solves RAM-pressure too, but heavier
   than needed just for offline base images.

## Considerations

- **Which bases to seed?** At minimum `fedora:44` (the template base every one of the maintainer's
  container-per-project repos uses). Possibly others a specific project pins. Baking many bases inflates
  the client image — pick the common set, document how to add more.
- **Image size / RAM budget.** The client image is already large (~22.3 GB per the nested-in-nested
  note); baking base images adds to it. `fedora:44` is a few hundred MB — acceptable; a full toolchain
  base would not be.
- **The depth caveat still applies** (`nested-podman-design.md`): running the client *itself* nested
  makes project builds three-deep. Seeding fixes the *pull*, not the depth limit — run the client on
  the host for a clean single level.
- **Verify with the offline export test** (personal-overlay convention): build client → `image-export`
  → `image-import` → run with `--network=none` and confirm an inner `podman run --cgroups=disabled
  --network=host <baked-base> echo ok` succeeds with no network.

## Plan

- [ ] Decide the approach (Open question 1) and the seed set (Open question 2).
- [ ] Client Dockerfile: pull/copy the chosen base image(s) into a committed store dir at build time
      (needs network **at build**, which the maintainer has — only *runtime* is offline).
- [ ] Baked `storage.conf`: add `additionalimagestores` (approach 1) — keep it consistent with the
      existing `mount_program = /usr/bin/fuse-overlayfs` block.
- [ ] Verify offline: the export/import + `--network=none` inner-run test above.
- [ ] Update `tasks/reference/nested-podman-design.md` (the "inner store is RAM / pull works" notes now
      need the offline-seeding story) and the repo `CLAUDE.md`/`README.md` if the nested workflow changes.

## Open questions

1. **Approach — which?** Recommend **(1) read-only `additionalimagestores` baked in** (self-contained,
   no per-launch cost), over (2) startup `podman load` or (3) a dir-backed persistent store. Your call.
2. **Seed set — which base images?** Recommend **just `fedora:44`** to start (the template base), with
   a documented way to add more, rather than pre-baking a broad set and inflating the image. Agree, or
   name specific project bases to include?

## Cross-links

- `tasks/reference/nested-podman-design.md` — the RAM-store operating note this gap sits under.
- `tasks/archive/2026/08/22/add-nested-podman-to-client.md` — the sibling offline bug (doc, not image).
- runClaudeInContainer: `tasks/dir-backed-nested-podman-storage.md` (the dir-backed-store open thread,
  approach 3's origin).
