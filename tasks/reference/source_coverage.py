#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# SHARED TOOL -- keep every copy byte-identical.
# Canonical: runClaudeInContainer tasks/reference/source_coverage.py
#   (github.com/billsix/runClaudeInContainer). Mirrored in runCrushInContainer
#   tasks/reference/ and its baked client copy. Run from a project's repo root:
#     python3 ~/.claude/reference/source_coverage.py [KEY ...]
#   (Crush: ~/.config/crush/reference/source_coverage.py). Used by
#   /source-coverage; conventions in external-source-outlines.md.
# ---------------------------------------------------------------------------
"""Report which entries of an external source's outline a project has covered.

A project keeps the outline of a book it draws on (chapters, lessons, topics, page
numbers) in ``tasks/sources/<key>.toml``.  The outline says what the source contains and
what the maintainer has decided about each entry; it never says whether the project has
covered it.  That is derived here, each time, from two places:

* a **tag** in a product file (a book page, a notebook, a proof): a comment holding
  ``covers:`` followed by one or more full entry IDs (``<key>/<entry id>``), separated
  by commas;
* a task's ``**Source:**`` line naming the outline file and the entry IDs the task is
  about (``**Source:** tasks/sources/<key>.toml within-triangles/medians``).

Each entry is then one of:

* **covered** -- at least one product file tags it;
* **planned** -- no file tags it, and a task still in ``tasks/`` cites it;
* **skipped** -- neither, and its ``decision`` is ``skip``;
* **not-addressed** -- none of the above;
* **withdrawn** -- the entry is marked ``withdrawn = true``.

A tag or citation counts for exactly the entry it names, not for the entries under it.

Usage::

    source_coverage.py [KEY ...] [--status STATUS] [--since DATE]
                       [--unverified-pages] [--cite FULL_ID]

With no KEY, every ``tasks/sources/*.toml`` is reported.  ``--cite`` prints the citation
of one entry (``<key>/<entry id>``) and nothing else.
"""

import argparse
import dataclasses
import datetime
import enum
import pathlib
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SOURCES_DIR: str = "tasks/sources"
TAG_RE: re.Pattern[str] = re.compile(r"covers:\s*(.+)$")
SOURCE_RE: re.Pattern[str] = re.compile(r"^\*\*Source:\*\*(.*)$")
ENTRY_ID_RE: re.Pattern[str] = re.compile(
    r"[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*"
)
LARGEST_FILE_READ: int = 2_000_000


class Decision(enum.StrEnum):
    """What the maintainer has decided about an entry.

    The values are the words written in the outline file's ``decision`` field:
    ``WANT`` (the project should cover it), ``SKIP`` (it should not; the entry's
    ``reason`` says why) and ``UNDECIDED`` (not decided yet; the default).
    """

    WANT = "want"
    SKIP = "skip"
    UNDECIDED = "undecided"


class Status(enum.StrEnum):
    """An entry's derived status.  The values are the words ``--status`` accepts."""

    COVERED = "covered"
    PLANNED = "planned"
    SKIPPED = "skipped"
    NOT_ADDRESSED = "not-addressed"
    WITHDRAWN = "withdrawn"


@dataclasses.dataclass(frozen=True)
class Entry:
    """One entry of an outline: a chapter, a lesson or a topic inside a lesson."""

    id: str
    title: str
    number: str
    page: str
    page_verified: bool
    decision: Decision
    reason: str
    added: datetime.date | None
    withdrawn: bool


@dataclasses.dataclass(frozen=True)
class Source:
    """An outline file: its key, the source's citation, its entries in file order."""

    key: str
    citation: str
    path: str
    entries: tuple[Entry, ...]


@dataclasses.dataclass(frozen=True)
class Citation:
    """A task's ``**Source:**`` line that names an outline file."""

    task: pathlib.Path
    done: bool
    ids: tuple[str, ...]


def parse_source(key: str, path: str, data: Mapping[str, Any]) -> Source:
    """The outline held in the parsed TOML ``data`` of ``tasks/sources/<key>.toml``.

    An entry without ``added`` takes the file's ``entered`` date; one without
    ``decision`` is undecided.

    >>> src: Source = parse_source("b", "tasks/sources/b.toml", {
    ...     "citation": "A Book, 2012",
    ...     "entered": datetime.date(2026, 11, 27),
    ...     "entries": [
    ...         {"id": "area", "title": "Area", "number": "10"},
    ...         {"id": "area/sector", "title": "sector", "page": 663,
    ...          "decision": "skip", "reason": "needs arc length"},
    ...     ],
    ... })
    >>> [(e.id, e.page, e.decision.value) for e in src.entries]
    [('area', '', 'undecided'), ('area/sector', '663', 'skip')]
    >>> [str(e.added) for e in src.entries]
    ['2026-11-27', '2026-11-27']
    """
    entered: datetime.date | None = data.get("entered")
    return Source(
        key,
        str(data.get("citation", key)),
        path,
        tuple(
            Entry(
                id=str(raw["id"]),
                title=str(raw.get("title", "")),
                number=str(raw.get("number", "")),
                page=str(raw.get("page", "")),
                page_verified=bool(raw.get("page_verified", False)),
                decision=Decision(raw.get("decision", Decision.UNDECIDED.value)),
                reason=str(raw.get("reason", "")),
                added=raw.get("added", entered),
                withdrawn=bool(raw.get("withdrawn", False)),
            )
            for raw in data.get("entries", [])
        ),
    )


def tagged_ids(line: str, keys: Iterable[str]) -> list[str]:
    """The full entry IDs a line tags: tokens after ``covers:`` that start with a key.

    A token belonging to no known key is ignored, so prose such as "this covers: a lot"
    is not a tag.

    >>> tagged_ids(".. covers: geo/area/sector, geo/circles", ["geo"])
    ['geo/area/sector', 'geo/circles']
    >>> tagged_ids("# covers: geo/area -->", ["geo"])
    ['geo/area']
    >>> tagged_ids("this covers: a lot", ["geo"])
    []
    """
    match: re.Match[str] | None = TAG_RE.search(line)
    known: frozenset[str] = frozenset(keys)
    return (
        []
        if match is None
        else [
            token
            for token in (t.strip("`.;") for t in re.split(r"[,\s]+", match.group(1)))
            if "/" in token and token.split("/")[0] in known
        ]
    )


def product_files(repo: pathlib.Path) -> list[str]:
    """Files that may carry tags: tracked or new, not ignored, outside ``tasks/``."""
    listed: str = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [name for name in listed.splitlines() if not name.startswith("tasks/")]


def tags(repo: pathlib.Path, keys: Sequence[str]) -> dict[str, list[str]]:
    """Each tagged full entry ID, with the product files that tag it."""
    found: dict[str, list[str]] = {}
    name: str
    for name in product_files(repo):
        file: pathlib.Path = repo / name
        if not file.is_file() or file.stat().st_size > LARGEST_FILE_READ:
            continue
        try:
            text: str = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "covers:" in text:
            line: str
            for line in text.splitlines():
                full_id: str
                for full_id in tagged_ids(line, keys):
                    if name not in found.setdefault(full_id, []):
                        found[full_id].append(name)
    return found


def refs_for(source_line: str, outline: str) -> str:
    """The part of a ``**Source:**`` line that belongs to the outline file ``outline``.

    A Source line may cite several files; each one's entry IDs run from its path to the
    next ``tasks/`` path.

    >>> line: str = " tasks/sources/a.toml x/y, z; tasks/review/r.md §2"
    >>> refs_for(line, "tasks/sources/a.toml")
    ' x/y, z; '
    """
    after: str = source_line[source_line.index(outline) + len(outline) :]
    following: int = after.find("tasks/")
    return after if following == -1 else after[:following]


def cited_ids(refs: str) -> tuple[str, ...]:
    """The entry IDs in the text after an outline's path, in order, without repeats.

    >>> cited_ids(" `area/sector`, circles; area/sector")
    ('area/sector', 'circles')
    """
    return tuple(
        dict.fromkeys(
            token
            for token in (t.strip("`.") for t in re.split(r"[,;\s]+", refs))
            if ENTRY_ID_RE.fullmatch(token) is not None
        )
    )


def citations(repo: pathlib.Path, outline: str) -> list[Citation]:
    """Every task's ``**Source:**`` line that names ``outline``, open and archived."""
    open_tasks: list[pathlib.Path] = sorted((repo / "tasks").glob("*.md"))
    done_tasks: list[pathlib.Path] = sorted((repo / "tasks" / "archive").rglob("*.md"))
    found: list[Citation] = []
    task: pathlib.Path
    done: bool
    for task, done in [
        *((t, False) for t in open_tasks),
        *((t, True) for t in done_tasks),
    ]:
        line: str
        for line in task.read_text(encoding="utf-8").splitlines():
            match: re.Match[str] | None = SOURCE_RE.match(line)
            if match is not None and outline in match.group(1):
                found.append(
                    Citation(
                        task.relative_to(repo),
                        done,
                        cited_ids(refs_for(match.group(1), outline)),
                    )
                )
    return found


def status_of(
    entry: Entry, pages: Sequence[str], cited_by: Sequence[Citation]
) -> Status:
    """An entry's status, from the files that tag it and the tasks that cite it.

    >>> e: Entry = Entry("a", "A", "", "", False, Decision.SKIP, "why", None, False)
    >>> open_task: Citation = Citation(pathlib.Path("tasks/t.md"), False, ("a",))
    >>> status_of(e, ["book/a.rst"], []).value, status_of(e, [], [open_task]).value
    ('covered', 'planned')
    >>> status_of(e, [], []).value
    'skipped'
    >>> status_of(dataclasses.replace(e, decision=Decision.WANT), [], []).value
    'not-addressed'
    """
    if entry.withdrawn:
        return Status.WITHDRAWN
    elif pages:
        return Status.COVERED
    elif any(not c.done for c in cited_by):
        return Status.PLANNED
    elif entry.decision is Decision.SKIP:
        return Status.SKIPPED
    else:
        return Status.NOT_ADDRESSED


def inherited(source: Source, entry_id: str, field: str) -> str:
    """An entry's ``field``, or its nearest parent's that has one (``""`` if none).

    >>> want: Decision = Decision.WANT
    >>> lesson: Entry = Entry("a/b", "B", "5-4", "312", True, want, "", None, False)
    >>> topic: Entry = Entry("a/b/c", "c", "", "", False, want, "", None, False)
    >>> inherited(Source("k", "K", "p", (lesson, topic)), "a/b/c", "page")
    '312'
    """
    by_id: dict[str, Entry] = {e.id: e for e in source.entries}
    parts: list[str] = entry_id.split("/")
    return next(
        (
            value
            for value in (
                str(getattr(by_id[candidate], field))
                for candidate in (
                    "/".join(parts[:end]) for end in range(len(parts), 0, -1)
                )
                if candidate in by_id
            )
            if value
        ),
        "",
    )


def citation_text(source: Source, entry_id: str) -> str:
    """How to cite an entry: the source, then the entry's number, title and page.

    >>> want: Decision = Decision.WANT
    >>> lesson: Entry = Entry("m", "Medians", "5-4", "12", False, want, "", None, False)
    >>> citation_text(Source("k", "A Book, 2012", "p", (lesson,)), "m")
    'A Book, 2012, 5-4, "Medians", p. 12 (page not checked against the source)'
    """
    entry: Entry = next(e for e in source.entries if e.id == entry_id)
    number: str = inherited(source, entry_id, "number")
    page: str = inherited(source, entry_id, "page")
    verified: bool = any(
        e.page_verified
        for e in source.entries
        if e.page == page and (entry_id == e.id or entry_id.startswith(e.id + "/"))
    )
    return ", ".join(
        part
        for part in (
            source.citation,
            number,
            f'"{entry.title}"' if entry.title else "",
            (
                f"p. {page}"
                + ("" if verified else " (page not checked against the source)")
                if page
                else ""
            ),
        )
        if part
    )


def problems(
    source: Source, tagged: Mapping[str, Sequence[str]], cited_by: Sequence[Citation]
) -> list[str]:
    """What is wrong in an outline or in what points at it, one line each."""
    ids: list[str] = [e.id for e in source.entries]
    known: frozenset[str] = frozenset(ids)
    prefix: str = source.key + "/"
    return [
        *(
            f"duplicate entry ID `{i}`"
            for i in sorted({i for i in ids if ids.count(i) > 1})
        ),
        *(
            f"`{e.id}` is not a valid entry ID (lower-case words, `-` inside a level, "
            "`/` between levels)"
            for e in source.entries
            if ENTRY_ID_RE.fullmatch(e.id) is None
        ),
        *(
            f"`{e.id}` is skipped without a `reason`"
            for e in source.entries
            if e.decision is Decision.SKIP and not e.reason
        ),
        *(
            f"`{full_id}` is tagged in {', '.join(files)} but is not in the outline"
            for full_id, files in sorted(tagged.items())
            if full_id.startswith(prefix) and full_id[len(prefix) :] not in known
        ),
        *(
            f"`{c.task}` cites `{i}`, which is not in the outline"
            for c in cited_by
            for i in c.ids
            if i not in known
        ),
        *(
            f"`{c.task}` cites the outline without an entry ID"
            for c in cited_by
            if not c.ids
        ),
        *(
            f"`{e.id}` is marked skip or withdrawn, but something tags or cites it"
            for e in source.entries
            if (e.withdrawn or e.decision is Decision.SKIP)
            and (prefix + e.id in tagged or any(e.id in c.ids for c in cited_by))
        ),
        *(
            f"`{e.id}`: an archived task cites it, but no product file tags it"
            for e in source.entries
            if prefix + e.id not in tagged
            and any(c.done and e.id in c.ids for c in cited_by)
            and not any(not c.done and e.id in c.ids for c in cited_by)
        ),
    ]


def report(
    repo: pathlib.Path,
    source: Source,
    tagged: Mapping[str, Sequence[str]],
    wanted: Sequence[Status],
    since: datetime.date | None,
    unverified_pages: bool,
) -> str:
    """The Markdown report of one outline: summary, problems, a row per entry kept."""
    cited_by: list[Citation] = citations(repo, source.path)
    rows: list[tuple[Entry, Status, list[str], list[Citation]]] = [
        (
            e,
            status_of(e, pages, cites),
            list(pages),
            cites,
        )
        for e in source.entries
        for pages, cites in [
            (
                tagged.get(f"{source.key}/{e.id}", []),
                [c for c in cited_by if e.id in c.ids],
            )
        ]
    ]
    counts: str = ", ".join(
        f"{sum(1 for row in rows if row[1] is state)} {state.value}" for state in Status
    )
    wanted_open: int = sum(
        1
        for e, state, _, _ in rows
        if e.decision is Decision.WANT and state is Status.NOT_ADDRESSED
    )
    unverified: int = sum(1 for e in source.entries if e.page and not e.page_verified)
    kept: list[tuple[Entry, Status, list[str], list[Citation]]] = [
        row
        for row in rows
        if (not wanted or row[1] in wanted)
        and (since is None or (row[0].added is not None and row[0].added >= since))
        and (not unverified_pages or (row[0].page != "" and not row[0].page_verified))
    ]
    found: list[str] = problems(source, tagged, cited_by)
    return "\n".join(
        [
            f"# Coverage of `{source.path}`",
            "",
            f"{source.citation}.",
            "",
            f"{len(rows)} entries: {counts}. {wanted_open} wanted and not addressed; "
            f"{unverified} page numbers not checked against the source.",
            *(["", "## Problems", "", *(f"- {p}" for p in found)] if found else []),
            "",
            "## Entries" + ("" if len(kept) == len(rows) else f" ({len(kept)} shown)"),
            "",
            "| Entry | No. | Page | Decision | Status | Where | Title |",
            "|---|---|---|---|---|---|---|",
            *(
                f"| `{e.id}` | {e.number or '—'} "
                f"| {(e.page + ('' if e.page_verified else '?')) if e.page else '—'} "
                f"| {e.decision.value} | {state.value} | "
                + (
                    ", ".join(
                        [
                            *(f"`{page}`" for page in pages),
                            *(
                                f"task `{c.task.stem}`" + ("" if c.done else " (open)")
                                for c in cites
                            ),
                        ]
                    )
                    or "—"
                )
                + f" | {e.title} |"
                for e, state, pages, cites in kept
            ),
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Print the coverage report of each outline (or one entry's citation)."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0]
    )
    parser.add_argument("keys", nargs="*", help="outline keys (default: every outline)")
    parser.add_argument(
        "--status",
        action="append",
        choices=[state.value for state in Status],
        help="show only entries with this status (repeatable)",
    )
    parser.add_argument(
        "--since",
        type=datetime.date.fromisoformat,
        help="show only entries added on or after this date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--unverified-pages",
        action="store_true",
        help="show only entries whose page number was not checked against the source",
    )
    parser.add_argument("--cite", metavar="FULL_ID", help="print one entry's citation")
    args: argparse.Namespace = parser.parse_args(argv)
    repo: pathlib.Path = pathlib.Path.cwd()
    files: list[pathlib.Path] = sorted((repo / SOURCES_DIR).glob("*.toml"))
    sources: list[Source] = [
        parse_source(
            file.stem,
            f"{SOURCES_DIR}/{file.name}",
            tomllib.loads(file.read_text("utf-8")),
        )
        for file in files
    ]
    if not sources:
        raise SystemExit(f"source_coverage: no outlines under {SOURCES_DIR}/")
    unknown: list[str] = [k for k in args.keys if k not in {s.key for s in sources}]
    if unknown:
        raise SystemExit(f"source_coverage: no outline for {', '.join(unknown)}")
    if args.cite is not None:
        key: str
        entry_id: str
        key, _, entry_id = args.cite.partition("/")
        cited: Source | None = next((s for s in sources if s.key == key), None)
        if cited is None or all(e.id != entry_id for e in cited.entries):
            raise SystemExit(f"source_coverage: no entry {args.cite}")
        sys.stdout.write(citation_text(cited, entry_id) + "\n")
        return 0
    tagged: dict[str, list[str]] = tags(repo, [s.key for s in sources])
    sys.stdout.write(
        "\n\n".join(
            report(
                repo,
                source,
                tagged,
                [Status(value) for value in args.status or []],
                args.since,
                args.unverified_pages,
            )
            for source in sources
            if not args.keys or source.key in args.keys
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
