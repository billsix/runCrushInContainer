# Layered reference docs (levels of detail) — native capability

**Status:** complete
**Completed:** 2026-09-06

## What this did

Made the maintainer's levels-of-detail reference-doc pattern native to this sandbox: added a
"Layered reference documents (levels of detail)" convention to
`client/entrypoint/dotfiles/.config/crush/CLAUDE.md` (now the "Layered levels of detail (LoD)"
paragraph) and a `/new-reference-set` command
(`client/entrypoint/dotfiles/.config/crush/commands/new-reference-set.md`) that scaffolds a layered
set. The pattern was harvested from the imps mario64 graphics reference set (github.com/billsix/imps,
`tasks/reference/mario64/`: 23 topics at L0-L2 with a `README.md` map), and extends the single-level
`/new-reference` convention with a level-of-detail dimension. The shape matches the sibling
runClaudeInContainer sandbox.

## The pattern as encoded

- **L0 capsule** (about one paragraph), aggregated into the set's `README.md` map; **L1 orientation**
  (about one page, no code), file `<topic>-overview.md`; **L2 mechanism** (anchored core), file
  `<topic>.md`; **L3 source**, cited by named region (a `doc-region` marker) rather than line.
- **Generate deepest-first, then compress upward**, each level about half the lines of the one below,
  written fresh at its altitude.
- **Every topic gets L0 + L2; L1 only when its mental model is non-obvious, self-contained, and not
  another topic's job** (otherwise cross-link the owning topic).
- Each doc links up to its capsule and down to its detail.

## Learnings folded in (imps mario64 run, 2026-09-06)

1. Levels are horizontal too: choosing a level includes deciding which topic owns an idea (the
   transforms topic's model lived in the scene-graph topic, so transforms got L2+L0 and a link).
2. Compare each doc to a baseline the reader already knows; without it a doc drifts into a file walk.
3. Cite stable named anchors, not line numbers (one function moved from line 1065 to 2251 between doc
   versions); a line number is only an "as of <pin>" aid.
4. A set also grows top-down: writing a higher level surfaces gaps that spawn new topics.
5. A "what's absent" capsule, with the check that proves the absence, is durable negative knowledge.
6. The L0 map is the table of contents and a status board, with a per-topic status column.

## Related

- Worked example and full rationale: imps `tasks/mario64-graphics-refdocs.md` and
  `tasks/reference/mario64/` (github.com/billsix/imps); origin was imps step 9
  (`mario64-graphics-refdocs-step-9-lod-doc-capability`).
