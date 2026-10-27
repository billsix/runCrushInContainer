# Document "doctests by default" for Python and Rust, wired into `make test`

**Status:** DONE 2026-10-27 (William Emerison Six <billsix@gmail.com>) — finalized after the gacalc
migration (the first project) rather than waiting for all of them; future per-project migrations now
**append** what they learn directly to the reference doc (each project's task carries that step).
Outcome: the convention + lessons live in **`tasks/reference/doctests-by-default.md`**
(language-agnostic core + `## Python` / `## Rust` sections), with pointer bullets added to
`python-coding-standard.md`, `rust-coding-standard.md`, the shared `CLAUDE.md` read-on-demand list,
and the personal overlay's Makefile contract; mirrored byte-identical to runCrushInContainer. This
task doc is the historical record and is being archived.
**Priority:** 7
**Difficulty:** 2
**Created:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)
**Updated:** 2026-10-27 (William Emerison Six <billsix@gmail.com>)

## BLUF

Write down, in the shared conventions layer, that **Python and Rust projects use doctests by
default** — prefer putting a unit test's `example → output` in the docstring / doc comment where it
reads well — **and that doctests must be wired to run as part of `make test`**. "Done" = the
convention is documented in the agreed home(s) (see the open question), mirrored into runCrush where
it belongs, and the per-language specifics are correct (Python: pytest `--doctest-modules`, guard
import-time-executing modules; Rust: `cargo test` runs `--doc` doctests for free).

## Depends on (do these first)

The per-project migrations that this convention generalizes from. Each is `proposed` in its repo:

- gacalc — github.com/billsix/geometricalgebra — `tasks/migrate-unit-tests-to-doctests.md`
  (wiring already done via `--doctest-modules`; migration only).
- mvp — github.com/billsix/modelviewprojection — `tasks/migrate-unit-tests-to-doctests.md`
  (wiring done, workaround testpaths to collapse; migration).
- hanoi — github.com/billsix/towersofhanoi — `tasks/python-doctests-into-make-test.md` and
  `tasks/rust-doctests-into-make-test.md` (needs the `make test` wiring added).
- methodfinder — github.com/billsix/methodfinder — `tasks/migrate-unit-tests-to-doctests.md`
  (itself gated on `tasks/adopt-container-project-template.md`, which adds the Makefile/`make test`).
- multivariate-math — github.com/billsix/multivariate-math — `tasks/migrate-unit-tests-to-doctests.md`
  (thin; may close as not-worth-it).

## What the convention should say (draft — refine from the landed work)

- **Default:** when a unit test is a short, deterministic `input → expected output` that also
  documents the code, write it as a **doctest** (Python `>>>` in a docstring; Rust ` ```rust ` in a
  `///`/`//!` doc comment). It documents and tests in one place.
- **Exception:** keep it a real test (pytest `#[test]`) when it needs a **debugger to understand**,
  uses fixtures/parametrization/`raises`/`should_panic`, is slow/randomized/symbolic, or guards an
  internal invariant not meant for the public docs. (The maintainer's framing, 2026-10-27:
  "most tests can be doctests; the ones that shouldn't are where you'd reach for a debugger.")
- **Wiring (the part that must not be forgotten):**
  - **Python:** pytest with `addopts = --doctest-modules` and `testpaths` covering `src`; `make
    test` runs it. Gotcha: `--doctest-modules` *imports* what it collects, so any module that
    executes at import (demos, scripts opening windows, `sys.exit()`) must have an
    `if __name__ == "__main__":` guard or be excluded — else collection crashes (mvp hit this).
  - **Rust:** `cargo test` already compiles and runs doc examples (`cargo test --doc`); ensure a
    `make test` target runs `cargo test` (the `make check` = `cargo check --all-targets` gate
    compiles but does **not run** tests, so it is not enough).

## Decided — where the convention lives (William Emerison Six <billsix@gmail.com>, 2026-10-27)

Split across homes, so the always-read layer stays lean:

- **The coding rule → the language coding-standard reference docs** (read-on-demand):
  `tasks/reference/python-coding-standard.md` and `tasks/reference/rust-coding-standard.md`. State
  it plainly: **a unit test should be a doctest BY DEFAULT** — put the `example → output` in the
  docstring / doc comment — **unless** one of the exception reasons applies (debugger needed to
  understand, fixtures/parametrization/`raises`/`should_panic`, slow/randomized/symbolic, or an
  internal invariant not meant for the public docs). The default is doctest; a plain test is the
  deliberate exception, and the author should be able to name which reason.
- **The "`make test` collects doctests" mechanics → the personal dotfiles overlay's Makefile
  contract** (`ai-coding-conventions.personal.md`), beside `format`/`type-check`: the `test` target
  runs the suite *including* doctests (Python pytest `--doctest-modules` with the import-time guard;
  Rust `cargo test`, which runs `--doc`).
- **The shared always-read `CLAUDE.md` → one terse pointer only** (it's paid every turn), e.g. a
  line under the coding-standards section saying doctests are the default and pointing at the two
  reference docs + the overlay's Makefile contract.

## Lessons from the gacalc migration (William Emerison Six <billsix@gmail.com>, 2026-10-27)

The first migration (github.com/billsix/geometricalgebra — ~34 pytest tests consolidated into
doctests across `vectorcalc`/`measure`/`frame`/`base.py` + the g2 generator, suite 711 → 695,
green after each batch) taught these, which the eventual reference-doc write-up should state:

- **Inventory existing doctests first — the job is often consolidation, not creation.** A
  book/pedagogical repo may already carry doctests *alongside* the pytest tests (gacalc's
  `measure`/`vectorcalc` were fully doctested already). So "push into doctests" is frequently just
  *delete the redundant pytest test* after confirming a doctest covers it — not writing new ones.
- **The wiring is often already present** — verify before assuming you must add it. gacalc and mvp
  already had `--doctest-modules`; only hanoi/methodfinder need wiring.
- **Consolidating deletes tests, so protect two things a doctest cannot replace:**
  - **`pinned by tests/…` doc references become dangling** when you delete the cited test. Fix the
    reference in the same change (point it at the doctest, or drop it) — cf. the "never cite an
    artifact you have not verified" rule.
  - **A test that is a book literalinclude source (doc-region markers) must NOT be deleted** — it
    breaks the book + the region gate. Grep for `doc-region` in the test files first. (gacalc's
    `test_multivector_add`/`subtract` carry a `# doc-region-end` marker — left untouched.)
- **Generated code: doctests live in the GENERATOR, never the generated file.** For a codegen
  project, author the doctest in the generator's doc table and regenerate; the gitignored output is
  never hand-edited (gacalc: `tools/gen_specialized.py`'s `CUSTOM_METHOD_DOCS`). The generated file
  IS still collected by `--doctest-modules`, so its doctests run — and are linted.
- **A doctest runs in its MODULE's globals**, so: a hand-written module's method doctest needs an
  explicit `import` of a concrete type to build a value; and a type exposes only its own attributes
  (a grade-1 `Vector` has `e_1` but not `e_12` → use `Bivector.e_12`). Keep outputs **repr-stable**:
  prefer `>>> expr == expected` → `True`, or wrap in `int(...)`, over printing a value whose repr
  may be a sympy/float form (and avoid long version-sensitive outputs — the methodfinder caveat).
- **Lint applies to doctest lines.** ruff **E501**/line-length counts docstring doctest lines — keep
  them within the limit by wrapping the statement with `...` continuation or trimming the inline
  comment. Run the format/lint gate on the doctests, not just pytest.
- **Keep-as-pytest, confirmed in practice** (the exception reasons): tolerance (`isclose`/numpy
  `allclose`), parametrized/fixtures, `pytest.raises`/`should_panic`, `typing.assert_type` or
  operation-driven **type** assertions (`type(x) is …`), symbolic/noisy repr, int-vs-float type
  regressions, and internal invariants not meant for user-facing docs.
- **Verify per batch, and capture the real exit code.** Run the suite after each small batch (stay
  green). A `pytest … | tail` pipe masks pytest's failure as the pipe's exit 0 — read the summary
  line or capture `${PIPESTATUS[0]}`. For a codegen project, also run the determinism gate
  (`make check-generated`) after a generator change.

## Notes

- **Mirror to runCrush.** The shared CLAUDE.md / reference-doc layer is kept byte-identical between
  runClaudeInContainer and runCrushInContainer (the `SHARED, VENDORED` pattern) — whatever lands in
  the shared layer here is copied there in the same change.
