# Make Crush's prompt history span sessions and days, like a shell's

**Status:** proposed — research done 2026-09-09. **The premise turned out to be partly wrong:
history already persists on the host.** Read the first section before planning anything.
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
