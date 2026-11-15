# Sync the delivered conventions: nested section, Python rule, unported docs

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 3
**Difficulty:** 3
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §3.2, §3.3, §0.1, §0.4 F9 F22

## BLUF

The delivered `crush/CLAUDE.md` has a stale nested section, the old Python-deps rule, and is missing the "Verification gates in nested containers" section. Its conventions and commands cite runClaude docs never ported. Maintainer decisions 2026-11-15: distro-first Python rule; port only the runClaude docs something here cites (into `tasks/reference/`, not baked), plus the nested-gates section.

## Context

- §3.2: `crush/CLAUDE.md:567-573` ("won't have those flags") vs `:561`.
- `crush/CLAUDE.md:398` "venv copy wins".
- §0.4: 13 unported runClaude docs; the cited ones include `task-doc-conventions.md`, `reference-doc-conventions.md`, `git-workflow-conventions.md`.

## Plan

1. Fix the nested section (converted Makefiles auto-apply `PODMAN_RUN_FLAGS`; keep `--network=host` as the Crush extra).
2. Replace the Python rule with the distro-first rule.
3. Add the nested-gates section.
4. grep the delivered conventions, commands and `tasks/reference/` for cites of runClaude docs not here; copy those into `tasks/reference/` as byte mirrors with the banner; note in `architecture.md`.
