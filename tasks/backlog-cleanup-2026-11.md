# Clean up the open-task backlog the review found stale

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §9.1, §9.2 F15

## BLUF

Two nested-storage tasks are code-done and need only the maintainer's host check, one port task is superseded, and three tasks rest on overturned premises. Done means each reads true.

## Context

- §9.1: `tasks/nested-podman-host-image-store-ignored.md` (work in `e87b68a`), `tasks/nested-store-cleanup-permission-denied.md` (launchers now default `NESTED_PODMAN=1`).
- §9.2: `tasks/port-lean-image-nested-convention.md` (superseded by `MINIMAL_IMAGE`); `port-runclaude-conventions-systems.md:242`; `force-read-diversion-stack-on-session-load.md:9`; `offline-nested-podman-base-images.md`.

## Plan

1. Set both nested tasks to `blocked` with `Blocked on:`/`Recheck:` (runClaude's 2026-11-13 verification as the recheck).
2. Archive `port-lean-image-nested-convention` as superseded.
3. Fix the three premises.
