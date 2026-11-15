# Port /new-reference-set to Crush's command format

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 3
**Difficulty:** 1
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §3.1 F6

## BLUF

`client/entrypoint/dotfiles/.config/crush/commands/new-reference-set.md` is a byte copy of runClaude's (YAML frontmatter, `$ARGUMENTS`, `~/.claude/` paths), which Crush cannot use. Port it like the other 11 commands. Done means no frontmatter, `$UPPERCASE` argument tokens, `~/.config/crush` paths.

## Context

- `tasks/reference/crush-capabilities.md:53-54,79-80` (no frontmatter, `$UPPERCASE` tokens become prompted args).
- Model: `commands/new-reference.md` (already ported).

## Plan

1. Port it.
2. Note in `architecture.md` that it is an adaptation, not a byte mirror.
