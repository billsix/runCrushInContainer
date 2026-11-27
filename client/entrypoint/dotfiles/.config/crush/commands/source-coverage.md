Report the coverage of an external source's outline in the repository we are in.
**Read-only:** edit and stage nothing. Coverage is derived from `covers:` tags in the
product's files and from the `**Source:**` lines of tasks; it is never written into the
outline.

Arguments: `$OPTIONS` (empty → every outline under `tasks/sources/`).

1. Find the repo root (`git rev-parse --show-toplevel`) and `cd` there.
2. Run `python3 ~/.config/crush/reference/source_coverage.py $OPTIONS`.
3. Report in chat:
   - the summary line of each outline (covered / planned / skipped / not-addressed counts,
     how many entries are wanted and not addressed, how many page numbers are unchecked);
   - every line of a "Problems" section, with what would fix it;
   - the entries that are **wanted and not addressed** (decision `want`, status
     `not-addressed`): these are what the maintainer may write next.

   Point at the tool's full table rather than pasting it, unless the maintainer asks.
4. Don't add entries, tags or tasks. To add to an outline, the maintainer says what to add;
   the steps are in the conventions doc below ("The outline grows").

Conventions (the outline file, entry IDs, `covers:` tags, what may be committed):
`~/.config/crush/reference/external-source-outlines.md`.
