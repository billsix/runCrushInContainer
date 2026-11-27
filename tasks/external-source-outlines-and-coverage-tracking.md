# Mirror: a convention for holding an external book's outline, citing it, and tracking which of its topics a project has covered

**Status:** ready — waits on the work in runClaudeInContainer's task of the same name (its questions were answered 2026-11-27)
**Priority:** 5
**Difficulty:** 3
**Created:** 2026-11-27 (William Emerison Six <billsix@gmail.com>)
**Depends on:** github.com/billsix/runClaudeInContainer `tasks/external-source-outlines-and-coverage-tracking.md`
**Related:** `tasks/review-record-shows-dispositions.md` (the same derived-status problem, for review records)

## BLUF

The maintainer (2026-11-27) wants a systematic way to hold the outline of a book he does not own the
rights to (chapters, lessons, topics, page numbers), to cite it from his own book, and to see which
of its topics his book has covered, plans to cover, has decided to skip, or has not addressed. The
investigation, the proposal, the copyright findings and the open questions are in
runClaudeInContainer's task; this task mirrors the result into this repo. Done means this repo's
shared conventions, reference docs and any shared tool match runClaudeInContainer's once that task
has been decided and built.

## Context

**Read first:** github.com/billsix/runClaudeInContainer
`tasks/external-source-outlines-and-coverage-tracking.md`. It holds everything; this doc repeats only
what a reader needs in order to know why the mirror exists.

- **The goal.** github.com/billsix/geometricalgebra is a library and a book, "Geometry 2", a course
  for high school or early college that bridges to linear algebra through geometric algebra. The
  maintainer reads a standard geometry textbook (Charles et al., *Geometry: Common Core*, Pearson,
  2012) for topics to connect to it. Deciding to cover a topic and writing it may be months apart,
  and he wants a record that does not depend on his memory. He wants to comply with US copyright law
  and to cite heavily.
- **The finding.** A hand-maintained reference doc is the wrong home for the coverage half: the
  review conventions already say "Status is derived, never written into the record", and
  geometricalgebra's existing hand-typed "Where" column is the weak version of this.
- **The design (accepted by the maintainer 2026-11-27).** One data file per external source (stable topic IDs, the
  source's page numbers, own-words descriptions, a want / skip / undecided decision); coverage read
  from grep-able tags in the product's pages; a report tool that prints covered / planned / skipped /
  not addressed; a reference doc for the prose; citations generated from the same data. Committed
  content is titles, page numbers and own-words descriptions, never the publisher's definitions,
  exercises or figures. The outline grows over months, a few topics at a time, so a partial
  outline is valid and a topic's ID never changes once written.
- **Why this repo is involved.** The convention would live in the shared `CLAUDE.md` and a reference
  doc, and the tool may be a sibling of `review_status.py`; this repo mirrors all three
  byte-identically where it mirrors them today.

## Plan

- [x] The maintainer answered runClaudeInContainer's five questions (2026-11-27; he took the agent's recommendation on each).
- [ ] Mirror the convention text, the reference doc and any shared tool, and check the mirrored
      copies with `cmp`.
- [ ] Bake the reference doc into the client image where this repo bakes the others.

## Open questions

None. The five questions were asked and answered in runClaudeInContainer's task.
