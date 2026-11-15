# Decide where tools live: repo tools, sandbox commands, and shared canonical sources

**Status:** proposed — needs decisions (Open questions), then go-ahead
**Priority:** 5
**Difficulty:** 3
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Spans:** this repo and github.com/billsix/runClaudeInContainer. That repo's `tasks/tools-layout-commands-and-shared-sources.md` is the primary copy: the decisions are made there and applied in both. This copy records what changes here.

## BLUF

Scripts live in two places in this repo: `tools/` (repo dev tools) and `tasks/reference/`, which holds
five scripts only because that directory is the one mounted into the sandbox at `~/.claude/reference/`.
`tasks/reference/` is the durable-knowledge docs directory, so it is the wrong home for them. Decide one
home per kind of tool, the same in both sandboxes, then move them and fix every reference. Done means
every script lives in its kind's home, the sandboxes still find each one, and no doc, command or banner
cites an old path.

## Context

There are three kinds of script, and they want different homes:

1. **Repo dev tools**, run against this repo (on the host or in the container): `tools/check_helm_file_at_point.{sh,el}`.
   runCrush's `tools/` holds its launcher gate, egress sweep, triage and ty probe, and its
   `server/tools/checksum.py` is Mac-side. These are fine where they are.
2. **Commands the sandbox provides to the agent**, run from any project inside the container: today only
   `tasks/reference/review_status.py`, run in place by `/review-status` and `/audit-repo deep` as
   `python3 ~/.claude/reference/review_status.py` (runCrush also bakes a copy into
   `~/.config/crush/reference/`).
3. **Shared canonical sources** that downstream projects copy byte-identically into their own `tools/`:
   `check_local_annotations.py`, `c_dispatch_check.py`, `c_designated_init_check.py` and
   `update_dep_common.sh`. They are files to copy, not commands; each vendored copy carries a
   "Canonical: runClaudeInContainer tasks/reference/…" banner.

What already exists:

- `tasks/sandbox-commands-in-tools-bin.md` (2026-11-09, proposed) covers kind 2: a `tools/bin/` directory
  baked into `/usr/local/bin` and each file bind-mounted over its baked copy at run time (the pattern
  `shell.sh` already uses), with `review_status.py` becoming `tools/bin/review-status`. It does not cover
  kind 3.
- `tasks/recopy-shared-checkers-downstream.md` (2026-11-15, proposed) re-copies the kind-3 files into
  spimulator, methodfinder, modelviewprojection and impo. Moving kind 3 changes the banners in those same
  copies, so the two tasks are cheaper done together.

Constraints found on 2026-11-15:

- **Never bind-mount a directory over `/usr/local/bin`.** Things installed there would be hidden:
  `shfmt` and `procs` (both images, from `entrypoint/01b-install-binary-tools.sh`) and `crush` itself in
  runCrush (`GOBIN=/usr/local/bin`). Bake with `COPY` and mount file by file, or mount a separate
  directory and put it on `PATH`.
- **What cites the current paths:** in this repo, 5 references in the shared `CLAUDE.md`, the commands and
  the reference docs (`grep -rn 'reference/<tool>'`); in runCrush, 10 files. Plus the banners in every
  vendored copy downstream, and this repo's `CLAUDE.md` ("SHARED, VENDORED tool scripts").
- The maintainer's suggestion (2026-11-15): container tools under `tools/usr/local/bin/`, placed in the
  container at `/usr/local/bin/` either at image creation or by a mount.

## What changes in this repo

- `tasks/reference/` holds byte mirrors of the five scripts; the baked
  `client/entrypoint/dotfiles/.config/crush/reference/review_status.py` is a sixth copy.
- 10 files here cite the current paths (the delivered `CLAUDE.md`, the ported commands, the reference
  docs, `CLAUDE.md`'s "mirrored copies of runClaude's SHARED, VENDORED tool scripts" paragraph).
- `tasks/reference/container-file-layout.md` (what `make manifest` prints) must list the new baked and
  mounted paths.
- `crush` is installed in `/usr/local/bin` (`GOBIN`), so a directory mount over it would hide the agent
  itself.

## Open questions

Answered in runClaudeInContainer's copy of this task; listed here so this doc can be read cold.


1. **One task or two?** (a) Extend `tasks/sandbox-commands-in-tools-bin.md` to cover kind 3 as well and
   close this one into it, or (b) keep this as the umbrella and that one as its kind-2 step.
   Recommended: (a), one task per repo.
2. **The commands directory's name:** (a) `tools/bin/` (the 2026-11-09 decision) or (b)
   `tools/usr/local/bin/` (mirrors the target path). Recommended: (a), shorter and already decided.
3. **How commands reach the container:** (a) bake with `COPY` into `/usr/local/bin` and bind-mount each
   file over its baked copy (works offline, host edits live); (b) bake only (an edit needs `make image`);
   (c) mount the directory at a separate path (e.g. `/opt/sandbox/bin`) and add it to `PATH`, no bake.
   Recommended: (a), the existing decision and the `shell.sh` pattern.
4. **Where the shared canonical sources (kind 3) live:** (a) `tools/shared/`, mounted read-only at
   `~/.claude/tools/` (runCrush: `~/.config/crush/tools/`) so the agent can copy them from inside any
   project; (b) stay in `tasks/reference/`; (c) also ship them as commands
   (`check-local-annotations`, …) in `tools/bin/`. Recommended: (a); projects vendor them so their CI is
   self-contained, so they stay files, not only commands.
5. **Do this together with `tasks/recopy-shared-checkers-downstream.md`?** The downstream banners change
   either way. Recommended: yes, in one batch, so each downstream copy is touched once.

## Plan (after the questions are answered)

1. Move the scripts (`git mv`), keeping byte-identity with runCrush's copies.
2. Wire the Dockerfile/Makefile of both sandboxes per question 3 (and the read-only mount per question 4).
3. Update every reference: the shared `CLAUDE.md`, the commands, the reference docs, this repo's
   `CLAUDE.md`, runCrush's `container-file-layout.md`, and the banners in the moved files.
4. Verify in a freshly launched container of each sandbox: `review-status` (or its new name) runs from any
   repo root; the shared sources are readable at their mounted path; `shfmt`, `procs` and (runCrush)
   `crush` still resolve; `git grep` for the old paths finds nothing outside the archive and review records.
