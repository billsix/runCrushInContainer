# Mirror the shared C dispatch checker

**Status:** in progress (branch `shared-dispatch-checker`, stacked on `c-dispatch-rules`)
**Priority:** 4
**Difficulty:** 1
**Created:** 2026-11-11 (William Emerison Six <billsix@gmail.com>)

## BLUF

runClaudeInContainer (github.com/billsix/runClaudeInContainer) is adding
`tasks/reference/c_dispatch_check.py`, a SHARED, VENDORED tool. It checks C code against the
"Dispatch" rules of `c-coding-standard.md`. Its task is that repo's `tasks/shared-dispatch-checker.md`.
Done means a byte-identical copy here in `tasks/reference/`, and `CLAUDE.md`'s paragraph on the
mirrored tools naming it.

## Context

- This repo mirrors runClaude's vendored tools in `tasks/reference/` (`check_local_annotations.py`,
  `update_dep_common.sh`). They are copied into downstream projects' `tools/`, not into the Crush
  client's baked reference set.
- The canonical copy is in runClaude. Edit it there and re-copy it here.
