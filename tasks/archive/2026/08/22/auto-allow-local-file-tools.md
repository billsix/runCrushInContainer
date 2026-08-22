# Auto-allow local file read/write in Crush, but keep prompting for network

**Status:** complete — crushrc `permissions allow`s **only the file tools** (`view edit multiedit write ls
glob grep`); everything else stays on ask (conservative). Takes effect on a client-image rebuild (baked
crushrc). Real-machine verification split to `verify-auto-allow-file-tools.md`.
**Priority:** 3
**Difficulty:** 4
**Started:** 2026-08-22 · **Implemented:** 2026-08-22 · **Completed:** 2026-08-22

**Final scope (maintainer, 2026-08-22): file read/write is the ONLY pain point — suppress just that;
be conservative (ask) for everything else.** So the broad first cut was narrowed: the LSP/agent/meta
allows were dropped, and the network-aware `bash` PreToolUse hook (built + battery-tested earlier this
task) was **removed** as more than needed — bash now simply asks, like all non-file tools. The hook is
recoverable from git history if wanted.

## Goal

Stop Crush prompting for permission on **local file operations** (read/view/edit/write/list/grep) —
the client is a throwaway container, so anything inside it is fair game to read or write, and the
prompts are pure noise. **Keep prompting for higher-consequence things — network access above all**
(fetch, and anything that reaches outside the container). The result should be: file work flows without
interruption; a network (or other outward-facing) action still stops and asks.

## Background — Crush's permission mechanism (verified, `crush-capabilities.md`)

- **Permissions are per-tool:** `permissions allow <tool>` / `permissions deny <tool>` in `crushrc`;
  the default is interactive-ask; `--yolo`/`-y` skips **all** prompts; there's also a per-session
  auto-approve (`crush-capabilities.md:99-100`).
- **`--yolo` is the wrong tool here** — it skips network prompts too, which the maintainer explicitly
  wants kept. The fix must be a **selective allow-list of the file tools**, leaving network tools on
  ask.
- **`PreToolUse` hooks exist** (`crush-capabilities.md:92-95`; `hook add PreToolUse --matcher …
  --command …`, exit-code + JSON-envelope contract) — an escape hatch for finer-grained,
  command-content-aware decisions than per-tool allow can express (relevant to the `bash` problem
  below).
- The baked config lives at `client/entrypoint/crushrc` → `/root/.config/crush/crushrc`; this is where
  an allow-list would go (same place as the provider pin). A crushrc change is baked, so it needs a
  `make image` rebuild to take effect.

## The design tension to resolve (this is most of the work)

Per-tool allow is clean for tools that are *purely* file or *purely* network, but two things need a
decision:

1. **`bash` does BOTH.** A single `bash` tool can `cat a file` **or** `curl a URL`. `permissions allow
   bash` would auto-approve network-via-shell — exactly what must keep prompting. Options:
   - **Leave `bash` on ask** (simplest, safe; but many file ops happen via bash, so noise remains).
   - **PreToolUse hook that inspects the command** and auto-approves only network-free commands
     (allow `cat`/`ls`/`sed`/`grep`/…; fall through to ask on `curl`/`wget`/`ssh`/`git fetch`/`pip`/
     `npm`/… or any host outside `127.0.0.1`). More work, but matches the intent precisely.
   - **Allow `bash` wholesale** — rejected: defeats the network-prompt requirement.
2. **What counts as "network" to keep on ask?** At least the `fetch` tool and all **MCP** tools
   (per-server, can reach out). Confirm the exact tool names in v0.89.0 (`internal/agent` tools;
   `crush` tool list) before writing the allow-list — don't guess the names.

## Implementation (final, 2026-08-22)

Tool registry enumerated from Crush source (`internal/config` `allToolNames`, 29 tools) + the config
skill's permission/hook contract — not guessed. **Shipped:**

- **crushrc:** one line — `permissions allow view edit multiedit write ls glob grep`. That's it.
  Everything else (bash, network `fetch`/`agentic_fetch`/`download`/`sourcegraph`, MCP, `lsp_*`,
  `agent`, meta) stays on ask; unlisted/new tools ask (fail-safe). (`permissions allow` accumulates +
  dedups — `TestShellConfigPermissionsAccumulateAndDedup` — but one line suffices here.)
- Documented in `tasks/reference/architecture.md` + crushrc comments.

**Evolution (why the diff looks bigger in history):** the first cut was broader — it also auto-allowed
the `lsp_*` and `agent`/meta tools, and added a network-aware `bash` PreToolUse hook
(`hooks/no-network-bash.sh`) that auto-approved network-free commands and asked on network ones
(built + battery-tested: 13 local→allow, 16 network→ask, empty→ask). The maintainer then clarified the
scope (below); the extras and the hook were removed. The hook is recoverable from git history.

- [→] Real-machine verification moved to `tasks/verify-auto-allow-file-tools.md`.

## Decisions

1. **Final scope (maintainer, 2026-08-22): file read/write is the ONLY pain point.** Suppress just the
   file tools; be **conservative (ask)** for everything else — bash, network, MCP, LSP, sub-agents. This
   superseded the earlier broader plan.
2. **Superseded (kept for history):** an earlier round resolved "keep asking → fetch + MCP only" and a
   two-part `bash` plan (leave-on-ask, then a network-aware hook). Both were overtaken by decision 1 —
   the hook was built then dropped, and the allow-list narrowed from ~22 tools to 7.

## Cross-links

- `tasks/reference/crush-capabilities.md` — permissions (`:99-100`), hooks (`:92-95`), the tool set.
- `client/entrypoint/crushrc` — the baked config where the allow-list lands (rebuild to apply).
