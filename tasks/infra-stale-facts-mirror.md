# Mirror the runClaude infra-doc fixes (:Z, counts, Fedora 44, rm sweep, clippy)

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.2, §1.4, §1.5 F17

## BLUF

Mirror of github.com/billsix/runClaudeInContainer `tasks/infra-docs-stale-facts.md` for the same stale facts here, plus this repo's own: the `NESTED_PODMAN_RUNTIME_TMPFS` that does not exist and the `nested-podman-design.md` header. Maintainer decision: "never `:Z`" for host trees.

## Context

- §0.2 F10 list (`:Z` at `client/Makefile:161,190,194,198,204,212,300,328,378` and `vendor.sh:69`; "~430"; "Fedora 44"; bare-`rm` sweep in `image-build-and-storage-pipeline.md:84,90,131`; clippy in `rust-gui-tui-and-ecosystem.md`).
- §1.5 `NESTED_PODMAN_RUNTIME_TMPFS`; §1.4 header and "default off".

## Plan

1. Fix each; drop `:Z` from host mounts (`:z` or none).
2. Re-grep each stale string.
