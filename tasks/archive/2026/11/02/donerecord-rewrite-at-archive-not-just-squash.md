# Make the done-record rewrite a step of ARCHIVING, not just pre-squash (runCrush side)

**Status:** complete — **Completed:** 2026-11-02 (William Emerison Six <billsix@gmail.com>).
**Priority:** 3 **Difficulty:** 3

## What this did

Mirrored a cross-repo convention change into this repo's delivered conventions. The "normalize a task
doc into a lean done-record" rewrite had been defined **only as a pre-squash step**; since squashing is
conditional but archiving always happens, a task archived without a squash kept its forward-looking
BLUF/Context/Plan/Open-questions scaffolding and stale `Status:` line. The fix makes the done-record
rewrite a step of **completing/archiving** a task — done **before** the `git mv`, shipped in the work
commit, decoupled from squash — so a scaffolded doc can never reach the archive. (Option 2 of three;
full root-cause, options, and decision are in the canonical task.)

## What was changed in THIS repo

- **`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`:** the squash/harvest section (reframed
  "normalize…" as the archive-time done-record rewrite the squash merely reuses), the authorized-batch
  step 3 ("pre-squash rewrite" → "done-record rewrite"), the §Task-documents archive lifecycle (the
  "owed" list + the three-commit enumeration now carry the rewrite), and the "Reference documents"
  section (names the done-record rewrite instead of just "archive the thin work record").
- **`client/entrypoint/dotfiles/.config/crush/commands/archive-task.md`:** step 8 was "set Status,
  **leave the rest alone**" — the very behavior that carried scaffolding into the archive. Rewrote it to
  perform the done-record rewrite. `/new-task` was left unchanged (creation-time scaffolding is correct
  there).

Committed over two commits (CLAUDE.md edits, then the archive-task/sweep edits). The term "pre-squash
rewrite" no longer appears; "pre-squash harvest" (the changelog `[Unreleased]` reconciliation) was left
intact.

## Canonical record

Full root cause, the three options, the decision rationale, and the runClaude-side edits are in the
canonical task: `tasks/archive/2026/11/02/donerecord-rewrite-at-archive-not-just-squash.md` in
**github.com/billsix/runClaudeInContainer** (that repo owns the shared `.claude` layer; this repo
carries mirrored copies). This doc is the runCrush half of the same change, kept for a symmetric task
history (as with the 2026-09-03 `squash-harvest-decision-history` task, which likewise lives archived in
both repos).
