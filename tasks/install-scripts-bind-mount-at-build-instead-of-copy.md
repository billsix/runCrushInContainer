# Mirror of a runClaudeInContainer task: must build-time install scripts be COPY'd into the image, or can they be bind-mounted during the build?

**Status:** done 2026-11-26 — verdict: they can be mounted; contract, both sandbox Dockerfiles and the per-project tasks follow from it
**Created:** 2026-11-26 (William Emerison Six <billsix@gmail.com>)
**Mirrored from:** github.com/billsix/runClaudeInContainer `tasks/install-scripts-bind-mount-at-build-instead-of-copy.md`, so this repo records what happened. The `tasks/reference/`, `tasks/adhoc/` and `tools/` paths below are in that repo.
**Touched:** github.com/billsix/runClaudeInContainer, this repo, the personal overlay template in
github.com/billsix/dotfiles, github.com/billsix/geometricalgebra (the trial), and one new task doc in
each of 23 projects.

## What this did

Every project's `Dockerfile` did `COPY entrypoint/0N-install-*.sh /usr/local/bin/` and then ran the
script. The question was whether that `COPY` is required, or whether the script can be supplied with
`RUN --mount=type=bind` for the one `RUN` that needs it, the build-time twin of how `shell.sh` is
bind-mounted at run time. The answer was measured, not argued: **the `COPY` is not required.**

Everything durable is in `tasks/reference/build-time-bind-mounts-for-install-scripts.md` (the shape,
every measurement, the SELinux and Docker tables, which files stay `COPY`).

## Findings, in the order they were established

1. **podman 6.2.0, nested in the sandbox.** With one mount per script, an edited script re-ran its own
   layer and no other; a whole-directory mount re-ran every layer on any edit; nothing was left in the
   image; `.dockerignore` did not filter a mount source.
2. **Trial on geometricalgebra.** 5 `COPY` instructions (12 scripts) became 12 mounts on 7 `RUN`s. A
   default-flag `make image` built in 16 minutes and `make test` gave 1412 passed, 3 skipped.
3. **SELinux, on the maintainer's enforcing host.** A plain mount of a `:Z`-labelled context passed,
   as did `,z`, `,Z`, `--security-opt label=disable` and the old `COPY` shape. This had been the
   expected obstacle: imps `n64/SuperMario64/Dockerfile` records a denial of this kind. It was not
   reproduced.
4. **Docker 29.9.3, same host.** The plain mount built and its cache keyed on the script's content.
   Docker rejected `z` and `Z` (`invalid field`), so the rule is a plain mount with no relabel option.

## What was changed

- **Contract** (dotfiles `.ai-coding-conventions.personal.template.md`, "Dockerfile contract", the
  script section's "Keep in the Dockerfile" list, and the conformance check): build-only scripts get
  one bind mount each, no relabel option, never a directory mount; `COPY` stays for what the running
  container uses.
- **runClaudeInContainer:** `Dockerfile` converted (3 scripts); image built nested in 42 minutes,
  `make format` green. The reference doc is in the conventions' read-on-demand list
  (`entrypoint/dotfiles/.claude/CLAUDE.md`) and named in `CLAUDE.md`.
- **runCrushInContainer:** `client/Dockerfile` converted (6 scripts); image built nested in 18 minutes,
  `make format` green; its `tasks/reference/container-file-layout.md` rows and `CLAUDE.md` updated; this
  task mirrored into its `tasks/`.
- **geometricalgebra:** `Dockerfile` converted (the trial), with its task
  `tasks/install-scripts-bind-mount-at-build.md` in progress.
- **23 projects:** `tasks/install-scripts-bind-mount-at-build.md`, `proposed — needs go-ahead`, each
  listing that repo's candidate files per Dockerfile from the survey (113 build-only files in 24
  repos; leads from a text match, to be read per project).

## Decisions

- **Per-file mounts only.** A directory mount keys every layer that uses it on every file in it.
- **No relabel option**, because Docker refuses it and nothing needed it.
- **Target path unchanged** (`/usr/local/bin/<script>`), so no `RUN` body changes.
- **Build inputs** (`constraints.txt`, `requirements.txt`) may be mounted the same way when nothing
  later needs them in the image; decided per project.
- **runCrushInContainer does not carry a copy of the reference doc**; it cites runClaudeInContainer's
  by URL.

## Tools

Promoted to runClaudeInContainer `tools/`: `survey_dockerfile_copies.py`,
`convert_install_copy_to_bind_mount.py` (idempotent; used on all three converted Dockerfiles) and
`check_build_bind_mount.sh` (the host check, podman or Docker). One-shot, in
`tasks/adhoc/install-scripts-bind-mount-at-build-instead-of-copy/`: `write_project_tasks.py` and its
input `data/copies.tsv` (removed when this task is archived).

## Not verified

- A host `make image` of geometricalgebra with the converted Dockerfile (the maintainer started one
  on 2026-11-26; the host check's context was under `/tmp`).
- geometricalgebra's first GitHub Actions run after the change.
- The imps denial, on the imps Dockerfile itself.
- runCrushInContainer's `tools/check_launchers.sh` and a launcher session against the rebuilt client.
