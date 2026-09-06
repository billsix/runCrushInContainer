---
description: Scaffold a LAYERED reference-doc set (levels of detail) at tasks/reference/<set>/ in the current repo
argument-hint: <set-slug> [topic-slug]
---

Scaffold a **layered reference-doc set** (levels of detail) — see "Layered
reference documents — levels of detail (LoD)" in `~/.claude/CLAUDE.md`. A set
lives at `tasks/reference/<set>/` with a `README.md` **map** (aggregating every
topic's L0 capsule; it doubles as the set's TOC + status board) and one
`<topic>.md` (L2) per topic, plus a `<topic>-overview.md` (L1) where the mental
model earns it.

Args: `$ARGUMENTS` — first token = set slug; optional second = a first topic slug.

Steps:

1. Repo root via `git rev-parse --show-toplevel` (else the current directory). If
   the set slug is empty or not kebab-case, stop and ask me for one.
2. Ensure `<repo-root>/tasks/reference/<set>/` exists (with an empty `.keep`).
3. If `tasks/reference/<set>/README.md` is missing, create it as the **map**: a
   title, a short "how to read this set — L0 capsule / L1 orientation / L2
   mechanism / L3 source" note, and a topics table
   `| Topic (L2 doc) | compared-to | Status | Capsule (L0) |` with a
   ⬜ / 🟡 / ✅ status legend.
4. If a topic slug was given (else ask whether to add one now), create
   `tasks/reference/<set>/<topic>.md` as an **L2 stub** with:
   - a **provenance banner** (which version/commit the anchors are valid at, plus
     today's date),
   - a `## TL;DR`,
   - a mechanism section placeholder,
   - a `## How this relates to <baseline>` section — REQUIRED; make me name the
     course / prior system the reader already knows, to compare against,
   - a `## Candidate named-anchor spans` section — cite code by **symbol or
     doc-region name, never a line number**.
   Then add the topic's row to the README map (status ⬜, capsule left blank).
5. Offer a `<topic>-overview.md` (L1) stub — but only when the mental model is
   **non-obvious AND self-contained AND not another topic's job** (otherwise
   cross-link to the owning topic instead of writing an L1).
6. Remind me of the method: **write the L2 first (deepest), then compress upward
   ~half the lines per level to the L0 capsule**; a small topic may skip L1.
