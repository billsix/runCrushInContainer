# Mirrored the /archive-task and stack command fixes into the Crush commands

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.1, §0.2 F8

## What this did

Applied github.com/billsix/runClaudeInContainer `tasks/archive/2026/11/15/archive-and-stack-command-lifecycle.md`
to the ported commands in `client/entrypoint/dotfiles/.config/crush/commands/`, keeping the Crush
adaptations (`$SLUG`, `~/.config/crush`, the in-session stack):

- `archive-task.md`: the done-record rewrite is staged with the work; the move waits for the work
  commit and is recorded as owed in the task's Status until then; never a plain `mv` in a git
  repo (step 9 allowed one); the last step stages by path instead of leaving staging to the user.
- `stack-pop.md`: closes the task doc and records an owed move in the task's Status (the stack
  does not outlive the session).
- `stack-push.md`: creates `## Active diversion chain` and pushes into it.
- `new-task.md`: `proposed — needs go-ahead` and a `Created:` stamp, as runClaude's now does.
- `audit-repo.md`: quick mode names `check_local_annotations.py`.

## Verification

Read each changed step against runClaude's versions of the same commands.
