
Audit the repository we're currently in. **Read-only:** do not edit, stage, or create any
file except the review record a deep audit writes. Fixes come later, as tasks the
maintainer makes from the findings.

Mode: `$MODE` (empty → **quick**; `deep` → **deep**; anything else → stop and ask).

Before either mode:

1. Find the repo root (`git rev-parse --show-toplevel`, else the working directory).
2. Read the project's `CLAUDE.md`.
3. If the repo is an upstream-only checkout (personal overlay), stop and say so.

## Quick

A full read of the current repo, cross-referencing the docs (`CLAUDE.md`, `README.md`,
`tasks/reference/*`, open `tasks/*.md`) against the actual source. Surface:

- stale claims;
- undocumented features;
- internal inconsistencies;
- paths and commands that don't exist.

Report in chat:

- findings grouped by severity, each with `path:line`, the evidence checked, and VERIFIED
  or LEAD;
- follow-ups tagged required / recommended / optional;
- any questions as a closing numbered list.

No record is written. If the quick pass shows the repo needs more than it can cover, say
so and suggest `/audit-repo deep`.

## Deep

**Read `~/.config/crush/reference/repo-review-conventions.md` first and follow it.** It defines:

- the ten dimensions;
- the method: inventory and size, then fan out readers of ~8–10K lines each, while the
  main thread reads the product itself;
- the record layout and its lifecycle.

Before fanning out, read `~/.config/crush/reference/token-and-context-economy.md`. A deep audit
is its named exception, but the reader-sizing and brief rules still apply.

Steps:

1. **Inventory.** `wc -l` every corpus and pick the reader split from the numbers.
2. **Find the baseline.** Look for the latest record under `tasks/review/` and the pointer
   to it in the project's `CLAUDE.md`. If one exists, read it: this review's "Carried over"
   section reports each of its findings as fixed / still open / no longer applies.
3. **Fan out the readers in one message.** Read the product yourself (book, tutorial,
   user-facing docs), and take one small corpus yourself if that fits.
4. **Verify every HIGH finding before recording it.** Then dedupe and consolidate.
5. **Write the record** to `tasks/review/<YYYY>/<MM>/<DD>/repo-review.md`, using today's
   date. Create `tasks/review/.keep` if the directory is new. Include:
   - the coverage table, one row per dimension (N/A where it doesn't apply);
   - findings, each VERIFIED or LEAD;
   - tagged follow-ups;
   - numbered open questions.
6. **Add or update the one-line "latest review" pointer** in the project's `CLAUDE.md`.
7. **Stage both files by path**, and nothing else.
8. **Report in chat.** Lead with the findings that change what the maintainer does next,
   then point at the record for the rest. Repeat the open questions as a numbered list.
