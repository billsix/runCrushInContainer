# Make Crush's Up-arrow recall the LAST prompt, the way bash does

**Status:** **DONE 2026-09-09.** Delivered by `client/patches/crush-shell-history.patch`
(flag `CRUSH_SHELL_HISTORY`, on by default), which carries all three history tasks — they turned
out to be one change to one subsystem. Verified: the patch applies to a pristine v0.89.0 clone
with the build script's own `git apply --unidiff-zero`, `go build ./...` is clean, and
`go test ./internal/ui/... ./internal/db/...` passes.
**How it all works:** `tasks/reference/crush-prompt-history.md`.
**Priority:** 3
**Difficulty:** 4

## BLUF

Pressing Up in Crush's editor recalls the prompt *before* the one you just sent, not the one you
just sent — so the maintainer's first Up lands on what he thinks of as "two commands ago". Two
independent defects in Crush v0.89.0 (the pinned `CRUSH_TAG`) cause it, and neither is fixed
upstream, so a bump will not remove the need for this patch. Done = a
`client/patches/crush-shell-history.patch`, applied **by default**, after which the first Up
recalls the last submitted prompt and repeated Ups walk strictly backwards in submission order.

## Context (read first)

- **How patching works here:** `client/entrypoint/03-build-crush.sh` clones `CRUSH_TAG`, applies
  each `client/patches/*.patch` under its own flag with `git apply --unidiff-zero`, then builds
  offline from `vendor/`. Read that script's header before adding a patch — it explains why the
  build is from source at all, and the flag-per-decision convention.
- **The precedent for a *feature* patch (as opposed to the egress ones) is `CRUSH_AT_IMPORT`:**
  `client/Makefile:38-45` defaults it to `1` (the maintainer wants the feature) while
  `03-build-crush.sh` defaults it to `0` (a bare `podman build` stays stock). Follow that shape.
  Its work record is `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`, and the parity
  follow-up is `tasks/crush-at-import-parity.md`.
- **Every patch must be re-verified on a `CRUSH_TAG` bump** — see `tasks/bump-crush-to-v0.90.0.md`,
  which is the open bump task; this patch will need rebasing there too.
- Every line number below is **v0.89.0**. Anchor on the symbol names, not the numbers, so a bump
  is a re-anchor rather than a re-derivation.

## Root cause 1 — the history is reloaded from SQLite *before* the new prompt is written

This is the one that produces the reported symptom, and it is not a subtle race; the reload
essentially always loses.

- `internal/ui/model/ui.go:2593` submits with
  `return tea.Batch(m.sendMessage(value, attachments...), m.loadPromptHistory())`. `tea.Batch`
  runs its commands **concurrently**.
- `sendMessage` (`ui.go:4082`) does not write the message. It calls
  `m.com.Workspace.AgentRun(...)`, which is fire-and-forget in **both** workspace modes:
  `AppWorkspace.AgentRun` (`internal/workspace/app_workspace.go:106`) hands off to the agent
  coordinator, and `ClientWorkspace.AgentRun` (`internal/workspace/client_workspace.go:226`) POSTs
  and returns on HTTP 202. The `messages` row is inserted by the agent side *after* acceptance —
  its own comment says "AgentRun is fire-and-forget: it returns once the prompt has been accepted".
- `loadPromptHistory` (`internal/ui/model/history.go:19`) issues its `SELECT` immediately, in the
  sibling goroutine. It therefore returns the list **without** the prompt just submitted.
- `promptHistoryLoadedMsg` (`ui.go:839-842`) then replaces `m.promptHistory.messages` wholesale and
  resets `index`/`draft`.

Net effect: for the rest of the session, `messages[0]` is the prompt *before* the last one, so the
first Up skips one. It does not self-correct, because the only other reloads are at startup
(`ui.go:521`), after a `!shell` command finishes (`ui.go:1313`), and on a new session
(`ui.go:4689`).

The navigation logic itself is **correct** and needs no change: `historyPrev`
(`internal/ui/model/history.go:139`) treats index `-1` as the live draft and index `0` as the most
recent entry, which matches the queries' `DESC` ordering.

## Root cause 2 — same-second prompts come back in arbitrary order

This explains "or more", and it bites hardest on `!shell` commands fired back to back.

- `CreateMessage` (`internal/db/sql/messages.sql:24`) stamps `created_at` with
  `strftime('%s', 'now')` — whole **seconds** — even though the schema comment at
  `internal/db/migrations/20250424200609_initial.sql:53` says "Unix timestamp in milliseconds".
- Both history queries order by `created_at DESC` with **no tiebreaker**
  (`listAllUserMessages` and `listUserMessagesBySession`, `internal/db/sql/messages.sql`), so any
  two user messages created in the same wall-clock second are returned in an order SQLite does not
  define — in practice index/rowid order, i.e. the *older* of the pair first.
- **`id` cannot be the tiebreak:** message ids are UUIDv4 (`internal/message/message.go:178`),
  random, not time-sortable. `rowid` can: no migration declares `WITHOUT ROWID`, so `messages` is
  an ordinary rowid table and rowid rises with insertion.

## The patch

Three edits. The first is the fix; the second is root cause 2; the third is hardening.

**1. Record the submitted prompt in memory instead of re-reading the database.** Add to
`internal/ui/model/history.go`:

```go
// historyPush records a just-submitted prompt at the front of the in-memory
// history, so the next Up recalls it the way a shell does.  Reloading from the
// database cannot do this at submit time: the row is written asynchronously by
// the agent run, so a SELECT issued alongside the submit returns a list that
// does not contain the prompt yet.
func (m *UI) historyPush(text string) {
	m.historyReset()
	if text == "" {
		return
	}
	if len(m.promptHistory.messages) > 0 && m.promptHistory.messages[0] == text {
		return // consecutive duplicate, as bash under HISTCONTROL=ignoredups
	}
	m.promptHistory.messages = append([]string{text}, m.promptHistory.messages...)
}
```

Then at the submit site (`ui.go:2591-2593`) replace `m.historyReset()` with
`m.historyPush(value)` and drop the racing reload, so it returns
`m.sendMessage(value, attachments...)` alone. Do the same in the bang-mode branch
(`ui.go:2580`): `m.historyReset()` becomes `m.historyPush("!" + value)`, which is the form
`loadPromptHistory` itself stores shell commands in (`history.go:40`) — that branch currently
records nothing at all until the command finishes.

**2. Break the tie by insertion order.** In `internal/db/sql/messages.sql`, both user-message
queries become `ORDER BY created_at DESC, rowid DESC`. **The queries are sqlc-generated and the
build does not run sqlc**, so the patch must edit the generated
`internal/db/messages.sql.go` (the `listAllUserMessages` and `listUserMessagesBySession` string
constants) as well as the `.sql` source — otherwise the change compiles and does nothing.

**3. Don't yank the list out from under an in-progress browse.** `promptHistoryLoadedMsg`
(`ui.go:839`) currently replaces `messages` and resets `index`/`draft` unconditionally, so a
reload arriving while the user is scrolling history drops them back to the draft. Skip the update
when `m.promptHistory.index >= 0`; the next reload will land. This is a pre-existing wart, not
something the other two edits introduce — include it or drop it as a separate call.

## Verification

- `go test ./internal/ui/model/` — extend `internal/ui/model/history_test.go`, which already has a
  `newTestUI()` seam and a `historyWorkspace` stub (`TestHistoryBangCommandStripsPrefixWhileAlreadyInBangMode`
  is the model to copy). A test that pushes a prompt and asserts the first `historyPrev()` returns
  it fails before the patch and passes after.
- `make image` at the pinned tag with the new flag on and off; both must build.
- **Manual, and only the maintainer can do it:** send three distinct prompts, press Up once, and
  confirm the third one comes back; press Up twice more and confirm strictly-backwards order. Then
  the same with three `!echo one` / `!echo two` / `!echo three` shell commands in quick succession,
  which is the case root cause 2 breaks.
- **Confirming root cause 2 on real data, one query** (this sandbox has no Crush database, so it
  was reasoned from the source rather than measured):

  ```sh
  sqlite3 ~/.local/share/crush/crush.db \
    "SELECT created_at, COUNT(*) FROM messages WHERE role='user'
     GROUP BY created_at HAVING COUNT(*) > 1 ORDER BY created_at DESC LIMIT 10;"
  ```

  Any row returned is a set of prompts whose relative order is currently arbitrary.

## Wiring

Following `CRUSH_AT_IMPORT`: a new `CRUSH_SHELL_HISTORY` flag, `?= 1` in `client/Makefile` (on by
default, which is what was asked for) and `:-0` in `client/entrypoint/03-build-crush.sh` (so a bare
`podman build` stays stock), guarding `client/patches/crush-shell-history.patch` in the
`apply_patch` list. Document it in the script's env block and the Makefile flag block, and add it
to `README.md` wherever the other flags are listed.

## Open questions

1. **Ship root cause 2's ordering fix in the same patch, or its own?** Recommend the same patch —
   it is two lines plus the generated mirror, and a user cannot tell the two symptoms apart.
2. **Include edit 3 (the mid-browse clobber guard)?** Recommend yes; it is three lines and it is
   the difference between "Up works" and "Up works unless a shell command finishes while you are
   scrolling".
3. **Report it upstream?** Neither defect is fixed upstream, so a fix there would eventually
   remove the need for this patch. Recommend filing after it is verified locally, and keeping the
   patch either way until a release we actually pin carries the fix.


## What was done (2026-09-09)

All three edits from "The patch" above, as designed, plus a fourth found while doing it.

1. **`historyPush`** added to `internal/ui/model/history.go`, and both submit sites in `ui.go`
   switched to it — the prompt (or `"!"+command`) is recorded in memory and the racing
   `loadPromptHistory` dropped from the submit batch. Consecutive duplicates are skipped, as bash
   does under `HISTCONTROL=ignoredups`.
2. **`ORDER BY created_at DESC, rowid DESC`** in both user-message queries, in the `.sql` source
   **and** the sqlc-generated `.go` mirror.
3. **The mid-browse clobber guard** in `promptHistoryLoadedMsg`.
4. **A test double had to grow a method.** `countingWorkspace` in
   `internal/ui/model/session_busy_test.go` implemented `ListUserMessages` but not
   `ListAllUserMessages`; once history loads across sessions it hits the second, and the embedded
   interface left it nil, so `TestSessionSwitchRefreshesQueueAndBusy` panicked. The stub now
   answers both. Nothing in production was affected — every real workspace implements it — but it
   is why the patch touches a `_test.go` file.

Four tests were added to `internal/ui/model/history_test.go` covering recall-the-last-prompt,
duplicate suppression, the bang prefix, and empty submissions.

**Answers to the open questions:** (1) yes, shipped in the same patch; (2) yes, included;
(3) not yet filed upstream — the patch stands on its own and filing is optional follow-up.
