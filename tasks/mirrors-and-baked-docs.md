# Re-sync every mirror and baked copy, and fix the layout map

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 2
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.1, §0.4, §1.3, §3.4 F4 F10

## BLUF

Re-copy the shared tools fixed in github.com/billsix/runClaudeInContainer (`tasks/archive/2026/11/15/shared-checker-gate-fixes.md`) and every drifted mirror, re-sync the stale baked copies, bake the two docs the baked standards cite (maintainer decision 2026-11-15), and bring `container-file-layout.md` up to date. Done means every claimed mirror `cmp`s clean and the layout map matches the Dockerfile and Makefile.

## Context

- §0.4: drift in `token-and-context-economy.md` (repo and baked), baked `recursive-design.md`, `rust-coding-standard.md`, `sandbox-capability-map.md`.
- §3.4: bake `doctests-by-default.md` and `code-style-conventions.md`.
- §1.3: `container-file-layout.md` lacks the `01b` COPY, the storage COPYs, the dir-store and shared-images mounts; says 27 files; table omits three.

## Plan

1. Copy the canonical files over each mirror (repo `tasks/reference/` and baked `crush/reference/`).
2. Bake the two docs (Dockerfile COPY list + layout table).
3. Fix `container-file-layout.md`; `make manifest` prints it.
4. `cmp` every claimed mirror.
