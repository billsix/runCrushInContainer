# The patches' Go tests now run in a gate

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 5
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §6.1 F14

## What this did

The patches add Go tests (`internal/agent/prompt/at_import_test.go`,
`internal/ui/model/history_test.go`, `internal/ui/dialog/history_test.go`,
`internal/ui/model/session_busy_test.go`) that no gate ran: `03-build-crush.sh` and the sweep only
built. The egress sweep (`tools/sweep_egress_patch_combos.py`) now runs
`go test -mod=vendor` of those three packages, offline, on the shipped (DEFAULT) combination,
right after building it; a failing test aborts the sweep.

## Verification

Full sweep run 2026-11-15: `ok` for `internal/agent/prompt` (0.007s), `internal/ui/model` (0.052s)
and `internal/ui/dialog` (0.026s), then `SWEEP OK: 46 combinations`.
