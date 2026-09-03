# Diversion stack is IN-SESSION only — stop host-persisting it; harvest it at session-end instead

**Status:** DONE 2026-09-03 — Makefile no longer creates/mounts the stack; conventions + layout doc updated; sweep harvests it.
**Priority:** 4
**Difficulty:** 3

## BLUF

The diversion stack (`~/.config/crush/stack.md`) is currently created on the **host** and mounted into the
container so it survives `--rm` (see the investigation [[crush-config-on-host-investigation]], which found the
`STACK_MOUNT` in `client/Makefile`). **Decision (maintainer, 2026-09-03): don't persist it — the stack's purpose
is purely in-session.** So: (1) nothing in the Makefile should create it on the host or mount it in — the stack
lives only in the ephemeral container; and (2) the **durable** part moves to the session-end sweep, which should
**consult the stack to see what work needs to continue and fold that into the task / reference docs** (which are
persisted in the repo). "Done" = no Makefile stack mount, the stack is container-only, and the session-end sweep
harvests it into the persisted docs.

## Context

- **What exists now:** `client/Makefile` (~lines 155-159) has `STACK_FILE := $(HOME)/.config/crush/stack.md` and
  `STACK_MOUNT := $(shell mkdir -p $(HOME)/.config/crush …; touch $(STACK_FILE) …; echo "-v …:/root/.config/crush/stack.md:Z")`
  — it `mkdir`s + `touch`es the host file at make-parse time and bind-mounts it in, so the stack persists across
  `--rm`. This is exactly the "files in host ~/.config/crush" the maintainer asked about (the investigation task).
- **Why the change:** the stack is a within-session depth gauge (what diversion we're on). Persisting the *file*
  across sessions preserves a raw stack that goes stale; what actually matters between sessions is *what work is
  still in flight and why* — and that belongs in the task/reference docs, which are versioned, not in an
  ephemeral scratch file on the host.
- **The diversion-stack convention** lives in `client/entrypoint/dotfiles/.config/crush/CLAUDE.md` ("The
  diversion stack (`~/.config/crush/stack.md`)"), and the layout is documented in
  `client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md` (which lists the host `stack.md`
  mount) — both need updating to match.

## Changes

1. **`client/Makefile`** — remove `STACK_FILE` + `STACK_MOUNT` and drop `$(STACK_MOUNT)` from the run flags. The
   stack is no longer created on the host or mounted; it lives at `/root/.config/crush/stack.md` **inside** the
   container, on the ephemeral `--rm` overlay (created by the diversion-stack commands as needed), and dies with
   the container — as intended.
2. **`.config/crush/CLAUDE.md`** (the diversion-stack convention) — restate: the stack is **in-session only**, not
   host-persisted; it's a live depth gauge, discarded at exit. Its cross-session value is captured by the
   session-end sweep (below), not by keeping the file.
3. **The session-end sweep convention** (in the same `.config/crush/CLAUDE.md`) — add a step: **consult the stack
   at session end**; for any still-open diversion, record what work needs to continue and why into the relevant
   **task doc** (or a reference doc for durable knowledge), so the persisted docs carry the in-flight state. That
   is the part that survives the session.
4. **`container-file-layout.md`** (reference) — remove the host `~/.config/crush/stack.md` mount row; note the
   stack is now container-only/ephemeral.

## Resolves

Supersedes the open decision in **[[crush-config-on-host-investigation]]** ("keep / relocate / stop persisting the
host stack file?") — the answer is **stop persisting**, plus harvest at session-end. That investigation task can
be archived once this lands.

## Verify

`make -n shell` shows **no** `-v …/stack.md` mount and no `mkdir …/.config/crush` at parse time; a fresh session
has an ephemeral in-container stack that's gone after exit; the session-end sweep writes any in-flight diversion
into a task/reference doc.
