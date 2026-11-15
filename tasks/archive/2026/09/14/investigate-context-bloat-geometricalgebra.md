# Investigate first-query context bloat on geometricalgebra (~48K tokens)

**Status:** complete
**Completed:** 2026-09-13

Diagnosed why the Crush client's first query against `geometricalgebra` already used ~48K tokens
(~70% of the window). Built a flag-gated debug patch that logs a per-source breakdown of the
assembled system prompt, and the maintainer's on-host run attributed it: two oversized context files
are 84% of the system prompt. The trim was spun off as `tasks/trim-crush-context-files.md`. The
durable mechanism and measurements are in `tasks/reference/crush-context-assembly.md`.

## Approach

Decided 2026-09-13 to instrument rather than guess, with print/trace logging rather than a debugger
(attaching to a TUI on the host box is impractical; a few logs answer "what is in the prompt and how
big" reproducibly). The patch fit the existing flag-gated patch system, reused Crush's own
`skills.ApproxTokenCount` and `log/slog`, logged at Info, and applied with or without
`CRUSH_AT_IMPORT`. Crush logs to `.crush/logs/crush.log` in the project, which the host run wrote
into the mounted project dir, so the agent read the log directly.

## What was built

- **`client/patches/crush-context-debug.patch`** instruments `internal/agent/prompt/prompt.go`. In
  `promptData`: one `CTXDBG context-file` line per context file (`scope`, `path`, `bytes`,
  `approx_tokens`, content already `@`-expanded), plus `CTXDBG skills-xml`, `CTXDBG git-status`, and
  `CTXDBG context-files-total`. In `Build`: `CTXDBG system-prompt-total`.
- **Build wiring:** `CRUSH_CONTEXT_DEBUG` (default **0**) in `client/entrypoint/03-build-crush.sh`,
  `client/Dockerfile` (ARG + RUN env) and `client/Makefile` (`?= 0` + `--build-arg`).
- Verified: the instrumented package compiled, the patch `git apply --check`ed on stock v0.89.0 and
  after `crush-at-import.patch`, and `make -n image` emitted `--build-arg CRUSH_CONTEXT_DEBUG=0` by
  default and `=1` when overridden.
- Kept the patch in `client/patches/` at archive, default OFF, as a retained diagnostic (not a
  one-shot script).

## Findings (measured 2026-09-13, `CRUSH_CONTEXT_DEBUG=1` against geometricalgebra)

The coder agent's system prompt was **158,955 B ≈ 39,739 tok**:

| Source | Bytes | ~Tok | % of system prompt |
|---|---|---|---|
| project geometricalgebra `CLAUDE.md` | 74,732 | 18,683 | 47% |
| global `/root/.config/crush/CLAUDE.md` (27 KB baked conventions **+ 32 KB personal overlay `@`-imported**) | 59,146 | 14,787 | 37% |
| base `coder` template (derived: total − the rest) | ~21,300 | ~5,315 | 13% |
| git-status | 2,599 | 650 | 1.6% |
| skills-xml | 1,214 | 304 | 0.8% |

- The ~48K first turn ≈ 39.7K system prompt + ~8K fixed tool schemas + the message, so the planned
  Stage 2 (instrumenting tools/messages) was not needed.
- **The bloat is two context files: 33,470 tok, 84% of the system prompt.**
- **`@`-import is not runaway recursion.** It splices exactly the 32 KB personal overlay:
  `27,116 + 32,080 − 50 (the @line) = 59,146`, matching the log byte-for-byte.
- Skills XML, git status and the `task` sub-agent prompt (943 B, no context files) were negligible.

**Recommended trim** (carried into `tasks/trim-crush-context-files.md`): first, shrink
geometricalgebra's own `CLAUDE.md` (18.7K tok; halving it saves ~9K every turn); second, the
`@`-imported personal overlay (~8K tok), recorded as an option for the maintainer, not a directive.

## Related

- `tasks/reference/crush-context-assembly.md` — the durable write-up.
- `client/patches/crush-at-import.patch` + `tasks/archive/2026/08/21/patch-crush-for-at-imports.md` — the `@`-import mechanism.
- `tasks/reference/crush-capabilities.md`, the baked `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`.
