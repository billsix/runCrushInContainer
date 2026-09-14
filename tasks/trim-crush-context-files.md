# Trim the always-loaded conventions layer (Lever 2 — global, every-session context)

**Status:** parked — only the overlay split (decision 3) remains, **deferred by the maintainer
(2026-09-14)**. Done so far: **Lever 1** (per-project `CLAUDE.md` trims) across every repo
(2026-09-13/14). **Decision 2** (2026-09-14) — the five `@`-imported reference docs demoted to
triggered read-on-demand pointers in runClaude's mounted conventions (~18.5K tok/session; Crush
already did this). **Decision 1** (2026-09-14) — runClaude's conventions body condensed 134.5 KB →
49.9 KB (−63%), rationale/examples relocated verbatim into 10 new topic reference docs + `print-debugging.md`;
runCrush's baked conventions were already the lean port, so no change there.
**Only decision 3 is left** (see below), and the maintainer has put it off.

**Priority:** 8 (parked — deferred)
**Difficulty:** 3

## BLUF

Per-project `CLAUDE.md` files are now trimmed everywhere (Lever 1). Lever 2 is the **always-loaded
conventions layer** — the cross-project conventions + `@`-imported reference docs + the personal
overlay, paid on *every* turn of *every* session. Measuring both sandboxes (2026-09-14) shows this
bloat is **almost entirely runClaudeInContainer, not the Crush client** — the Crush port is already
lean. So Lever 2 is mostly a runClaude job plus the shared overlay, and it is **not a mechanical trim
like Lever 1**: it partly reverses the maintainer's deliberate "auto-load conventions so they're never
skipped" design, so it needs explicit decisions before any edit.

## The always-loaded set, measured (2026-09-14)

**runClaudeInContainer — mounted every Claude Code session (`~/.claude/`):**

| Piece | Size | ~Tok |
|---|---|---|
| conventions `CLAUDE.md` (`entrypoint/dotfiles/.claude/CLAUDE.md`) | 133,501 B | ~33.4K |
| `@`-import `llm-overused-phrases.md` | 29,341 B | ~7.3K |
| `@`-import `nested-podman-design.md` | 15,741 B | ~3.9K |
| `@`-import `claude-config-layering.md` | 12,695 B | ~3.2K |
| `@`-import `print-debugging.md` | 8,721 B | ~2.2K |
| `@`-import `sandbox-capability-map.md` | 7,203 B | ~1.8K |
| `@`-import personal overlay (host file) | 32,080 B | ~8.0K |
| **total** | **~239 KB** | **~60K/session** |

**runCrushInContainer — baked into the client, every Crush session (`~/.config/crush/`):**

| Piece | Size | ~Tok |
|---|---|---|
| baked conventions `CLAUDE.md` (the condensed port) | 27,505 B | ~6.9K |
| `@`-import personal overlay (host file) | 32,080 B | ~8.0K |
| **total** | **~60 KB** | **~15K/session** |

The Crush client is **already lean**: the port condensed the conventions to 27.5 KB (vs runClaude's
133.5 KB for the same rules) and made the reference docs **read-on-demand** (on disk at
`~/.config/crush/reference/`, not `@`-imported). So the client's only Lever-2 item is the shared
32 KB overlay. **The ~45K-tok/session excess lives in runClaude.**

## The design tension (why this is not a free win)

runClaude's size is **deliberate**: its own conventions state the `@`-imports exist so the content is
"loaded by the harness, not by my choosing" — the fix for "CLAUDE.md tells me to read X but I skip
it." Trimming Lever 2 trades that never-skipped guarantee for context savings. The Crush port already
chose the opposite (lean + read-on-demand). So Lever 2 = **bring runClaude toward the Crush model**,
which reverses a stated design choice — the maintainer's call, not a discretionary bulk edit. The
personal overlay is additionally a **host file** (personal content), so how to split it is the
maintainer's too.

## Decisions needed (each with a recommendation)

1. **✓ DONE 2026-09-14 — did (a): condensed to 49.9 KB (−63%), all rules kept inline, rationale/examples
   relocated verbatim into 10 new topic reference docs (`task-doc-conventions`, `reference-doc-conventions`,
   `communication-conventions`, `code-style-conventions`, `git-workflow-conventions`, `versioning-and-changelogs`,
   `codegen-conventions`, `nested-run-and-gates`, `shell-and-gate-scripts`, `diversion-stack-and-scope`) +
   appended to `print-debugging.md`; all 53 headings preserved. runCrush's baked conventions were already lean.**
   *(Original framing:)* **runClaude conventions `CLAUDE.md` (133.5 KB → ?).** The Crush port proves the same rules fit in
   ~27.5 KB. Recommend **(a) condense toward the port's density** — keep every *rule* inline, move
   worked-examples/rationale/history to read-on-demand reference docs — saving ~25K tok/session.
   Alt: (b) leave as-is (you want the full detail always in front of the agent).
2. **✓ DONE 2026-09-14 — the maintainer chose (a): demote ALL five with triggered pointers.** All
   five are now referenced read-on-demand at task triggers in runClaude's mounted conventions
   (`llm-overused-phrases`'s distilled list stays inline); ~18.5K tok/session removed. *(Original
   options, for the record:)* **The 5 `@`-imported reference docs (~73.7 KB / ~18K tok, runClaude only).** Recommend **(c) split**:
   keep the always-relevant `llm-overused-phrases.md` `@`-imported; demote the situational ones
   (`nested-podman-design`, `sandbox-capability-map`, `print-debugging`, `claude-config-layering`) to
   read-on-demand (matching Crush), pointed at from the conventions. Alt: (a) demote all (max saving,
   most reversal of the design) or (b) keep all auto-loaded.
3. **Personal overlay (32 KB / ~8K tok, both sandboxes — a host file).** Recommend **(a) split**:
   essentials (identity, project→URL map, standing authorizations) stay always-loaded; the long
   project-template/spec detail → a read-on-demand personal reference doc. You'd steer what counts as
   essential since it's your content. Alt: (b) leave as-is.

The Crush baked conventions need no trim (already condensed); only the overlay decision (#3) touches
the client side.

## Verification

- After edits, re-run each sandbox and confirm the always-loaded token count dropped as expected
  (Crush: `CRUSH_CONTEXT_DEBUG=1` + `grep CTXDBG .crush/logs/crush.log`; runClaude: compare the
  mounted-file sizes / the session's reported context).

## Related

- `tasks/investigate-context-bloat-geometricalgebra.md` (archived) — the diagnosis + method.
- `tasks/reference/crush-context-assembly.md` — how the system prompt is assembled; the re-measure procedure.
- Lever 1 work records: `tasks/archive/2026/09/{13,14}/trim-claude-md.md` (this repo) and the same in every project repo.
