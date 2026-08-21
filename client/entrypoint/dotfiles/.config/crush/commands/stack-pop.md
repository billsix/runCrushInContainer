The work we just finished is done. Pop it and resume what was underneath.

The stack file is `~/.config/crush/stack.md`.

Steps:

1. **Verify it is actually finished before popping.** Check the real state — tests, the
   task doc's status, `git status`. If it does not look done, **say so and ask** rather
   than popping. A stack that pops unfinished work is worse than no stack.

2. **If the completed work has a task doc, archive it** per the task-document convention
   (`/archive-task`, moving it to `tasks/archive/<YYYY>/<MM>/<DD>/`) — recording *why* it
   is complete, not just flipping a status line.

3. **Remove the TOP entry** from `~/.config/crush/stack.md`.

4. **Resume the new top entry, and resume it properly.** Do not just name it — restate it
   so it can be acted on cold:
   - its `resume with` action;
   - its `open questions`, **re-asked as a numbered list with both positions named**, since
     they may be many messages back and I will not remember them;
   - anything that changed underneath it while it was paused (the code moved on, a
     dependency landed, a decision was made) — check, don't assume it is untouched.

5. If the stack is now empty, say so, and ask what to work on next rather than picking
   something yourself.
