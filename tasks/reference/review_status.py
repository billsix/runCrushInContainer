#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# SHARED TOOL -- keep every copy byte-identical.
# Canonical: runClaudeInContainer tasks/reference/review_status.py
#   (github.com/billsix/runClaudeInContainer). Mirrored in runCrushInContainer
#   tasks/reference/ and its baked client copy. Run from a project's repo root:
#     python3 ~/.claude/reference/review_status.py [tasks/review/YYYY/MM/DD/<slug>.md]
#   (Crush: ~/.config/crush/reference/review_status.py). Used by /review-status
#   and by /audit-repo deep's "Carried over" step; conventions in
#   repo-review-conventions.md.
# ---------------------------------------------------------------------------
"""Derive the status of a frozen review record from the tasks that cite it.

A review record (``tasks/review/<YYYY>/<MM>/<DD>/<slug>.md``) is never edited, so it
cannot say what has been done.  Every task made from it carries a ``**Source:**`` line
naming the record, the sections and the follow-up IDs it came from
(``... repo-review.md §5.1 F3``).  This tool reads those lines from ``tasks/*.md``
(open) and ``tasks/archive/**/*.md`` (done) and reports, for the record's numbered
sections (a section counts its subsections' citations) and for each of its
"Suggested follow-ups" bullets:

* **done** -- every task citing it is archived (and at least one does);
* **open** -- at least one task citing it is still in ``tasks/``;
* **untracked** -- no task cites it.

A follow-up bullet that carries an ID (``- [F3] Fix ...``) is matched only by tasks
that cite that ID, so its status is exact.  A bullet without an ID (records written
before IDs were required) is matched by its sections, and its status is marked
"(by §)": a section can hold several findings, so an archived task citing the section
does not prove *this* bullet is done.  A section's status is always by citation.  A
task that cites the record with neither a section nor an ID is listed separately, since
it cannot be placed.

Usage::

    review_status.py [RECORD] [--carried-over]

With no RECORD, the latest record under ``tasks/review/`` is used.  ``--carried-over``
prints a Markdown "Carried over from the previous review" section instead of the table.
"""

import argparse
import dataclasses
import pathlib
import re
import sys
from collections.abc import Iterable, Sequence

SECTION_RE: re.Pattern[str] = re.compile(r"^#{2,3} (\d+(?:\.\d+)*)\.? (.+)$")
SECTION_REF_RE: re.Pattern[str] = re.compile(r"§(\d+(?:\.\d+)*)")
SOURCE_RE: re.Pattern[str] = re.compile(r"^\*\*Source:\*\*(.*)$")
FOLLOW_UP_ID_RE: re.Pattern[str] = re.compile(r"\bF\d+\b")
BULLET_ID_RE: re.Pattern[str] = re.compile(r"^\[(F\d+)\]\s*")
FOLLOW_UPS_HEADING: str = "## Suggested follow-ups"
STATES: tuple[str, ...] = ("done", "open", "untracked")


@dataclasses.dataclass(frozen=True)
class Citation:
    """A task's ``**Source:**`` line that names the record."""

    task: pathlib.Path
    done: bool
    sections: tuple[str, ...]
    follow_up_ids: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class FollowUp:
    """One "Suggested follow-ups" bullet: its tier, ID (``""`` if none), text, sections."""

    tier: str
    id: str
    text: str
    sections: tuple[str, ...]


def section_refs(text: str) -> tuple[str, ...]:
    """The section numbers cited in ``text``, in order, without repeats.

    >>> section_refs("From the record §5.1, §6.1 and §5.1 again")
    ('5.1', '6.1')
    >>> section_refs("no sections")
    ()
    """
    return tuple(dict.fromkeys(SECTION_REF_RE.findall(text)))


def covers(cited: str, section: str) -> bool:
    """True when a citation of ``cited`` covers ``section``: the same section, or a parent.

    >>> covers("4", "4.1"), covers("4.1", "4.1"), covers("4.1", "4.12"), covers("4.1", "4")
    (True, True, False, False)
    """
    return section == cited or section.startswith(cited + ".")


def parse_sections(lines: Sequence[str]) -> list[tuple[str, str]]:
    """The record's numbered ``##``/``###`` headings, as ``(number, title)`` pairs.

    >>> parse_sections(["## 1. Docs", "text", "### 1.2 Out of date", "## Coverage"])
    [('1', 'Docs'), ('1.2', 'Out of date')]
    """
    found: list[tuple[str, str]] = []
    line: str
    for line in lines:
        match: re.Match[str] | None = SECTION_RE.match(line)
        if match is not None:
            found.append((match.group(1), match.group(2).strip()))
    return found


def parse_follow_ups(lines: Sequence[str]) -> list[FollowUp]:
    """The bullets under "Suggested follow-ups", grouped by their bold tier label.

    A bullet's continuation lines are joined to it; a tier label is a top-level bullet
    such as ``- **Required:** ...``, and the bullets indented under it belong to it.  A
    leading ``[F<n>]`` is the bullet's ID.

    >>> parse_follow_ups([
    ...     "## Suggested follow-ups",
    ...     "- **Required:** wrong in front of a reader.",
    ...     "  - Fix `project` (§4.1).",
    ...     "  - Fix the three generator bugs",
    ...     "    in one pass (§5.1).",
    ...     "- **Optional:**",
    ...     "  - [F3] Lint (§4.3, §5.4).",
    ...     "## Open questions",
    ... ])  # doctest: +NORMALIZE_WHITESPACE
    [FollowUp(tier='Required', id='', text='Fix `project` (§4.1).', sections=('4.1',)),
     FollowUp(tier='Required', id='',
              text='Fix the three generator bugs in one pass (§5.1).', sections=('5.1',)),
     FollowUp(tier='Optional', id='F3', text='Lint (§4.3, §5.4).',
              sections=('4.3', '5.4'))]
    """
    follow_ups: list[FollowUp] = []
    inside: bool = False
    tier: str = ""
    current: list[str] = []

    def flush() -> None:
        if current:
            text: str = " ".join(current)
            id_match: re.Match[str] | None = BULLET_ID_RE.match(text)
            bullet_id: str = id_match.group(1) if id_match is not None else ""
            body: str = text[id_match.end() :] if id_match is not None else text
            follow_ups.append(FollowUp(tier, bullet_id, body, section_refs(body)))
            current.clear()

    line: str
    for line in lines:
        if line.startswith(FOLLOW_UPS_HEADING):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("#"):
            break
        tier_match: re.Match[str] | None = re.match(r"^- \*\*([A-Za-z]+):\*\*", line)
        bullet_match: re.Match[str] | None = re.match(r"^\s{2,}- (.*)$", line)
        match (tier_match, bullet_match, line.strip()):
            case (re.Match() as found, _, _):
                flush()
                tier = found.group(1)
            case (None, re.Match() as found, _):
                flush()
                current.append(found.group(1).strip())
            case (None, None, ""):
                flush()
            case (None, None, text):
                if current:
                    current.append(text)
    flush()
    return follow_ups


def citations(repo: pathlib.Path, record: str) -> list[Citation]:
    """Every task's ``**Source:**`` line that names ``record``, open and archived."""
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
            if match is not None and record in match.group(1):
                found.append(
                    Citation(
                        task.relative_to(repo),
                        done,
                        section_refs(match.group(1)),
                        tuple(dict.fromkeys(FOLLOW_UP_ID_RE.findall(match.group(1)))),
                    )
                )
    return found


def state_of(matching: Sequence[Citation]) -> str:
    """``done`` / ``open`` / ``untracked`` for the citations that cover an item.

    >>> state_of([]), state_of([Citation(pathlib.Path("a.md"), True, (), ())])
    ('untracked', 'done')
    """
    match (len(matching), all(c.done for c in matching)):
        case (0, _):
            return "untracked"
        case (_, True):
            return "done"
        case _:
            return "open"


def status(
    sections: Iterable[str],
    cited_by: Sequence[Citation],
    include_subsections: bool = False,
) -> tuple[str, list[Citation]]:
    """The status of an item citing ``sections``, and the citations that cover it.

    With ``include_subsections``, a citation of a subsection also counts (a section's own
    row: ``§1`` is open while a task citing ``§1.2`` is).

    >>> c = Citation(pathlib.Path("tasks/a.md"), False, ("4.1",), ())
    >>> d = Citation(pathlib.Path("tasks/archive/b.md"), True, ("5",), ("F2",))
    >>> status(["4.1"], [c, d])[0], status(["5.2"], [c, d])[0], status(["6"], [c, d])[0]
    ('open', 'done', 'untracked')
    >>> status(["4"], [c, d])[0], status(["4"], [c, d], include_subsections=True)[0]
    ('untracked', 'open')
    """
    wanted: list[str] = list(sections)
    matching: list[Citation] = [
        c
        for c in cited_by
        if any(
            covers(ref, s) or (include_subsections and covers(s, ref))
            for ref in c.sections
            for s in wanted
        )
    ]
    return state_of(matching), matching


def follow_up_status(
    follow_up: FollowUp, cited_by: Sequence[Citation]
) -> tuple[str, list[Citation]]:
    """A follow-up's status: by its ID when it has one, else by section, marked "(by §)".

    >>> d = Citation(pathlib.Path("tasks/archive/b.md"), True, ("5",), ("F2",))
    >>> follow_up_status(FollowUp("Required", "F2", "x", ("5",)), [d])[0]
    'done'
    >>> follow_up_status(FollowUp("Required", "F9", "x", ("5",)), [d])[0]
    'untracked'
    >>> follow_up_status(FollowUp("Required", "", "x", ("5.1",)), [d])[0]
    'done (by §)'
    """
    if follow_up.id:
        by_id: list[Citation] = [c for c in cited_by if follow_up.id in c.follow_up_ids]
        return state_of(by_id), by_id
    state: str
    matching: list[Citation]
    state, matching = status(follow_up.sections, cited_by)
    return (state if state == "untracked" else f"{state} (by §)"), matching


def latest_record(repo: pathlib.Path) -> pathlib.Path:
    """The newest record under ``tasks/review/`` (its path sorts by date)."""
    records: list[pathlib.Path] = sorted((repo / "tasks" / "review").rglob("*.md"))
    if not records:
        raise SystemExit("review_status: no records under tasks/review/")
    return records[-1]


def table(rows: Iterable[tuple[str, str, str, list[Citation]]]) -> str:
    """A Markdown table of (item, title, status, citations) rows."""
    out: list[str] = ["| Item | Status | Tasks | |", "|---|---|---|---|"]
    item: str
    title: str
    state: str
    cited: list[Citation]
    for item, title, state, cited in rows:
        tasks: str = ", ".join(
            f"`{c.task.stem}`" + ("" if c.done else " (open)") for c in cited
        )
        out.append(f"| {item} | {state} | {tasks or '—'} | {title} |")
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    """Print the record's status table (or its "Carried over" section)."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "record", nargs="?", help="the review record (default: the latest)"
    )
    parser.add_argument(
        "--carried-over", action="store_true", help="print a Carried-over section"
    )
    args: argparse.Namespace = parser.parse_args(argv)
    repo: pathlib.Path = pathlib.Path.cwd()
    record_path: pathlib.Path = (
        repo / args.record if args.record is not None else latest_record(repo)
    )
    record: str = str(record_path.relative_to(repo))
    lines: list[str] = record_path.read_text(encoding="utf-8").splitlines()
    cited_by: list[Citation] = citations(repo, record)
    follow_ups: list[FollowUp] = parse_follow_ups(lines)
    follow_up_rows: list[tuple[str, str, str, list[Citation]]] = [
        (
            (
                f"{f.tier}{' ' + f.id if f.id else ''}: "
                f"{', '.join('§' + s for s in f.sections) or '(no §)'}"
            ),
            f.text,
            *follow_up_status(f, cited_by),
        )
        for f in follow_ups
    ]
    section_rows: list[tuple[str, str, str, list[Citation]]] = [
        (f"§{number}", title, *status([number], cited_by, include_subsections=True))
        for number, title in parse_sections(lines)
    ]
    unplaced: list[Citation] = [
        c for c in cited_by if not c.sections and not c.follow_up_ids
    ]
    counts: dict[str, int] = {
        state: sum(1 for row in follow_up_rows if row[2].split(" ")[0] == state)
        for state in STATES
    }
    by_section: int = sum(1 for row in follow_up_rows if row[2].endswith("(by §)"))
    summary: str = (
        f"{len(follow_ups)} follow-ups: {counts['done']} done, {counts['open']} open, "
        f"{counts['untracked']} untracked"
        + (f" ({by_section} matched by section only)" if by_section else "")
        + f"; {len(cited_by)} task citations ({sum(c.done for c in cited_by)} archived)."
    )
    out: list[str]
    if args.carried_over:
        out = [
            "## Carried over from the previous review",
            "",
            f"Baseline: `{record}`. {summary}",
            "",
            table(follow_up_rows),
        ]
    else:
        out = [
            f"# Status of `{record}`",
            "",
            summary,
            "",
            "## Suggested follow-ups",
            "",
            table(follow_up_rows),
            "",
            "## Sections",
            "",
            table(section_rows),
        ]
        if unplaced:
            out += [
                "",
                "## Tasks that cite the record without a section or ID",
                "",
                *(f"- `{c.task}`" for c in unplaced),
            ]
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
