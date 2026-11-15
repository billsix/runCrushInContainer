# Fix the open tasks' headers (BLUF, Context, blocked status)

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 6
**Difficulty:** 1
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §9.3 F19

## BLUF

Eleven open tasks lack BLUF/Context, gated tasks are filed `proposed` with no `Blocked on`/`Recheck`, and a few headers contradict their bodies. Done means every open task has BLUF + Context and every gated one is `blocked` with both fields.

## Context

- §9.3 lists the tasks.

## Plan

1. Add BLUF/Context to each; set gated tasks to `blocked`.
2. Fix `bump-crush-to-v0.90.0`'s Status and `verify-vendor-pulls-all-quants`'s answered question.
