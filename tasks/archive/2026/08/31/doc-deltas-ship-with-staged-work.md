# Doc deltas ship with staged work — reconcile always-read docs per unit, not only at session end

**Status:** DONE — implemented and archived 2026-08-31 (go-ahead given the same day); the ported
conventions carry the amended wording, condensed to this file's style.
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-08-31 (William Emerison Six <billsix@gmail.com>)
**Sibling:** runClaudeInContainer `tasks/archive/2026/08/31/doc-deltas-ship-with-staged-work.md` —
the ORIGIN copy, carrying the full context/decision record.

## BLUF

Amend this repo's ported cross-project conventions
(`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`) the same way as runClaudeInContainer's:
**reconciling the always-read docs (project CLAUDE.md / README / pertinent reference doc) becomes
part of finishing a unit of work, triggered at the existing staging moment** ("stage finished
work automatically") — the doc deltas a unit implies are updated and staged in the same handoff.
The session-end sweep stays, **demoted to a verification net** expected to find nothing from
finished units. Done means this file's two sections carry the amended wording.

## Context

Read the sibling task in runClaudeInContainer for the full origin story (a 2026-08-31 gacalc
session whose end-sweep did doc updates knowable at unit completion) and the three settled
decisions (trigger = staging moment, not archive-only; scope = the docs the unit conceptually
touches, full re-read stays at session end; apply to both repos). This repo's conventions file
was ported from runClaudeInContainer's (see `tasks/port-runclaude-conventions-systems.md`), so
the same two sections exist here:

## Edit points (`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`)

1. **"Git: I commit, you don't — but you DO stage"** (~line 57) — extend the "stage finished
   work" guidance: staging a finished unit INCLUDES the always-read-doc deltas it implies.
2. **"Ending a session — sweep the always-read docs"** (~line 207) — reword as a verification
   pass expected to find nothing from properly-finished units; still catches
   conversation-only decisions, cross-repo drift, and mid-session redesigns. Cross-reference
   the staging rule.
3. Mirror the exact wording the sibling task lands in runClaudeInContainer, adjusted only for
   this port's local naming.

## Open questions

None — design settled; the remaining gate is the maintainer's go-ahead to make the edits.
