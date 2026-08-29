# Standardize the project container-template (mounts, shell.sh, shell-exec)

**Status:** proposed — needs go-ahead. Sibling of the same-named task in runClaudeInContainer.
William Emerison Six <billsix@gmail.com>, 2026-08-29.
**Priority:** 5
**Difficulty:** 5

## Why

runCrushInContainer, like runClaudeInContainer, is a **metaproject that defines how projects are
structured** (the Fedora + Podman container-per-project template). The `make shell-exec` fan-out across
~45 projects (tracked in `runClaudeInContainer/tasks/fan-out-shell-exec-to-projects.md`) exposed that
the template has drifted in accidental ways — `shell.sh` mount path, whole-vs-selective mount, baked-vs-
bind-mounted launcher, `REPO_MOUNT` naming, prereq policy, X11 flag var name. Each divergence turned a
mechanical cross-cutting edit into a per-project judgment call.

Bill's instruction (2026-08-29): where projects aren't done in a standard way (e.g. texExpToPng's
selective mount), **formalize a standard in the nested CLAUDE.md** for the projects these meta-repos
manage — in **both** runClaudeInContainer and runCrushInContainer.

## The proposed standard

The full divergence table + the proposed standard (one `shell.sh` path, always bind-mounted; mandatory
`REPO_MOUNT`; whole-repo mount as default with selective as a documented exception; shared
`SHELL_RUN_FLAGS`; `PODMAN_RUN_FLAGS` everywhere; `set -e` + `exec bash "$@"`; a decided prereq policy;
one X11 var name) lives in **`runClaudeInContainer/tasks/standardize-project-container-template.md`** —
adopt the SAME standard here so the two meta-repos agree.

## Plan (runCrushInContainer side)

- [ ] Adopt the agreed standard (decided in the runClaudeInContainer sibling) in **this** repo's
      contract doc / **nested CLAUDE.md** (`CLAUDE.md` here documents the two-part client/server layout
      and the "Conventions for changing this repo" section — the standard's conformance checklist
      belongs alongside it).
- [ ] Apply it to the projects **this** repo manages — notably `client/` (the Crush client image) and
      this repo's own `shell` target when `shell-exec` is ported here (see the fan-out's runCrush phase).
- [ ] Keep the two meta-repos' contract docs in sync (a divergence between them is itself the drift this
      task fights).

## Decisions (Bill, 2026-08-29)

Resolved in the sibling task, apply in both:
1. **Whole-repo mount = the default** (selective = documented exception). ✅
2. **`shell-exec` depends on `image`, never `format`** (no source-mutating prereq on a runner). ✅
   (Applied across the fleet; the client port here already uses `shell-exec: image`.)
3. **Outliers get standardized INTO the template, not excluded** — done for `graphicalcontainer`.

Remaining for this repo: adopt the standard in this repo's `CLAUDE.md`, and — since the client's
`shell.sh` is **baked** (COPY) — decide whether to bind-mount it (so a `shell.sh` edit is live without
a 22 GB image rebuild), per the "bind-mount the launcher" standard.

## Cross-links

- `runClaudeInContainer/tasks/standardize-project-container-template.md` — the canonical analysis + standard.
- `runClaudeInContainer/tasks/fan-out-shell-exec-to-projects.md` — the fan-out + full kinks log.
- This repo's `CLAUDE.md` "Conventions for changing this repo" — where the conformance checklist lands here.
