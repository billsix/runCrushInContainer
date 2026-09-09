# Crush's prompt history — how it is loaded, cycled, searched, and stored

**What this is:** the standing description of Crush's prompt-history subsystem — what Up and
Down actually do, what the history list contains, where it is persisted, and what it would take
to add a bash-style reverse search. Written because three separate wants (bash-like Up, `Ctrl-R`,
and history that survives closing the container) all turn out to be the same subsystem, and each
was being re-derived from scratch. Read this before touching any of them.

**Pinned to:** Crush `v0.89.0` — the `CRUSH_TAG` in `client/Makefile:22`. That is the version
this document describes. (Checked once, 2026-09-09, that none of it has been fixed upstream since,
so the patches below will still be needed after a bump; that check is not maintained here.)

**Re-sync check:** compare `client/Makefile`'s `CRUSH_TAG` to the banner above. If they differ,
`git diff v0.89.0..<newtag> -- internal/ui/model/history.go internal/db/sql/messages.sql
internal/ui/model/keys.go` and re-verify the anchors here. Line numbers rot; the symbol names
below do not.

**Upstream:** `github.com/charmbracelet/crush`. All `file:line` references are at v0.89.0.

## 1. What the history list actually is

There is no history *file*. The list is rebuilt from the SQLite database on demand by
`loadPromptHistory` (`internal/ui/model/history.go:19`), which returns a
`promptHistoryLoadedMsg` carrying a `[]string`.

Two things go into it, in this order per message:

- the message's text, `msg.Content().Text`, skipped when empty;
- one entry per shell command on the message, stored **with the bang restored** — `"!"+sc.Command`
  (`history.go:40`). That is why recalling a `!ls` puts you back in bang mode: `historyPrev` calls
  `syncBangModeFromTextarea` (`history.go:120`), which strips the `!` and flips the editor into
  bang mode.

**The list is scoped to the current session as soon as one exists** (`history.go:24-29`): with a
session it calls `ListUserMessages(sessionID)`, and only with no session at all does it call
`ListAllUserMessages()`. This is the single biggest difference from a shell, where there is one
history for the user. See §5.

## 2. Cycling with Up and Down

State lives in `m.promptHistory`: `messages []string`, `index int`, `draft string`. Index `-1`
means "not browsing — the editor holds the live draft"; index `0` is the **most recent** entry.

- `handleHistoryUp` (`history.go:47`) enters history only when the editor is empty or the cursor
  is at the very start (`isAtEditorStart`, `history.go:190`); otherwise Up is ordinary cursor
  movement. This is deliberate and worth keeping: it lets Up navigate a multi-line draft.
- `historyPrev` (`history.go:139`) saves the draft on first entry, steps the index forward, and
  replaces the textarea contents. `historyNext` (`history.go:159`) steps back, restoring the draft
  at index `-1`.
- `Esc` while browsing restores the draft (`handleHistoryEscape`, `history.go:93`).
- Typing anything resets to the draft (`updateHistoryDraft`, `history.go:109`).
- The bindings are `up`/`down` with no help text (`internal/ui/model/keys.go:153-158`).

There is **no de-duplication**: the same prompt sent twice appears twice, unlike bash under
`HISTCONTROL=ignoredups`.

## 3. Ordering, and why it is unreliable

Both queries sort newest-first, which is what index-0-is-most-recent requires:

- `listAllUserMessages` and `listUserMessagesBySession`, `internal/db/sql/messages.sql` —
  `WHERE role = 'user' ORDER BY created_at DESC`.

But `CreateMessage` (`internal/db/sql/messages.sql:24`) stamps `created_at` with
`strftime('%s', 'now')` — whole **seconds** — even though the schema comment
(`internal/db/migrations/20250424200609_initial.sql:53`) says "Unix timestamp in milliseconds".
With no tiebreaker in the `ORDER BY`, any two user messages created in the same wall-clock second
come back in an order SQLite does not define. Message ids are UUIDv4
(`internal/message/message.go:178`), random, so `id` is not a usable tiebreak; `rowid` is (no
migration declares `WITHOUT ROWID`).

**These queries are sqlc-generated.** The source of truth is `internal/db/sql/messages.sql`, and
`internal/db/messages.sql.go` holds the generated copy as string constants. The build does not run
sqlc, so anything that edits one must edit both.

## 4. When the list is reloaded — and the defect that follows

Four call sites in `internal/ui/model/ui.go`: startup `:521`, after a `!shell` command finishes
`:1313`, on submit `:2593`, and on a new session `:4689`.

The submit site is wrong:

```go
return tea.Batch(m.sendMessage(value, attachments...), m.loadPromptHistory())
```

`tea.Batch` runs its commands concurrently, and `sendMessage` does not write the message —
`AgentRun` is fire-and-forget in both workspace modes (`internal/workspace/app_workspace.go:106`
hands to the agent coordinator; `client_workspace.go:226` returns on HTTP 202). The row is
inserted by the agent side afterwards, so the reload returns a list **without** the prompt just
sent, and `promptHistoryLoadedMsg` (`ui.go:839`) installs it wholesale. For the rest of the
session, the first Up recalls the prompt *before* the last one.

Tracked in `tasks/crush-up-arrow-skips-last-prompt.md`.

`promptHistoryLoadedMsg` also resets `index` and `draft` unconditionally, so a reload landing
mid-browse drops the user back to the draft.

## 5. Persistence — where the history actually lives

**In the project, not in the user's home.** `defaultDataDirectory = ".crush"`
(`internal/config/config.go:24`), resolved by `setDefaults` (`internal/config/load.go:539-565`):
`LookupClosestBounded` walks up from the working directory to the **git worktree root**
(`projectBoundary`, `load.go:1320`) looking for an existing `.crush`, else uses
`<workingDir>/.crush`. The database is `<dataDir>/crush.db` (`internal/db/connect.go:93`).

For this repo's client that means **`/work/.crush/crush.db`** — and `/work` is the host bind mount
`-v $(PROJECT):/work` (`client/Makefile:223`). So prompt history **already survives the container
exiting**; it is per project, sitting in the project directory on the host. Nothing in this repo
sets `--data-dir` or `option data-directory`.

Two ways to move it, both requiring **no source patch**:

- `crush --data-dir /path` / `-D` (`internal/cmd/root.go:58`);
- `option data-directory /path` in `~/.config/crush/crushrc` (`data_directory` in the JSON
  schema, `internal/config/config.go:326`). **Absolute paths are used as-is**, relative ones
  resolve against the working directory.

**The constraint on sharing one data dir across projects:** Crush takes an exclusive `flock` on
`{dataDir}/crush.lock` at connect (`internal/db/datadirlock.go`), returning `ErrDataDirLocked` if
another process holds it. One shared data dir therefore means **one Crush at a time** — and the
PID written into the lock file is a container PID, so the diagnostic on a stale lock is
misleading. Weigh that before consolidating.

Tracked in `tasks/crush-history-across-sessions-and-days.md`.

## 6. What a bash-style `Ctrl-R` would take

There is **no search UI today** — the only history keys are Up and Down (§2).

- **The key is already taken.** `ctrl+r` is the editor's attachment-delete prefix:
  `AttachmentDeleteMode` (`internal/ui/model/keys.go:141-144`), with `ctrl+r+{i}` deleting
  attachment *i* and `ctrl+r+r` deleting all (`DeleteAllAttachments`, `keys.go:149`). It is passed
  into the attachments component's keymap at `ui.go:430`, and only advertised in help when
  attachments exist (`ui.go:3254`) — but it is *bound* unconditionally.
- **There is a reusable filtered-list widget**: `internal/ui/list.FilterableList`, used by the
  sessions dialog (`internal/ui/dialog/sessions.go:34`) and the commands and models dialogs. A
  history-search dialog built on it is a new file plus a few lines of wiring — which matters,
  because a patch that adds a file rebases across upstream bumps far more easily than surgery
  inside `ui.go`'s key routing.
- **A literal inline `(reverse-i-search)` prompt** — bash's actual behaviour — instead needs a new
  editor mode: its own key routing, a replaced prompt line, `Ctrl-R` again to walk to older
  matches, `Ctrl-G`/`Esc` to cancel restoring the draft, and Enter to accept into the editor.

Tracked in `tasks/crush-ctrl-r-history-search.md`.

## 7. The patch system these changes live in

Every local change to Crush is a `client/patches/*.patch` applied at image build by
`client/entrypoint/03-build-crush.sh` under its own flag, with `git apply --unidiff-zero`. Feature
patches follow `CRUSH_AT_IMPORT`: default `1` in `client/Makefile` (the maintainer wants it),
default `0` in the build script (a bare `podman build` stays stock). Read that script's header
before adding one, and re-verify every patch on a `CRUSH_TAG` bump
(`tasks/bump-crush-to-v0.90.0.md`).
