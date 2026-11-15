# Check that Granite works with the 64k context it is served and registered with

**Status:** proposed — needs go-ahead (a hands-on check on the Mac)
**Priority:** 6
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §2.5

## BLUF

IBM Granite 34B Code Instruct is an 8k-context model, but the server runs it with the shared
`CTX ?= 65536` and the crushrc registers it with a 64k context window. The maintainer chose to keep
64k for now (2026-11-15). This task checks whether that works in practice. Done means a recorded
result: Granite either holds up past 8k tokens, or its context is set to 8k on both sides.

## Context

- `server/Makefile:67` describes Granite as "(8k ctx)". `server/Makefile:176` sets
  `CTX ?= 65536` for every model, so `make serve MODEL=granite` passes `-c 65536`.
- `client/entrypoint/crushrc:85` registers it as
  `try_model 8082 granite-code "IBM Granite 34B Code" 65536`, so Crush's compaction assumes 64k.
- If the model degrades past its trained 8k context, long Crush sessions would get worse answers
  before compaction kicks in. If it holds up (RoPE scaling, or the GGUF carries a longer context),
  64k is fine.
- `CLAUDE.md` asks to keep the server `CTX` and the crushrc `--context-window` in sync. That
  coupling holds today (both 64k), so a change here must change both.

## Plan

1. `[MAC]` `make serve MODEL=granite` and read the llama-server log lines that report the model's
   trained context (`n_ctx_train`) and any RoPE/context warning (`tasks/reference/new-hardware-bringup.md`
   names the log lines).
2. `[CONTAINER]` Run a Crush session against Granite that goes well past 8k tokens (for example,
   ask about a large file, then follow up), and judge whether answers stay coherent.
3. Record the result here. If 64k does not hold up, give Granite its own context (a per-model
   `MODEL_CTX_granite` in `server/Makefile` and 8192 in the crushrc line), keeping the two in sync.
