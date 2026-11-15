# Doc deltas ship with staged work — reconcile always-read docs per unit, not only at session end

**Status:** complete
**Completed:** 2026-08-31
**Created:** 2026-08-31 (William Emerison Six <billsix@gmail.com>)
**Sibling:** runClaudeInContainer `tasks/archive/2026/08/31/doc-deltas-ship-with-staged-work.md` —
the origin copy, carrying the full context and decision record.

## What this did

Amended this repo's ported cross-project conventions
(`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`) to match runClaudeInContainer's: reconciling
the always-read docs (project `CLAUDE.md`, `README`, the pertinent reference doc) became part of
finishing a unit of work, done at the existing staging moment, so a unit's doc deltas are updated
and staged in the same handoff. The session-end sweep was kept but demoted to a verification net
expected to find nothing from finished units. The go-ahead was given the same day.

## Changes

Both edits were in `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, mirroring the sibling's
wording condensed to this file's style:

1. **"Git: I commit, you don't — but you DO stage"**: staging a finished unit includes the
   always-read-doc deltas it implies.
2. **"Ending a session — sweep the always-read docs"**: reworded as a verification pass that still
   catches conversation-only decisions, cross-repo drift and mid-session redesigns, cross-referencing
   the staging rule.

## Decisions (settled in the sibling task)

- Trigger is the staging moment, not archive time only.
- Scope is the docs the unit conceptually touches; the full re-read stays at session end.
- Applied to both repos (this conventions file was ported from runClaudeInContainer's, see
  `tasks/port-runclaude-conventions-systems.md`).
