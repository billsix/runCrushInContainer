# Ported the blocked-task convention and /recheck-blocked into the Crush conventions

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 3
**Started:** 2026-08-23
**Source:** tasks/review/2026/11/15/repo-review.md §3.3

## What this did

Ported github.com/billsix/runClaudeInContainer's blocked-task convention (2026-08-23), with the
maintainer's go-ahead from the 2026-11-15 review (its open question 1):

- `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, "Task documents": a compact rule:
  `**Status:** blocked` + `**Blocked on:**` + `**Recheck:**`, a high priority-number, out of the
  easy-wins ranking, listed separately at session start and end, blocked ≠ parked, and
  `/recheck-blocked` on demand only. Kept to one paragraph because the file is always loaded into the
  local model's window.
- `commands/recheck-blocked.md` (new, the 13th command, in Crush's format: `$SCOPE` argument, no
  frontmatter): finds blocked tasks, lists them, runs each Recheck (command, version compare,
  URL + signal, or human-gated), reports CLEARED / still blocked / unknown, offers to un-block, stages
  only.
- `commands/new-task.md`: a step for creating a task as `blocked` with the two fields.
- Command counts 12 → 13 in `CLAUDE.md`, `README.md`, `FORKING.md`, `architecture.md` and
  `container-file-layout.md` (and its baked twin).

Decision on the task's open risk (does the client have a web-fetch tool?): the web tools are kept by
default (`PATCH_OUT_WEB_TOOLS=0`), so a URL Recheck works from the with-internet launcher; in
no-internet mode the command reports it **unknown** and says it needs internet.

## Verification

The command file and the convention text are in the baked dotfiles tree, so the client
`make image` bakes them (`COPY entrypoint/dotfiles/ /root/`). Not verified here: the command
appearing under Crush's `/` "User" tab, which needs a Crush session against the model (the
maintainer's).
