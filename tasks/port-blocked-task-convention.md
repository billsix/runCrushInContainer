# Port the blocked-task convention + `/recheck-blocked` into runCrushInContainer

**Status:** proposed — needs go-ahead. Not started.
**Priority:** 5
**Difficulty:** 3
**Started:** 2026-08-23

## Goal

Port the **blocked-task convention** and its **`/recheck-blocked`** command — just added to
runClaudeInContainer (`github.com/billsix/runClaudeInContainer`) on 2026-08-23 — into this
Crush sibling, so the two conventions systems stay in sync. A *blocked* task is one that
can't start until an **external condition** changes (an upstream tool ships a feature, a
release lands, a standard stabilizes, or the maintainer runs a hands-on verification), and it
carries a **runnable re-check** so a future session can test whether the gate has cleared
without re-deriving anything.

This is a follow-on to `tasks/port-runclaude-conventions-systems.md` (the original conventions
port) and reuses the same delivery mechanism it established.

## What to port (source: runClaudeInContainer, 2026-08-23)

Three pieces, all already written in the source repo — adapt, don't reinvent:

1. **Convention text** — a `### Blocked tasks — deferred until an external condition changes`
   subsection in the "Task documents" section of the shared `CLAUDE.md`, plus three small
   tweaks: the Priority note mentions blocked tasks; the session-start scan lists them
   separately (kept out of the easy-wins ranking); the session-end sweep reminds they exist.
   Defines `**Status:** blocked` + two header fields: **`Blocked on:`** (the condition) and
   **`Recheck:`** (a cheap runnable check + the *cleared* signal — a `WebFetch` URL + what to
   look for, a version compare with a version-aware sort, a command, or a named manual step).
   Distinguishes **blocked** (a concrete testable gate) from **parked** (subjective not-now).
2. **`recheck-blocked` command** — runs every blocked task's `Recheck:` and reports which
   gates cleared, offering to un-block and re-rate Priority. Default scope = current repo;
   `--all` sweeps every mount. Re-checking is **on demand — never automatic**.
3. **`new-task` command tweak** — a note that a task blocked on an external condition uses
   `Status: blocked` + the `Blocked on:`/`Recheck:` fields.

## Crush-specific wiring (how this repo delivers conventions + commands)

Per `tasks/port-runclaude-conventions-systems.md`:

- **Conventions** live baked at `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`
  (registered as the one `option global-context-path` in `crushrc`). Add the blocked-task
  subsection + the three tweaks there. **Mind the context budget:** that `CLAUDE.md` was
  deliberately trimmed to a **lean core (~11.5 KB / ~2.9k tokens)** to fit the local model's
  32k/64k window — keep the ported text tight (tighter than the runClaude wording if needed),
  not a verbatim copy.
- **Commands** are Crush custom-command `.md` files at
  `client/entrypoint/dotfiles/.config/crush/commands/` (currently 7). Add `recheck-blocked.md`
  as the 8th and edit `new-task.md`. They appear under the `/` dialog's **"User" tab** (press
  `Tab`) and **only after `make image`** bakes them.

## Key risk / open question (verify before relying on `/recheck-blocked` here)

- **Does the Crush client have a usable web-fetch tool, and can the local model drive it?**
  `recheck-blocked` leans on fetching a URL and reading it (runClaude uses `WebFetch`). The
  vendored Crush tool set (`client/vendor/crush/internal/`) shows no obvious `fetch`/`web`
  tool, and the client runs a **local model with a small context window** that may be weak at
  multi-step web-checking. If web-fetch isn't available or reliable, scope `Recheck:` here to
  **command-based / version-compare / manual-step** checks and say so in the command, rather
  than URL-fetch checks. Confirm the tool situation first.

## Verify

- After `make image`, `/recheck-blocked` shows under the `/` "User" tab and runs against a
  test blocked task.
- The lean `CLAUDE.md` still fits the model window (no overflow like the first conventions
  port hit — see `tasks/archive/2026/08/20/context-window-sizing.md`).
- Existing informally-"blocked" tasks in this repo (e.g. `bump-crush-to-v0.90.0.md`, noted
  "blocked on…") can adopt the new `Blocked on:`/`Recheck:` shape — do that as part of the port
  or note it as a fast-follow.

## Open questions

1. Web-fetch tooling on the Crush client — available and local-model-drivable, or should
   `Recheck:` be restricted to non-web checks here? (See "Key risk" — recommend confirming the
   tool set before wiring the command.)
2. Fold this into `port-runclaude-conventions-systems.md` (still open) as another phase, or
   keep it as this separate focused task? (Recommend: keep separate; cross-link both.)
