# Add nested-podman support to the Crush client

**Status:** proposed — needs go-ahead to implement
**Priority:** 3
**Difficulty:** 5
**Started:** 2026-08-21

## Goal

Give the `client/` container the same **`NESTED_PODMAN=1`** capability the runClaudeInContainer
sandbox has, so that when Crush drives work on a project, it can **build and run that project's own
containers nested inside the Crush client** (`make image` / `make run` / `make shell` for
container-per-project repos like mvp, gacalc, spimulator, …). Right now the client Makefile does
**not** implement `NESTED_PODMAN` (passing it is a silent no-op — `architecture.md`).

## Why (this corrects a miss)

During the conventions port (`tasks/port-runclaude-conventions-systems.md`, P4.4) nested-podman was
**skipped** on the reasoning "the Crush client doesn't run nested containers." That was wrong: the
client is the **full runClaudeInContainer toolchain** (~430 packages) — a general dev sandbox — and
the maintainer's projects all build/run in their own containers. So driving Crush to build/test a
project means running its container nested, exactly the runClaude use case. Same need, so it should
have the same capability.

## Plan

- [ ] **Client Makefile — the `NESTED_PODMAN` flag set** (port from runClaudeInContainer, opt-in,
      default off). Append to the `shell` target's `podman run` when `NESTED_PODMAN=1`:
      `--device /dev/fuse`, `--device /dev/net/tun`, `--security-opt label=disable`,
      `--security-opt unmask=ALL`, `--cap-add=sys_admin,mknod,net_admin`, a tmpfs
      `/var/lib/containers` sized by `NESTED_PODMAN_TMPFS_SIZE` (default 8g), and a tmpfs over
      `$XDG_RUNTIME_DIR/libpod`. (The client's SELinux `label=disable` is already always-on; keep it.)
- [ ] **`storage.conf`** — bake `client/entrypoint/dotfiles/.config/containers/storage.conf`
      (points inner podman at `/usr/bin/fuse-overlayfs`); it rides the existing dotfiles `COPY`.
      *Verify:* the toolchain already ships `podman`, `buildah`, `skopeo`, `fuse-overlayfs`
      (`01-install-base.sh`), so no package changes.
- [ ] **Conventions** — re-add a **terse** "Running projects in a nested container" note to the lean
      `CLAUDE.md`: the two prerequisites (launch with `NESTED_PODMAN=1`; every inner `podman run`
      needs `--cgroups=disabled`) and the RAM-store caveat. Keep it short (lean-core context budget);
      push the full rationale to the reference doc below.
- [ ] **Reference doc** — port `nested-podman-design.md` from runClaudeInContainer into
      `tasks/reference/` (adapt: it's mostly tool-agnostic about the podman stack, but the banner,
      paths, and "runClaude" framing need updating for this repo).
- [ ] **Un-skip P4.4** in `tasks/port-runclaude-conventions-systems.md` (point it at this task).
- [ ] **Verify** (needs nested-podman available on the host, i.e. the outer sandbox launched with
      `NESTED_PODMAN=1`, or a real host): `make shell NESTED_PODMAN=1`, then inside the client build
      or run one of the maintainer's project containers with `--cgroups=disabled` (e.g. a small
      `podman run --rm --cgroups=disabled fedora:44 echo ok`, then a real project's `make image`).
      Confirm `/dev/fuse` present and `podman info` works inside.

## Notes / decisions

- **Nested-in-nested caveat:** the Crush client is *itself* often run nested (inside the
  runClaudeInContainer sandbox). Building/running a project container inside the Crush client is then
  **podman-in-podman-in-podman**. runClaude's nested support is one level; three levels may hit
  limits (RAM store, cgroups). The realistic path is: run the Crush client **on the host** (or with
  the outer sandbox's `NESTED_PODMAN=1`), then this gives one level of nesting for project work.
  Document the depth limit; don't over-promise three-deep.
- The `--cgroups=disabled` requirement on inner runs can't be baked into *other* projects' Makefiles
  — same as runClaude, it's applied per inner run (or via the standing "transient add + revert"
  authorization in the personal overlay).

## Open questions

1. **Conventions section — terse always-loaded, or on-demand only?** The lean `CLAUDE.md` is kept
   small on purpose (local-model context). Recommend a **short always-loaded** note (the 2
   prerequisites + `--cgroups=disabled`) with the full detail in the ported `nested-podman-design.md`
   (referenced, not `@`-imported). OK?
2. **Port `nested-podman-design.md` verbatim or adapt?** It has runClaude-specific paths/framing.
   Recommend **adapt** (keep the tool-agnostic podman-stack rationale; fix banner/paths for this
   repo). OK?
3. **Default `NESTED_PODMAN_TMPFS_SIZE`?** runClaude defaults 8g; the client image itself is ~22 GB,
   but *inner project* images are usually smaller. Recommend **8g default**, overridable. OK?

## Cross-links

- `tasks/port-runclaude-conventions-systems.md` (P4.4 — the skip this corrects).
- `tasks/reference/architecture.md` (notes the client doesn't implement `NESTED_PODMAN`; and the
  nested-*build* gotcha for the 22.3 GB client image).
- runClaudeInContainer: `Makefile` (the flag set), `entrypoint/dotfiles/.config/containers/storage.conf`,
  `tasks/reference/nested-podman-design.md` (the source reference doc).
