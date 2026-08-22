# Verify the file-tool auto-allow on a rebuilt client image

**Status:** proposed — real-machine check; needs a client-image rebuild (baked crushrc). Split out
2026-08-22 from the implemented `tasks/archive/2026/08/22/auto-allow-local-file-tools.md`.
**Priority:** 3
**Difficulty:** 2
**Started:** 2026-08-22

## Goal

Confirm the permission policy behaves as intended once baked into a rebuilt image: **file read/write
flows without prompts; everything else still prompts.**

## Steps

1. `cd client && make image` (bakes the updated crushrc), then `make shell`.
2. In Crush, drive a small edit and confirm **no permission prompt** for the file tools:
   `view` (read a file), `ls`/`glob`/`grep` (list/find/search), `edit`/`multiedit`/`write` (modify).
3. Confirm the conservative side still **prompts**: a `bash` command (any — e.g. `ls` via bash), a
   `fetch`/network tool, and an MCP tool if one is configured.

## Done when

- File view/edit/write happen silently; bash and network/MCP still ask. If a file tool still prompts
  or a non-file tool is silently allowed, capture which and reconcile against `client/entrypoint/crushrc`
  (`permissions allow …`) and Crush's tool registry (`internal/config` `allToolNames`).

## Cross-links

- `tasks/archive/2026/08/22/auto-allow-local-file-tools.md` — the implementation this verifies.
- `client/entrypoint/crushrc` — the `permissions allow` line.
- `tasks/reference/architecture.md` — "Permissions: auto-allow file read/write" bullet.
