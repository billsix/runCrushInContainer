# Ported /new-reference-set to Crush's command format

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 1
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §3.1 F6

## What this did

`client/entrypoint/dotfiles/.config/crush/commands/new-reference-set.md` was a byte copy of
runClaudeInContainer's: YAML frontmatter, `$ARGUMENTS`, `~/.claude/CLAUDE.md`. Crush commands take
no frontmatter and turn each `$UPPERCASE` token into a prompted argument
(`tasks/reference/crush-capabilities.md`), so the frontmatter leaked into the prompt. The port drops
the frontmatter, takes `$SET` and an optional `$TOPIC`, and cites `~/.config/crush/CLAUDE.md` (whose
"Layered levels of detail" paragraph it relies on), matching the other 11 ported commands.
`tasks/reference/architecture.md` now says the commands are ports, not byte mirrors.

## Verification

`head -1` of the command is prose, not `---`; `grep -c 'ARGUMENTS\|~/.claude' ` on it is 0.
