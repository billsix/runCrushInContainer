# Small fixes the review found

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 6
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §1.4, §1.6, §2.4, §3.6, §4.3, §4.4, §4.5, §8.2, §0.2 F21

## What this did

- **Personal details:** `williamsix@macmini` in both launchers' usage comments and
  `client/runCrush-common.sh` → `you@mac-studio.local`.
- **Stale comments:** `client/entrypoint/00-install-minimal.sh` no longer describes the removed
  `FULL_TOOLCHAIN`; `vendor.sh` says the vendored Crush tree is unpatched (the build applies the
  patches) and vendors one GGUF per active model; `tools/ty_lsp_probe.py`'s docstring says four modes
  and names `crush-lsp-router-notif.patch` as the fix, with AsyncHandler defensive.
- **`tools/ty_lsp_probe.py`:** typed state (a dataclass), every binding annotated, docstrings; ty's
  four errors, ruff and `check_local_annotations.py` clean. Run on a scratch file: minimal, rich and
  crushcfg answer in 0.02 s; noconfig stays pending, as documented.
- **Unverified downloads:** `client/entrypoint/01b-install-binary-tools.sh` checks the shfmt and procs
  release assets against pinned SHA-256s (taken from a download on 2026-11-15; neither project
  publishes a checksum file) and fails on a mismatch. runClaudeInContainer's copy got the same change,
  so the two scripts are identical again.
- **Gates:** `client/entrypoint/format.sh` also formats `entrypoint/vendor/*.sh` and `runCrush*.sh`;
  every shell script in `client/`, `vendor.sh` and `tools/` (except the byte-mirrored
  `check_helm_file_at_point.sh`) is shfmt-clean; `tools/check_launchers.sh`'s four bare `cd`s exit on
  failure (SC2164).
- **Makefile:** `make image-import` without `FILE=` prints usage and exits 2.

Not done, with reasons: the history-narration sentences in `CLAUDE.md` and the Makefiles (§1.6) are
dated decision notes that still explain current behaviour, so they stay; `03-build-crush.sh`'s
`GOBIN` version check (§4.5) is a lead with no observed failure (`GOBIN=/usr/local/bin` is on `PATH`
in the image); the parse-time `touch`/`mkdir` in the Makefile (§8.2) is what makes `make shell` work
on a first run, and moving it is a design change, not a fix.

## Verification

`bash tools/check_launchers.sh` → ALL PASS; `shellcheck -S warning tools/check_launchers.sh` clean;
`shfmt -d` clean on the covered scripts; `01b-install-binary-tools.sh` run for real → 0, with a bad
hash → 1; all scripts keep mode 100755.
