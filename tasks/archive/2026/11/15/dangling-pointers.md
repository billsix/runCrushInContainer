# Repointed dangling task pointers in code and docs

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §2.3, §10.3, §0.2 F16

## What this did

- Code comments and docs that cited tasks since archived now cite their archive paths:
  `investigate-context-bloat-geometricalgebra` (2026/09/14), `suppress-embedded-provider-catalog`
  (2026/08/20), `lsp-python-server-not-registering` (2026/09/13),
  `vendor-build-sources-for-airgap-rebuild` and `vendor-via-client-image` (2026/08/22),
  `minimal-client-image` (2026/09/10). Files: `.gitignore`, `client/Dockerfile`, `client/Makefile`,
  `client/entrypoint/00-install-minimal.sh`, `client/entrypoint/03-build-crush.sh`,
  `client/entrypoint/crushrc`, `server/Makefile`, `tasks/reference/crush-context-assembly.md`,
  `tasks/reference/architecture.md`, `tasks/trim-crush-context-files.md`.
- Paths that never existed: `crush-lsp-integration.md`'s `archive/2026/09/10/crushrc-startup…`
  (the file is under 2026/09/22); `nested-podman-vs-image-content.md`'s
  `tasks/reference/minimal-nested-images.md` now names runClaudeInContainer, where that doc lives.
- runClaude's archived `add-shell-exec-target.md` (and its fan-out sibling) are cited by repo URL
  and archive path in `client/Makefile` and `architecture.md`.
- Left: the comment inside `client/patches/crush-context-debug.patch` (a `+` line of Crush source
  that the patch adds; editing it changes the patch for no runtime effect).
- The archive's own dangling paths and the squashed SHA `5d2515f` are fixed by the archive
  done-record work (`tasks/archive/2026/11/15/archive-done-records.md`).

## Verification

`git grep` for each moved slug's old `tasks/<slug>.md` path outside the archive and review records
finds only the patch comment; every new path exists.
