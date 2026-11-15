# Made the egress sweep cover the image that ships, and fail instead of passing vacuously

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 2
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §5.1, §5.3 F5

## What this did

`tools/sweep_egress_patch_combos.py` listed 14 of the 17 patches, so its "audit-default"
combination was not the shipped image (the two LSP patches are on by default). Changed:

- `ALL` lists all 17 in `client/entrypoint/03-build-crush.sh`'s order; `DEFAULT` (the shipped set)
  adds `crush-lsp-async.patch` and `crush-lsp-router-notif.patch`.
- `touched_files()` also reads `+++ b/<path>` lines, so the two LSP patches (plain `diff -u`
  output, no `diff --git` header) are in the byte-identity manifest. Decision: extend the parser
  rather than regenerate the patches, which would change patch files for no behavioural gain.
- `check_setup()` makes the sweep exit 2 when `ALL` and `client/patches/` differ, or when
  `client/vendor/crush` is not its own git repo (inside the runCrush work tree, `git apply` skips
  the patches silently and every combination would "pass"). `--list` still works without the tree.
- Docs: `tasks/reference/architecture.md` and `dependency-network-audit.md` say 46 combinations over
  17 patches.

The same commit adds the patches' Go tests (`tasks/archive/2026/11/15/patch-go-tests-gate.md`).

## Verification

`--list` → 46 combinations (14 singles became 17; the build and power-set combinations are
unchanged in number). The full sweep against `client/vendor/crush` (`v0.89.0`): `SWEEP OK: 46
combinations applied, reversed, and verified byte-identical`, 2m40s. `touched_files()` returns 34
files including the two powernap files. ruff, ty, `check_local_annotations.py` clean.
