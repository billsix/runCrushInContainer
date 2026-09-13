# Port the lean-image-when-nested convention into the Crush-side conventions file

**Status:** proposed — needs go-ahead; small. Sibling of runClaudeInContainer
`tasks/minimal-image-for-nested-podman-standard.md` (the umbrella that defines the convention). Created
2026-09-10 (William Emerison Six <billsix@gmail.com>: "make a task in the nested CLAUDE.md both for
runClaudeInContainer and runCrushInContainer").
**Priority:** 4
**Difficulty:** 1

## BLUF

`client/entrypoint/dotfiles/.config/crush/CLAUDE.md` is this repo's port of the tracked cross-project
conventions (`tasks/port-runclaude-conventions-systems.md`); its § "Running projects in a nested
container" must carry the same **point 3 — the lean-image default** that the runClaudeInContainer
umbrella adds to the original: every optional-feature build flag defaults lean when `NESTED_PODMAN=1`
(`FLAG ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)`), gates and product build deps never trimmed,
`FLAG=1` overrides, new projects start that way — **for downstream container-per-project repos ONLY,
never the two sandboxes themselves** (the sandboxes are host-built and merely launched nested;
decoupled 2026-09-12, see `tasks/reference/nested-podman-vs-image-content.md` and runClaudeInContainer
`tasks/scope-lean-image-to-downstream-not-sandboxes.md`). Done = the paragraph (carrying that scope
boundary) is in the ported file, and `make image` bakes it.

## Context — read first

- runClaudeInContainer `tasks/reference/minimal-nested-images.md` §2 — the standard and the draft text.
- This repo's `client/Makefile` **no longer has a `FULL_TOOLCHAIN` flag** (removed 2026-09-12 — the
  client is always the full toolchain; see `tasks/reference/nested-podman-vs-image-content.md`). It is
  therefore NOT an example of the convention; the convention applies to *downstream* projects only.
  History of the (now-removed) flag: `tasks/archive/2026/09/10/minimal-client-image.md`.
- `tasks/reference/architecture.md` › "Conventions machinery — ported": the ported file is trimmed to a
  lean core for the 64k window — add the paragraph, not the reference doc.

## Plan

- [ ] Wait for the runClaudeInContainer umbrella's §1 text to land, then copy point 3 into the ported
      file's § "Running projects in a nested container".
- [ ] `make image` (nested = minimal, automatically) and confirm the baked file has it
      (`crush run` a question about nested image flags, or just `grep` in the container).

## Open questions

None.
