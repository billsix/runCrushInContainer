#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# SHARED TOOL -- keep every copy byte-identical.
# Canonical: runClaudeInContainer tasks/reference/nest_one_caller.py
#   (github.com/billsix/runClaudeInContainer). Mirrored in runCrushInContainer
#   tasks/reference/ and its baked client copy. Run it from inside a Python
#   project's repository:
#     python3 ~/.claude/reference/nest_one_caller.py [--dry-run] FILE [FILE ...]
#   (Crush: ~/.config/crush/reference/nest_one_caller.py). It implements the
#   "A helper with one caller is nested inside that caller" rule of
#   python-coding-standard.md ("What earns an extraction").
# ---------------------------------------------------------------------------
"""Nest each module-level helper that has one caller inside that caller.

The shared Python standard ("What earns an extraction") nests a helper with one
caller inside it.  For every top-level function ``H`` in the given files this
tool finds the top-level functions that read ``H``.  When there is exactly one,
``C``, it moves ``H`` (its decorators and the comment lines directly above it
included) to the start of ``C``'s body, below ``C``'s docstring.  A helper that
becomes single-caller once its sibling has nested follows in the same run, so
the nesting cascades.

It skips, and reports, a helper that:

* is read anywhere else: another top-level function, module-level code, or
  another file by import or attribute access (found with ``git grep -w``);
* carries a doctest (``doctest`` does not collect a nested function);
* contains a triple-quoted string other than a function docstring (re-indenting
  would change the string);
* reads a name its caller binds itself (the closure would capture the caller's
  local instead of the module-level name);
* is named in ``--keep`` or is called ``main`` or a dunder.

Re-indenting can push comment and docstring lines past a line-length limit, and
a formatter does not reflow prose: run the project's formatter afterwards and
reflow each flagged paragraph whole.  Idempotent: a nested helper is no longer
top-level, so a second run finds nothing.  Run it from inside the repository.

Usage::

    python3 ~/.claude/reference/nest_one_caller.py [--dry-run] [--keep NAME ...] FILE ...
"""

import argparse
import ast
import pathlib
import re
import subprocess

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef












def referencing_functions(
    helper: str, functions: dict[str, FunctionNode], tree: ast.Module
) -> tuple[set[str], int]:
    """The top-level functions that read ``helper``, and the reads elsewhere.

    Args:
        helper: The name of a top-level function.
        functions: The module's top-level functions by name.
        tree: The module.

    Returns:
        The names of the other top-level functions that read ``helper``, and
        the number of reads that are in neither those functions nor
        ``helper`` itself (module-level code, decorators of other defs).
    """

    def name_count(node: ast.AST, name: str) -> int:
        """How many times ``name`` appears as a bare name under ``node``."""
        return sum(
            1 for n in ast.walk(node) if isinstance(n, ast.Name) and n.id == name
        )

    users: set[str] = set()
    inside: int = 0
    name: str
    fn: FunctionNode
    for name, fn in functions.items():
        if name == helper:
            continue
        count: int = name_count(fn, helper)
        if count:
            users.add(name)
            inside += count
    own: int = name_count(functions[helper], helper)
    return users, name_count(tree, helper) - inside - own










def nest_once(
    path: pathlib.Path, source: str, root: pathlib.Path, keep: set[str]
) -> str | None:
    """Nest one eligible helper of ``source``.

    Args:
        path: The file being edited (its name labels the report).
        source: The file's current text.
        root: The repository root.
        keep: Helper names that must not nest.

    Returns:
        The new text, or ``None`` when no helper in ``source`` can nest.
    """

    def skip_reason(
        name: str,
        fn: FunctionNode,
        host: FunctionNode,
        lines: list[str],
        path: pathlib.Path,
        root: pathlib.Path,
        keep: set[str],
    ) -> str | None:
        """Why ``name`` must stay at module level, or ``None`` if it can nest."""

        def has_extra_triple_quoted_string(fn: FunctionNode, lines: list[str]) -> bool:
            """True if ``fn`` holds a triple-quoted string that is not a docstring."""
            docstrings: set[int] = set()
            node: ast.AST
            for node in ast.walk(fn):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    first: ast.stmt = node.body[0]
                    if isinstance(first, ast.Expr) and isinstance(
                        first.value, ast.Constant
                    ):
                        docstrings.add(id(first.value))
            for node in ast.walk(fn):
                if (
                    isinstance(node, (ast.Constant, ast.JoinedStr))
                    and id(node) not in docstrings
                    and node.end_lineno != node.lineno
                ):
                    opening: str = lines[node.lineno - 1][node.col_offset :].lstrip(
                        "rbfRBF"
                    )
                    if opening.startswith(('"' * 3, "'" * 3)):
                        return True
            return False


        def referenced_in_other_files(
            helper: str, path: pathlib.Path, root: pathlib.Path
        ) -> list[str]:
            """Lines in other tracked files that import or access ``helper``.

            Args:
                helper: The name of a top-level function.
                path: The file that defines it.
                root: The repository root.

            Returns:
                ``git grep`` rows from other files that import the name or reach it
                through an attribute (``module.helper``).  A same-named function that
                another file defines for itself does not count.
            """
            result: subprocess.CompletedProcess[str] = subprocess.run(
                ["git", "grep", "-nw", helper, "--", "*.py", "*.rst", "*.ipynb"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            own: str = path.relative_to(root).as_posix()
            uses: re.Pattern[str] = re.compile(
                rf"(\bimport\b.*\b{helper}\b|\.{helper}\b|^\s*{helper},?\s*$)"
            )
            return [
                row
                for row in result.stdout.splitlines()
                if not row.startswith(own + ":") and uses.search(row.split(":", 2)[2])
            ]


        def loaded_names(fn: FunctionNode) -> set[str]:
            """Names ``fn`` reads."""
            return {
                node.id
                for node in ast.walk(fn)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            }


        def bound_names(fn: FunctionNode) -> set[str]:
            """Names ``fn`` binds in its own body: parameters, targets, imports, defs."""
            names: set[str] = {a.arg for a in ast.walk(fn.args) if isinstance(a, ast.arg)}
            node: ast.AST
            for node in ast.walk(fn):
                match node:
                    case ast.Name(ctx=ast.Store() | ast.Del()):
                        names.add(node.id)
                    case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef():
                        if node is not fn:
                            names.add(node.name)
                    case ast.Import() | ast.ImportFrom():
                        names.update(
                            (alias.asname or alias.name).split(".")[0]
                            for alias in node.names
                        )
                    case ast.ExceptHandler(name=str()):
                        names.add(node.name)
                    case _:
                        pass  # every other node binds nothing
            return names

        doc: str | None = ast.get_docstring(fn)
        if name in keep or name == "main" or name.startswith("__"):
            return "kept"
        if doc is not None and ">>>" in doc:
            return "doctest"
        if has_extra_triple_quoted_string(fn, lines):
            return "triple-quoted string"
        if referenced_in_other_files(name, path, root):
            return "named in another file"
        clash: set[str] = (loaded_names(fn) - bound_names(fn)) & bound_names(host)
        if clash:
            return f"caller binds {sorted(clash)}"
        return None


    def start_line(fn: FunctionNode, lines: list[str]) -> int:
        """The first line (0-based) of ``fn``: decorators and comments above it."""
        first: int = min([d.lineno for d in fn.decorator_list] + [fn.lineno]) - 1
        while first > 0 and lines[first - 1].lstrip().startswith("#"):
            first -= 1
        return first


    def top_level_functions(tree: ast.Module) -> dict[str, FunctionNode]:
        """The module's top-level functions, by name."""
        return {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    tree: ast.Module = ast.parse(source)
    functions: dict[str, FunctionNode] = top_level_functions(tree)
    lines: list[str] = source.splitlines(keepends=True)
    pending: dict[str, str] = {}
    name: str
    for name in functions:
        users: set[str]
        elsewhere: int
        users, elsewhere = referencing_functions(name, functions, tree)
        if len(users) == 1 and elsewhere == 0:
            pending[name] = next(iter(users))
    caller: str
    for name, caller in pending.items():
        if name in pending.values():
            continue  # the caller of a pending helper: that helper nests first
        fn: FunctionNode = functions[name]
        host: FunctionNode = functions[caller]
        reason: str | None = skip_reason(
            name, fn, host, lines, path, root, keep
        )
        if reason is not None:
            print(f"  skip  {path.name}: {name} -> {caller}: {reason}")
            continue
        top: int = start_line(fn, lines)
        end: int = fn.end_lineno or fn.lineno
        indented: list[str] = [
            ("    " + row if row.strip() else row) for row in lines[top:end]
        ]
        first: ast.stmt = host.body[0]
        insert_at: int = (
            (first.end_lineno or first.lineno)
            if isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            else first.lineno - 1
        )
        print(f"  nest  {path.name}: {name} -> {caller}")
        rest: list[str] = lines[:top] + lines[end:]
        at: int = insert_at - (end - top if top < insert_at else 0)
        rest[at:at] = ["\n", *indented, "\n"]
        return "".join(rest)
    return None


def main() -> None:

    def repo_root() -> pathlib.Path:
        """The root of the git repository containing the current directory."""
        return pathlib.Path(
            subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )

    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("files", nargs="+", help="Python files to edit")
    parser.add_argument(
        "--dry-run", action="store_true", help="report without writing"
    )
    parser.add_argument(
        "--keep",
        nargs="*",
        default=[],
        metavar="NAME",
        help="helper names that must stay at module level",
    )
    args: argparse.Namespace = parser.parse_args()
    root: pathlib.Path = repo_root()
    file: str
    for file in args.files:
        path: pathlib.Path = pathlib.Path(file).resolve()
        print(path.relative_to(root).as_posix())
        text: str = path.read_text()
        updated: str | None = nest_once(path, text, root, set(args.keep))
        while updated is not None:
            text = updated
            updated = nest_once(path, text, root, set(args.keep))
        if not args.dry_run:
            path.write_text(text)


if __name__ == "__main__":
    main()
