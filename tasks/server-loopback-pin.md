# Pin llama-server to loopback (HOST cannot be overridden)

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 1
**Difficulty:** 1
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §2.1 F3

## BLUF

`server/Makefile:175` is `HOST ?= 127.0.0.1`, so `make serve HOST=0.0.0.0`, or an exported `HOST`, binds the model server to the LAN, against the repo's "loopback only" rule. Make it `override HOST := 127.0.0.1`, like `PORT`. Done means no command line or environment can change the bind address.

## Context

- `server/Makefile:175` and `:307` (`--host $(HOST)`); `:147` already `override`s `PORT`.
- `CLAUDE.md:65`, `tasks/reference/architecture.md:80` state the rule.

## Plan

1. `override HOST := 127.0.0.1`, with a comment.
2. Verify with `make -n serve HOST=0.0.0.0` and `HOST=0.0.0.0 make -n serve`: both show `--host 127.0.0.1`.
