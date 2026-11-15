# Small fixes the review found

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 6
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §1.4, §1.6, §2.4, §3.6, §4.3, §4.4, §4.5, §8.2, §0.2 F21

## BLUF

A batch of small, independent fixes. Done means each listed item is fixed and the checkers are clean.

## Context

- §3.6 `williamsix@macmini` → a placeholder; §1.6 history narration; §2.4 `00-install-minimal.sh` header; §4.3 stale comments; §4.4 ruff/ty/annotations/shellcheck/shfmt findings and `format.sh` coverage; §4.5 unverified `01b` downloads (checksum them), the `GOBIN` check; §8.2 Makefile parse-time side effects and the `image-import` guard; §0.2 `.gitignore` `#*#`, the unused `/etc/containers/storage.conf` COPY.

## Plan

1. Work through the list.
2. ruff, ty, `check_local_annotations.py`, shellcheck, shfmt clean.
