<!-- SHARED, MIRRORED REFERENCE DOC -- keep the runClaudeInContainer and
     runCrushInContainer copies byte-identical. Canonical:
     runClaudeInContainer tasks/reference/repo-review-conventions.md
     (github.com/billsix/runClaudeInContainer). -->

# Repository reviews — the deep audit of a whole repo, and where it is stored

**Reference document.** How to run a **deep review**: an in-depth, read-only audit of
everything in one repository. The output is a dated, frozen record stored under
`tasks/review/`. It covers what a review is, the dimensions it covers, how to run one
without wasting tokens, the record's layout, and the record's lifecycle. Written
2026-11-08 (William Emerison Six <billsix@gmail.com>), after the first one was run on
github.com/billsix/geometricalgebra. That record is
`tasks/review/2026/11/08/repo-review.md` in that repo, and it is the worked example.

## What a deep review is, and what it is not

A deep review reads the **whole repository**. It checks every layer against the others,
and against the project's `CLAUDE.md` and these cross-project conventions:

- docs against docs and docs against code;
- the product itself, judged for content and correctness, not just consistency;
- the code, the tests, any proofs;
- the build, container and CI layer;
- the task backlog and the task archive.

It **reports and changes nothing**. Fixes come afterwards, as tasks the maintainer makes
from the record.

Compared with the neighbouring practices:

| | Session-end sweep | `/audit-repo` (quick) | `/audit-repo deep` (this doc) |
|---|---|---|---|
| Scope | always-read docs a session *touched* | docs ↔ source of the current repo | **everything**, every dimension below |
| Trigger | maintainer signals end of session | on request | on request — never automatic |
| Expected result | usually nothing (a safety net) | a findings list in chat | a dated record in `tasks/review/` |
| Edits | applies doc fixes, stages | none | none (only writes + stages the record) |
| Cost | small | moderate | large (see "Cost") |

The session-end sweep keeps the docs current one session at a time. A deep review finds
what has built up across many sessions: drift in the archive, a book whose narrative stopped
holding together, a gate a doc says exists but doesn't run. It also judges the **quality**
of the product, which no sweep does.

**When to run one:** when the maintainer asks. Good moments are before a release, after a
long burst of agent-written work, when adopting a project, or periodically (a few times a
year). Never run one unprompted: it is the most expensive routine operation in these
conventions.

## The dimensions — every review names which ones it covered

"Everything" means these dimensions. A record lists each one with what was read for it
(read in full, sampled, or not covered), so a reader knows what a clean result does *not*
prove. A dimension that doesn't apply to the repo (no proofs, no product content) is marked
N/A, not silently dropped.

1. **Docs ↔ docs.** `CLAUDE.md`, `README.md` and every `tasks/reference/*` doc, checked
   against each other: contradictions, duplicated content that has drifted, convention
   violations (history-narration, bare first-name stamps, non-root-relative paths, a dated
   record living in `reference/`).
2. **Docs ↔ code.** Every claim a doc makes about a file, function, `make` target, gate,
   flag or behaviour, checked against the tree. Pay most attention to claims about
   **gates**: "X is checked by Y" is the claim most often false, and the most expensive one
   to believe.
3. **Product content.** Whatever the repo exists to deliver to a reader or user: a book's
   pages and notebooks, a tutorial, user-facing docs, demo notebooks, the README as a
   reader sees it. Judge narrative order, correctness (math, claims about the code),
   cross-references, the project's notation and voice rules, author notes leaking into
   reader-facing text, and draft markings.
4. **Code quality.** The hand-written source: correctness bugs (with a failing input),
   docstrings that misstate behaviour, the project's and the shared coding standard, dead
   code, duplication, layering.
5. **Generators and tools.** Code generators (sample their output; never read whole
   generated trees), check scripts (does each gate enforce what the docs say, or can it
   pass vacuously?), and one-shot or dead tools that should have been removed.
6. **Tests.** Coverage gaps ranked by risk, tests that cannot fail, circular ground truth,
   unmarked slow tests, candidates for doctests (`doctests-by-default.md`).
7. **Proofs / formal artifacts** (where the repo has any). Statements against names and doc
   comments, the project's proof style rules, dead lemmas, gate gaps (is every file built?
   does the gate catch every escape hatch?), cited theorem names that don't exist.
8. **Build, container, CI, packaging.** The `Makefile`, `Dockerfile`, `entrypoint/`,
   `.dockerignore`, workflows, `pyproject.toml`/manifests, version ↔ changelog ↔ tags. Check
   them against the project's own docs *and* against the container-template conformance
   checklist in the personal overlay. Look for stale comments, a group script whose failure
   is masked, CI building a heavier image than it needs, ports or tokens exposed, scripts
   missing their executable bit.
9. **Open-task backlog.** Each open `tasks/*.md`: already done? overlapping another task?
   premise overturned? missing BLUF/Context/ratings? Priority/Difficulty ratings that don't
   match the content? Include the backlog ranked as the docs currently read.
10. **Archive hygiene.** `tasks/archive/`: docs never rewritten into done-records,
    superseded decisions with no "superseded" note, decisions still in force but never
    harvested into `CLAUDE.md`/`tasks/reference/`, dangling paths and SHAs, one-shot
    scripts never `git rm`'d.

Skip upstream-only checkouts (personal overlay). Do not read vendored trees. Do not read
generated trees beyond a sample that confirms a claim.

## Method

1. **Inventory and size first.** `wc -l` each corpus (`book/`, `src/`, `tests/`, `tools/`,
   `proofs/`, `tasks/reference/`, `tasks/*.md`, each archive month, the build files).
   Decide the split from the numbers, not by guessing.
2. **Fan out one reader per corpus, about 8–10K lines each.** Above that, a reader starts
   sampling. (The first run gave one reader ~11.6K lines; it skipped full reads of ~60
   docs, which it disclosed.) Partition the archive by month. Give generated code to the
   generator's reader as a sample only. Launch all readers in one message so they run in
   parallel.
3. **Brief each reader as a peer, tightly** (`token-and-context-economy.md`):
   - "READ-ONLY; edit, stage, create nothing";
   - the repo path, plus which docs set the standard (the project `CLAUDE.md`, the
     relevant shared coding standard, the relevant `tasks/reference/` docs);
   - the exact file scope, "read in full";
   - the numbered list of what to look for, from the dimension above;
   - the report shape: a one-line **coverage statement** first, then findings grouped
     HIGH / MEDIUM / LOW, each with `path:line`, what's wrong, the evidence checked, the
     suggested fix, and **VERIFIED or LEAD**;
   - a word cap (~900–1000).

   A reader in a later wave gets a pointer to the record so far, so it doesn't re-report
   known findings.
4. **The main thread reads the product itself, without delegating** (dimension 3). Content
   findings need judgment that holds across many pages ("this page promises what no
   chapter delivers"), and a summary loses exactly that. The main thread can also take one
   small corpus itself (the build layer is a good fit) while the readers run.
5. **Verify before trusting.** A reader's VERIFIED is a claim. Before the record calls
   something HIGH, re-check it, or make sure the reader showed the command and output.
   "grep found nothing" is not proof of absence. "X is dead" needs a check of every way X
   could be reached.
6. **Consolidate.** Dedupe findings across readers: two readers finding the same thing
   independently raises confidence, so say so. Order the record by what changes the
   maintainer's next action: errors in front of a reader, and gates that silently don't
   run, come first.
7. **Write the record, stage it, report in chat.** The chat report leads with the few
   findings that matter most and points at the record for the rest.

## Where records live: `tasks/review/<YYYY>/<MM>/<DD>/<slug>.md`

- **A fourth task directory**, beside `tasks/reference/`, `tasks/archive/` and
  `tasks/adhoc/`, with its own `.keep`. The default slug is `repo-review`; a narrower
  review names its scope (`book-review`, `lean-review`). The date-nested layout mirrors
  `tasks/archive/`, so paths look familiar, sort by date, and grep the same way.
- **Not in `tasks/reference/`.** A reference doc states what is true now and is updated in
  place, and agents read it before touching a subsystem. A review is a frozen snapshot
  that goes stale as each finding is fixed. In `reference/` a future agent would read it as
  current truth. (The first run found exactly this problem: an older dated proof-corpus
  audit sitting in `tasks/reference/` with a coverage table that had become false.)
- **Not in `tasks/archive/`.** The archive holds finished *tasks*. A review is an input to
  future tasks, not a finished one.

## The record's layout

```markdown
# Repository review — <YYYY-MM-DD>

**What this is / requested by** (Name <email>, date) / **snapshot warning** ("re-check a
finding against the tree before acting on it") / **baseline:** the previous review's path,
or "none — first review".

**Coverage** — a table: dimension → what was read (in full / sampled / not covered / N/A)
and by whom (main thread or a reader).

## 1. … one section per dimension, numbered …   (findings, each VERIFIED or LEAD)

## Carried over from the previous review       (only when there is a baseline: each prior
                                                finding → fixed / still open / no longer applies)

## Suggested follow-ups                         (tagged required / recommended / optional)

## Open questions for the maintainer            (numbered, one ask each, with the reviewer's
                                                recommendation)
```

- Every finding names its location (`path:line`, or a section / theorem name) and the
  evidence.
- Fence any span that quotes a spelling the project's notation rules reject with that
  project's skip markers (e.g. `<!-- notation-rule: begin/end -->`), so a later notation
  sweep doesn't "fix" the quotation.
- Paths are repo-root-relative. Other repos are cited by URL.

## Lifecycle

- **Never edit a record after it is written.** Act on it by making tasks that cite it by
  path and section (by hand, or with `/findings-to-tasks <record> [§sections]`) (`tasks/review/2026/11/08/repo-review.md` §1.3). Its value as a baseline
  depends on it staying exactly what was found that day. Two exceptions: correcting the
  reviewer's own factual error in the record, or answering one of its open questions.
  Either gets a dated note, never a silent rewrite.
- **The project's `CLAUDE.md` holds a one-line pointer to the latest review**, so the next
  review finds its baseline and an agent knows one exists. Update the pointer when a new
  review lands.
- **The next review diffs against the previous one** in its "Carried over" section ("12 of
  15 fixed, 3 still open"). That turns the series into a measure of whether the repo is
  getting healthier.
- **Records are never archived or deleted.** They are small and they are the history.
- **The review itself is not a task.** No task doc is needed to run one. If the maintainer
  turns findings into tasks, each task links back to its record section.

## Cost

First run (github.com/billsix/geometricalgebra, 2026-11-08): about **2.5M subagent tokens**
across eight readers in two waves (≈1.17M + ≈1.31M, read from each reader's reported usage),
plus a long main thread:

- wave 1: reference docs, open tasks + the two newest archive months, two older archive
  windows;
- wave 2: library source, generator + tools, tests + demo notebooks, Lean proofs.

The repo held ~11K lines of task/reference docs, ~28K lines of archive, ~7K lines of
hand-written Python, ~8K lines of tools, ~6.5K lines of tests, ~7K lines of Lean, and a
~30-page book. This is why a deep review runs only on request. It is the deliberate,
named exception to the default-to-inline rule in `token-and-context-economy.md`: the work
is large, the corpora are independent, and keeping whole-corpus reads out of the main
thread is the point.

Ways to keep the cost down:

- the right reader size (oversized readers sample; undersized ones pay the ~25K
  instruction ingest for little work);
- fresh agents, not forks — a fork also re-ingests the whole conversation;
- one wave where possible;
- the main thread reads only the product and the small corpus it took on itself.
