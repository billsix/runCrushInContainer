# Investigate first-query context bloat on geometricalgebra (~48K tokens)

**Status:** Done (diagnosed 2026-09-13) — the ~48K is attributed; two oversized context files are
84% of the system prompt. Trim is the follow-up `tasks/trim-crush-context-files.md`. Ready to
archive in its own commit after the work commit lands.
**Priority:** 3
**Difficulty:** 3

## BLUF

Running the Crush client against `geometricalgebra`, the **first** query already consumes ~70%+ of
the context window (~48K tokens) before the model does much. The task is to find out **exactly what
fills the context on the first turn and report it** (diagnosis only; a trim is a follow-up). The
approach is instrumentation, not guessing: a build-gated debug patch (`crush-context-debug.patch`,
`CRUSH_CONTEXT_DEBUG=1`, default OFF) logs a per-source token/byte breakdown of the assembled system
prompt to the crush log, which the maintainer's on-host run writes into the project's
`.crush/logs/crush.log` — readable by the agent through the mount. "Done" = the ~48K is attributed
source-by-source and reported, with a recommended trim.

## Context — read first

- **`tasks/reference/crush-context-assembly.md`** — the durable write-up produced for this task: how
  Crush v0.89.0 builds the first-turn context (system prompt = base coder template + project context
  files + global context files + skills XML + git status; plus tool schemas + messages outside it),
  the measured file sizes, the log path, and the instrumentation. Read it before touching this.
- **The `@`-import autoload patch:** `client/patches/crush-at-import.patch` (default ON,
  `CRUSH_AT_IMPORT=1`) expands a whole-line `@path` recursively **inside `processFile`**, so a
  context file's size already includes what it imports. `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`.
- **The baked global context:** `client/entrypoint/crushrc` sets
  `option global-context-path /root/.config/crush/CLAUDE.md`. That baked conventions file
  (`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, 27 KB) `@`-imports only
  `ai-coding-conventions.personal.md` — the host overlay, mounted unconditionally (32 KB on the
  maintainer's host).
- **The mounted project's own context:** geometricalgebra's `/work/CLAUDE.md` (**~75 KB ≈ 18.7K
  tokens**) auto-loads on top of the global one; it has no `@`-import lines (loaded verbatim).

**Preliminary arithmetic (a HYPOTHESIS the log confirms or refutes — do not report as the answer):**
geometricalgebra CLAUDE.md (~18.7K) + baked global CLAUDE.md (~6.8K) + `@`-imported personal overlay
(~8K) ≈ **~33.5K tokens of context files alone**, before the base template, skills XML, tool schemas,
and messages. That already approaches the observed ~48K, so the single largest lever is likely
geometricalgebra's own oversized `CLAUDE.md`, not `@`-import runaway (the imports here are shallow).
The instrumentation exists precisely to prove this rather than assume it — there could be a
configured directory context-path being walked recursively, a large skills XML, or a surprise.

## Is the logging-patch approach reasonable? — yes

Decided 2026-09-13. It fits cleanly and is the right tool:

- **The patch system already works this way.** `crush-context-debug.patch` is one more flag-gated
  patch in `client/patches/`, applied by `03-build-crush.sh` under `CRUSH_CONTEXT_DEBUG` (default 0),
  plumbed through the Dockerfile ARG and Makefile `--build-arg` like every other flag. Kept in the
  repo, off by default — same "keep the patch, don't ship it applied" posture as the LSP patches,
  except default OFF because it is a diagnostic, not a fix.
- **Logs reach the agent.** Crush logs to `<data-dir>/logs/crush.log` = `.crush/logs/crush.log` in
  the project. The maintainer runs on the host, so the log lands in the host project dir, which is
  mounted into this sandbox — the agent reads `/foo/opt/geometricalgebra/.crush/logs/crush.log`
  directly. This is the exact "you record logs, I read them" loop the maintainer asked for.
- **Small and low-risk.** It reuses Crush's own `skills.ApproxTokenCount` and `log/slog` (both
  already imported), touches only `promptData`/`Build`, logs at Info (no `option debug` needed), and
  applies with or without `CRUSH_AT_IMPORT`. Verified: the instrumented package compiles, and the
  patch `git apply --check`s on stock v0.89.0 **and** after `crush-at-import.patch` (real build order).
- **No debugger.** Print/trace instrumentation (per the print-debugging reference) is the fit here:
  the question is "what is in the assembled prompt and how big," which a few well-placed logs answer
  directly and reproducibly across the maintainer's runs, where attaching a debugger to a TUI on the
  airgapped/host box is impractical.

## What was built (2026-09-13)

- **`client/patches/crush-context-debug.patch`** — instruments `internal/agent/prompt/prompt.go`.
  In `promptData`: one `CTXDBG context-file` line per context file (`scope` project/global, `path`,
  `bytes`, `approx_tokens`, content already `@`-expanded), plus `CTXDBG skills-xml`,
  `CTXDBG git-status`, and a `CTXDBG context-files-total` summary. In `Build`: `CTXDBG
  system-prompt-total` (bytes + approx tokens of the whole assembled system prompt).
- **Build wiring:** `03-build-crush.sh` (`CRUSH_CONTEXT_DEBUG` env default 0 + `apply_patch` line +
  header doc), `client/Dockerfile` (`ARG CRUSH_CONTEXT_DEBUG=0` + RUN env passthrough),
  `client/Makefile` (`CRUSH_CONTEXT_DEBUG ?= 0` + `--build-arg`). Verified `make -n image` emits
  `--build-arg CRUSH_CONTEXT_DEBUG=0` by default and `=1` when overridden.

## Findings (measured 2026-09-13, `CRUSH_CONTEXT_DEBUG=1` run against geometricalgebra)

The CTXDBG log (`/foo/opt/geometricalgebra/.crush/logs/crush.log`) attributed the first-turn
context. The **coder** agent's assembled system prompt was **158,955 B ≈ 39,739 tok**, of which:

| Source | Bytes | ~Tok | % of system prompt |
|---|---|---|---|
| project `/foo/opt/geometricalgebra/CLAUDE.md` | 74,732 | 18,683 | 47% |
| global `/root/.config/crush/CLAUDE.md` (27 KB baked conventions **+ 32 KB personal overlay `@`-imported**) | 59,146 | 14,787 | 37% |
| base `coder` template (derived: total − the rest) | ~21,300 | ~5,315 | 13% |
| git-status | 2,599 | 650 | 1.6% |
| skills-xml | 1,214 | 304 | 0.8% |

The maintainer's ~48K first turn ≈ **39.7K system prompt + ~8K fixed tool schemas + the message**.
Conclusions:

- **The bloat is two context files — 33,470 tok, 84% of the system prompt.** Stage 2 (tools/messages)
  was not needed: the system prompt alone accounts for the bulk, and the ~8K remainder is fixed,
  project-independent tool-schema overhead, not the complaint.
- **`@`-import is not runaway recursion.** It splices exactly one file — the 32 KB personal overlay —
  into the global CLAUDE.md: `27,116 + 32,080 − 50 (the @line) = 59,146`, matching the logged size
  byte-for-byte. So the personal overlay costs ~8K tok every session by being `@`-imported into the
  always-loaded global file.
- **Not LSP, not skills.** skills-xml is 304 tok; git-status 650; both negligible.
- The `task` sub-agent's prompt is 943 B (236 tok) — no context files spliced; irrelevant to the
  first-turn cost.

**Recommended trim (spawned as `tasks/trim-crush-context-files.md`, proposed):**
1. **Biggest lever — shrink geometricalgebra's `/work/CLAUDE.md` (18.7K tok).** 75 KB in an
   always-loaded file is the exact anti-pattern the maintainer's own conventions warn against (keep
   CLAUDE.md lean; push detail into `tasks/reference/`). Halving it saves ~9K tok every turn.
2. **Second — the global context (14.8K tok).** The 32 KB personal overlay (~8K tok) is `@`-imported
   into every session; trimming it, or not `@`-importing the whole of it, is a cross-project win.
   (Judgment call — it's the maintainer's conventions body; recorded as an option, not a directive.)

## Debugging strategy (instrumentation-driven, staged)

**Stage 1 — attribute the system prompt (the built patch).**
1. `[HOST]` `make -C client image CRUSH_CONTEXT_DEBUG=1`
2. `[HOST]` run the client against geometricalgebra and send **one** query.
3. `[AGENT]` `grep CTXDBG /foo/opt/geometricalgebra/.crush/logs/crush.log` and tabulate: each context
   file's tokens, skills XML, git status, and `system-prompt-total`. Compare `system-prompt-total`
   against the input-token count the client UI showed for that first turn.
   - If `system-prompt-total` explains most of the UI number → the bloat is context files; report the
     ranked contributors and stop. The trim follow-up is obvious (shrink geometricalgebra's
     `/work/CLAUDE.md`, and/or narrow what the baked global file `@`-imports).
   - If a large gap remains → go to Stage 2.

**Stage 2 — only if a gap remains: attribute tools + messages.** Add a second small patch near
`internal/agent/agent.go:687` (where `fantasy.WithSystemPrompt` and the tools are attached) logging
the serialized tool-definitions size and the message-token estimate. The UI total = system prompt +
tool schemas + messages; Stage 1 measures the first, Stage 2 the rest.

**Change one variable at a time.** If a contributor is suspected (e.g. the `@`-import of the personal
overlay), a clean re-measure with that input removed (a run with a trimmed overlay, or
`CRUSH_AT_IMPORT=0`) isolates its share — but only after Stage 1 names the suspect.

## Verification / done-state

- The CTXDBG breakdown accounts for the observed ~48K first-turn context (system-prompt-total plus,
  if needed, Stage-2 tools/messages), reported ranked largest-first.
- A recommended trim is named (and, if the maintainer wants it, spun into a follow-up "trim the
  context" task).

## Archival note

At archive time: set/keep `CRUSH_CONTEXT_DEBUG` default **0** (it already is) so shipped images are
unaffected, **keep `crush-context-debug.patch`** in `patches/` for reuse, and fold any durable
findings into `tasks/reference/crush-context-assembly.md`. The patch is not a one-shot adhoc script —
it is a retained, flag-gated diagnostic like the LSP patches, so it is **not** `git rm`'d on archive.

## Related

- `tasks/reference/crush-context-assembly.md` — the durable mechanism + measurements (created for this).
- `client/patches/crush-context-debug.patch` — the instrumentation.
- `client/patches/crush-at-import.patch` + `tasks/archive/2026/08/21/patch-crush-for-at-imports.md` — the `@`-import mechanism.
- `tasks/reference/crush-capabilities.md` (context/instruction-file behavior), the baked
  `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`.
