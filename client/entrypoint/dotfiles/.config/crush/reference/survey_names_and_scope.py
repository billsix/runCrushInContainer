#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# SHARED TOOL -- keep every copy byte-identical.
# Canonical: runClaudeInContainer tasks/reference/survey_names_and_scope.py
#   (github.com/billsix/runClaudeInContainer). Mirrored in runCrushInContainer
#   tasks/reference/ and its baked client copy. Run from inside a project:
#     python3 ~/.claude/reference/survey_names_and_scope.py [--language rust] [--exclude REGEX]
#   (Crush: ~/.config/crush/reference/survey_names_and_scope.py). Needs universal-ctags.
#   The rules it surveys for: each language standard's "Locals and helpers" section.
# ---------------------------------------------------------------------------
"""List where the naming and scope rules may fire in Rust, C++, C, Haskell, bash and JavaScript.

Read-only.  For each language it prints two lead lists: functions whose name occurs
exactly twice in that language's tracked files (a definition and one call, so a
candidate for "a helper with one caller"), and local bindings whose name occurs exactly
twice inside the function that declares them (a candidate for "inline a binding used
once").  The counts are textual, so every line is a lead to read, not a finding: a
method called through a trait, a callback passed by name, and a name that also appears
in a comment are all miscounted.  Python is not covered; ``nest_one_caller.py`` and a
project's own survey do that.

A header that C and C++ share (``.h``) is surveyed as C.
"""

import argparse
import collections
import dataclasses
import enum
import json
import pathlib
import re
import subprocess

DEFAULT_EXCLUDE: str = r"elpa/|/imgui/|doctest/|vendor|third_party|node_modules|^builddir/"


class Language(enum.Enum):
    """The languages surveyed, valued by the name given to ``--language``."""

    RUST = "rust"
    CPP = "c++"
    C = "c"
    HASKELL = "haskell"
    BASH = "bash"
    JAVASCRIPT = "javascript"


def suffixes(language: Language) -> tuple[str, ...]:
    """Return the file suffixes that belong to a language.

    Args:
        language: The language to look up.

    Returns:
        The suffixes, each with its leading dot.

    Raises:
        ValueError: If the language has no suffixes recorded.
    """
    match language:
        case Language.RUST:
            return (".rs",)
        case Language.CPP:
            return (".cpp", ".cc", ".cxx", ".hpp", ".hh")
        case Language.C:
            return (".c", ".h")
        case Language.HASKELL:
            return (".hs",)
        case Language.BASH:
            return (".sh",)
        case Language.JAVASCRIPT:
            return (".js", ".mjs")
        case _:
            raise ValueError(language)


def binding_pattern(language: Language) -> re.Pattern[str]:
    """Return the pattern that finds a local binding's name on a line.

    Args:
        language: The language whose declaration syntax to match.

    Returns:
        A pattern whose first group is the bound name.

    Raises:
        ValueError: If the language has no pattern recorded.
    """
    match language:
        case Language.RUST:
            return re.compile(r"^\s*let (?:mut )?(\w+)\s*[:=]")
        case Language.CPP | Language.C:
            return re.compile(r"^\s+(?:const )?[\w:<>,\*& ]+?[ \*&](\w+)\s*(?:=|\{).*;\s*$")
        case Language.HASKELL:
            return re.compile(r"^\s+(?:let\s+)?!?([a-z_]\w*)\s*(?:::[^=<]*)?(?:<-|=)(?!=)")
        case Language.BASH:
            return re.compile(r"^\s*(?:local |declare |readonly )?(?:-\w+ )?(\w+)=")
        case Language.JAVASCRIPT:
            return re.compile(r"^\s*(?:const|let) (\w+)\s*=")
        case _:
            raise ValueError(language)


@dataclasses.dataclass(frozen=True)
class Function:
    """A function definition found by ctags, or a whole file surveyed as one scope."""

    name: str
    path: str
    line: int
    end: int
    scope: str


def survey(language: Language, root: pathlib.Path, tracked: list[str]) -> None:
    """Print the two lead lists for one language, or nothing if it has no files.

    Args:
        language: The language to survey.
        root: The repository root the paths are relative to.
        tracked: The tracked paths to consider, already filtered for exclusions.
    """

    def functions_in(paths: list[str]) -> list[Function]:
        """Ask ctags for every function definition in the given files.

        Args:
            paths: Repository-relative paths of one language's files.

        Returns:
            The definitions, in ctags' order.
        """
        ctags: subprocess.CompletedProcess[str] = subprocess.run(
            ["ctags", "--output-format=json", "--fields=+neK", "-o", "-", "-L", "-"],
            cwd=root,
            input="\n".join(paths),
            capture_output=True,
            text=True,
            check=True,
        )
        tags: list[dict[str, object]] = [json.loads(line) for line in ctags.stdout.splitlines()]
        return [
            Function(
                name=str(tag["name"]),
                path=str(tag["path"]),
                line=int(str(tag["line"])),
                end=int(str(tag.get("end", tag["line"]))),
                scope=str(tag.get("scope", "")),
            )
            for tag in tags
            if tag.get("kind") in ("function", "method")
        ]

    def with_ends(functions: list[Function]) -> list[Function]:
        """Give every function an end line, and every function-free file one whole-file scope.

        ctags reports no end line for Rust, Haskell or JavaScript, so a function without
        one is taken to run to the line before the next function in its file (or to the
        end of the file).  A file with no functions at all (most shell scripts) is
        surveyed as a single scope.

        Args:
            functions: The definitions ctags found.

        Returns:
            The definitions with usable end lines, followed by the whole-file scopes.
        """
        starts_of: dict[str, list[int]] = {
            path: sorted(function.line for function in functions if function.path == path)
            for path in lines_of
        }
        ended: list[Function] = [
            function
            if function.end > function.line
            else dataclasses.replace(
                function,
                end=min(
                    (start - 1 for start in starts_of[function.path] if start > function.line),
                    default=len(lines_of[function.path]),
                ),
            )
            for function in functions
        ]
        whole_files: list[Function] = [
            Function(name="", path=path, line=1, end=len(lines), scope="whole file")
            for path, lines in lines_of.items()
            if not starts_of[path]
        ]
        return ended + whole_files

    paths: list[str] = [path for path in tracked if path.endswith(suffixes(language))]
    if not paths:
        return
    lines_of: dict[str, list[str]] = {
        path: (root / path).read_text(errors="replace").splitlines()
        for path in paths
        if (root / path).is_file()
    }
    # word_counts: how often each identifier occurs across the language's files.
    word_counts: collections.Counter[str] = collections.Counter(
        word for lines in lines_of.values() for line in lines for word in re.findall(r"\w+", line)
    )
    functions: list[Function] = with_ends(functions_in(list(lines_of)))
    print(f"== {language.value}: {len(lines_of)} files, {len(functions)} scopes")
    print("-- functions named exactly twice (definition and one call)")
    for function in functions:
        if function.name and word_counts[function.name] == 2:
            print(f"{function.path}:{function.line}: {function.name} [{function.scope}]")
    print("-- locals named exactly twice inside their function")
    pattern: re.Pattern[str] = binding_pattern(language)
    for function in functions:
        body: list[str] = lines_of[function.path][function.line - 1 : function.end]
        for offset, line in enumerate(body):
            found: re.Match[str] | None = pattern.match(line)
            if found is None:
                continue
            # A Haskell signature line (`name :: Type`) names the binding without using it.
            signature: re.Pattern[str] = re.compile(rf"^\s*(?:let\s+)?{found.group(1)}\s*::[^=]*$")
            uses: int = sum(
                len(re.findall(rf"\b{found.group(1)}\b", row))
                for row in body
                if not (language is Language.HASKELL and signature.match(row))
            )
            if uses == 2:
                print(f"{function.path}:{function.line + offset}: {line.strip()}")


def main() -> None:
    """Survey the chosen languages of the repository that holds the current directory."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--language",
        action="append",
        choices=[language.value for language in Language],
        help="a language to survey; repeat for several (default: all)",
    )
    parser.add_argument(
        "--exclude",
        default=DEFAULT_EXCLUDE,
        help="regular expression; tracked paths it matches are skipped (default: %(default)s)",
    )
    arguments: argparse.Namespace = parser.parse_args()
    root: pathlib.Path = pathlib.Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        ).stdout.strip()
    )
    exclude: re.Pattern[str] = re.compile(arguments.exclude)
    tracked: list[str] = [
        path
        for path in subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.splitlines()
        if not exclude.search(path)
    ]
    for language in Language:
        if arguments.language is None or language.value in arguments.language:
            survey(language, root, tracked)


if __name__ == "__main__":
    main()
