# Fix checksum.py's edge cases and make serve fail closed

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §4.2, §5.2, §6.1 F12

## BLUF

`server/tools/checksum.py` exits 0 when `write` skips a missing file, crashes on two inputs, and `make serve` lets a model through on an empty manifest. Done means each case exits non-zero with a message, `serve` refuses an unpinned model, and doctests cover the cases.

## Context

- §4.2: `cmd_write` status never set; `verify --quarantine` with no files → `IndexError`; a manifest line missing an algorithm → `KeyError`.
- §5.2: `server/Makefile:305` runs `verify --warn-unpinned`; all five models are pinned now.

## Plan

1. Fix the three cases; add doctests.
2. Drop `--warn-unpinned` from `serve` (keep it where unpinned is expected, if anywhere).
3. ruff, ty, annotations clean.
