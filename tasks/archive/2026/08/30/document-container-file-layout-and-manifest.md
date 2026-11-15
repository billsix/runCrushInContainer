# Document container file layout and manifest

**Status:** complete
**Started:** 2026-08-30 · **Completed:** 2026-08-30

Wrote `tasks/reference/container-file-layout.md`, the map of every file the client image bakes, every
mount the Makefile lays over it, and the final container paths, and added a read-only `make manifest`
target that prints it. Implemented with go-ahead from William Emerison Six <billsix@gmail.com>.

## Why

The client image bakes many files and the Makefile mounts others over them, and reference docs live in
two places (repo `tasks/reference/` vs baked `~/.config/crush/reference/`). The originating Crush session
confused baked vs mounted identity for `shell.sh` and `ai-coding-conventions.personal.md`, could not tell
which reference docs were baked and which repo-only, and had no single source of truth for final container
paths. The task doc cited a sibling session log, `crush.log`; it was never committed.

## What was done

- **`tasks/reference/container-file-layout.md`**: tables for baked files (source, container path,
  overridable?), mounts (host path, container path, conditional or not), and the repo-path ↔ baked-path
  reference-doc mapping, plus notes on the `CRUSH_AT_IMPORT` patch and the `crushrc` location. Inventoried
  from the `client/Dockerfile` `COPY` lines, the `client/entrypoint/` tree, the baked
  `client/entrypoint/dotfiles/.config/crush/reference/` docs, and `client/Makefile` `SHELL_RUN_FLAGS`.
- **A baked copy** at `client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md`, kept
  in sync, so the in-container agent can read it with no repo mounted (beyond the original plan).
- **`make manifest`** in `client/Makefile`: a static `cat` of the reference doc, read-only, no image build.
- Pointers from `tasks/reference/architecture.md` (client section) and the project `CLAUDE.md`.
- **Fixed en route**: `client/entrypoint/shell.sh`'s header comment claimed the file was baked, not
  mounted; that had been stale since `SHELL_RUN_FLAGS` gained the `/shell.sh` bind mount. It now describes
  the baked fallback plus mounted override.

## Decisions (2026-08-30)

1. **`make manifest` is a static `cat`** of the reference doc rather than generated from the Dockerfile
   and Make variables. Dynamic generation was deferred and not done.
2. **No `server/` layout doc**: the server runs natively on macOS and is not containerized.

The plan also asked that the manifest work with `FULL_TOOLCHAIN` and `NESTED_PODMAN`; as a static `cat`
it is independent of build flags.

> **Superseded:** `FULL_TOOLCHAIN` was removed 2026-09-12 (the client is always the full toolchain), and
> the diversion stack, then mounted unconditionally from the host's `~/.config/crush/stack.md`, became
> in-session only on 2026-09-03 (`tasks/archive/2026/09/03/stack-in-session-only-harvest-at-sweep.md`).
> The current layout is whatever `tasks/reference/container-file-layout.md` says.

## Related

- `tasks/reference/container-file-layout.md` (the deliverable, updated in place).
- `tasks/reference/architecture.md`; `client/Dockerfile`; `client/Makefile`.
