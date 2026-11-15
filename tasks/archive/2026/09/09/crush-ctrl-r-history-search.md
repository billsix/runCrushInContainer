# Give Crush a bash-style Ctrl-R reverse history search

**Status:** complete
**Completed:** 2026-09-09

## What this did

Crush `v0.89.0` had no history search (only Up and Down). Added a `ctrl+r` history-search dialog,
on by default, delivered by `client/patches/crush-shell-history.patch` (flag `CRUSH_SHELL_HISTORY`:
`?= 1` in `client/Makefile`, `:-0` in `client/entrypoint/03-build-crush.sh`). That one patch carries
all three history tasks, which turned out to be one change to one subsystem; the siblings are
`tasks/archive/2026/09/09/crush-up-arrow-skips-last-prompt.md` and
`tasks/archive/2026/09/09/crush-history-across-sessions-and-days.md`. How it all works:
`tasks/reference/crush-prompt-history.md`.

## Decisions

1. **Key collision: `ctrl+r` made conditional** (option (a) of three). Upstream binds `ctrl+r` as the
   attachment-delete prefix (`AttachmentDeleteMode` in `internal/ui/model/keys.go`): `ctrl+r+{i}`
   deletes attachment *i*, `ctrl+r+r` all. The patch routes `ctrl+r` to history search only when no
   attachments are pending. Rejected: (b) moving attachment-delete to another prefix (changes a
   documented upstream binding, could surprise on a bump) and (c) a different key (not what was asked).
2. **Design A, a filtered picker dialog**, over Design B, a literal inline `(reverse-i-search)` prompt.
   Reason: patch maintenance. A patch that adds a file rebases across `CRUSH_TAG` bumps far more easily
   than one editing `ui.go`'s key routing, and B is materially more code in the files upstream changes
   most. B was left as a possible follow-up; it was not done.
3. **The cross-session change shipped in the same patch**, so search covers the whole project's
   history (searching one session's prompts is not what `Ctrl-R` is for).

## What was built (2026-09-09)

- New `internal/ui/dialog/history.go`: a `History` dialog and `HistoryItem` on `list.FilterableList`
  with the shared `renderItem`/`RenderContext` helpers, so it behaves like the sessions and commands
  pickers. Typing filters fuzzily; `enter` (or `tab`/`ctrl+y`) inserts the entry into the editor
  unsent; `esc` closes; `ctrl+r` inside the dialog moves to the next match, bash-style.
- `ui.go` checks `len(m.attachments.List()) == 0` before the key reaches the attachments component
  (which claims it otherwise). Both editor help blocks advertise `ctrl+r  search history` under the
  same condition, so hint and behaviour cannot disagree.
- The dialog reads `m.promptHistory.messages`, not the database, so it cannot disagree with Up and
  needs no query of its own.
- A list row is one line, so a multi-line prompt is flattened for display while `Text()` returns the
  original; otherwise recalling would silently rewrite it. Two tests in
  `internal/ui/dialog/history_test.go` cover that and the bang prefix.

## Verification

The patch applies to a pristine v0.89.0 clone with the build script's own `git apply --unidiff-zero`,
`go build ./...` is clean, and `go test ./internal/ui/... ./internal/db/...` passes. The manual check
(search a fragment, accept, confirm it lands unsent; repeat with an attachment pending) was the
maintainer's to do; its result is not recorded here.
