# Make Crush's Up-arrow recall the LAST prompt, the way bash does

**Status:** complete
**Completed:** 2026-09-09

## What this did

Fixed Crush `v0.89.0`'s Up arrow, which recalled the prompt before the one just sent. Two independent
upstream defects caused it (neither fixed upstream, so a `CRUSH_TAG` bump does not remove the need).
Delivered by `client/patches/crush-shell-history.patch`, guarded by `CRUSH_SHELL_HISTORY` (`?= 1` in
`client/Makefile`, `:-0` in `client/entrypoint/03-build-crush.sh`, following the `CRUSH_AT_IMPORT`
feature-patch precedent from `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`). The same patch
carries the sibling tasks `tasks/archive/2026/09/09/crush-ctrl-r-history-search.md` and
`tasks/archive/2026/09/09/crush-history-across-sessions-and-days.md`. How it all works:
`tasks/reference/crush-prompt-history.md`. The patch must be rebased on every bump (open:
`tasks/bump-crush-to-v0.90.0.md`).

## Root causes (anchored by symbol at v0.89.0)

1. **History reloaded before the new prompt is written.** The submit site in `ui.go` returned
   `tea.Batch(m.sendMessage(...), m.loadPromptHistory())`, which runs both concurrently. `sendMessage`
   calls `Workspace.AgentRun`, fire-and-forget in both workspace modes (`AppWorkspace.AgentRun`,
   `ClientWorkspace.AgentRun`), and the `messages` row is inserted after acceptance. So
   `loadPromptHistory`'s `SELECT` returned the list without the just-sent prompt, and
   `promptHistoryLoadedMsg` replaced the in-memory list wholesale. Navigation (`historyPrev`, index
   `-1` = draft, `0` = newest) was correct.
2. **Same-second prompts in arbitrary order.** `CreateMessage` stamps `created_at` with
   `strftime('%s', 'now')` (seconds, despite the schema comment saying milliseconds), and both history
   queries ordered by `created_at DESC` with no tiebreak. `id` is UUIDv4, so not usable; `rowid` is
   (no `WITHOUT ROWID` table), rising with insertion. This was reasoned from source, not measured on a
   real database.

## What was done (2026-09-09)

1. **`historyPush`** added to `internal/ui/model/history.go` and used at both submit sites in `ui.go`:
   the prompt (or `"!"+command`, the form `loadPromptHistory` stores shell commands in) is recorded in
   memory and the racing reload dropped from the submit batch. Consecutive duplicates are skipped, as
   bash does under `HISTCONTROL=ignoredups`.
2. **`ORDER BY created_at DESC, rowid DESC`** in both user-message queries, in
   `internal/db/sql/messages.sql` and the sqlc-generated `internal/db/messages.sql.go` (the build does
   not run sqlc, so editing only the `.sql` would compile and do nothing).
3. **Mid-browse clobber guard** in `promptHistoryLoadedMsg`: a reload arriving while the user scrolls
   history no longer drops them back to the draft.
4. **Test double extended.** `countingWorkspace` in `internal/ui/model/session_busy_test.go` lacked
   `ListAllUserMessages`; once history loaded across sessions, `TestSessionSwitchRefreshesQueueAndBusy`
   panicked on the nil embedded method. The stub now answers both; production was unaffected.

Four tests were added to `internal/ui/model/history_test.go`: recall-the-last-prompt, duplicate
suppression, the bang prefix, and empty submissions.

### Bug in the first cut, reported by the maintainer and fixed the same day

After relaunching Crush, Up did nothing until one prompt was submitted. Cause: edit 3's guard read
`promptHistory.index`, which was never initialized, so its Go zero value `0` (meaning "on the newest
entry") looked like mid-browse and the startup history load was discarded until `historyReset()` set
`-1`. Fix: initialize `ui.promptHistory.index = -1` at construction (with a comment), and also require
`len(m.promptHistory.messages) > 0` in the guard, which covers `newTestUI()`'s same gap.
`TestPromptHistoryLoadedIsAcceptedOnAFreshUI` (verified to fail without the fix) and
`TestPromptHistoryLoadedIsSkippedWhileBrowsing` pin both halves. Lesson: a `-1` sentinel in a field
left at its zero value is a trap, because `0` is a valid-looking state.

## Decisions

1. The ordering fix shipped in the same patch: two lines plus the generated mirror, and a user cannot
   tell the two symptoms apart.
2. Edit 3 was included: it is the difference between "Up works" and "Up works unless a shell command
   finishes while you scroll".
3. Not filed upstream; filing is optional, and the patch stays until a pinned release carries a fix.

## Verification

The patch applies to a pristine v0.89.0 clone with the build script's `git apply --unidiff-zero`,
`go build ./...` is clean, and `go test ./internal/ui/... ./internal/db/...` passes. The manual
check (three prompts and three quick `!echo` commands recalled strictly backwards) was the
maintainer's; the relaunch bug above came from it, and the result after the fix is not recorded.
