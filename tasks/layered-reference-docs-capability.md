# Layered reference docs (levels of detail) — native capability

**Status:** proposed — needs go-ahead
**Priority:** 5
**Difficulty:** 4

## BLUF

Make the maintainer's **levels-of-detail reference-doc pattern** a native
part of this sandbox: a `CLAUDE.md` convention plus a command-system entry,
so future sessions produce layered reference docs by default. The pattern was
developed and proven in the **imps mario64 graphics reference set**
(github.com/billsix/imps, `tasks/reference/mario64/` — 23 topics at L0-L2 with
a `README.md` map). This task promotes that from practice to convention. Done
when this repo carries the convention and a command that scaffolds a layered
set.

## Context — the proven pattern (do not re-invent; harvest it)

The existing reference-doc convention (`tasks/reference/`, the
`/new-reference` command) makes SINGLE-level docs. This EXTENDS it with a
**level-of-detail dimension**: a topic becomes a column of docs at decreasing
detail.

- **L0 — capsule** (≤1 paragraph / ~5 sentences): the whole topic in a
  breath. All L0s aggregate into one top **map doc** so a set is graspable at
  a glance.
- **L1 — orientation** (~1 page, NO code): the mental model.
- **L2 — mechanism** (the anchored core): the full algorithm/data flow.
- **L3 — source**: the code itself; a later pass can add `doc-region` markers
  so Sphinx `literalinclude` pulls exact spans by NAME (drift-proof).

Proven rules (from the mario64 run, 2026-09-06):

- **Generate deepest-first, then compress upward**, each level ~half the
  lines of the one below — a size budget and forcing function, not a
  delete-half (write each level fresh at its altitude).
- **Every topic gets L0 + L2; add L1 only when its mental model is BOTH
  non-obvious AND self-contained** (else cross-link the topic that owns it).
  Worked calibration: trivial model → L2+L0; a genuinely distinct,
  self-contained model → +L1; a model that belongs to another topic →
  cross-link, no L1.
- **File naming:** L2 = `<topic>.md`, L1 = `<topic>-overview.md`, L0 = a row
  in the set's `README.md` map.
- Each doc links UP to its capsule and DOWN to its detail; the map holds
  every L0.

## Deliverables

1. **A `CLAUDE.md` convention section** — "Layered reference documents
   (levels of detail)": the L0-L3 definitions, size budgets, the naming
   scheme, the generation method, the L1-only-when-non-obvious-and-
   self-contained rule, and the map-aggregates-L0s rule. Generic (not
   game-specific), citing the imps mario64 set as the worked example.
2. **A command-system entry** — extend `/new-reference` (or add a sibling
   command) to scaffold a layered set for a topic: generate the L0 stub (map
   row), an L1 stub (when requested), and an L2 stub with the provenance
   banner + cross-links pre-wired, and register the topic in the map doc.
   Match this repo's existing command conventions.
3. **Consistency:** the convention + command should be the same shape in the
   sibling sandbox repo (runClaudeInContainer / runCrushInContainer share the
   dotfiles/command lineage); note any deliberate divergence.

## Note

Changing the sandbox conventions/command layer is the maintainer's to approve
(his "confirm before acting" rule). This task is the proposal; wait for
go-ahead before editing `CLAUDE.md` or the commands.

## Learnings from the first full run (imps mario64, 2026-09-06)

Beyond the L0-L3 scheme above, doing 23 topics + a book taught these — fold
them into the eventual convention/command:

1. **Levels are HORIZONTAL as well as vertical.** Choosing a level is not only
   "how much detail" but "which topic OWNS this idea." When a topic's mental
   model actually belongs to another topic, do NOT write a duplicate L1 —
   cross-link to the owner. (Worked example: the transforms topic's mental model
   lived in the scene-graph topic, so transforms got L2+L0 and a link, not its
   own L1.) The L1-earns-its-place rule is really: **non-obvious AND
   self-contained AND not another topic's job.**

2. **Compare to a baseline the reader already knows.** Every doc anchored itself
   to what the reader knew (here, the maintainer's course). That framing forces
   the right altitude and turns a code tour into teaching material — it is where
   each doc earned its keep. A reference doc with no "how this relates to X the
   reader knows" tends to drift into an undifferentiated file walk.

3. **Cite STABLE named anchors, not line numbers.** Line numbers rot — this run
   hit a function that moved from line 1065 to 2251 between doc versions. When a
   reference doc points at code, prefer a **named region** (a `doc-region`
   marker, or at least a function/symbol name) over a bare `file:line`; treat a
   line number as an "as of <pin/commit>" aid, never the durable handle. This is
   general, not book-specific.

4. **The set is grown TOP-DOWN too.** Writing a higher level (an L0 map, or a
   whole book on top of the set) surfaces gaps that spawn NEW topics and deeper
   levels — synthesis reveals what the lower levels are missing. The layered set
   is living; do not treat L2 as "written once, bottom-up."

5. **A "what's absent" capsule is durable negative knowledge.** One short doc
   stating what is NOT there (and the check that proves it) stops future readers
   re-searching for a thing that does not exist — worth its own map row.

6. **The L0 map IS the table of contents.** Because every capsule aggregates
   into the one map doc, that map doubles as navigation and a status board.
   Build it as the aggregation of capsules, with a per-topic status column.

## Related

- Worked example + full rationale: imps `tasks/mario64-graphics-refdocs.md`
  and `tasks/reference/mario64/` (github.com/billsix/imps).
- Origin: imps step 9 (`mario64-graphics-refdocs-step-9-lod-doc-capability`).
