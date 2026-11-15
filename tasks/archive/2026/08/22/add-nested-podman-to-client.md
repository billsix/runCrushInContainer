# Add nested-podman support to the Crush client

**Status:** complete
**Started:** 2026-08-21 · **Implemented:** 2026-08-21 · **Reopened:** 2026-08-22 · **Completed:** 2026-08-22

Gave the `client/` container the same opt-in `NESTED_PODMAN=1` capability as the runClaudeInContainer
sandbox, so Crush can build and run a project's own containers nested inside the client. Verified with
a real inner run. A 2026-08-22 follow-up baked the nested-podman reference doc into the image after the
offline agent could not find it.

## Why

The conventions port (`tasks/port-runclaude-conventions-systems.md`, P4.4) had skipped nested podman
on the reasoning that "the Crush client doesn't run nested containers." That was wrong: the client is
the full runClaudeInContainer toolchain (~430 packages), and the maintainer's projects all build and run
in their own containers, so driving Crush on them means running those containers nested. Before this,
passing `NESTED_PODMAN` to the client Makefile was a silent no-op.

## What was done

- **`client/Makefile`**: ported the `NESTED_PODMAN` flag set (opt-in, default off), appended to the
  `shell` run: `--device /dev/fuse`, `--device /dev/net/tun`, `--security-opt label=disable` (already
  always-on in the client), `--security-opt unmask=ALL`, `--cap-add=sys_admin,mknod,net_admin`, and a
  tmpfs `/var/lib/containers` sized by `NESTED_PODMAN_TMPFS_SIZE` (default 8g).
  > **Superseded (2026-09-27):** the inner store defaults to a disk-backed directory
  > (`NESTED_PODMAN_STORE ?= dir`); tmpfs is an opt-in. See
  > `tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`.
- **`client/entrypoint/dotfiles/.config/containers/storage.conf`**: baked (points inner podman at
  `/usr/bin/fuse-overlayfs`), riding the existing dotfiles `COPY`. No package changes: the toolchain
  already ships `podman`, `buildah`, `skopeo` and `fuse-overlayfs` (`client/entrypoint/01-install-base.sh`).
- **Conventions**: added a terse "Running projects in a nested container" note to the lean baked
  `CLAUDE.md` (launch with `NESTED_PODMAN=1`; every inner `podman run` needs `--cgroups=disabled` and
  `--network=host`; the RAM-store caveat; don't edit the project's build files).
- **`tasks/reference/nested-podman-design.md`**: an adapted Crush-client version of runClaudeInContainer's
  doc (flag set, differences from runClaude, the depth caveat), pointing to runClaude's copy for the full
  rationale.
- Un-skipped P4.4 in `tasks/port-runclaude-conventions-systems.md`, pointing at this task.

## Decisions (2026-08-21, maintainer: "your call")

1. **Conventions note is terse and always-loaded**; full detail lives in the reference doc, keeping the
   lean-core context small.
2. **The reference doc was adapted, not copied verbatim.**
3. **`NESTED_PODMAN_TMPFS_SIZE` defaults to 8g**, overridable.
4. **Omitted the `$XDG_RUNTIME_DIR/libpod` shadow tmpfs** the plan listed. runClaude needs it only because
   it bind-mounts the host `$XDG_RUNTIME_DIR`; the client does not, so there is no host podman state to
   collide with. Re-add only if X/Wayland passthrough is ever added to the client.
- **Depth caveat**: the client is often itself run nested inside the runClaudeInContainer sandbox, which
  makes project containers podman-in-podman-in-podman. Documented the limit rather than promising
  three-deep; the realistic path is running the client on the host (or with the outer sandbox's
  `NESTED_PODMAN=1`) for one clean level.
- `--cgroups=disabled` cannot be baked into other projects' Makefiles; it is applied per inner run.

## Follow-up (2026-08-21): `-e NESTED_PODMAN` passthrough

Crush "thought NESTED_PODMAN wasn't set" because it was only a host-side make variable that added run
flags, never an env var in the container. The `shell` target now always passes
`-e NESTED_PODMAN=$(NESTED_PODMAN)` (definitive `0`/`1` inside), and the conventions note and reference
doc tell the agent to check `$NESTED_PODMAN` (intent) together with `test -e /dev/fuse && podman info`
(works).

## Follow-up (2026-08-22): the reference doc was unreachable offline

On the offline system, Glimmer looked for the nested-podman doc and could not find it. The baked
`CLAUDE.md` and `sandbox-capability-map.md` pointed at `tasks/reference/nested-podman-design.md`, a repo
path absent inside the container (the agent's `/work` is the mounted project, not this repo). Only three
reference docs were baked then; this one had been deliberately left un-baked under Decision 1, which
conflated "not always-loaded" with "not present at all."

Fixed by copying the doc to `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md`
(an on-demand read, no context-budget cost) and pointing both baked files at
`~/.config/crush/reference/nested-podman-design.md`. The two copies must be kept in sync.

Similar-issue scan of all baked files (`CLAUDE.md`, `reference/*`, `commands/*`): those two were the only
dangling pointers. The slash commands' `tasks/reference/`, `tools/`, `CLAUDE.md` references are correct
(they operate on the mounted project at `/work`). `print-debugging.md`'s pointer to the baked
`CLAUDE.md` "Instrumentation-driven debugging" section resolves. `llm-overused-phrases.md` still cites
runClaude's source path as provenance text; left as-is to stay verbatim with runClaude.

## Verification

- 2026-08-21 (maintainer-confirmed): in a rebuilt client launched with `make shell NESTED_PODMAN=1`,
  `$NESTED_PODMAN=1`, `/dev/fuse` present, `podman info` worked.
- 2026-08-21: an inner image pull worked, and the inner run needed both `--cgroups=disabled` (read-only
  cgroup) and `--network=host` (bridged netavark fails nested with
  `netavark: setns: Operation not permitted`). Documented in the reference doc and conventions. A real
  project's nested `make image` was not recorded.
- 2026-08-22 static: in the rebuilt image, `~/.config/crush/reference/nested-podman-design.md` was present
  and both pointers read the baked path. That rebuild also carried the `mounts.conf`-suppression change.
- 2026-08-22 behavioral: with the tunnel up (`n_ctx 65536`) and `make shell NESTED_PODMAN=1`, `crush run -q`
  asked for the doc's path and the two inner-run flags answered
  `/root/.config/crush/reference/nested-podman-design.md`, `--cgroups=disabled`, `--network=host`.

## Related

- `tasks/port-runclaude-conventions-systems.md` (P4.4).
- `tasks/reference/nested-podman-design.md`; `tasks/reference/architecture.md` (the nested-build gotcha
  for the 22.3 GB client image).
- runClaudeInContainer: `Makefile` (the flag set), `entrypoint/dotfiles/.config/containers/storage.conf`,
  `tasks/reference/nested-podman-design.md`.
