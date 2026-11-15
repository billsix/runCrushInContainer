# Fixed triage_dependency_egress.py's nested-module walk and tier labels

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 5
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §4.1 F13

## What this did

`tools/triage_dependency_egress.py` walked each module's whole directory, so a parent module also
scanned every nested module (20 parent/child pairs in `modules.txt`): `cloud.google.com/go`, which
ships no `.go` files of its own, was reported as NETWORK. `scan_module` now prunes other modules'
roots from its walk. The header names the four tiers `classify` returns (it said
NETWORK / maybe / no-network), and the sort order covers all of them, so `imports-only` and
`url-strings-only` rows no longer sort after `no-network`. Also: every binding annotated, docstrings
on `main`, files opened with `with` (SIM115), `startswith` with a tuple (PIE810), the file
executable (EXE001), ruff-formatted.

`tasks/reference/dependency-network-audit.md`'s triage counts and the `cloud.google.com/go` row are
updated to the new output.

## Verification

Before and after outputs against the vendored tree (213 modules): the only tier change is
`cloud.google.com/go` NETWORK → no-network (NETWORK 46 → 45, no-network 147 → 148). ruff, ty and
`check_local_annotations.py --include-module` clean.
