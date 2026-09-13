# How Crush assembles the first-turn context — and how to measure it

**Reference document** — what fills the context window on the very first query, read from Crush
v0.89.0 source (`internal/agent/prompt/prompt.go`, `internal/agent/agent.go`,
`internal/skills/`, `internal/log/log.go`, `internal/cmd/root.go`, `internal/config/`), 2026-09-13
by William Emerison Six <billsix@gmail.com>. Written for the "first query eats ~48K tokens on
geometricalgebra" investigation (`tasks/investigate-context-bloat-geometricalgebra.md`); update in
place.

## Version banner + re-sync check

Pinned to **Crush `v0.89.0`** (the tag `client/Makefile` `CRUSH_TAG` builds). Every `file:line`
below is from that tag. **Re-sync:** if `CRUSH_TAG` no longer reads `v0.89.0`, re-clone the tag and
re-verify — Crush moves fast and the prompt-assembly code can be refactored, not just line-shifted.

## L0 — the capsule

The first request to the model is **system prompt + tool schemas + the conversation messages**.
Only the **system prompt** is project-dependent and is where bloat lives: it is the base "coder"
template with the project's context files, the per-user global context files, the skills XML, and a
git-status summary all spliced in. On a big repo the context files dominate — geometricalgebra's own
`/work/CLAUDE.md` is ~75 KB (~18.7K tokens) by itself. Tool schemas and the base template are
roughly fixed per session. To attribute the total, instrument the system-prompt assembly (the
`crush-context-debug.patch`, below) and compare its total against the provider-reported input
tokens; the gap is tools + messages.

## L2 — what goes into the system prompt, source by source

`prompt.Build()` (`prompt.go:82`) parses the `coder` template (`internal/agent/prompts.go:21`,
`coderPromptTmpl`) and executes it against a `PromptDat` built by `promptData()` (`prompt.go:165`).
`PromptDat` (`prompt.go:31`) carries every spliced piece:

| Field | Source | How loaded | Notes |
|---|---|---|---|
| base template | `coderPromptTmpl` (embedded) | — | fixed text; a few K tokens |
| `ContextFiles` | project context files | `loadContextFiles(cfg.Options.ContextPaths)` → `processContextPath` → `processFile` | **cwd-only discovery** for instruction files (`CLAUDE.md`/`AGENTS.md`/`CRUSH.md` + variants); no walk up to git root (`config.go:28` `defaultContextPaths`). A configured **directory** context-path is walked **recursively** (`processContextPath`, `prompt.go:117` `WalkDir`). |
| `GlobalContextFiles` | per-user context files | `loadContextFiles(cfg.Options.GlobalContextPaths)` | the client sets `option global-context-path /root/.config/crush/CLAUDE.md` (baked crushrc). |
| `AvailSkillXML` | builtin + user skills metadata | `skills.DiscoverBuiltin()` + `skills.ToPromptXML` (`prompt.go:177-205`) | one XML block describing every enabled skill; grows with the builtin skill set. |
| `GitStatus` | `git branch/status/log` | `getGitStatus` (`prompt.go:240`), only if `.git` present | small; branch + short status (≤20 lines) + last 3 commits. |

**`@`-import interaction (this repo's patch).** `crush-at-import.patch` (`CRUSH_AT_IMPORT`, default
ON in the client) expands a whole-line `@path` **inside `processFile`**, recursively (≤5 hops, cycle-
guarded). So a context file's logged size already **includes** everything it `@`-imports — a big
imported file shows up as its importer's byte count, not as a separate entry. The client's baked
global `CLAUDE.md` `@`-imports exactly one file, `ai-coding-conventions.personal.md` (the host
overlay, mounted unconditionally); geometricalgebra's `/work/CLAUDE.md` has no `@`-import lines.

**Deduplication.** `loadContextFiles` keys by **lowercased** expanded path (`prompt.go:151`), so the
same file registered twice is loaded once; distinct files that only differ in case collapse (a
footgun on case-sensitive filesystems, not a bloat source here).

### Measured sizes (2026-09-13, via `ApproxTokenCount`, unconfirmed until logged)

`skills.ApproxTokenCount(s) = (len(s)+3)/4` — the ~4-chars/token heuristic Crush itself uses "well
enough for diagnostic logging" (`skills/skills.go:382`). Byte sizes are exact; token figures are
that estimate:

- geometricalgebra `/work/CLAUDE.md`: **74,732 B ≈ 18.7K tok** (no `@`-imports; loaded verbatim).
- client baked global `CLAUDE.md`: **27,116 B ≈ 6.8K tok**, which `@`-imports —
- host `ai-coding-conventions.personal.md`: **32,080 B ≈ 8.0K tok** (spliced into the global file).

Those three total ~34 KB… no — ~134 KB ≈ **~33.5K tokens** of context files alone, before the base
template, skills XML, tool schemas, and messages. That already plausibly reaches the observed ~48K,
which is why the instrumentation measures rather than assumes. **Do not treat this table as the
answer** — it is the hypothesis the CTXDBG log confirms or refutes (there may be a configured
directory context-path being walked, a large skills XML, or a surprise).

## L2 — the authoritative total, and where the gap is

The number the UI shows as "context used" comes from the provider's reported usage
(`fantasy.Usage.InputTokens`); when a provider returns zero usage, Crush falls back to
`estimateMessageTokens(messages)` (`internal/agent/usage_fallback.go:23`). That total covers
**system prompt + tool schemas + all conversation messages** — more than the system prompt alone.
The system prompt is attached at `agent.go:687` (`fantasy.WithSystemPrompt`), tools alongside it.
So: **CTXDBG `system-prompt-total`** (below) vs the UI's input tokens → the difference is the tool
schemas plus the messages. On the *first* turn the only message is the user's prompt, so the gap is
essentially the fixed tool-schema overhead.

## Where the log goes, and how to read it

`log.Setup(logFile, debug)` (`internal/log/log.go:19`) writes **JSON lines** via a lumberjack
rotator (10 MB, 30-day). For the interactive TUI the path is
`filepath.Join(cfg.Options.DataDirectory, "logs", "crush.log")` (`internal/cmd/root.go:372`), and
`DataDirectory` defaults to **`.crush`** (`config.go:24`), resolved against the working dir. So when
the maintainer runs the client against a project mounted at `/work`, the log is
**`/work/.crush/logs/crush.log`** — which is the project dir on the host, and therefore also visible
from this sandbox at **`<project>/.crush/logs/crush.log`** (e.g.
`/foo/opt/geometricalgebra/.crush/logs/crush.log`). That mounted-through path is how the agent reads
what the maintainer's run produced.

- Default log level is **Info**; `option debug true` (or `--debug`) raises it to Debug. The CTXDBG
  lines are logged at **Info**, so no debug flag is needed to see them.
- `option debug-lsp true` adds LSP server stderr (that is how the ty id-0 bug was caught — see
  `crush-lsp-integration.md` §3a); unrelated to context logging.
- Filter the JSON log for the diagnostic lines: `grep CTXDBG .crush/logs/crush.log` (each is one
  JSON object with `msg` starting `CTXDBG`).

## The instrumentation: `crush-context-debug.patch`

A **DEBUG-only, build-gated** patch (`client/patches/crush-context-debug.patch`, flag
`CRUSH_CONTEXT_DEBUG`, default **0**). It touches only `promptData` and `Build` (regions the
`@`-import patch does not), and uses only already-imported packages (`log/slog`, `internal/skills`),
so it applies cleanly with or without `CRUSH_AT_IMPORT`. It logs, at Info level:

- `CTXDBG context-file` — one line per context file, `scope` project/global, `path`, `bytes`,
  `approx_tokens` (content already `@`-expanded).
- `CTXDBG skills-xml`, `CTXDBG git-status` — bytes + approx tokens.
- `CTXDBG context-files-total` — file counts and summed tokens per scope.
- `CTXDBG system-prompt-total` — bytes + approx tokens of the whole assembled system prompt.

**Build / run / read workflow** (the maintainer builds and runs on the host; the agent reads):

1. `[HOST]` `make -C client image CRUSH_CONTEXT_DEBUG=1`
2. `[HOST]` run the client against the project (e.g. geometricalgebra) and send one query.
3. `[AGENT]` read `<project>/.crush/logs/crush.log`, `grep CTXDBG`, and attribute the total.

Leave the flag **0** in shipped images; keep the patch in `patches/` for the next investigation.
This is the same "keep the patch, don't apply it" posture as the LSP bugfix patches, except this one
defaults OFF because it is a diagnostic, not a fix.

### Stage 2 (only if a large gap remains)

If `system-prompt-total` explains most of the UI's input tokens, stop — the fix is trimming context
files. If a big gap remains, the tool schemas or message history are the culprit; instrument the
request assembly near `agent.go:687` (log the serialized tool-definitions size and the message-token
estimate) as a second small patch. Prefer confirming Stage 1 first — the measured context-file sizes
above suggest the system prompt is the bulk.

## Sources

- Crush v0.89.0: `internal/agent/prompt/prompt.go` (assembly), `internal/agent/prompts.go` (coder
  template), `internal/skills/skills.go` (`ApproxTokenCount`, `ToPromptXML`),
  `internal/log/log.go` (`Setup`), `internal/cmd/root.go:372` (log path),
  `internal/config/config.go:24,28` (data dir, default context paths), `internal/agent/agent.go:687`
  (system prompt + tools attached), `internal/agent/usage_fallback.go` (token estimate fallback).
- `client/patches/crush-context-debug.patch`, `client/patches/crush-at-import.patch`.
- Companion: `tasks/reference/crush-capabilities.md` (context/instruction-file mechanics),
  `tasks/reference/crush-lsp-integration.md` (the debug-log path in practice).
