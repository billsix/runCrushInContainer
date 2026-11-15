# Pinned llama-server to loopback (HOST can no longer be overridden)

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 1
**Difficulty:** 1
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §2.1 F3

## What this did

`server/Makefile` had `HOST ?= 127.0.0.1`, so `make serve HOST=0.0.0.0`, or a `HOST` exported in the
Mac's environment (`?=` takes either), would bind the model server to the LAN, against the repo's
"loopback only" rule (`CLAUDE.md`, `tasks/reference/architecture.md`). It is now
`override HOST := 127.0.0.1`, the same way `PORT` is fixed, with a comment saying why.

## Verification

`make -n serve MODEL=glimmer` with no override, with `HOST=0.0.0.0` on the command line, and with
`HOST=0.0.0.0` exported, and `make -n serve-mlx` with it exported: all four show `--host 127.0.0.1`.
