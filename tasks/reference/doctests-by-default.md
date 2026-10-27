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
  doctests run — and are linted.

## Writing doctests that actually pass

- **A doctest runs in its MODULE's namespace** (Python) / crate scope (Rust): a hand-written
  module's method example must **import the concrete type** it builds a value from, and a type
  exposes only its **own** attributes (e.g. a grade-1 `Vector` has `e_1` but not the bivector
  `e_12` — reach the right type). 
- **Keep outputs `repr`-stable:** prefer `>>> expr == expected` → `True`, or coerce
  (`int(...)`), over printing a value whose `repr` is a library-specific form. Avoid long
  version-sensitive outputs (new library/runtime versions add entries and break the expected block —
  the failure then means "regenerate the expected text", not a real bug).
- **Lint applies to doctest lines.** A line-length limit (ruff `E501`, rustfmt) counts doctest lines
  inside docstrings/doc comments — keep them within the limit by wrapping the statement (Python
  `...` continuation) or trimming the inline comment. Run the format/lint gate over the doctests,
  not just the test runner.
- **Capture the real exit code when checking.** A `pytest … | tail` pipe reports the pipe's exit
  (0), masking a failed doctest — read the summary line or capture `${PIPESTATUS[0]}`.

## Python

- **Wiring:** pytest with `addopts = --doctest-modules` and `testpaths` covering `src` (and the
  package). The `make test` target runs it. Check whether this is already configured before adding.
- **Import-time-execution trap:** `--doctest-modules` *imports* every module it collects, so a
  module that runs code at import — a demo, a script that opens a window or calls `sys.exit()` —
  must be guarded with `if __name__ == "__main__":` or excluded from `testpaths`, else collection
  crashes.
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
