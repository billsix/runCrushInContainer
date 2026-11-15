# Documented all 17 patches and made CRUSH_LSP_ASYNC settable from make

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §1.2, §2.2 F11

## What this did

- `client/patches/` holds 17 patches, but `CLAUDE.md`, `tasks/reference/architecture.md` (twice) and
  `tasks/reference/crush-capabilities.md` said fourteen, and `architecture.md` never listed the two
  powernap LSP bugfix patches or `crush-context-debug.patch`. All four places now say seventeen, and
  both `architecture.md` lists name the three.
- `CRUSH_LSP_ASYNC` (read by `client/entrypoint/03-build-crush.sh`, default 1) could not be set from
  `make`. It is now `CRUSH_LSP_ASYNC ?= 1` in `client/Makefile`, passed as a `--build-arg`, declared
  `ARG CRUSH_LSP_ASYNC=1` in `client/Dockerfile` (1 even for a bare `podman build`, since these are
  fixes) and passed to the script; the script's comment no longer says "not plumbed via the
  Makefile".

The sweep's combination count (42) changes when the sweep covers all 17 patches; that is
`tasks/egress-sweep-coverage.md`.

## Verification

`make -n image` passes `CRUSH_LSP_ASYNC=1`; `make -n image CRUSH_LSP_ASYNC=0` passes 0. The image
build itself is verified with the batch's client `make image`.
