# Trim runCrushInContainer's root CLAUDE.md (23,580 B ≈ 5.9K tok, loaded every session)

**Status:** complete
**Completed:** 2026-09-13

Trimmed this repo's own root `CLAUDE.md` from **23,580 B to 10,223 B** (about 57% smaller), because
it is inlined into the agent's context every turn (method and numbers:
`tasks/reference/crush-context-assembly.md`). Durable detail was relocated to existing reference docs
before removal, so no knowledge was lost. Distinct from `tasks/trim-crush-context-files.md`, which
covers the baked global conventions, personal overlay and mounted-project context.

## Decisions

1. **Target ≈9-10 KB, keeping one-line reference-doc pointers** rather than a leaner ≈7 KB that
   relied on `ls tasks/reference/`: the pointers are cheap and serve as the on-demand index.
2. **Folded the ported-machinery inventory into `tasks/reference/architecture.md`** (the "read this
   first" doc, already covering the same ground) instead of a new `ported-machinery.md`.

## What moved where

- Ported-machinery inventory and the "not a template" rationale → `tasks/reference/architecture.md`
  (new § "Ported machinery inventory"; template clause in "What this is").
- crushrc-as-Bash edit gate (build vendored tree + `crush models`) →
  `tasks/reference/crush-capabilities.md` (Config system); the one-value-per-flag and model-preselect
  notes were already there.
- Already present, so nothing appended: LSP dnf-only + RHEL 9 (`tasks/reference/crush-lsp-integration.md`
  §4 / § RHEL 9), image-content vs `NESTED_PODMAN` history
  (`tasks/reference/nested-podman-vs-image-content.md`), version pins and quant ladder
  (`architecture.md`), the baked-path cite rule (`tasks/reference/container-file-layout.md`).
- Each convention rule stayed in `CLAUDE.md` as a one-line guardrail; the reference-doc list became
  one-line pointers; the machine-labels section stayed as is.
- The in-flight/completed task census was deleted, not moved (it duplicated the session-start
  `tasks/` scan and lives in git/archive), replaced by a one-paragraph "scan `tasks/`" note.

## Related

- `tasks/reference/crush-context-assembly.md` — measurement and method.
- `tasks/trim-crush-context-files.md` — the client-agent context trim (separate scope).
