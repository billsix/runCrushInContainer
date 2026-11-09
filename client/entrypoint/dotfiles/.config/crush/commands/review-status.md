Report the status of a review record in the repository we are in. **Read-only:** edit and
stage nothing. The record is frozen; its status comes from the tasks that cite it.

Record: `$RECORD` (empty → the record named by the "latest review" pointer in the
project's `CLAUDE.md`, else the newest file under `tasks/review/`).

1. Find the repo root (`git rev-parse --show-toplevel`) and `cd` there.
2. Run `python3 ~/.config/crush/reference/review_status.py [record]`.
3. Report in chat:
   - the summary line (done / open / untracked counts);
   - the **open** and **untracked** follow-ups, each with its tier and §s; these are what
     the maintainer may act on next;
   - any "done (by §)" rows: the record has no follow-up IDs, so the tool matched by
     section. Say which of those you checked against the task and which are still leads;
   - tasks that cite the record with no § or ID (they cannot be placed until their
     `**Source:**` line names the §s).

   Point at the tool's full table rather than pasting it, unless the maintainer asks.
4. If untracked items are worth tasks, suggest `/findings-to-tasks <record> §…`; don't make
   them.

Conventions (record layout, follow-up IDs, `**Source:**` lines):
`~/.config/crush/reference/repo-review-conventions.md` › "Lifecycle".
