# Fixed the open tasks' headers (BLUF, Context, blocked status)

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 6
**Difficulty:** 1
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §9.3 F19

## What this did

Done by a delegated agent (top-level `tasks/*.md` only), reviewed and committed here.

- `## BLUF` + `## Context` added to bump-crush-to-v0.90.0, context-advisor-script,
  crush-at-import-parity, disable-crush-telemetry, offline-nested-podman-base-images,
  port-blocked-task-convention, port-runclaude-conventions-systems,
  standardize-project-container-template, verify-auto-allow-file-tools,
  verify-vendor-pulls-all-quants and verify-vendored-airgap-rebuild; `## Context` added to
  file-powernap-lsp-bugs-upstream, model-files-extras-country-gate and trim-crush-context-files.
  Existing equivalent sections (Goal, Why, Background) were renamed rather than duplicated; no
  task's substance, decisions or plan changed.
- Set `blocked` with `Blocked on:` and `Recheck:`: bump-crush-to-v0.90.0 (it read
  "proposed — BLOCKED"), verify-auto-allow-file-tools (the maintainer's client rebuild on the real
  machine), verify-vendored-airgap-rebuild (a run on the airgapped box) and
  verify-vendor-pulls-all-quants (the airgap hardware and quant choice). context-advisor-script
  stays `proposed`: "not yet" is a go-ahead, not an external gate.
- verify-vendor-pulls-all-quants: its answered open question is marked answered, and its Context
  notes that the "Current state" section predates the per-model `server/Makefile` table.
- Bare first names → `William Emerison Six <billsix@gmail.com>` in stamps, "the maintainer" in
  prose (standardize-project-container-template, audit-baked-reference-doc-drift); Priority and
  Difficulty on separate lines (audit-baked-reference-doc-drift, nested-store-cleanup-permission-denied).

Judgment call to revisit: verify-vendor-pulls-all-quants is `blocked` on choosing the airgap
hardware; if that choice is read as a plain go-ahead, it goes back to `proposed`.
