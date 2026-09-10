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
`FLAG=1` overrides, new projects start that way. Done = the paragraph is in the ported file, word-for-word
with the original (the port is near-verbatim by decision), and `make image` bakes it.

## Context — read first

- runClaudeInContainer `tasks/reference/minimal-nested-images.md` §2 — the standard and the draft text.
- This repo's `client/Makefile` `FULL_TOOLCHAIN` line — the reference implementation the convention
  generalizes; `tasks/minimal-client-image.md` for its decisions.
- `tasks/reference/architecture.md` › "Conventions machinery — ported": the ported file is trimmed to a
  lean core for the 64k window — add the paragraph, not the reference doc.

## Plan

- [ ] Wait for the runClaudeInContainer umbrella's §1 text to land, then copy point 3 into the ported
      file's § "Running projects in a nested container".
- [ ] `make image` (nested = minimal, automatically) and confirm the baked file has it
      (`crush run` a question about nested image flags, or just `grep` in the container).

## Open questions

None.
