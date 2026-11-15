# Document all 17 patches and make CRUSH_LSP_ASYNC settable

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §1.2, §2.2 F11

## BLUF

Docs say fourteen local patches; there are 17, and three are documented only in their own reference docs. `CRUSH_LSP_ASYNC` is read by the build script but cannot be set from `make`. Done means every count and list matches `client/patches/`, and the flag threads through like the other patch flags.

## Context

- §1.2: `CLAUDE.md:96`, `architecture.md:206,367`, `crush-capabilities.md:43`; sweep count 42 → 43.
- §2.2: `client/entrypoint/03-build-crush.sh:50-64,106`.

## Plan

1. Fix the counts and add the three patches to `architecture.md`'s list.
2. Add `CRUSH_LSP_ASYNC ?= 1` to `client/Makefile`, an `ARG` in `client/Dockerfile`, pass it to the build script.
