# Convention: on "I'm going to squash", harvest the full decision history into the task doc first

**Status:** complete
**Completed:** 2026-09-03

## What this did

Added a standing convention to `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, next to the
existing quick-save/squash rule: when the maintainer says they are about to squash, the agent first
walks every commit in `<upstream>..HEAD` (the unpushed range, `<upstream>` from
`git rev-parse --abbrev-ref @{u}`), reads both the task-doc and code diffs, and updates the task doc
with a chronological record of every decision: what changed and why, what was rejected and why, what
each step discovered. Only then is the squash done.

## Rationale

After a squash the per-commit trail is gone, so the archived task doc is the only record of the
reasoning. The rule bridges the squash rule and the "Task documents" requirement that decisions be
recorded with rationale. It is general working practice, so it went in the conventions layer, not a
personal overlay.

## Decisions

- The same convention went into runClaudeInContainer's `entrypoint/dotfiles/.claude/CLAUDE.md`
  (its copy of this task is runClaudeInContainer `tasks/archive/2026/09/03/squash-harvest-decision-history.md`), with the
  wording trimmed to each file's density.
- The harvest target during a squash is the task doc; harvesting into reference docs stays at archive
  time under the existing rule.
