# Mirror: a convention for holding an external book's outline, citing it, and tracking which of its topics a project has covered

**Status:** done 2026-11-27 — staged; the archive move is owed after the work commit
**Priority:** 5
**Difficulty:** 3
**Created:** 2026-11-27 (William Emerison Six <billsix@gmail.com>)
**Mirrors:** github.com/billsix/runClaudeInContainer `tasks/external-source-outlines-and-coverage-tracking.md`
**Related:** `tasks/review-record-shows-dispositions.md` (the same derived-status problem, for review records)

## What this did

Mirrored runClaudeInContainer's external-source-outline convention into this repo, so that a
project developed with Crush gets it too. The reason, the investigation, the maintainer's five
decisions and the design calls are in runClaudeInContainer's task; the rules are in
`tasks/reference/external-source-outlines.md`.

In short: a project keeps the outline of a book it does not own in `tasks/sources/<key>.toml`
(the maintainer's first is a high-school geometry textbook, for his book "Geometry 2" in
github.com/billsix/geometricalgebra), tags the pages of its own product that cover an entry with a
`covers:` comment, and gets covered / planned / skipped / not-addressed from a report. Coverage is
never typed by hand, and the source's own wording is never committed.

## What was mirrored

- `tasks/reference/source_coverage.py` and `tasks/reference/external-source-outlines.md`, and
  their baked copies under `client/entrypoint/dotfiles/.config/crush/reference/`: byte-identical
  to runClaudeInContainer's (`cmp`).
- `client/entrypoint/dotfiles/.config/crush/commands/source-coverage.md`: a port, not a byte
  mirror, like the other commands (no frontmatter, an `$OPTIONS` token, `~/.config/crush` paths).
- `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`: the "External source outlines" section,
  with `~/.config/crush` paths and its read trigger folded into the section.
- `tasks/reference/container-file-layout.md` and its baked copy: two rows.
- `CLAUDE.md`, `README.md`, `FORKING.md`, `tasks/reference/architecture.md`: the tool named, and
  the command count 13 → 14.

## Verification

`cmp` of the four copied files against runClaudeInContainer's. The client image was not rebuilt and
the command was not run in a Crush session.

## Found on the way, not fixed

The baked `client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md` already
differed from `tasks/reference/container-file-layout.md` before this work: its install-script rows
predate the 2026-11-27 bind-mount change, and it lacks the `survey_names_and_scope.py` row. The two
new rows were added to both; the older drift belongs to `tasks/audit-baked-reference-doc-drift.md`.
