# Fixed checksum.py's edge cases and made the serve gate fail closed without a manifest

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §4.2, §5.2, §6.1 F12

## What this did

`server/tools/checksum.py` decides whether a model is served. Changed:

- `verify` with a missing or empty manifest now **fails** (exit 1, saying which), even with
  `--warn-unpinned`; it used to warn and exit 0, so `make serve` let the model through.
  `--warn-unpinned` now covers only a file with no entry (an ad-hoc quant), which is what the pull
  and serve gates use it for.
- `write` exits 1 when a FILE is not on disk (it printed "skip" and exited 0, so
  `make checksums-refresh` succeeded with an active model missing); the other files are still
  pinned.
- A manifest line lacking an algorithm makes `write` exit 2 with the file and algorithm named (it
  raised `KeyError`); nothing is written.
- No MANIFEST argument (`verify --quarantine`) exits 2 with usage (it raised `IndexError`).
- `main` dispatches with `match … case _`; the docstring gives the exit statuses; `HashConstructor`
  is a `type` alias; doctests cover `format_entry` and `main`'s usage paths.
- `server/Makefile`'s comments on `checksums-verify` and `serve` describe the new behaviour.

Decision (made in the batch, within the task's scope): `serve` keeps `--warn-unpinned`, because
the README documents `make serve MODEL_FILE=<another downloaded quant>`, and `checksums-refresh`
pins only the active defaults; failing closed on an unpinned file would break that. The review's
concern, an empty or missing manifest letting everything through, is closed.

## Verification

Scratch files: write with a missing file → 1 (the present file still pinned); verify OK → 0;
empty manifest → 1; no manifest → 1; `verify --quarantine` → 2; a manifest line without MD5 →
`write` 2 naming it; a changed file → 1. ruff, ty and `check_local_annotations.py --include-module`
clean; doctests pass.
