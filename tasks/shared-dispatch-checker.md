# Mirror the shared C dispatch checker

**Created:** 2026-11-11 (William Emerison Six <billsix@gmail.com>)
**Completed:** 2026-11-11
**Branch:** `shared-dispatch-checker`, stacked on `c-dispatch-rules`

## Outcome

`tasks/reference/c_dispatch_check.py` is a byte-identical mirror of runClaudeInContainer's
(github.com/billsix/runClaudeInContainer) shared checker for the C standard's Dispatch rules. Like
the canonical, it is executable. Both copies of `c-coding-standard.md` here were re-synced, since its
Dispatch section now names the tool. `CLAUDE.md` lists the tool among the mirrored ones. The
design, tests and verification are in runClaude's
`tasks/archive/2026/11/11/shared-dispatch-checker.md`.
