# Document "doctests by default" for Python and Rust, wired into `make test`

**Status:** complete
**Completed:** 2026-10-27
Created 2026-10-27 (William Emerison Six <billsix@gmail.com>).

Documented in the shared conventions layer that Python and Rust projects use doctests by default and
that `make test` must run them. The convention and the migration lessons live in
**`tasks/reference/doctests-by-default.md`** (language-agnostic core + `## Python` / `## Rust`
sections), with pointer bullets in `tasks/reference/python-coding-standard.md`,
`tasks/reference/rust-coding-standard.md`, the shared `CLAUDE.md` read-on-demand list and the personal
overlay's Makefile contract; mirrored byte-identical from runClaudeInContainer (the `SHARED, VENDORED`
pattern).

Decided (William Emerison Six <billsix@gmail.com>, 2026-10-27) to finalize after the first project
migration (gacalc) instead of waiting for all five; later per-project migrations append what they
learn directly to the reference doc (each project's task carries that step). The other migrations
(github.com/billsix/modelviewprojection, github.com/billsix/towersofhanoi Python and Rust,
github.com/billsix/methodfinder, github.com/billsix/multivariate-math) were not done as part of this
task.

## The convention

- **Default:** a short, deterministic `input → expected output` unit test that also documents the
  code is a doctest (Python `>>>` in a docstring; Rust ` ```rust ` in a `///`/`//!` comment).
- **Exception:** keep a plain test when it needs a debugger to understand, uses
  fixtures/parametrization/`raises`/`should_panic`, is slow/randomized/symbolic, or guards an internal
  invariant not meant for public docs; the author should be able to name the reason. (The
  maintainer's framing, 2026-10-27: "most tests can be doctests; the ones that shouldn't are where
  you'd reach for a debugger.")
- **Wiring:** Python pytest `addopts = --doctest-modules` over `src`, with an
  `if __name__ == "__main__":` guard on any module that executes at import (else collection crashes;
  mvp hit this). Rust `make test` runs `cargo test`, which runs `--doc`; `cargo check --all-targets`
  compiles but does not run them.

## Decided — where the convention lives (William Emerison Six <billsix@gmail.com>, 2026-10-27)

Split across homes so the always-read layer stays lean:

- **The coding rule → the language coding-standard reference docs** (read on demand), stated as a
  doctest-by-default rule with the named exception reasons.
- **The "`make test` collects doctests" mechanics → the personal overlay's Makefile contract**
  (`ai-coding-conventions.personal.md`), beside `format`/`type-check`.
- **The shared always-read `CLAUDE.md` → one terse pointer only** (it is paid every turn).

## Lessons from the gacalc migration (2026-10-27)

github.com/billsix/geometricalgebra consolidated ~34 pytest tests into doctests across
`vectorcalc`/`measure`/`frame`/`base.py` and the g2 generator (suite 711 → 695, green after each
batch). The lessons were written into `tasks/reference/doctests-by-default.md`: inventory existing
doctests first (the job is often deleting redundant pytest tests); verify the wiring before adding
it; fix dangling `pinned by tests/…` references and never delete a test that is a book
`doc-region` source; author doctests in the generator, not the generated file; a doctest runs in its
module's globals and should keep repr-stable outputs; ruff E501 applies to doctest lines; verify per
batch and capture `${PIPESTATUS[0]}` rather than trusting a `pytest … | tail` pipe.
