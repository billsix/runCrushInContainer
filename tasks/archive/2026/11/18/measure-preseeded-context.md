# A tool that measures how much context Crush preseeds, and what to defer (done)

**Done:** 2026-11-18 (William Emerison Six <billsix@gmail.com>)

The maintainer wants to run models with smaller context windows and had no way to see how much of the
window is used before the first prompt. The only earlier measurement (2026-09-13) came from the
build-gated `client/patches/crush-context-debug.patch`, which needs a special image and a manual session.

## The tool

`tools/measure_context.py` rebuilds the first-turn system prompt's file-backed part statically, from
this repo and the vendored Crush source (`client/vendor/crush`, v0.89.0), and prints bytes, tokens, and
the share of every `--context-window` the `client/entrypoint/crushrc` registers (plus any `--window`).
It needs no container, network or Crush build. How it models Crush, and how to run it, is in
`tasks/reference/crush-context-assembly.md` ("Measuring it statically: `tools/measure_context.py`").
Checks run on it: its doctests, `ruff check`/`ruff format --check` (88 columns), `ty check`, and
`tasks/reference/check_local_annotations.py`, all clean.

## Results (2026-11-18, `(bytes + 3) / 4` tokens)

Every session pays the global layer, **44,799 tokens: 68% of the 65,536 window** every model is
registered with, before the project or the first prompt.

| Source | Bytes | ~Tok |
| --- | --- | --- |
| `/root/.config/crush/CLAUDE.md` (baked conventions) | 57,785 | 14,447 |
| ↳ `@`-imported personal overlay | 66,721 | 16,681 |
| base `coder` template | 21,523 | 5,381 |
| tool schemas (CTXDBG 2026-09-13) | - | 8,000 |
| skills XML (CTXDBG 2026-09-13) | - | 304 |

Adding the project, measured for all 30 owned repos at `/mnt/sda1`: from 45,449 (no `CLAUDE.md`) to
**60,099 tokens for geometricalgebra (92% of 65,536)**, then epix-mirror 52,159 (80%) and imps 50,879
(78%). Most land around 72–75%.

Since September the global layer doubled, from 59,146 B to 124,506 B. The overlay went from 32 KB to
66.7 KB, and the baked conventions from 27 KB to 57.8 KB.

**The floor without any conventions** (template + tool schemas + skills) is about 13.7K tokens. That
is 42% of a 32K window and 84% of a 16K one, so with Crush a 16K model is unusable and a 32K one needs
the conventions cut to a few thousand tokens.

## Recommendations (the maintainer's to decide)

Recommendation 1 was done the same day: the global layer is now 30,237 tokens (46% of 65,536);
see `tasks/archive/2026/11/18/trim-crush-context-files.md`. Recommendations 2–4 are not done.


1. **Defer the personal overlay's "My project layout (the container-per-project template)" section:
   14,756 tokens, 23% of a 64K window, in every session.** It is a conformance reference needed only
   when working on a project's Dockerfile/Makefile/entrypoint. Move it to a read-on-demand reference
   doc with a short trigger line in the overlay. This alone takes the global layer from 44.8K to about
   30K. It is decision 3 in `tasks/archive/2026/11/18/trim-crush-context-files.md` (parked by the maintainer 2026-09-14),
   now twice the size it was then. The overlay is the maintainer's own file (github.com/billsix/dotfiles)
   and Claude Code loads it too.
2. **Move the baked conventions' long sections behind triggers**, as runClaudeInContainer did in
   September. The largest are "Code conventions" (2,436 tok), "Running projects in a nested container"
   (1,034), "Ad-hoc scripts" (1,021), "Task documents" (1,017) and "Git: I commit, you don't" (995).
3. **For a small-window model, a lean profile:** a crushrc variant that registers no global context
   path (or a short one), and `permissions deny` for tools that model won't use. `deny` writes
   `options.disabled_tools`, which removes a tool and its schema from the request
   (`tasks/reference/crush-capabilities.md`, "Permissions"). How much that saves wasn't measured; the
   schemas only exist at run time.
4. **Per-project trims for the largest project files:** geometricalgebra `CLAUDE.md` (58.6 KB,
   14,650 tok) and epix-mirror (~7.4K tok). For geometricalgebra the biggest sections are "Dev
   workflow" (2,836), "Module layout" (2,659) and "Architecture" (2,290).

The tool's token counts are Crush's 4-bytes-per-token estimate. To get the real tokenizer's count for
a given model, run it on the Linux host with the tunnel up: `--tokenize-url http://127.0.0.1:8080`.
