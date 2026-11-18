#!/usr/bin/env python3
"""Measure the context the client's Crush preseeds into every session.

Before the first prompt, Crush sends the model a system prompt built from the base
``coder`` template, the global context files (``option global-context-path`` in
``client/entrypoint/crushrc``), the project's context files (Crush's
``defaultContextPaths``, looked up in the working directory ``/work``), a skills XML
block and a git-status summary, plus the tool schemas. This tool rebuilds the
file-backed part of that statically, from this repository and the vendored Crush
source, applying this repository's ``@``-import patch exactly as the patched Crush
does, and prints how much of each registered model's context window it uses before
anything is typed. The parts that only exist at run time (tool schemas, skills XML,
git status) are added from the CTXDBG measurement recorded in
``tasks/reference/crush-context-assembly.md``.

Token counts are Crush's own estimate, ``skills.ApproxTokenCount`` =
``(bytes + 3) / 4``, unless ``--tokenize-url`` points at a llama-server, whose
``/tokenize`` endpoint then counts exactly for the model it serves.

Usage (from anywhere; paths are resolved from this file)::

    python3 tools/measure_context.py [PROJECT_DIR ...] [--overlay FILE]
        [--window TOKENS ...] [--tokenize-url URL] [--sections N]

With no PROJECT_DIR it reports only the global layer, which every session pays.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import pathlib
import re
import sys
import urllib.request
from collections.abc import Callable, Sequence

REPO_ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parents[1]
CLIENT_DIR: pathlib.Path = REPO_ROOT / "client"
CRUSH_SOURCE: pathlib.Path = CLIENT_DIR / "vendor" / "crush"
CRUSHRC: pathlib.Path = CLIENT_DIR / "entrypoint" / "crushrc"
BAKED_CRUSH_CONFIG: pathlib.Path = (
    CLIENT_DIR / "entrypoint" / "dotfiles" / ".config" / "crush"
)
OVERLAY_NAME: str = "ai-coding-conventions.personal.md"

CONTAINER_HOME: pathlib.PurePosixPath = pathlib.PurePosixPath("/root")
CONTAINER_CRUSH_CONFIG: pathlib.PurePosixPath = CONTAINER_HOME / ".config" / "crush"
CONTAINER_WORKDIR: pathlib.PurePosixPath = pathlib.PurePosixPath("/work")

# expandContextImports in client/patches/crush-at-import.patch: a line that is only
# `@path`, recursion capped at 5 hops.
IMPORT_LINE: re.Pattern[str] = re.compile(r"(?m)^[ \t]*@(\S+)[ \t]*$")
MAX_IMPORT_DEPTH: int = 5

# The run-time parts the files can't show, from the CTXDBG log of 2026-09-13
# (tasks/reference/crush-context-assembly.md, "Measured sizes"). Tool schemas are the
# ~8K first-turn residual over the system prompt, which also held the user's message.
TOOL_SCHEMA_TOKENS: int = 8_000
SKILLS_XML_TOKENS: int = 304
GIT_STATUS_TOKENS: int = 650

HEADING: re.Pattern[str] = re.compile(r"^(#{1,2}) +(.+?)\s*$")
FENCE: re.Pattern[str] = re.compile(r"^\s*(```|~~~)")


def approx_tokens(text: str) -> int:
    """Crush's token estimate, ``skills.ApproxTokenCount``: about 4 bytes per token.

    Args:
        text: the text to count.

    Returns:
        int: ``(len(text.encode()) + 3) // 4``, or 0 for empty text.

    Example:
        >>> approx_tokens("")
        0
        >>> approx_tokens("abcde")
        2
    """
    size: int = len(text.encode())
    return 0 if size == 0 else (size + 3) // 4


def llama_tokenizer(url: str) -> Callable[[str], int]:
    """A counter that asks a llama-server's ``/tokenize`` endpoint for exact counts.

    Args:
        url: the server's base URL, such as ``http://127.0.0.1:8080``.

    Returns:
        Callable[[str], int]: maps a text to its token count for the served model.
    """

    def count(text: str) -> int:
        body: bytes = json.dumps({"content": text}).encode()
        request: urllib.request.Request = urllib.request.Request(
            url.rstrip("/") + "/tokenize",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            reply: dict[str, list[int]] = json.load(response)
        return len(reply["tokens"])

    return count


@dataclasses.dataclass(frozen=True, slots=True)
class Mounts:
    """How container paths map onto host files, longest container prefix first.

    Attributes:
        table: ``(container prefix, host path)`` pairs.
    """

    table: tuple[tuple[pathlib.PurePosixPath, pathlib.Path], ...]

    def resolve(self, container_path: pathlib.PurePosixPath) -> pathlib.Path | None:
        """The host file behind a container path, or None when nothing mounts it.

        Args:
            container_path: an absolute path as Crush sees it in the container.

        Returns:
            pathlib.Path | None: the host path, by the longest matching prefix.

        Example:
            >>> mounts: Mounts = Mounts(
            ...     table=(
            ...         (pathlib.PurePosixPath("/root/x.md"), pathlib.Path("/h/x.md")),
            ...         (pathlib.PurePosixPath("/root"), pathlib.Path("/repo/a")),
            ...     )
            ... )
            >>> mounts.resolve(pathlib.PurePosixPath("/root/x.md"))
            PosixPath('/h/x.md')
            >>> mounts.resolve(pathlib.PurePosixPath("/root/b/y.md"))
            PosixPath('/repo/a/b/y.md')
            >>> mounts.resolve(pathlib.PurePosixPath("/etc/z")) is None
            True
        """
        ordered: list[tuple[pathlib.PurePosixPath, pathlib.Path]] = sorted(
            self.table, key=lambda pair: len(pair[0].parts), reverse=True
        )
        for prefix, host in ordered:
            if container_path == prefix or prefix in container_path.parents:
                return host.joinpath(*container_path.parts[len(prefix.parts) :])
        return None


@dataclasses.dataclass(frozen=True, slots=True)
class Splice:
    """One context file, with the files its ``@`` lines spliced in.

    Attributes:
        path: the file's container path.
        raw: the file's own text, before splicing.
        children: the files it imported, in order.
    """

    path: pathlib.PurePosixPath
    raw: str
    children: tuple[Splice, ...]


def expand_imports(
    content: str,
    base_dir: pathlib.PurePosixPath,
    depth: int,
    visited: set[pathlib.PurePosixPath],
    mounts: Mounts,
) -> tuple[str, tuple[Splice, ...]]:
    """Splice whole-line ``@path`` imports, as the patched Crush does.

    Mirrors ``expandContextImports`` (``client/patches/crush-at-import.patch``): ``~``
    is the container home, a relative path resolves against ``base_dir``, past depth 5
    the text is left as is, and ``visited`` is shared by the whole tree, so a file is
    spliced at most once. A cycle or an unreadable target keeps the literal line.

    Args:
        content: the importing file's text.
        base_dir: the importing file's container directory.
        depth: the import depth of ``content`` (a context file itself is 1).
        visited: container paths already spliced; updated in place.
        mounts: the container-to-host path map.

    Returns:
        tuple[str, tuple[Splice, ...]]: the expanded text and the imported files.

    Example:
        >>> expand_imports("a\\n@missing.md\\nb", pathlib.PurePosixPath("/x"), 1,
        ...                set(), Mounts(table=()))
        ('a\\n@missing.md\\nb', ())
    """
    if depth > MAX_IMPORT_DEPTH:
        return content, ()
    children: list[Splice] = []

    def splice(match: re.Match[str]) -> str:
        target: str = match.group(1)
        path: pathlib.PurePosixPath = (
            CONTAINER_HOME / target[2:]
            if target.startswith("~/")
            else pathlib.PurePosixPath(target)
        )
        absolute: pathlib.PurePosixPath = pathlib.PurePosixPath(
            os.path.normpath(base_dir / path)
        )
        host: pathlib.Path | None = mounts.resolve(absolute)
        if absolute in visited or host is None or not host.is_file():
            return match.group(0)
        visited.add(absolute)
        raw: str = host.read_text()
        expanded: str
        grandchildren: tuple[Splice, ...]
        expanded, grandchildren = expand_imports(
            raw, absolute.parent, depth + 1, visited, mounts
        )
        children.append(Splice(path=absolute, raw=raw, children=grandchildren))
        return expanded

    expanded_text: str = IMPORT_LINE.sub(splice, content)
    return expanded_text, tuple(children)


def load_context_file(
    path: pathlib.PurePosixPath, mounts: Mounts
) -> tuple[Splice, str] | None:
    """Read one context file and splice its imports.

    Args:
        path: the file's container path.
        mounts: the container-to-host path map.

    Returns:
        tuple[Splice, str] | None: the import tree and the fully expanded text, or
        None when the file doesn't exist.
    """
    host: pathlib.Path | None = mounts.resolve(path)
    if host is None or not host.is_file():
        return None
    raw: str = host.read_text()
    expanded: str
    children: tuple[Splice, ...]
    expanded, children = expand_imports(raw, path.parent, 1, {path}, mounts)
    return Splice(path=path, raw=raw, children=children), expanded


def crush_default_context_paths() -> list[str]:
    """``defaultContextPaths`` read from the vendored Crush source.

    Returns:
        list[str]: the project instruction-file names Crush looks for in its cwd.
    """
    source: str = (CRUSH_SOURCE / "internal" / "config" / "config.go").read_text()
    block: re.Match[str] | None = re.search(
        r"var defaultContextPaths = \[\]string\{(.*?)\n\}", source, re.DOTALL
    )
    if block is None:
        raise RuntimeError("defaultContextPaths not found in the vendored Crush")
    return re.findall(r'"([^"]+)"', block.group(1))


def crushrc_global_context_paths() -> list[pathlib.PurePosixPath]:
    """The global context paths the client registers, or Crush's defaults if none.

    Returns:
        list[pathlib.PurePosixPath]: the container paths, sorted as Crush sorts them.
    """
    found: list[str] = re.findall(
        r"(?m)^\s*option\s+global-context-path\s+(\S+)", CRUSHRC.read_text()
    )
    defaults: list[str] = [
        str(CONTAINER_CRUSH_CONFIG / "CRUSH.md"),
        str(CONTAINER_HOME / ".config" / "AGENTS.md"),
    ]
    return [pathlib.PurePosixPath(p) for p in sorted(set(found or defaults))]


def crushrc_context_windows() -> list[int]:
    """Every distinct ``--context-window`` the crushrc registers a model with.

    Returns:
        list[int]: the windows, largest first.
    """
    found: list[str] = re.findall(r"--context-window\s+(\d+)", CRUSHRC.read_text())
    return sorted({int(window) for window in found}, reverse=True)


def project_context_paths(project: pathlib.Path) -> list[pathlib.PurePosixPath]:
    """The project context files Crush would load with ``project`` mounted at /work.

    Args:
        project: the project's host directory.

    Returns:
        list[pathlib.PurePosixPath]: container paths, deduplicated case-insensitively
        like Crush's ``loadContextFiles``.
    """
    paths: list[pathlib.PurePosixPath] = []
    seen: set[str] = set()
    name: str
    for name in crush_default_context_paths():
        host: pathlib.Path = project / name
        found: list[pathlib.Path] = (
            sorted(p for p in host.rglob("*") if p.is_file())
            if host.is_dir()
            else [host]
            if host.is_file()
            else []
        )
        file: pathlib.Path
        for file in found:
            container: pathlib.PurePosixPath = CONTAINER_WORKDIR / file.relative_to(
                project
            )
            if str(container).lower() not in seen:
                seen.add(str(container).lower())
                paths.append(container)
    return paths


def sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown into ``#``/``##`` sections, ignoring headings inside code fences.

    Args:
        text: a Markdown document.

    Returns:
        list[tuple[str, str]]: ``(heading, body including the heading line)`` pairs;
        text before the first heading is titled ``(preamble)``.

    Example:
        >>> [h for h, _ in sections("intro\\n# A\\nx\\n```\\n# not\\n```\\n## B\\ny")]
        ['(preamble)', 'A', 'B']
    """
    result: list[tuple[str, list[str]]] = [("(preamble)", [])]
    in_fence: bool = False
    line: str
    for line in text.splitlines(keepends=True):
        if FENCE.match(line):
            in_fence = not in_fence
        heading: re.Match[str] | None = None if in_fence else HEADING.match(line)
        if heading is not None:
            result.append((heading.group(2), []))
        result[-1][1].append(line)
    return [(title, "".join(lines)) for title, lines in result if "".join(lines)]


def tree_rows(
    splice: Splice, count: Callable[[str], int], indent: int = 0
) -> list[tuple[str, int, int]]:
    """Table rows for an import tree: each file's own bytes and tokens.

    Args:
        splice: the tree's root.
        count: the token counter.
        indent: the nesting level of ``splice``.

    Returns:
        list[tuple[str, int, int]]: ``(label, bytes, tokens)`` per file, depth first.
    """
    label: str = ("  " * indent) + ("@" if indent else "") + str(splice.path)
    own: tuple[str, int, int] = (label, len(splice.raw.encode()), count(splice.raw))
    return [own] + [
        row for child in splice.children for row in tree_rows(child, count, indent + 1)
    ]


def flatten(splice: Splice) -> list[Splice]:
    """Every file in an import tree, root first.

    Args:
        splice: the tree's root.

    Returns:
        list[Splice]: the root and all its descendants.
    """
    return [splice] + [node for child in splice.children for node in flatten(child)]


def percent_line(tokens: int, windows: Sequence[int]) -> str:
    """``tokens`` as a share of each context window.

    Args:
        tokens: the preseeded token count.
        windows: the context windows to compare against.

    Returns:
        str: one ``window: percent`` entry per window.

    Example:
        >>> percent_line(16384, [65536, 32768])
        '65,536: 25%   32,768: 50%'
    """
    return "   ".join(f"{window:,}: {100 * tokens / window:.0f}%" for window in windows)


def print_table(rows: Sequence[tuple[str, int | None, int]]) -> None:
    """Print ``(label, bytes, tokens)`` rows; a None byte count prints as ``-``.

    Args:
        rows: the rows to print.
    """
    width: int = max(len(label) for label, _, _ in rows)
    label: str
    size: int | None
    tokens: int
    for label, size, tokens in rows:
        size_text: str = "-" if size is None else f"{size:,}"
        print(f"  {label:<{width}}  {size_text:>9}  {tokens:>8,}")


def default_overlay() -> pathlib.Path:
    """The personal overlay ``make shell`` mounts, as seen from where this runs.

    Returns:
        pathlib.Path: the host overlay (``~/.ai-coding-conventions.personal.md``), the
        copy a sandbox mounts at ``~/.claude/``, or the baked placeholder.
    """
    candidates: list[pathlib.Path] = [
        pathlib.Path.home() / ("." + OVERLAY_NAME),
        pathlib.Path.home() / ".claude" / OVERLAY_NAME,
    ]
    return next(
        (p for p in candidates if p.is_file()), BAKED_CRUSH_CONFIG / OVERLAY_NAME
    )


def main(argv: Sequence[str]) -> int:
    """Print the preseeded-context report.

    Args:
        argv: the command-line arguments, without the program name.

    Returns:
        int: the exit status.
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0]
    )
    parser.add_argument("projects", nargs="*", type=pathlib.Path)
    parser.add_argument("--overlay", type=pathlib.Path, default=default_overlay())
    parser.add_argument("--window", type=int, action="append", default=[])
    parser.add_argument("--tokenize-url")
    parser.add_argument("--sections", type=int, default=12)
    args: argparse.Namespace = parser.parse_args(argv)

    count: Callable[[str], int] = (
        approx_tokens
        if args.tokenize_url is None
        else llama_tokenizer(args.tokenize_url)
    )
    windows: list[int] = sorted(
        set(crushrc_context_windows()) | set(args.window), reverse=True
    )
    base_mounts: tuple[tuple[pathlib.PurePosixPath, pathlib.Path], ...] = (
        (CONTAINER_CRUSH_CONFIG / OVERLAY_NAME, args.overlay),
        (CONTAINER_CRUSH_CONFIG, BAKED_CRUSH_CONFIG),
    )
    template: str = (
        CRUSH_SOURCE / "internal" / "agent" / "templates" / "coder.md.tpl"
    ).read_text()

    global_trees: list[Splice] = []
    global_text: str = ""
    path: pathlib.PurePosixPath
    for path in crushrc_global_context_paths():
        loaded: tuple[Splice, str] | None = load_context_file(path, Mounts(base_mounts))
        if loaded is not None:
            global_trees.append(loaded[0])
            global_text += loaded[1]
    global_rows: list[tuple[str, int | None, int]] = [
        row for tree in global_trees for row in tree_rows(tree, count)
    ]
    global_rows += [
        ("base coder template (Crush source)", len(template.encode()), count(template)),
        ("tool schemas (CTXDBG 2026-09-13)", None, TOOL_SCHEMA_TOKENS),
        ("skills XML (CTXDBG 2026-09-13)", None, SKILLS_XML_TOKENS),
    ]
    global_tokens: int = count(global_text) + count(template) + TOOL_SCHEMA_TOKENS
    global_tokens += SKILLS_XML_TOKENS

    method: str = "llama-server /tokenize" if args.tokenize_url else "(bytes + 3) / 4"
    print(f"Crush preseeded context, before the first prompt. Tokens: {method}.")
    print(f"Overlay: {args.overlay}\n")
    print("Every session (global layer):")
    print_table(global_rows)
    print(f"  = {global_tokens:,} tokens   {percent_line(global_tokens, windows)}\n")

    candidates: list[tuple[int, str, str]] = [
        (count(body), str(node.path), title)
        for tree in global_trees
        for node in flatten(tree)
        for title, body in sections(node.raw)
    ]
    summary: list[tuple[str, int, int]] = []
    project: pathlib.Path
    for project in args.projects:
        mounts: Mounts = Mounts(base_mounts + ((CONTAINER_WORKDIR, project.resolve()),))
        trees: list[Splice] = []
        text: str = ""
        for path in project_context_paths(project.resolve()):
            loaded = load_context_file(path, mounts)
            if loaded is not None:
                trees.append(loaded[0])
                text += loaded[1]
        rows: list[tuple[str, int | None, int]] = [
            row for tree in trees for row in tree_rows(tree, count)
        ]
        project_tokens: int = count(text) + (
            GIT_STATUS_TOKENS if (project / ".git").exists() else 0
        )
        if rows:
            print(f"Project {project.resolve().name} (at /work):")
            print_table(
                rows + [("git status (CTXDBG upper bound)", None, GIT_STATUS_TOKENS)]
            )
            print(f"  = {project_tokens:,} tokens\n")
        summary.append(
            (project.resolve().name, project_tokens, global_tokens + project_tokens)
        )
        candidates += [
            (count(body), f"{project.resolve().name}:{node.path}", title)
            for tree in trees
            for node in flatten(tree)
            for title, body in sections(node.raw)
        ]

    if summary:
        print("Total per session (global + project):")
        name: str
        own: int
        total: int
        for name, own, total in sorted(summary, key=lambda row: row[2], reverse=True):
            shares: str = percent_line(total, windows)
            print(f"  {name:<40} {own:>7,} + global = {total:>7,}   {shares}")
        print()
    print(f"Largest sections (deferral candidates), top {args.sections}:")
    tokens: int
    where: str
    title: str
    for tokens, where, title in sorted(candidates, reverse=True)[: args.sections]:
        print(f"  {tokens:>7,}  {title[:60]:<60}  {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
