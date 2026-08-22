# Crush capabilities vs Claude Code — what ports, what doesn't

**Reference document** — a verified map of Crush's extensibility/context features, so the
runClaudeInContainer→runCrushInContainer convention port can target real mechanisms instead
of guesses. Not a task; update in place. Companion to
`tasks/port-runclaude-conventions-systems.md` (the ordered plan built on this). Last updated
2026-08-19 by William Emerison Six <billsix@gmail.com>.

## Version banner + re-sync check

Pinned to **Crush `v0.89.0`** (commit `ba531a4`, 2026-08-12) — the tag the client image
builds (`client/Makefile` `CRUSH_TAG`). Every `file:line` below is from that tag's source,
cloned and read directly (not from docs alone). Crush is young and moving fast, so a version
bump can be a structural refactor, not line drift.

**Re-sync:** if `client/Makefile`'s `CRUSH_TAG` no longer reads `v0.89.0`, re-clone that tag
and re-verify the claims here before trusting them — treat "ABSENT" verdicts as
v0.89.0-specific (several absent features are on Crush's in-repo `docs/*/FUTURE.md` roadmap).

## The three findings that shape the whole port

1. **Crush DOES auto-load a conventions file** — `CLAUDE.md`, `AGENTS.md`, `CRUSH.md` (and
   `.local`/case variants, plus Cursor/Copilot/Gemini files) are read from the working
   directory and spliced into the system prompt. So the runClaudeInContainer conventions body
   has a real home. **But discovery is cwd-only for instruction files — no walk up to the git
   root** (config files *do* walk up; instruction files don't). `internal/config/config.go:28`
   (`defaultContextPaths`), `internal/agent/prompt/prompt.go:110` (`processContextPath`,
   `SmartJoin(WorkingDir(), p)`).
2. **Crush has NO recursive `@`-import.** A `@path` written inside a loaded `CLAUDE.md`/
   `AGENTS.md`/`CRUSH.md` is passed to the model as **literal text** — `processFile` is just
   `os.ReadFile` with no scanning (`prompt.go:99`). This breaks runClaudeInContainer's entire
   delivery mechanism, which `@`-imports the 5 reference docs + the personal overlay into every
   session. **The replacement:** register each file as its own **global context path** (below),
   which Crush loads and splices natively — cleaner than `@`-import, just more explicit.
   **Update (2026-08-20):** this repo also carries a **local patch** that adds recursive `@`-import
   to Crush itself (`client/patches/crush-at-import.patch`, applied at image build when
   `CRUSH_AT_IMPORT=1`), so under the patched image a `@path` on its own line *is* spliced — see
   `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`. This finding describes **stock** v0.89.0; global-context-path
   stays the zero-maintenance fallback.
3. **Custom commands exist and port**, but the file format differs: the **entire `.md` file is
   the prompt body** (no YAML frontmatter parsing — `loadCommand` at `commands.go:174` reads
   the whole file as `Content`; the filename is the command name), and arguments are any
   `$UPPERCASE` token, each auto-becoming a **required** arg Crush prompts for in a dialog
   (`extractArgNames`, regex `\$([A-Z][A-Z0-9_]*)`, `commands.go:18,190`). No `$ARGUMENTS`
   catch-all.

## Context / instruction files

- **Auto-loaded filenames** (`config.go:28-45`): `.github/copilot-instructions.md`,
  `.cursorrules`, `.cursor/rules/` (dir, walked recursively), `CLAUDE.md`, `CLAUDE.local.md`,
  `GEMINI.md`/`gemini.md`, `crush.md`/`Crush.md`/`CRUSH.md` (+`.local`), `AGENTS.md`/`agents.md`/
  `Agents.md`. `crush init` writes `AGENTS.md` by default (`option initialize-as`,
  `config.go:25,332`).
- **Add more project context files:** `option context-path <p>` (crushrc) / `context_paths`
  (JSON). User paths are **appended to** the defaults, not replacing them (`load.go:593`).
  `option reset context-path` clears.
- **Global (per-user) context — the `@`-import replacement:** `option global-context-path <p>`
  / `global_context_paths` (`config.go:316`). Defaults to `~/.config/crush/CRUSH.md` and
  `~/.config/AGENTS.md` (`load.go:546-552`); it's an **extendable list of absolute paths**, each
  loaded and spliced. Point entries at the reference docs + personal overlay to make them
  always-in-context.
- Path values expand `~` and `$VAR` (`prompt.go:139`).

## Custom commands (the slash-command analogue)

- **Load dirs** (`commands.go:121-136`): `~/.config/crush/commands/` and `~/.crush/commands/`
  (both `user:` prefix), and `<data-dir>/commands/` (default `.crush/commands`, `project:`
  prefix). `.md` only, walked recursively; nested dirs → `:`-joined IDs.
- **Format:** whole file = prompt body; filename = name; `$UPPERCASE` tokens = required prompted
  args (no frontmatter, no `$ARGUMENTS`). Porting a Claude command = drop its YAML frontmatter
  and rename `$ARGUMENTS` → a named token like `$SLUG`.
- MCP-server prompts and user-invocable skills also surface in the command palette
  (`commands.go:64,89`).

## Config system

- **`crushrc` is the modern format; `crush.json` is deprecated** (confirmed:
  `docs/config/README.md:66-69`, `569-573`). `crushrc` is an executable **Bash** script run
  through the embedded `mvdan.cc/sh` interpreter, exposing builtins: `provider`, `model`, `mcp`,
  `lsp`, `hook`, `permissions`, `option`.
- **Discovery/precedence** (`load.go:915-948`): global `/etc/crush/crush.json`,
  `~/.config/crush/{crushrc,crush.json}`, machine-state JSON `~/.local/share/crush/crush.json`
  (never executed); project configs found by walking **up from cwd to the git-worktree root**.
  Per-dir name priority `.crushrc > crushrc > .crush.json > crush.json`; project overrides
  global; crushrc overrides JSON.
- Env expansion: native in crushrc (Bash); selected string fields expanded in JSON. `$CRUSH_VERSION`
  exposed for version-gating.
- Per-project data dir `.crush/` holds `crush.db` (SQLite) and machine state.

## Other features (relevant to the port)

- **Hooks — SUPPORTED, Claude-Code-compatible, but only `PreToolUse` fires in v0.89.0** (more
  events are FUTURE-roadmap). `hook add PreToolUse --matcher … --command …` in crushrc;
  exit-code + JSON-envelope contract; `docs/hooks/README.md`, `internal/hooks`,
  `internal/agent/hooked_tool.go`. Only top-level agent tool calls are hooked, not sub-agents'.
- **Skills — SUPPORTED, interoperates with Claude Code.** Project skills auto-discovered from
  `.agents/skills`, `.crush/skills`, `.claude/skills`, `.cursor/skills` (cwd + git root); global
  from `~/.config/crush/skills`, `~/.claude/skills`, etc. (`load.go:1338-1372`).
- **Permissions — SUPPORTED:** `permissions allow/deny <tool>`, interactive ask default,
  `--yolo`/`-y` skip-all, per-session auto-approve. (Verified from source 2026-08-22:) `allow`
  **accumulates + dedups** across lines and skips the prompt for the listed tools; `deny` writes
  `options.disabled_tools`, which **hides** the tool from the agent entirely (not merely prompts).
  The tool names come from the registry **`internal/config` `allToolNames`** (29 tools; enumerated from
  the v0.90.0 source tree — the client pins v0.89.0, and the set is expected to match, but confirm
  against the pinned tag if it matters — file: `view edit multiedit write ls glob grep`; network:
  `fetch agentic_fetch download sourcegraph`; MCP: `list_mcp_resources read_mcp_resource`; plus `bash
  agent lsp_* crush_info crush_logs job_output job_kill question todos`). A PreToolUse hook can override per-call: stdout `{"decision":"allow"}`
  skips the prompt, `"deny"` blocks, `"none"`/omit falls through to the normal prompt; the command is in
  `$CRUSH_TOOL_INPUT_COMMAND`. runCrush uses `permissions allow` for the file tools (see
  `architecture.md` "Permissions").
- **MCP — SUPPORTED:** stdio/sse/http transports, per-server tool allow/deny, OAuth for http.
- **LSP — SUPPORTED, first-class:** `lsp add …`, `option auto-lsp`, LSP-backed edit/view tools.
- **Sessions — SUPPORTED:** SQLite `crush.db`; `--continue`/`-C`, `--session`/`-s`;
  `option auto-summarize` for compaction.
- **Context window & compaction:** the effective context is `min(server -c, model context_window)`.
  Crush auto-summarizes when the remaining budget drops below **~20% of `context_window`** (a flat
  20k buffer if `> 200k`); `context_window == 0` (unknown) **skips** compaction entirely
  (`internal/agent/agent.go:1038-1053`). For a `llamacpp` provider the enricher sets `context_window`
  from the server's `n_ctx` (`internal/discover/llamacpp.go`); pin it explicitly with `model add …
  --context-window N`. `option auto-summarize false` disables compaction. Read the server's live window
  from `/v1/models` `meta.n_ctx` / `n_ctx_train`. Full write-up:
  `tasks/archive/2026/08/20/context-window-sizing.md`.
- **Ignore files — SUPPORTED:** `.gitignore` + `.crushignore` (per-dir) + `~/.config/crush/ignore`.
- **Model switching — SUPPORTED:** `large`/`small` slots, `model add`, `provider add`.

## Provider & model selection — the built-in catalog and how to suppress it

Crush ships an embedded **Catwalk provider catalog** (OpenAI/Anthropic/… — *hundreds* of models) that it
merges in by default and offers in the model picker. The list is built by `config.Providers(cfg)`
(`internal/config/provider.go:170`), which returns the catalog UNLESS **`disable_default_providers`** is
set (`provider.go:175,186` short-circuit to custom-only). Two behaviors that surprise you:

- **The picker/onboarding shows the catalog when no usable provider is configured.** `IsConfigured()`
  = ≥1 enabled provider (`config.go:720`); if false, Crush enters onboarding and lists the catalog
  (`internal/ui/model/ui.go:491`).
- **A custom provider (e.g. `llamacpp`) with no explicit models auto-triggers discovery** at load
  (`GET /v1/models`, 3-second timeout, `load.go:382-475`); if discovery fails (endpoint down / airgapped)
  the provider is **deleted** (`load.go:471`), leaving zero providers → onboarding → the catalog appears.
  This is why an offline `crushrc` that relied on discovery showed ~15-20 models.

**To offer only a local model** (crushrc): `option default-providers false` (inverted → sets
`disable_default_providers`, `options.go:191`) **plus** an explicit `model add <provider>/<id>` so the
provider survives without discovery. runCrushInContainer's baked `crushrc` does exactly this — verified
`crush models` drops from **1532 → 1**. Full history + before/after:
`tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md`.

## What Crush does NOT have (so the port must drop or rework these)

- **Recursive `@`-import** — see finding 2. Use `global-context-path` instead.
- **User-defined named sub-agents** — only two hardcoded agents (`coder`, `task`); no
  `.claude/agents/*.md` analogue (`config.go:847-871`; `Agents` map is `json:"-"`). Sub-agent
  *delegation* exists (the `agent` tool); custom named agents don't.
- **Cross-session "memory"** — no auto-memory / persistent-notes feature (only an in-session
  TODO tool + session resume). runClaudeInContainer's `~/.claude/.../memory/` has no analogue —
  and it was never wanted for Crush anyway.
- **Themes / output styles** — placeholder only (`config.go:262` "add themes later"); just
  `option ui` layout toggles.
- **Instruction-file hierarchy walk** — cwd-only; a conventions file must sit at the working
  dir Crush is launched in (or be registered as a global context path).

## Confidence

Every verdict above is code-verified against v0.89.0. Findings 1–3 and the global-context-path
mechanism were independently re-checked at the source (`config.go:28`, `prompt.go:99`,
`commands.go:174`, `load.go:548`) before this doc was written, because the whole port plan
rests on them. Not done: a diff against `main` (shallow tag clone only) — so "ABSENT" is a
v0.89.0 statement, not a permanent one.
