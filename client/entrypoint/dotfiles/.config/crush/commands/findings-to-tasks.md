
Turn a set of findings into task documents for the project we're currently in: one
`tasks/<slug>.md` per item, each `**Status:** proposed — needs go-ahead`. This command only
**writes task docs**. It does not fix anything and does not change code.

Source: `$SOURCE`

- **A review record** (`tasks/review/<YYYY>/<MM>/<DD>/<slug>.md`, from `/audit-repo deep`),
  optionally narrowed to sections (`§4.1 §5.1`, or `required` for the record's "Suggested
  follow-ups › Required" items). Read the record and the sections named. With no sections named,
  use its "Suggested follow-ups" list as the item list.
- **Anything else** (a list earlier in this conversation, a pasted list, a findings report in chat).
  Use the items as given.
- **Empty or ambiguous:** stop and ask which findings.

Steps:

1. **Find the repo root and read its conventions.** Use `git rev-parse --show-toplevel`, then read
   the project's `CLAUDE.md`. If the repo is an upstream-only checkout (personal overlay), stop and
   say so.
2. **Group the findings into tasks before writing anything.**
   - One task per **unit of work a person would do and stage in one go**, not one per bullet.
   - Several findings that share a fix and its files become one task (e.g. "the three generator
     bugs in `gen_specialized.py`" if they get one regenerate-and-test pass). An unrelated finding
     gets its own task even when it is small.
   - A theme too big for one doc (3+ sizeable sequential chunks) becomes an umbrella with
     step-tasks, per "Step tasks" in `CLAUDE.md`. Don't over-scaffold.
3. **Check for overlap with existing work.**
   - Scan open `tasks/*.md`. If a finding already belongs to an open task, propose adding it there
     (name the task) instead of creating a duplicate.
   - If an archived task already settled it, say so and skip it.
4. **Show the plan and wait.** Present the proposed task list: for each, a slug, a one-line title,
   which findings it covers (by record section), and a proposed Priority/Difficulty. Mark the
   overlaps and skips. Add the questions as a closing numbered list. **Create nothing until I
   answer.** Per "Confirm before acting", the plan is the deliverable of this step.
5. **Once approved, write each task** with the `/new-task` skeleton, filled in, not left as
   placeholders:
   - `**Status:** proposed — needs go-ahead`. Use `blocked` plus `**Blocked on:**`/`**Recheck:**` only
     for an external gate.
   - `**Priority:**` / `**Difficulty:**` as approved, and `**Created:**` with today's date.
   - `**Source:**`: the record path and section(s) it came from (`tasks/review/2026/11/08/repo-review.md`
     §5.1), or "conversation, <date>".
   - `## BLUF`: what the task is and what "done" means.
   - `## Context`, enough to execute cold:
     - the finding(s) restated, with their evidence (`path:line`, the command that shows the bug and
       its output);
     - what to read first, and related tasks and reference docs.
     - Re-check each finding against the tree before writing it in. A review record is a snapshot,
       so if a finding is already fixed, drop it and say so.
   - `## Plan`: the steps, including the gate that proves the fix (the test to add, the `make` target
     to run).
   - `## Open questions`: anything the finding leaves for the maintainer. A question the record
     already asked goes here verbatim, numbered as in the record.
6. **Never edit the review record.** It is frozen. The tasks point at it; it doesn't point at them.
7. **Stage the new task docs by path**, and nothing else.
8. **Report:** the paths created, the findings merged into existing tasks, the findings skipped (and
   why), and every task's open questions as one closing numbered list.
