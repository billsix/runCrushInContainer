# Make Crush's prompt history span sessions and days, like a shell's

**Status:** **DONE 2026-09-09.** Delivered by `client/patches/crush-shell-history.patch`
(flag `CRUSH_SHELL_HISTORY`, on by default), which carries all three history tasks — they turned
out to be one change to one subsystem. Verified: the patch applies to a pristine v0.89.0 clone
with the build script's own `git apply --unidiff-zero`, `go build ./...` is clean, and
`go test ./internal/ui/... ./internal/db/...` passes.
**How it all works:** `tasks/reference/crush-prompt-history.md`.
**Priority:** 3
**Difficulty:** 3

## BLUF

The want was "history preserved on the host, so on later days I still have my old history even
after closing the container". The persistence half is **already true** — the database lives in the
mounted project directory. What actually hides yesterday's prompts is that the history list is
filtered to the **current session**. Done = Up and search offer prompts from earlier sessions.

## What is already true (verified, do not re-derive)

Full detail in `tasks/reference/crush-prompt-history.md` §5.

Crush's data directory defaults to `.crush` **relative to the project**
(`internal/config/config.go:24`, resolved in `internal/config/load.go:539-565` against the git
worktree root), and the database is `<dataDir>/crush.db` (`internal/db/connect.go:93`). The client
runs with `-v $(PROJECT):/work` (`client/Makefile:223`), so the database is
**`<host project>/.crush/crush.db`** — on the host, surviving the container, already. Nothing in
this repo overrides it.

**Confirm in one command before doing anything else** (this sandbox has no Crush data dir, so this
was read from the source, not measured):

```sh
ls -la <a project you have used crush in>/.crush/
```

A `crush.db` there means the persistence half needs no work.

## The actual gap: history is session-scoped

`loadPromptHistory` (`internal/ui/model/history.go:24-29`) calls `ListUserMessages(sessionID)` as
soon as a session exists, and `ListAllUserMessages()` **only** when there is no session at all. So
starting a new session — which is what happens on a new day — leaves Up offering just that
session's prompts. Yesterday's are in the database, and unreachable.

**The fix is small:** always load across sessions, or add a config option and default it to
cross-session. Recommend unconditional cross-session in our patch, matching a shell: one history,
not one per invocation. Note the ordering caveat from
`tasks/crush-up-arrow-skips-last-prompt.md` — `ORDER BY created_at DESC` with second-resolution
timestamps and no tiebreak — bites harder here, since a cross-session list has many more
same-second ties.

## The optional second half: one history across ALL projects

Today the database is per project, so each repo has its own history. A shell has one. If that is
wanted, it needs **no source patch** — an absolute `option data-directory /root/.local/share/crush`
in `client/entrypoint/crushrc` (or `crush --data-dir`), plus a host mount for that path in
`client/Makefile` alongside `PERSONAL_MOUNT`.

**The blocker to weigh first:** Crush takes an exclusive `flock` on `{dataDir}/crush.lock`
(`internal/db/datadirlock.go`) and refuses to start if another process holds it. One shared data
directory means **one Crush container at a time**, and the PID in the lock file is a container PID,
so a stale-lock message will name a process that does not exist. If two projects are ever open at
once, keep per-project data dirs and accept per-project history.

## Verification

- `go test ./internal/ui/model/`.
- **Manual, only the maintainer can do it:** send a prompt, `Ctrl-N` for a new session, press Up,
  and confirm the earlier session's prompt is offered. Then exit the container, relaunch, and
  confirm it is still there.

## Open questions

1. **Cross-session history unconditionally, or behind a config option?** Recommend
   unconditionally in the patch — it is the shell behaviour that was asked for.
2. **Do you want one history across all projects (a shared data dir), or per project?**
   Recommend per project unless you never run two Crush containers at once, because of the
   exclusive data-dir lock.


## What was done (2026-09-09)

**`loadPromptHistory` now always calls `ListAllUserMessages`**, dropping the session-scoped branch:
one history for the project, the way a shell has one history for the user. That is the whole change
— five lines and a comment.

**No data-directory change was made, and none is needed.** The maintainer's clarification settled
it: storing history wherever Crush is launched is exactly what Crush already does, and since the
client launches in `/work` — the mounted project — it persists on the host when launched in a
mount and is lost otherwise, which is the desired behaviour. The shared-data-dir option in the
section above was **not** taken; the exclusive `flock` would have limited the setup to one Crush
container at a time.

One consequence to know about: a test double needed a method it had never been asked for — see
`tasks/crush-up-arrow-skips-last-prompt.md`, item 4.

**Answers to the open questions:** (1) unconditional, no config option; (2) per project — no
shared data dir.
