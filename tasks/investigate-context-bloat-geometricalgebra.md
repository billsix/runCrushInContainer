# Investigate first-query context bloat on geometricalgebra (~48K tokens)

**Status:** proposed — needs go-ahead (investigation)
**Priority:** 3
**Difficulty:** 3

## BLUF

Running the Crush client against `geometricalgebra`, the **first** query already consumes ~70%+ of the
context window (~48K tokens) before the model does much. The maintainer suspects the `CRUSH_AT_IMPORT`
patch (recursive `@path` autoloading of context files), or geometricalgebra's many `tasks/` /
`tasks/reference/` docs being loaded, or something LSP-related. **The task is to find out exactly what
is filling the context on the first turn and report it** (then decide whether/how to trim). Diagnosis
only — no fix without a follow-up decision.

## Context — what to read / how it plausibly happens

- **The `@`-import autoload patch:** `client/patches/crush-at-import.patch` +
  `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`. It makes a bare `@path` line in a context
  file (CLAUDE.md/AGENTS.md/CRUSH.md) recursively splice that file's contents in. Recursion is the
  prime suspect: one `@`-import can pull in a whole tree.
- **The baked global context:** `client/entrypoint/crushrc` sets
  `option global-context-path /root/.config/crush/CLAUDE.md`. That baked conventions file (and anything
  it `@`-imports — reference docs, the personal overlay) is spliced into every session's system prompt.
  Check how large the baked `~/.config/crush/CLAUDE.md` is and what it `@`-imports
  (`client/entrypoint/dotfiles/.config/crush/CLAUDE.md` + its `reference/` twins).
- **The mounted project's own context:** geometricalgebra's `/work/CLAUDE.md` auto-loads *on top* of
  the global one, and geometricalgebra has an extensive `CLAUDE.md` plus many `tasks/` and
  `tasks/reference/` docs. If its `CLAUDE.md` `@`-imports reference docs (or the patch recurses into
  them), that compounds.
- **LSP angle (lower likelihood):** with the language servers now working, check whether diagnostics or
  symbol data are being injected into the prompt. Less likely to be 48K, but rule it out.

## Plan

- Measure the first-turn context composition: what files/sections are spliced in and their token
  cost. Options: run the client with a debug/verbose that dumps the assembled system prompt, or count
  the bytes of the global-context file + its transitive `@`-imports + geometricalgebra's `/work/CLAUDE.md`
  + its imports. Attribute the ~48K to specific sources.
- Determine whether the `@`-import recursion is pulling in more than intended (e.g. the whole
  `tasks/reference/` set, or archived tasks).
- Report the breakdown (biggest contributors first) and options to trim (e.g. stop `@`-importing large
  reference docs into the always-loaded file; scope what geometricalgebra's `/work/CLAUDE.md` loads).

## Open questions (for the maintainer)

- None blocking — this is a diagnosis. It will likely spawn a follow-up "trim the context" task once the
  culprit is known.

## Related

- `client/patches/crush-at-import.patch` — the autoload mechanism under suspicion.
- `tasks/reference/crush-capabilities.md` (context/model behavior), the baked
  `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`.
