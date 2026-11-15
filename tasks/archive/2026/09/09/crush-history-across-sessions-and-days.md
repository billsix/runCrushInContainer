# Make Crush's prompt history span sessions and days, like a shell's

**Status:** complete
**Completed:** 2026-09-09

## What this did

Made Up (and the `ctrl+r` search) offer prompts from earlier sessions, not just the current one.
Delivered by `client/patches/crush-shell-history.patch` (flag `CRUSH_SHELL_HISTORY`, on by default),
which carries all three history tasks; the siblings are
`tasks/archive/2026/09/09/crush-ctrl-r-history-search.md` and
`tasks/archive/2026/09/09/crush-up-arrow-skips-last-prompt.md`. How it all works:
`tasks/reference/crush-prompt-history.md`.

## Findings

- **Persistence was already true.** Crush's data directory defaults to `.crush` relative to the
  project (`internal/config/config.go`, resolved against the git worktree root in
  `internal/config/load.go`), the database is `<dataDir>/crush.db` (`internal/db/connect.go`), and the
  client runs with `-v $(PROJECT):/work`, so the database is `<host project>/.crush/crush.db` and
  survives the container. This was read from source, not measured in the sandbox.
- **The real gap was session scoping.** `loadPromptHistory` (`internal/ui/model/history.go`) called
  `ListUserMessages(sessionID)` whenever a session existed, and `ListAllUserMessages()` only with no
  session, so a new session (a new day) hid earlier prompts.

## What was done (2026-09-09)

`loadPromptHistory` now always calls `ListAllUserMessages`, dropping the session-scoped branch: one
history per project, as a shell has one per user. Five lines and a comment. A test double then needed
a method it had never been asked for; see item 4 of
`tasks/archive/2026/09/09/crush-up-arrow-skips-last-prompt.md`. The `ORDER BY created_at DESC`
same-second-tie problem bites harder with cross-session lists; that fix is in the same sibling.

## Decisions

1. **Cross-session unconditionally, no config option**: it is the shell behaviour that was asked for.
2. **Per-project history, no shared data directory.** The maintainer clarified that storing history
   where Crush is launched is what Crush already does; since the client launches in the mounted
   `/work`, it persists on the host when launched in a mount and is lost otherwise, as desired. The
   rejected alternative (an absolute `option data-directory` in `client/entrypoint/crushrc` plus a host
   mount) would have hit Crush's exclusive `flock` on `{dataDir}/crush.lock`
   (`internal/db/datadirlock.go`), limiting the setup to one Crush container at a time, with stale-lock
   messages naming container PIDs.

## Verification

The patch applies to a pristine v0.89.0 clone with the build script's `git apply --unidiff-zero`,
`go build ./...` is clean, and `go test ./internal/ui/... ./internal/db/...` passes. The manual check
(prompt, `Ctrl-N`, Up shows the earlier session's prompt; survives a container relaunch) was the
maintainer's to do; its result is not recorded here.
