# Document "doctests by default" for Python and Rust, wired into `make test`

**Status:** proposed — needs go-ahead. **Do this AFTER the per-project doctest migrations land**
(see "Depends on" below) — the maintainer's explicit ordering: document the convention once the
per-project work has shown what the convention should actually say.
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

## Notes

- **Mirror to runCrush.** The shared CLAUDE.md / reference-doc layer is kept byte-identical between
  runClaudeInContainer and runCrushInContainer (the `SHARED, VENDORED` pattern) — whatever lands in
  the shared layer here is copied there in the same change.
