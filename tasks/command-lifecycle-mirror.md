# Mirror the /archive-task and stack command fixes

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.1, §0.2 F8

## BLUF

Mirror of github.com/billsix/runClaudeInContainer `tasks/archive-and-stack-command-lifecycle.md` into the ported Crush commands: the three-commit archive lifecycle (`archive-task.md` steps 8–11, which even allow a plain `mv`), `stack-pop.md:11`, and the sectioned stack for `stack-push.md` (this stack lives one session). Done means the ported commands follow the same lifecycle.

## Context

- `client/entrypoint/dotfiles/.config/crush/commands/{{archive-task,stack-pop,stack-push}}.md`.

## Plan

1. Apply runClaude's fixes, keeping the Crush adaptations (`$SLUG`, `~/.config/crush`).
2. Never plain `mv`.
