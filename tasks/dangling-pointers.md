# Repoint dangling task pointers in code, docs and the archive

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §2.3, §10.3, §0.2 F16

## BLUF

Code comments, docs and archive docs point at tasks that were archived, at paths that never existed, and one squashed SHA. Done means every in-repo path resolves (`test -e`) and every SHA resolves.

## Context

- §2.3 lists the code and doc sites; §10.3 the archive sites and SHA `5d2515f` (squashed into `0f9548f`).
- `client/Makefile:324`, `architecture.md:365` cite runClaude's archived `add-shell-exec-target.md` (cite by URL and archive path).

## Plan

1. Repoint each site.
2. Re-run the `test -e` sweep: zero misses.
