# Drop procs; keep shfmt (the Fedora 44 leftovers in /usr/local/bin)

**Status:** proposed — decided 2026-11-15 (drop procs, keep shfmt); ready to implement
**Priority:** 6
**Difficulty:** 2
**Created:** 2026-11-06 (William Emerison Six <billsix@gmail.com>); investigated 2026-11-15
**Spans:** this repo and github.com/billsix/runClaudeInContainer. That repo's
`tasks/consider-dropping-shfmt-procs.md` is the primary copy (investigation, sources, plan); decide
there, apply in both.

## BLUF

The client installs the same two Fedora 44 leftovers as runClaude, **shfmt** and **procs**, through the
identical `client/entrypoint/01b-install-binary-tools.sh` (pinned, checksum-verified upstream binaries in
`/usr/local/bin`). Fedora retired both from Fedora 45: shfmt failed to build, procs was orphaned.
**Recommendation: drop procs, keep shfmt.** Done means the same as in runClaude, applied here.

## Decision (William Emerison Six <billsix@gmail.com>, 2026-11-15)

**Drop procs and keep shfmt**, in both runClaudeInContainer and runCrushInContainer, as recommended
below: procs is unused and covered by the packaged `htop`, `btop`, `ps` and `pstree`; shfmt has no
Fedora 45 replacement and runs both sandboxes' `make format` gates (and, in runCrush, the bash language
server's formatting). shfmt stays a pinned, checksum-verified upstream binary.

## Context

- Investigation, Fedora sources and replacements: the primary copy in runClaudeInContainer.
- What differs here: shfmt is also what `nodejs-bash-language-server` (one of the six LSPs the crushrc
  declares, `client/entrypoint/crushrc`) uses to format shell when it is on `PATH`, so dropping shfmt
  would also cost Crush's `lsp` formatting for `.sh` files. Another reason to keep it.
- `client/entrypoint/format.sh` (`make -C client format`) runs shfmt over `entrypoint/*.sh`,
  `entrypoint/vendor/*.sh` and `runCrush*.sh`.
- Docs that mention procs here: `CLAUDE.md`, `client/Dockerfile`'s comment, the baked
  `client/entrypoint/dotfiles/.config/crush/reference/sandbox-capability-map.md` (a byte mirror; re-copy
  it from runClaude after runClaude's change), `tasks/reference/container-file-layout.md`.

## Plan (on go-ahead)

1. Re-copy runClaude's updated `01b-install-binary-tools.sh` over `client/entrypoint/01b-install-binary-tools.sh`.
2. Update the docs above; re-copy the baked capability map.
3. Verify: `make -C client image`; `command -v procs` fails, `shfmt --version` prints v3.14.1,
   `make -C client format` passes.
