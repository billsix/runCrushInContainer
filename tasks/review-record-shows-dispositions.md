# Mirror: a review record shows which findings were handled, by which task, in which commit

**Status:** proposed — waits on the decision in runClaudeInContainer's task of the same name
**Priority:** 5
**Difficulty:** 3
**Created:** 2026-11-16 (William Emerison Six <billsix@gmail.com>)
**Depends on:** github.com/billsix/runClaudeInContainer `tasks/review-record-shows-dispositions.md`

## BLUF

The maintainer (2026-11-16) can't tell, by reading a review record, which findings were handled,
by which task, and in which commit. The options are explored, decided and implemented in
github.com/billsix/runClaudeInContainer `tasks/review-record-shows-dispositions.md`, the canonical
copy of the review conventions. This task mirrors the chosen design into runCrush, which carries
its own copies of the conventions, the tool and the commands. Done means runCrush's copies match
the canonical change, and runCrush's own review record is handled as the decision says.

## Context

- **runCrush's copies of the review machinery** (mirrored from runClaudeInContainer):
  - `tasks/reference/repo-review-conventions.md` and `tasks/reference/review_status.py`;
  - the client's baked copy `client/entrypoint/dotfiles/.config/crush/reference/review_status.py`;
  - the commands `client/entrypoint/dotfiles/.config/crush/commands/findings-to-tasks.md`,
    `archive-task.md`, `review-status.md` and `audit-repo.md`.

  `review_status.py` is mirrored byte-identically (runClaudeInContainer `CLAUDE.md`). Check whether
  the client's baked reference copy is kept in sync by a script or by hand before editing.
- **runCrush's own record:** `tasks/review/2026/11/15/repo-review.md`.
- **The design isn't decided yet.** The options are listed in the runClaude task: (A) each task
  writes its disposition back into the record, which is the maintainer's first idea; (B) a
  hand-kept sidecar; (C) a generated, committed status file beside the record, with commits derived
  from git; (D) a view only; (E) combinations.

## Plan

1. Wait for the runClaude task's decision and implementation.
2. Copy its `review_status.py` byte-identically into both runCrush locations, and `cmp` them
   against the canonical.
3. Port its edits to `repo-review-conventions.md` and the four commands, adapting only the
   Claude-specific wording (command paths, `~/.claude` versus `~/.config/crush`).
4. Apply the decision to runCrush's 2026-11-15 record if it says to backfill.
5. Run runCrush's gates for the touched files: ruff, ty and the doctests for the tool.

## Open questions

None of its own. The design questions are in the runClaude task.
