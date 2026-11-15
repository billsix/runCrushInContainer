# Mirrored runClaude's infra-doc fixes (:Z, counts, the rm sweep) and fixed this repo's own

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.2, §1.4, §1.5 F17

## What this did

Mirrors github.com/billsix/runClaudeInContainer `tasks/archive/2026/11/15/infra-docs-stale-facts.md`
for the same facts here, plus this repo's own:

- **`:Z` → `:z`** on every non-comment mount in `client/Makefile` (the config-file, personal-overlay,
  socket-dir, vendor-dir, `shell.sh` and nested-store mounts) and on `vendor.sh`'s `server/` mount
  (maintainer decision 2026-11-15: never `:Z` a host tree; the client runs `label=disable`, so `:Z`
  gained nothing and relabelled host files).
- "~430" → "~460" packages (the list has 461 entries) in `CLAUDE.md`, `client/Dockerfile`,
  `client/Makefile`, `00-install-minimal.sh`, `01-install-base.sh`, `architecture.md` and
  `nested-podman-design.md`.
- `image-build-and-storage-pipeline.md`: the leaked-store sweep uses `podman unshare rm -rf`; §(c)
  no longer documents a `NESTED_PODMAN_RUNTIME_TMPFS` that does not exist (the client has no libpod
  tmpfs).
- `nested-podman-design.md`: says the launchers turn nested podman on; drops its stale "Last
  updated" date.

Not here: Fedora 44 in `client/Dockerfile:30` is a true historical note ("were dnf packages under
Fedora 44"); the baked mirror copies (`crush/reference/sandbox-capability-map.md`,
`rust-gui-tui-and-ecosystem.md`, …) are re-copied from runClaude's fixed canonicals by
`tasks/mirrors-and-baked-docs.md`.

## Verification

`grep -c ':Z' client/Makefile` → 2, both in the comment that states the rule; `make help` and
`make -n shell` parse. The client image build is the batch's client `make image`.
