# Force the diversion stack to load at session start (mirror the runClaude fix)

**Status:** proposed — needs go-ahead (do NOT implement yet; maintainer, 2026-09-04)
**Priority:** 4
**Difficulty:** 2

## BLUF

The global diversion stack (`~/.config/crush/stack.md`) is **mounted and referenced** in the
Crush client but is **not force-loaded** at session start, so — exactly as happened in
runClaudeInContainer — it silently drifts out of sync with the actual work and nobody notices.
Wire it to be **force-read every session**, mirroring the fix just made in runClaudeInContainer
(there, an `@`-import of `~/.claude/stack.md` + a Makefile seed + a strengthened "reconcile at
session start" directive). In Crush the natural mechanism is a **second `crushrc`
`global-context-path`** (Crush's native always-load — the non-`@` force-read), or an `@`-import
in the baked `CLAUDE.md` (the vendored patch supports it). The one real consideration is the
local model's tight context window. **Feasibility/decision task — don't implement until the
mechanism is chosen.**

## Context (read first)

- **Prior art on the Claude side (the thing to mirror):** runClaudeInContainer, 2026-09-04 — the
  shared `CLAUDE.md` now `@`-imports `~/.claude/stack.md`, the Makefile seeds a starter `stack.md`
  if absent (so the import never dangles), and the "diversion trail" section gained a **"reconcile
  the stack at session start"** directive. Root cause it fixed: the stack convention said the
  agent keeps the stack current unprompted, but nothing forced the stack into context, so it
  drifted. (Same failure just observed on the Claude side.)
- **What already exists here** (`tasks/port-runclaude-conventions-systems.md` › P2.3, 2026-08-21):
  the stack is a **mounted host path** — host `~/.config/crush/stack.md` → container
  `/root/.config/crush/stack.md`, unconditional `mkdir`/`touch` in the Makefile so it survives
  `--rm`. The conventions body (the diversion-trail section) is ported and **references** that
  path. **What's missing is only the force-READ** — the file is present but not loaded into
  context automatically, so the agent must *remember* to open it (the exact reliance that fails).
- **Crush's force-read mechanisms (two, both available):**
  1. **Native `global-context-path`** (crushrc) — `client/entrypoint/crushrc:22` already sets
     `option global-context-path /root/.config/crush/CLAUDE.md`; a file registered this way is
     always loaded. Adding a **second** line for the stack is the native, non-`@` force-read (and
     is likely what "a way to force files read, not via @" referred to).
  2. **`@`-import** inside the baked `CLAUDE.md` — the vendored Crush patch
     (`client/patches/crush-at-import.patch`, see `tasks/crush-at-import-parity.md`) supports it;
     the client CLAUDE.md already `@`-imports the personal overlay
     (`.../crush/CLAUDE.md:275`). So `@~/.config/crush/stack.md` would also work.
- **The one real tension — local-model context budget.** P1.2 (same port task) deliberately kept
  the heavy reference docs **baked-but-referenced-on-demand, NOT force-loaded**, because the local
  server window is small (32k, raised to 64k) and force-loading everything overflowed it. The
  stack is different in kind — it's a **small breadcrumb trail** (points at task docs, never a
  task log), so force-loading it should cost little — but the budget must be respected, and the
  "keep the stack SMALL" rule matters more here than on the Claude side.

## The edits to make (once the mechanism is chosen — cold-executable)

**Recommended: option 1 (native `global-context-path`)** — no dependency on the patch, keeps the
live-state stack as its own registered context file (cleanly separate from the conventions doc),
and matches the maintainer's "non-`@`" intuition.

1. `client/entrypoint/crushrc` — add, after line 22:
   `option global-context-path /root/.config/crush/stack.md`
2. Confirm the Makefile still seeds/mounts `~/.config/crush/stack.md` (P2.3) so the path always
   exists — and seed it with a **starter template** if it's currently just `touch`ed empty, so a
   force-read of an empty file isn't confusing (mirror runClaude's seeded
   `# Work stack\n\nRead BOTTOM-up: …\nEmpty for now.`).
3. `client/entrypoint/dotfiles/.config/crush/CLAUDE.md` — in the diversion-trail section, mirror
   runClaude's strengthened directive: the stack is now force-loaded, so **at session start check
   it against reality and reconcile it before other work**; a stale "live thread" is a visible
   failure. (Keep it lean — this is the tight-window client.)

*(Alternative: option 2 — add `@~/.config/crush/stack.md` to the baked CLAUDE.md instead of a
second global-context-path. Functionally equivalent; less clean separation of live-state from
conventions.)*

## Verification (when implemented)

- `make image` bakes the crushrc/CLAUDE.md changes (custom context takes effect only after a
  rebuild — same as the slash-commands note in the port task).
- Start a session and confirm the stack contents are in the model's context (a `crush run` /
  `processFile`-style check, as used to verify the `@`-import port).
- Watch the **token budget**: confirm the always-loaded set (lean CLAUDE.md + personal overlay +
  stack) still fits the 64k window with room for real work (the P1.2 overflow lesson).

## Open questions

1. **Mechanism:** native second `global-context-path` (recommended) vs `@`-import in CLAUDE.md?
   *(Recommend the native `global-context-path` — no patch dependency, clean separation.)*
2. **Shared vs per-agent stack:** the diversion stack is meant to be *global across repos*. Should
   the runCrush client and the runClaude sandbox **share one host stack file** (bind the same host
   path into both, so diversions are visible across agents), or keep separate stacks
   (`~/.claude/stack.md` vs `~/.config/crush/stack.md`)? *(Your call — separate is simplest and is
   the current state; sharing is a bigger, cross-tool decision.)*
3. **Budget check:** confirm force-loading the stack is acceptable within the local model's 64k
   window before committing (it should be — the stack is small — but the P1.2 overflow makes this
   worth an explicit check).

## Related

- `tasks/port-runclaude-conventions-systems.md` — P2.3 mounted/seeded the stack + ported the
  diversion-trail convention; this task closes its **force-read** gap.
- `tasks/crush-at-import-parity.md` — the `@`-import patch (option 2's mechanism).
- runClaudeInContainer (2026-09-04): the mirror change — `@`-import of `~/.claude/stack.md` +
  Makefile seed + strengthened session-start reconciliation directive in the shared `CLAUDE.md`.
