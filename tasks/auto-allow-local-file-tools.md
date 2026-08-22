# Auto-allow local file read/write in Crush, but keep prompting for network

**Status:** proposed — **design decisions resolved 2026-08-22** (see Decisions); implementation still
needs go-ahead.
**Priority:** 3
**Difficulty:** 4
**Started:** 2026-08-22

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

## Plan

- [ ] **Enumerate Crush v0.89.0's actual tool names** (file vs network) from `internal/agent` / the
      tool registry — e.g. view, edit, write, ls, grep, glob (file) vs fetch, MCP tools (network).
      Don't hardcode guessed names.
- [ ] **Add `permissions allow …` lines for the file tools** to the baked `client/entrypoint/crushrc`,
      leaving `fetch`/MCP (and, pending Q1, `bash`) on ask.
- [ ] **`bash` handling (decided — see Decisions):** first cut leaves `bash` on ask; **then** add a
      network-aware `PreToolUse` hook as a follow-up that auto-approves network-free commands and falls
      through to ask on anything reaching out (`curl`/`wget`/`ssh`/`git fetch`/`pip`/`npm`/… or a host
      other than `127.0.0.1`). Write the hook under the baked hook/command layout and document its
      allow/deny rules.
- [ ] **Verify:** rebuild the client image, run Crush, confirm file view/edit/write happen with **no**
      prompt while a `fetch` (and a `curl` via bash, per Q1) **still** prompts. Capture the before/after.
- [ ] **Document** in `crush-capabilities.md` (or a short note) what's auto-allowed and why, and add a
      terse pointer in the baked `CLAUDE.md` if the agent needs to know the policy.

## Decisions (resolved 2026-08-22, maintainer: "sure for both" / "sounds good")

1. **`bash` handling → both, in order.** (a) First cut: file tools auto-allowed, **`bash` left on ask**
   (zero risk to the network requirement). (b) Follow-up: add a **network-aware `PreToolUse` hook** that
   auto-approves network-free bash commands and falls through to ask on outward-reaching ones. Both are
   in scope for this task — (a) then (b).
2. **Scope of "keep asking" → `fetch` + MCP tools only.** Everything else that is file-local is
   auto-allowed; no other tools singled out to keep on ask.

## Cross-links

- `tasks/reference/crush-capabilities.md` — permissions (`:99-100`), hooks (`:92-95`), the tool set.
- `client/entrypoint/crushrc` — the baked config where the allow-list lands (rebuild to apply).
