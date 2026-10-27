# Doctests by default (Python and Rust)

> **SHARED doc.** Canonical copy: github.com/billsix/runClaudeInContainer
> `tasks/reference/doctests-by-default.md`; kept **byte-identical** in the runCrushInContainer
> mirror. Edit the canonical copy and re-copy. Read on demand (trigger: migrating tests to
> doctests, or wiring doctests into the test gate).

A **unit test should be a doctest by default** — put the `example → output` in the docstring / doc
comment next to the code it documents, so it documents and tests in one place, and wire it to run
as part of the project's test gate. A plain test (`pytest` function / Rust `#[test]`) is the
deliberate **exception**, taken only for a reason below. This is language-agnostic; the per-language
*wiring* is in the sections at the end.

## Keep it a plain test (the exception) when it

- would need a **debugger to understand** the code under test;
- uses **fixtures / parametrization / `pytest.raises` / `#[should_panic]`** — machinery a doctest
  can't express cleanly;
- is **tolerance-based** (`math.isclose`, `numpy.allclose`, `pytest.approx`) or **randomized**;
- is a **type-checker assertion** (`typing.assert_type`) or an **operation-driven type** check
  (`type(x) is …` / `assert isinstance(...)`), including int-vs-float type regressions;
- has a **noisy or version-unstable `repr`** (long symbolic output; a value whose text changes with
  a library/compiler version);
- guards an **internal invariant or a specific regression** not meant for user-facing docs.

If none apply, it is a doctest. The author should be able to name which reason when it isn't.

## The migration is usually consolidation, not creation

A book/pedagogical repo often already carries doctests **alongside** the plain tests. So "push into
doctests" is frequently just **delete the redundant plain test once a doctest covers it** — after
confirming the doctest asserts the same thing (extend the doctest first if it covers only part).
Verify the test gate is green after each small batch. (Also check whether the *wiring* already
exists before adding it — see the per-language sections.)

### Hazards when deleting a test it duplicates

- **A `pinned by tests/…` / `proved in tests/…` doc reference goes dangling** when you delete the
  cited test. Fix the reference in the same change (repoint it at the doctest, or drop it) — a
  reference to a deleted test is a broken artifact.
- **A test that is a book/doc literalinclude source must NOT be deleted** — it is the book's code,
  and deleting it breaks the rendered doc and the region gate. Grep the test files for the doc-region
  marker (e.g. `doc-region`) before deleting anything.
- **Generated code: the doctest lives in the GENERATOR, never the generated file.** For a codegen
  project, author the doctest in the generator's doc table and regenerate; the (usually gitignored)
  output is never hand-edited. The generated file is still collected by the doctest runner, so its
  doctests run — and are linted. **But a docstring SHARED across generated classes or dimensions can
  host a doctest only if it is valid for every one of them.** A doc reused by two roles (a `.i()` on
  both a bivector and a versor), or a per-grade class/property doc emitted for every dimension (where
  the type's constructor arity or which blades exist differ), cannot carry one doctest that fits all
  — that test stays a plain test unless the generator is refactored to emit a per-role / per-dimension
  doc. (And editing a doc built directly as an AST constant means getting its indentation and
  regen-determinism exactly right.)

Not every test has a clean doctest home — a **broad multi-case regression** (one test asserting many
distinct behaviors across several dimensions) also keeps its plain test; migrate only the subset that
has a single home, and leave the regression.

## Writing doctests that actually pass

- **Annotate every binding IN the doctest too.** The house "annotate every binding" rule does not
  stop at the doctest fence: a Python doctest writes `name: T = ...` and a Rust doctest writes
  `let x: T = ...`, exactly as the surrounding code would. A doctest is example code the reader
  copies, so it models the house style. (hanoi, 2026-10-27 — the bindings were retrofitted when the
  first batch shipped them bare.)
- **A doctest runs in its MODULE's namespace** (Python) / crate scope (Rust): a hand-written
  module's method example must **import the concrete type** it builds a value from, and a type
  exposes only its **own** attributes (e.g. a grade-1 `Vector` has `e_1` but not the bivector
  `e_12` — reach the right type). 
- **Keep outputs `repr`-stable:** prefer `>>> expr == expected` → `True`, or coerce
  (`int(...)`), over printing a value whose `repr` is a library-specific form. Two concrete traps: a
  value whose type **eagerly normalizes** numbers (gacalc's `Gn` turns `1.5` into a `sympy` `Float`
  that prints `1.50000…`, so print from the lazy type or compare with `==`); and long
  version-sensitive outputs (a new library/runtime version adds entries and breaks the expected
  block — the failure then means "regenerate the expected text", not a real bug).
- **A doctest whose output contains backslashes needs a RAW docstring** (`r"""`), or an escape like
  the `\v` in `\vec` becomes a vertical tab in the docstring *value* before the doctest runner ever
  sees it. (gacalc's `blade_dict_latex` was converted to `r"""` to host a LaTeX-string doctest.)
- **Lint applies to doctest lines.** A line-length limit (ruff `E501`, rustfmt) counts doctest lines
  inside docstrings/doc comments — keep them within the limit by wrapping the statement (Python
  `...` continuation) or trimming the inline comment. Run the format/lint gate over the doctests,
  not just the test runner.
- **Capture the real exit code when checking.** A `pytest … | tail` pipe reports the pipe's exit
  (0), masking a failed doctest — read the summary line or capture `${PIPESTATUS[0]}`.

## Python

- **Wiring:** pytest with `addopts = --doctest-modules` and `testpaths` covering `src` (and the
  package). The `make test` target runs it. Check whether this is already configured before adding.
- **Import-mode for a src-layout package with relative imports:** add `--import-mode=importlib`
  alongside `--doctest-modules`. Without it `--doctest-modules` imports each module as a top-level
  module, and a `from . import x` then fails with "attempted relative import with no known parent
  package" — collection crashes before any doctest runs. (hanoi, 2026-10-27.)
- **Import-time-execution trap, and the `__main__` guard as the fix:** `--doctest-modules` *imports*
  every module it collects, so a module that runs code at import — a demo, a script that opens a
  window or calls `sys.exit()` — crashes collection. The fix is to guard that code with
  `if __name__ == "__main__":` (see the standard-practice rule in `python-coding-standard.md`); only
  exclude a module from `testpaths` when it genuinely cannot be made import-safe. When every module
  is already `__main__`-guarded (hanoi's were), `testpaths = tests src` needs no allowlist — a good
  reason to apply the guard project-wide *before* wiring the doctest gate, so the gate's config stays
  a plain "collect everything". (hanoi, 2026-10-27: confirmed all 11 modules import cleanly headless,
  so no per-module exclusion was needed.)
- **Discoverability:** a test file named with a hyphen or `-test` (e.g. `foo-test.py`) is collected
  by neither `pytest` nor `-m unittest`; migrating its cases into module doctests sidesteps that.

## Rust

- **Wiring is nearly free:** `cargo test` already compiles and runs every ` ```rust ` example in a
  `///` / `//!` doc comment (`cargo test --doc`). Ensure a `make test` target runs `cargo test` —
  a `cargo check --all-targets` gate compiles but does **not run** tests, so it is not enough.
- Show the `use` lines an example needs, or hide pure setup with a leading `#` on the line.

## Contributing projects

Each project that does a doctest migration appends what it newly learned here (the project's task
says to). First contributor: gacalc (github.com/billsix/geometricalgebra, 2026-10-27) — source of
the consolidation, doc-region, generator, namespace, and lint lessons above.

- **hanoi** (github.com/billsix/towersofhanoi, 2026-10-27) — a two-language migration (Python
  package + Rust workspace) done together. Lessons: `--import-mode=importlib` for the src-layout
  package; the `__main__`-guard as the import-safety fix (and applying it project-wide first, so the
  gate config is a plain "collect everything"); typed doctest bindings in both languages; and the
  cross-language shape of the consolidation — in Rust it is "delete the `#[test]` once a ` ```rust `
  doctest on the function covers it", keeping the loop/property (`move_count_is_2n_minus_1`,
  `render_dimensions`), exhaustive (`labelling_for_round_trip`), and multi-step
  (`render_after_one_move`, the `apply`/`replay` sequences) tests as plain `#[test]`s — the same
  exception list as Python, spelled in Rust.
