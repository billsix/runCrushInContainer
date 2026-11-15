# Reorder the client Dockerfile and pin Lean

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 6
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §8.1 F18

## BLUF

The Lean install sits after the Crush build and all its `ARG`s, so a Crush bump or patch edit re-downloads Lean, and `ARG VENDOR_TOOLS` near the top couples the vendor build and the normal build. Done means Lean sits next to `01b` and is pinned, and each `ARG` is declared just before the first layer that reads it.

## Context

- `client/Dockerfile:151-152` (Lean, unpinned elan `master` + `stable`), `:93-112` (ARGs), `:61` (`VENDOR_TOOLS`).

## Plan

1. Move the Lean layer up; pin the elan and toolchain versions as Makefile variables.
2. Move `ARG VENDOR_TOOLS` / `CRUSH_VENDORED` down.
3. `make image` (nested).
