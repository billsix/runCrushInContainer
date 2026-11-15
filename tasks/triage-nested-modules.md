# Fix triage_dependency_egress.py's nested-module walk and tier labels

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 5
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §4.1 F13

## BLUF

`tools/triage_dependency_egress.py` scans each child module's source again under its parent, so a parent with no code of its own is reported as NETWORK. Its header and sort table also disagree with the tiers it returns. Done means each module is scanned alone and the tiers sort and read correctly.

## Context

- `scan_module`'s `os.walk(root)`; `cloud.google.com/go` reported NETWORK with 0 own `.go` files.
- `classify` returns `imports-only`/`url-strings-only`; the header says `maybe`; the `order` table lacks them.

## Plan

1. Prune child-module directories from the walk.
2. Fix the header and the order table.
3. ruff, ty, annotations clean; re-run against the vendored tree and compare.
