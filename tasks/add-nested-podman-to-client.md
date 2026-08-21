# Add nested-podman support to the Crush client

**Status:** COMPLETE + verified (2026-08-21) — flags, storage.conf, `-e NESTED_PODMAN` passthrough,
conventions note, and reference doc all in. **Live-verified:** prerequisites pass and an inner
`podman run --cgroups=disabled --network=host fedora:44 echo nested-ok` printed `nested-ok`. Inner
runs need BOTH flags (netavark bridged fails nested because the client is `--network=host`). The benign
`Failed to mount subscriptions` WARN on inner runs is now **suppressed** by emptying
`/usr/share/containers/mounts.conf` in the client Dockerfile (the RHEL subscription-secrets mount is
useless on Fedora; needs a rebuild to take effect).
**Priority:** 3
**Difficulty:** 5
**Started:** 2026-08-21 · **Implemented:** 2026-08-21

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

- [x] **Client Makefile — the `NESTED_PODMAN` flag set** (port from runClaudeInContainer, opt-in,
      default off). Append to the `shell` target's `podman run` when `NESTED_PODMAN=1`:
      `--device /dev/fuse`, `--device /dev/net/tun`, `--security-opt label=disable`,
      `--security-opt unmask=ALL`, `--cap-add=sys_admin,mknod,net_admin`, a tmpfs
      `/var/lib/containers` sized by `NESTED_PODMAN_TMPFS_SIZE` (default 8g), and a tmpfs over
      `$XDG_RUNTIME_DIR/libpod`. (The client's SELinux `label=disable` is already always-on; keep it.)
- [x] **`storage.conf`** — bake `client/entrypoint/dotfiles/.config/containers/storage.conf`
      (points inner podman at `/usr/bin/fuse-overlayfs`); it rides the existing dotfiles `COPY`.
      *Verify:* the toolchain already ships `podman`, `buildah`, `skopeo`, `fuse-overlayfs`
      (`01-install-base.sh`), so no package changes.
- [x] **Conventions** — re-add a **terse** "Running projects in a nested container" note to the lean
      `CLAUDE.md`: the two prerequisites (launch with `NESTED_PODMAN=1`; every inner `podman run`
      needs `--cgroups=disabled`) and the RAM-store caveat. Keep it short (lean-core context budget);
      push the full rationale to the reference doc below.
- [x] **Reference doc** — port `nested-podman-design.md` from runClaudeInContainer into
      `tasks/reference/` (adapt: it's mostly tool-agnostic about the podman stack, but the banner,
      paths, and "runClaude" framing need updating for this repo).
- [x] **Un-skip P4.4** in `tasks/port-runclaude-conventions-systems.md` (point it at this task).
- [x] **Verify — prerequisites confirmed (2026-08-21):** in a rebuilt client launched with
      `make shell NESTED_PODMAN=1`, `$NESTED_PODMAN=1`, `/dev/fuse` is present, and `podman info`
      works (maintainer-confirmed).
- [x] **Verify — inner run (remaining):** confirm an actual nested container runs:
      `podman run --rm --cgroups=disabled --network=host fedora:44 echo nested-ok` inside the client,
      then a real project's `make image` (with both flags on its inner run).
      **Finding (2026-08-21):** the image *pull* works, but the inner run needs **both**
      `--cgroups=disabled` (read-only cgroup) **and `--network=host`** — bridged netavark fails nested
      with `netavark: setns: Operation not permitted`. Documented in the reference doc + conventions.

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

## Decisions (resolved 2026-08-21, maintainer: "your call")

1. **Conventions section → terse always-loaded**, self-contained (the 2 prerequisites +
   `--cgroups=disabled` + don't-edit-their-build-files); full detail in `tasks/reference/
   nested-podman-design.md` (repo doc, not baked/`@`-imported — keeps the lean-core context small).
2. **`nested-podman-design.md` → adapted, not verbatim.** Wrote a focused Crush-client version
   (flag set, the differences from runClaude, the depth caveat) that points to runClaude's copy for
   the full rationale/declined-alternatives.
3. **`NESTED_PODMAN_TMPFS_SIZE` → 8g default**, overridable.
4. **Omitted the `$XDG_RUNTIME_DIR/libpod` shadow tmpfs** (the plan listed it): it's only needed
   because runClaude bind-mounts the host `$XDG_RUNTIME_DIR`; the barebones client does NOT, so
   there's no host podman state to collide with. Documented in the reference doc — re-add only if
   X/Wayland passthrough is ever added to the client.

## Follow-up (2026-08-21): `-e NESTED_PODMAN` passthrough

Symptom: Crush "thought NESTED_PODMAN wasn't set" — because `NESTED_PODMAN=1` is a host-side **make
variable** that only adds run flags; it is **not** an env var inside the container, so the agent
checking `$NESTED_PODMAN` always saw it empty. Fix: the `shell` target now **always** passes
`-e NESTED_PODMAN=$(NESTED_PODMAN)` (definitive `0`/`1` inside). The conventions note + reference doc
now tell the agent to detect nesting via `$NESTED_PODMAN` (intent) **and** `test -e /dev/fuse &&
podman info` (works). Needs a client-image rebuild is NOT required for this (it's a `run` flag), but
the conventions note change IS baked — so `make image` to get both.

## Cross-links

- `tasks/port-runclaude-conventions-systems.md` (P4.4 — the skip this corrects).
- `tasks/reference/architecture.md` (notes the client doesn't implement `NESTED_PODMAN`; and the
  nested-*build* gotcha for the 22.3 GB client image).
- runClaudeInContainer: `Makefile` (the flag set), `entrypoint/dotfiles/.config/containers/storage.conf`,
  `tasks/reference/nested-podman-design.md` (the source reference doc).
