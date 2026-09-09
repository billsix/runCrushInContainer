# Give Crush a bash-style Ctrl-R reverse history search

**Status:** **DONE 2026-09-09.** Delivered by `client/patches/crush-shell-history.patch`
(flag `CRUSH_SHELL_HISTORY`, on by default), which carries all three history tasks — they turned
out to be one change to one subsystem. Verified: the patch applies to a pristine v0.89.0 clone
with the build script's own `git apply --unidiff-zero`, `go build ./...` is clean, and
`go test ./internal/ui/... ./internal/db/...` passes.
**How it all works:** `tasks/reference/crush-prompt-history.md`.
**Priority:** 3
**Difficulty:** 5

## BLUF

Crush has no history search at all: the only history keys are Up and Down. Add one, reachable by a
single keystroke, on by default via a `client/patches/` patch. Done = typing a fragment finds the
matching earlier prompt and Enter puts it in the editor.

## Context (read first)

**Read `tasks/reference/crush-prompt-history.md` first** — it documents the whole subsystem (what
the history list contains, the Up/Down state machine, ordering, persistence) and §6 is the survey
this task acts on. The patch conventions are in `client/entrypoint/03-build-crush.sh`'s header and
`client/Makefile:38-45` (`CRUSH_AT_IMPORT` is the model: Makefile default `1`, script default `0`).

Two related tasks, all three touching the same code:
`tasks/crush-up-arrow-skips-last-prompt.md` (the Up-arrow off-by-one) and
`tasks/crush-history-across-sessions-and-days.md` (history scoped to one session). **Search is
worth little until that second one is fixed** — searching a single session's prompts is not what
`Ctrl-R` is for. Recommend landing that one first.

## The two blockers found

1. **`ctrl+r` is already bound.** It is the editor's attachment-delete prefix
   (`AttachmentDeleteMode`, `internal/ui/model/keys.go:141-144`): `ctrl+r+{i}` deletes attachment
   *i*, `ctrl+r+r` deletes all. It is only *advertised* when attachments exist (`ui.go:3254`) but
   it is bound unconditionally. Options, in the order I'd try them:
   - **(a)** Make `ctrl+r` conditional — attachment-delete when attachments exist, history search
     otherwise. One `if`, no relearning, and the collision is invisible in practice since you
     rarely search with attachments pending. Slightly magic.
   - **(b)** Move attachment-delete to another prefix and give `ctrl+r` to search outright.
     Cleanest semantics, but it changes a documented upstream binding, so a bump could surprise you.
   - **(c)** Bind search to something free and leave `ctrl+r` alone. Safest, but it is not the
     thing that was asked for.

   **Recommend (a)**, with (b) as the fallback if the conditional reads badly in the help line.
2. **There is no search UI to extend** — this is net-new interaction code, which is why the
   difficulty is 5 rather than 3.

## Two designs

**Design A — a history-search dialog (recommended).** Build on `internal/ui/list.FilterableList`,
the widget the sessions, commands and models dialogs already use
(`internal/ui/dialog/sessions.go:34`). New file `internal/ui/dialog/history.go`, one entry per
history string, Enter inserts the selection into the textarea. Not literally bash — it is a filtered
picker rather than an inline incremental prompt — but it delivers the function, reuses tested
components, and matters for maintenance: **a patch that adds a file rebases across `CRUSH_TAG`
bumps far more easily than one that edits `ui.go`'s key routing**, and this patch has to be
rebased on every bump.

**Design B — a literal inline `(reverse-i-search)`.** A new editor mode: replace the prompt line
with `(reverse-i-search)\`frag': match`, `Ctrl-R` again walks to older matches, `Ctrl-G`/`Esc`
cancels restoring the draft, Enter accepts, any other key exits into the editor. This is what was
actually asked for, and it is materially more code, all of it inside the files upstream changes
most.

**Recommend A for v1**, and revisit B once it is in daily use — the honest reason is patch
maintenance, not that A is better bash.

## Verification

- `go test ./internal/ui/model/` and `./internal/ui/dialog/`; `internal/ui/model/history_test.go`
  has a `newTestUI()` seam to copy.
- `make image` with the flag on and off; both must build.
- **Manual, only the maintainer can do it:** send several distinct prompts, search a fragment that
  matches an older one, accept it, and confirm it lands in the editor unsent. Then repeat with an
  attachment pending, to exercise whichever `ctrl+r` resolution was chosen.

## Wiring

`CRUSH_HISTORY_SEARCH` — `?= 1` in `client/Makefile`, `:-0` in `client/entrypoint/03-build-crush.sh`,
guarding `client/patches/crush-history-search.patch`. Document it in both flag blocks and in
`README.md` alongside the others.

## Open questions

1. **Which `ctrl+r` resolution — (a) conditional, (b) rebind attachments, or (c) a different key?**
   Recommend (a).
2. **Design A (a filtered picker dialog) or B (a literal inline `(reverse-i-search)` prompt)?**
   Recommend A first, for patch-rebase cost, and treat B as a follow-up.
3. **Land `tasks/crush-history-across-sessions-and-days.md` before this?** Recommend yes —
   searching one session's prompts is not the feature.


## What was done (2026-09-09)

**Design A**, as recommended: a new `internal/ui/dialog/history.go` — a `History` dialog and a
`HistoryItem`, built on `list.FilterableList` and the shared `renderItem`/`RenderContext` helpers,
so it looks and behaves like the sessions and commands pickers. Typing filters fuzzily; `enter`
(or `tab`/`ctrl+y`) inserts the entry into the editor **unsent**; `esc` closes. `ctrl+r` inside the
dialog moves to the next match, so holding it walks backwards the way bash does.

**Resolution (a) for the key collision**, as recommended: `ui.go` routes `ctrl+r` to the history
dialog only when `len(m.attachments.List()) == 0`, checked **before** the key reaches the
attachments component — which claims it either way otherwise. Both editor help blocks advertise
`ctrl+r  search history` under that same condition, so the hint and the behaviour cannot disagree.

Two details worth keeping:

- **The dialog reads `m.promptHistory.messages`, not the database.** It cannot then disagree with
  what Up would show, and it needs no query of its own.
- **A list row is one line tall**, so a multi-line prompt is flattened for display while `Text()`
  returns the original — otherwise recalling an entry would silently rewrite the prompt. Two tests
  in `internal/ui/dialog/history_test.go` cover that and the bang prefix.

**Answers to the open questions:** (1) resolution (a); (2) Design A; (3) yes — the cross-session
change shipped in the same patch, so search covers the whole project's history.
