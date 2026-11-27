<!-- SHARED, MIRRORED REFERENCE DOC -- keep the runClaudeInContainer and
     runCrushInContainer copies byte-identical. Canonical:
     runClaudeInContainer tasks/reference/external-source-outlines.md
     (github.com/billsix/runClaudeInContainer). -->

# External source outlines — holding a book's outline, citing it, and tracking coverage

**Reference document.** How a project keeps the outline of a book it draws on but does not
own (chapters, lessons, topics, page numbers), cites it, and finds out which of its entries
the project has covered. Read it before creating or adding to a `tasks/sources/*.toml`
file, tagging a page with `covers:`, or answering "what haven't I covered yet?". Written
2026-11-27 (William Emerison Six <billsix@gmail.com>) for github.com/billsix/geometricalgebra,
whose book reads a high-school geometry textbook for topics to connect to geometric
algebra; that repo's `tasks/sources/pearson-geo.toml` is the worked example. The task that
produced this is `external-source-outlines-and-coverage-tracking.md` in
github.com/billsix/runClaudeInContainer (under `tasks/`, then `tasks/archive/`).

## The three parts

| Part | Where | Written by | Changes when |
|---|---|---|---|
| The **outline** | `tasks/sources/<key>.toml` | the maintainer, through an agent | he reads more of the source, or decides something |
| The **coverage tags** | a `covers:` comment in a product file; a `**Source:**` line in a task | whoever writes the page or the task | the product covers a topic, or a task plans to |
| The **status** | nowhere: `source_coverage.py` prints it | nobody | never stored |

**Status is derived, never written down.** This is the rule review records already follow
(`repo-review-conventions.md`, "Lifecycle"). An outline file has no "covered" field, and a
reference doc has no hand-kept coverage column: a typed status is wrong the first time
someone forgets it, and nobody can tell. The two tools share one citation form, a task's
`**Source:** <path> <item IDs>` line, so a task can cite a review record and an outline on
the same line.

## The outline file: `tasks/sources/<key>.toml`

`tasks/sources/` is a sibling of `tasks/reference/`: durable, never archived, with a
`.keep`. One file per source; the file's stem is the source's **key**.

```toml
# Banner: what this is, which copy it was typed from, what may and may not be added.
citation = "Charles et al., *Geometry: Common Core*, Pearson, 2012"
isbn = "978-0-13-328115-6"
licence = "all rights reserved"
entered = 2026-11-27            # the date of entries that carry no `added` of their own

[[entries]]
id = "within-triangles"         # a chapter
number = "5"
title = "Relationships Within Triangles"

[[entries]]
id = "within-triangles/medians"         # a lesson
number = "5-4"
title = "Medians and Altitudes"
page = 312
page_verified = false
decision = "want"

[[entries]]
id = "within-triangles/medians/centroid"    # a topic inside the lesson
title = "centroid"
summary = "where the three medians meet; (a + b + c) / 3"
decision = "skip"
reason = "named on the page, not built"
added = 2026-12-14
```

| Field | Meaning |
|---|---|
| `id` | required; the entry's permanent name (next section) |
| `title` | the source's own title for a chapter or lesson; for a topic, its name |
| `number` | the source's number for it (`5`, `5-4`); may be corrected later |
| `page`, `page_verified` | the source's page, and whether the maintainer checked it against his copy (default `false`) |
| `page_note` | what the page number points at, when it is not the entry's first page |
| `summary` | the topic **in the project's own words** |
| `decision` | `want`, `skip` or `undecided` (the default) |
| `reason` | required with `skip` |
| `standards` | codes shared across sources, e.g. Common Core `["HSG-CO.C.10"]` |
| `added` | the date the entry was written, when it is later than the file's `entered` |
| `withdrawn` | `true` for an entry made by mistake that something still cites |
| `note` | anything else a later reader needs (a doubt to check against the copy) |

The tool reads `id`, `title`, `number`, `page`, `page_verified`, `decision`, `reason`,
`added`, `withdrawn` and the file's `citation` and `entered`. The other fields are for
readers.

### Entry IDs are names, not numbers, and never change

An ID is lower-case words, `-` inside a level and `/` between levels:
`<chapter>/<lesson>/<topic>`. A product file and a task name an entry by its **full ID**,
`<key>/<id>` (`pearson-geo/within-triangles/medians`).

- **Use a short name, not the source's number.** A lesson number or a page number can turn
  out wrong and be corrected; an ID that pages and tasks already cite cannot. So the number
  is the `number` field, and the ID is a name that would still be right.
- **An ID is fixed once written.** Never rename one and never reuse one. Correct a title,
  number or page by editing the entry.
- **An entry made by mistake** is deleted only if nothing cites it; otherwise it gets
  `withdrawn = true` and the tool reports whatever still points at it.

### The outline grows, a few entries at a time

The maintainer adds to an outline over months. So:

- **A partial outline is valid.** Three lessons of one chapter is a complete file. A lesson
  may be present without its chapter. The tool never reports a missing entry.
- **Adding an entry updates nothing else.** A new entry is "not addressed" until a page
  tags it or a task cites it.
- **A new source is a new file** in the same format. One product page may carry tags for
  several sources.

**When the maintainer asks to add to an outline** ("add lesson 5-4, medians and altitudes,
p. 312, I want medians"), the agent:

1. reads the outline file's banner and the neighbouring entries;
2. writes the entries, with `added = <today>`, the page as he gave it and
   `page_verified = true` only if he said he read it from his copy; a decision only where
   he stated one;
3. picks IDs by the rules above, checking that none exists already;
4. runs `source_coverage.py <key> --since <today>` and reports the new rows and any
   problem lines;
5. stages the file.

It does not add entries he did not ask for, and it does not fill `summary` from a source it
has not read.

## What may be committed (copyright)

*Not legal advice; the sources are quoted so the maintainer can judge. Ask before
committing anything this section does not clearly allow.*

- **Titles, numbers and bare lists are not protected.** 37 CFR 202.1(a) lists as not
  subject to copyright "Words and short phrases such as names, titles, and slogans" and
  "mere listing of ingredients or contents" (https://www.law.cornell.edu/cfr/text/37/202.1);
  Copyright Office Circular 33 (revised 03/2021) says the same
  (https://www.copyright.gov/circs/circ33.pdf).
- **Ideas are not protected; their expression is.** 17 U.S.C. 102(b): no protection for
  "any idea, procedure, process, system", concepts or principles
  (https://www.law.cornell.edu/uscode/text/17/102). A definition's mathematics is free. The
  publisher's wording of it, the figures, the worked examples and the exercises are not.
- **A whole table of contents, verbatim, is the soft spot.** A compilation can have thin
  protection for its selection and arrangement (Feist v. Rural). No ruling on a textbook's
  table of contents was found (2026-11-27). The fair-use factors
  (https://www.law.cornell.edu/uscode/text/17/107) favour a factual citation index that
  replaces nothing, but that is a judgment.

So, for a source that is all rights reserved, an outline file holds:

- **yes:** chapter and lesson titles, numbers, page numbers, the names of topics, and
  summaries written in the project's own words;
- **no:** the source's definitions, theorem statements, exercises, examples, figures or
  captions, copied or closely paraphrased. If the product needs the exact wording, it
  quotes one short passage, attributed, where a reader needs it; the outline file is not
  the place;
- **out of git entirely:** scans, photographs and verbatim study notes. A repository with a
  public remote publishes whatever is committed.

For an openly licensed source (CC BY, CC BY-SA), record the licence and its required
attribution in the banner; quoting is then a matter of following that licence. Check the
edition: Illustrative Mathematics' first edition is CC BY 4.0 and its v.360 edition is
CC BY-NC 4.0 (https://www.illustrativemathematics.org/terms-of-use, read 2026-11-27).

## Tagging the product: `covers:`

A product file says which entries it covers in a comment, in that file's comment syntax,
holding `covers:` and one or more full IDs separated by commas:

```rst
.. covers: pearson-geo/within-triangles/medians/median, pearson-geo/tools/segments/midpoint
```

```python
# covers: pearson-geo/area/parallelograms-and-triangles
```

- **Put the tag where the coverage is**: directly above the section, equation or cell that
  builds the topic. The tool reports the file; a reader of the file finds the tag.
- **A tag counts for the entry it names, not for the entries under it.** Tag the most
  specific entry the passage covers; tag a lesson only when the page covers the lesson as
  a whole.
- **Tag when the page is written**, as part of the same unit of work, the way a `twin:` tag
  or a changelog entry is.
- **Tags point at the source, never at the product's page numbers.** Those shift with every
  revision; the tool finds the file by itself.
- Only tokens that start with a known key count, so the words "covers:" in prose are not a
  tag. A tag naming an entry that is not in the outline is reported as a problem.

Files under `tasks/` are not searched for tags: a task or reference doc that names an
entry is not coverage.

## Citing an outline from a task

A task about one or more entries names them on its `**Source:**` line, after the outline's
path:

```markdown
**Source:** tasks/sources/pearson-geo.toml circles/tangent-lines, circles/chords-and-arcs
```

While that task is in `tasks/`, those entries are **planned**. When it is archived, they
are covered only if a product file tags them; an entry cited by an archived task and tagged
nowhere is reported as a problem, because the task finished without its page saying so.

## The report: `source_coverage.py`

A shared tool beside this doc, run in place from the project's repo root (never copied
into the project): `python3 ~/.claude/reference/source_coverage.py [KEY ...]`, or
`/source-coverage`. In a Crush session it is `~/.config/crush/reference/source_coverage.py`.

| Status | Means |
|---|---|
| `covered` | at least one product file tags the entry |
| `planned` | no file tags it, and an open task cites it |
| `skipped` | neither, and its decision is `skip` |
| `not-addressed` | none of the above |
| `withdrawn` | the entry is marked `withdrawn = true` |

- `--status not-addressed` (repeatable) filters by status; the summary line also counts the
  entries that are **wanted and not addressed**, which is the list of what to write next.
- `--since 2026-12-01` shows the entries added on or after a date.
- `--unverified-pages` shows the entries whose page number the maintainer has not checked
  against his copy. In the table such a page carries a `?`.
- `--cite pearson-geo/within-triangles/medians` prints the citation of one entry: the
  file's `citation`, then the entry's number, title and page (a topic takes the number and
  page of its lesson). Use it when a page cites the source, so the wording is the same
  everywhere.
- A "Problems" section lists duplicate or malformed IDs, a `skip` with no reason, tags and
  citations of entries that do not exist, and a skipped or withdrawn entry that something
  still points at.

It is a report, not a gate: it exits 0 whatever it finds, and no `make` target runs it.
Deciding what an uncovered entry means needs the maintainer.

## What stays in a reference doc

The prose about the source: how its ideas map onto the project's (in geometricalgebra, the
vector construction that builds each textbook object), and what the project claims about
that relation. The reference doc links to the outline file and names the report command.
It carries no column saying where, or whether, the project covers an entry.

## Why not something simpler, or something that already existed

- **A reference doc with a hand-kept "Where" column** is what geometricalgebra had. It
  drifts; the first deep review found exactly such a table gone false.
- **A layered reference set's `README.md` status board** is hand-kept too.
- **`review_status.py` as it stands** reads a Markdown record with two heading levels and
  `F<n>` follow-up IDs, and its "done" means "the citing task is archived". An outline needs
  three levels, per-entry fields, and coverage read from the product, so it is a sibling
  tool with the same `**Source:**` convention. A generated, committed status file (option
  (C) of `tasks/review-record-shows-dispositions.md` in
  github.com/billsix/runClaudeInContainer) is decided there; if it is chosen, both tools
  gain the same `--write`.
