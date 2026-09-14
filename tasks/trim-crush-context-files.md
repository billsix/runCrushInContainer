# Trim the always-loaded Crush context files (~33K tok/turn on geometricalgebra)

**Status:** proposed — needs go-ahead
**Priority:** 3
**Difficulty:** 3

## BLUF

The context-bloat investigation (`tasks/investigate-context-bloat-geometricalgebra.md`) measured that
**two always-loaded context files are 84% (~33.5K tok) of Crush's first-turn system prompt** on
geometricalgebra: the project's own `/work/CLAUDE.md` (18.7K tok) and the global
`/root/.config/crush/CLAUDE.md` (14.8K tok, of which ~8K is the personal overlay `@`-imported in).
Because a CLAUDE.md is spliced into the system prompt on **every** turn, trimming these cuts context
cost for the whole session, every session. This task is the trim; it needs a go-ahead and a decision
on how far to cut each file.

## Context — read first

- `tasks/investigate-context-bloat-geometricalgebra.md` — the diagnosis (measured breakdown table).
- `tasks/reference/crush-context-assembly.md` — how Crush assembles the system prompt; how to
  re-measure with `CRUSH_CONTEXT_DEBUG=1` and read the CTXDBG log.
- The maintainer's own convention (mounted `CLAUDE.md` → "A project's README is commands-forward"
  and the task/reference-doc split): **CLAUDE.md stays lean; detail goes to `tasks/reference/`.** A
  75 KB project CLAUDE.md is the anti-pattern that convention exists to prevent.

## The two levers (measured)

1. **geometricalgebra `/work/CLAUDE.md` — 74,732 B ≈ 18,683 tok (47% of the system prompt).** Biggest
   win, and it's this project's own file — trimming it does not touch the shared conventions. Push its
   detail into `geometricalgebra/tasks/reference/` and leave a lean CLAUDE.md that points there.
   **Note:** geometricalgebra is a separate repo (`github.com/billsix/geometricalgebra`); this edit
   happens there, not in runCrushInContainer. Halving it saves ~9K tok/turn.
2. **Global `/root/.config/crush/CLAUDE.md` — 59,146 B ≈ 14,787 tok (37%).** = 27 KB baked
   cross-project conventions + 32 KB personal overlay pulled in by the `@`-import. Options: trim the
   baked conventions body; and/or stop `@`-importing the *entire* personal overlay into the
   always-loaded file (e.g. split the overlay so only the essential part is always-loaded). This is a
   cross-project change (affects every Crush session), so it needs an explicit decision.

## Open questions (for the maintainer)

1. **Scope — which lever(s) to pull?** Recommend **(a) geometricalgebra's `/work/CLAUDE.md` first**
   (biggest, self-contained, no shared-conventions risk); optionally **(b) also the global/overlay**
   as a second pass. Or (c) both now. Which?
2. **How lean for the project CLAUDE.md?** A target helps — e.g. "≤ ~20 KB, push the rest to
   `tasks/reference/`". What budget do you want?

## Verification

- Re-run `CRUSH_CONTEXT_DEBUG=1` against geometricalgebra and confirm the CTXDBG `context-files-total`
  and `system-prompt-total` dropped by the expected amount; report before/after.

## Related

- `tasks/investigate-context-bloat-geometricalgebra.md` — the diagnosis this implements.
- `tasks/reference/crush-context-assembly.md` — mechanism + the re-measure procedure.
