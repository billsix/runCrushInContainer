# Reordered the client Dockerfile and pinned Lean

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 6
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §8.1 F18

## What this did

- The Lean install now comes right after the toolchain layers (`00`, `01`, `01b`) and before the Crush
  build and its seventeen-odd `ARG`s, so a `CRUSH_TAG` bump, a patch edit or a flag flip no longer
  re-downloads Lean.
- Lean is pinned: `ELAN_VERSION ?= v4.2.4` and `LEAN_TOOLCHAIN ?= leanprover/lean4:v4.35.0` in
  `client/Makefile`, passed as build args, declared just before the Lean layer, and read by
  `client/entrypoint/install-lean.sh` and `client/entrypoint/vendor/vendor-lean.sh` (they fetched elan
  from `master` and the `stable` toolchain). Both tags were checked with `git ls-remote`.
- `ARG VENDOR_TOOLS` and its `hf` install moved after the Crush build, so `make vendor`
  (`VENDOR_TOOLS=1`) and a normal build share every layer above it.

## Verification

Nested `make -C client image` (on a native-overlay store) passed in 22m32s: `Lean (version 4.35.0)`,
both LSP patches PRESENT, `crush version v0.89.0+dirty`. `make -n image` passes the two pins.
