# Trim runCrushInContainer's root CLAUDE.md (23,580 B ≈ 5.9K tok, loaded every session)

**Status:** Done — trimmed 2026-09-13 (pending archive after the work commit)
**Priority:** 4
**Difficulty:** 3

**Result:** CLAUDE.md **23,580 B → 10,223 B** (≈57% smaller, MODERATE target). No durable knowledge
lost — everything moved was appended verbatim to (or already present in) the destination reference
docs before removal. Decisions applied: Q1 = kept one-line reference pointers; Q2 = folded the
ported-machinery inventory into the existing `architecture.md` (no new doc). What moved where:
- Ported-machinery inventory + "not a template" rationale → `architecture.md`
  (new § "Ported machinery inventory"; template clause in "What this is").
- crushrc-as-Bash edit gate (build vendored tree + `crush models`) → `crush-capabilities.md`
  (Config system). crushrc-as-Bash / one-value-per-flag / model-preselect probe were already present there.
- LSP dnf-only + RHEL 9 detail — already fully present in `crush-lsp-integration.md` §4 / § RHEL 9 (no append).
- Image-content vs `NESTED_PODMAN` history — already fully present in `nested-podman-vs-image-content.md` (no append).
- Version pins / quant ladder — already present in `architecture.md` (no append).
- Baked-path cite rule — already present in `container-file-layout.md` § Reference-doc mapping (no append).
- The in-flight/completed task census (L209–282) was deleted, not moved (it duplicated the session-start
  `tasks/` scan and lives in git/archive); replaced with a one-paragraph "scan `tasks/` at session start" note.

## BLUF
This repo's own root `CLAUDE.md` is 23,580 B (≈5.9K tok) and is spliced into the agent's
context on every session/turn in this repo. Roughly half of it is durable history/rationale
that belongs in `tasks/reference/` and a full duplicate of the in-flight/completed task list
that duplicates the session-start `tasks/` scan. Move that detail into existing reference docs
and cut the task census, leaving a lean operational file of ≈9 KB — with no loss of durable
knowledge (it relocates, it is not deleted).

## Context
- Why: `CLAUDE.md` is inlined into the system prompt on every turn, so an oversized one wastes
  context budget continuously. Method + measured numbers:
  `tasks/reference/crush-context-assembly.md`.
- Distinct scope: this is the **repo's own root `CLAUDE.md`** (the file a maintainer working *on
  this repo* loads). It is NOT the baked global conventions / personal overlay / mounted-project
  context — that trim is the separate `tasks/trim-crush-context-files.md`. Cross-link, don't
  overlap.
- Current size: 23,580 B ≈ 5.9K tok. `@`-imports: **none** (this file has no bare `@path` import
  lines; the `@`-import machinery it describes lives in the baked *global* CLAUDE.md, not here).
- Convention: `CLAUDE.md` stays lean + operational, loaded every session; durable detail moves to
  `tasks/reference/<slug>.md`, read on demand. Prefer folding into an EXISTING reference doc.
- Existing `tasks/reference/` docs (fold-into targets): `architecture.md` (the two halves, pins,
  quant ladder, crushrc/config, vendoring/airgap — the primary MOVE target),
  `crush-capabilities.md`, `crush-lsp-integration.md`, `crush-prompt-history.md`,
  `nested-podman-design.md`, `nested-podman-vs-image-content.md`, `dependency-network-audit.md`,
  `gemma-4-alongside-glimmer.md`, `glimmer-models-and-airgap-quant-selection.md`,
  `container-file-layout.md`, `new-hardware-bringup.md`, `crush-context-assembly.md`.

## Stay vs move (section-by-section)

| CLAUDE.md section (heading) | ~bytes | Verdict | Destination |
|---|---|---|---|
| Header + "Status: working, conventions ported." blurb (L1–7) | ~600 | TRIM | CLAUDE.md — collapse the multi-line status paragraph to one line; drop the porting narrative. |
| "What this repo is for." (L9–21) | ~1300 | TRIM | CLAUDE.md — keep the one-paragraph "what is this / two-fold job". Move the fork-friendly/template rationale to `architecture.md`. |
| "Two parts, two machines" (L23–38) | ~1500 | TRIM | CLAUDE.md keeps a 2-bullet server/client summary + ports; move deep pins (`b10883`, floors `b10353`/PR#28335, MLX alt) to `architecture.md` (already holds the pins). |
| "Labels: which machine a command runs on" (L40–46) | ~500 | STAY | CLAUDE.md — invariant `[MAC]`/`[LINUX HOST]`/`[CONTAINER]` guardrail. |
| "Conventions for changing this repo" (L48–105) | ~4500 | TRIM | Keep each rule as a one-line guardrail in CLAUDE.md; MOVE the embedded rationale/history/origin-task refs — crushrc-as-Bash detail → `crush-capabilities.md`; LSP dnf-only + RHEL9 detail → `crush-lsp-integration.md`; image-content/`NESTED_PODMAN` history → `nested-podman-vs-image-content.md`; version-pin lore → `architecture.md`. |
| "What's in use (the runClaudeInContainer machinery is ported)" (L107–161) | ~4000 | MOVE | `architecture.md` (or a short new `ported-machinery.md`). This is a durable porting inventory, not per-turn operational guidance. Leave a 2-line pointer in CLAUDE.md. Biggest single MOVE. |
| "Reference docs" (L163–207) | ~3000 | TRIM | CLAUDE.md — collapse each full paragraph to a one-line pointer (`slug — one-clause purpose`). Keep the "also baked into the image at `~/.config/crush/reference/`" note as one line; its cite-by-baked-path rule → `container-file-layout.md`. |
| "In-flight tasks" enumerated + annotated list (L209–255) | ~4000 | MOVE/TRIM | Drop the enumerated census from CLAUDE.md — it duplicates the session-start `tasks/` scan the conventions already mandate and rots fast. Replace with one line: "scan `tasks/` (top-level) at session start; blocked tasks carry `Blocked on:`/`Recheck:`." |
| "Completed & archived" prose (L256–282) | ~1800 | MOVE | Pure history → it already lives in `tasks/archive/` and `architecture.md`. Delete from CLAUDE.md (git + archive are the record). |

## Projected result
- Trimmed CLAUDE.md ≈ 9 KB (from 23.6 KB) — the four STAY/lean sections (repo purpose, two
  machines summary, machine labels, one-line conventions + one-line reference pointers).
- Reference docs updated: `architecture.md` (absorbs ported-machinery inventory + version-pin
  and template rationale), `crush-capabilities.md`, `crush-lsp-integration.md`,
  `nested-podman-vs-image-content.md`, `container-file-layout.md` (baked-path cite rule). No new
  reference doc strictly required; a small `ported-machinery.md` is optional if `architecture.md`
  would grow unwieldy.

## Open questions (for the maintainer)
1. How lean do you want the target — the ≈9 KB above (keep one-line reference pointers + a
   1-line task-scan note), or leaner still (≈7 KB) by also dropping the per-doc reference
   pointers and relying on the agent to `ls tasks/reference/`? Recommendation: keep the one-line
   pointers (≈9 KB) — they are cheap and are the on-demand index.
2. For the ported-machinery inventory (L107–161), fold into `architecture.md`, or spin a new
   `tasks/reference/ported-machinery.md`? Recommendation: fold into `architecture.md` (it is the
   "read this first" doc and already covers the same ground) unless it bloats past readability.

## Related
- `tasks/reference/crush-context-assembly.md` — measurement + method.
- `tasks/trim-crush-context-files.md` — the *baked global-context / personal-overlay /
  mounted-project* trim (distinct scope: that is the context the client agent loads; this is the
  repo's own root CLAUDE.md).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
