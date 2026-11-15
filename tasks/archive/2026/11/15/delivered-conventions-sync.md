# Synced the delivered conventions: the nested section, the nested-gates rule, the cited docs

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 3
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §3.2, §3.3, §0.1, §0.4 F9 F22

## What this did

- **`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, "Running projects in a nested container":**
  it said a project's Makefile "won't have those flags — don't silently edit". It now says a
  converted Makefile applies `--cgroups=disabled` itself via `PODMAN_RUN_FLAGS`, that converting one
  is pre-authorized, and that `--network=host` is this client's extra (pass it per run or through
  `PODMAN_RUN_FLAGS`; don't silently edit a project's build files for it).
- **Added the "Verification gates in nested containers" section** (from runClaudeInContainer's
  shared `CLAUDE.md`): done means the project's containerized gate passed, flag coverage, one
  default-flags gate before ending a session, and the `: image` rebuild gotcha.
- **Cited runClaude docs** (maintainer decision 2026-11-15, option (a): only what something here
  cites, into `tasks/reference/`, not baked): `nested-run-and-gates.md` (8 cites),
  `codegen-conventions.md` (5), `minimal-nested-images.md` (2) and `claude-config-layering.md` (1),
  copied as byte mirrors. `tasks/reference/architecture.md` lists them, and lists the "Blocked tasks"
  convention among what was not ported yet (it is `tasks/port-blocked-task-convention.md`).
- **Python-deps rule:** no change. The review's contradiction came from a stale copy of the
  personal overlay; the delivered "venv copy wins" rule matches the overlay (record correction).
- `nested-podman-signal…` and `minimal-image…` sections already carried the current rules.

## Verification

A scan of the delivered `CLAUDE.md`, `commands/`, `tasks/reference/` and the baked reference dir for
every runClaude reference-doc name found exactly those four cited without a copy here; each copy
`cmp`s equal to runClaude's.
