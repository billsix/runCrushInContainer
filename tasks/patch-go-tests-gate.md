# Run the patches' Go tests in a gate

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 5
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §6.1 F14

## BLUF

The patches add Go tests (`at_import_test.go`, two `history_test.go`, `session_busy_test.go`) that pass but are never run. Done means a gate runs them against the patched tree.

## Context

- `client/entrypoint/03-build-crush.sh` only builds; the sweep only builds.

## Plan

1. Add `go test` of the patched packages to the sweep's default combination (offline, vendored).
2. Document it next to the sweep.
