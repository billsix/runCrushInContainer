# Make the egress sweep cover the image that ships

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 2
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §5.1, §5.3 F5

## BLUF

`tools/sweep_egress_patch_combos.py` lists 14 of the 17 patches; two missing ones are on by default, so its "audit-default" combination is not the shipped image. Its patches can also silently not apply. Done means the sweep's sets match `03-build-crush.sh`, it fails when they drift, and it fails instead of passing when patches do not apply.

## Context

- `ALL`/`DEFAULT` at `tools/sweep_egress_patch_combos.py:53-85`; missing `crush-lsp-async.patch`, `crush-lsp-router-notif.patch` (default on, `client/entrypoint/03-build-crush.sh:106`) and `crush-context-debug.patch`.
- The two LSP patches lack `diff --git` headers, so `touched_files()` misses them.
- §5.3: without `client/vendor/crush/.git`, `git apply` silently skips (rc=0).

## Plan

1. Add the three patches in build order; the two LSP ones to `DEFAULT`.
2. Regenerate the LSP patches with `git diff` headers (verify they apply and reverse).
3. Assert `set(ALL) == patch dir` and that `client/vendor/crush/.git` exists.
4. Run `--list`; update the combination count in `architecture.md`.
