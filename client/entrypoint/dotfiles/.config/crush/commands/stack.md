Show me the current work stack from `~/.config/crush/stack.md`.

Steps:

1. If the file is missing or has no entries, say "the stack is empty" and stop. Do not
   invent entries.

2. Print the trail as a **descent, ROOT first** — the bottom entry (root purpose) at the
   top of the display, each diversion indented under the one it diverted from, the current
   weeds at the deepest indent. This is a depth gauge; the shape should make the depth
   obvious at a glance:

   ```
   PURPOSE: <root entry>                       [repo]  — READY
     └ diverted to: <next>                      [repo]  — BLOCKED on Q1
        └ diverted to: <next>                   [repo]  — BLOCKED on Q1,Q2
           └ NOW: <current weeds>               [repo]  — BLOCKED on Q1
   ```

   For each level also give its one-line `resume with` and its open questions. Mark each
   **BLOCKED** (unanswered questions gate it) or **READY** (no decision from me needed).

3. **Verify each entry against reality before showing it** — this is the part that makes
   the command trustworthy:
   - if it names a task doc, confirm the file still exists (and report if it has been
     archived or deleted);
   - if the entry looks already-done (the task doc says complete, or the work is
     obviously landed), **say so and suggest `/stack-pop`** rather than presenting stale
     work as pending.

4. After the trail, do the thing this whole gauge is FOR — a depth/purpose sanity check:
   - **Restate the ROOT purpose and the depth in one line:** "we're N diversions deep; we
     started this to <root purpose>." This is the most important line of the whole output.
   - **Ask whether we're rabbit-holing:** has a diversion grown out of proportion to the
     purpose beneath it? If so, say it plainly — "this began as <root> and has become
     <weeds>; is that worth it?" — as an honest observation, not a rhetorical one.
   - **Then one recommendation, phrased as a recommendation, never a present-tense fact.**
     Prefer the actionable entry **closest to the root** (climbing back toward the purpose,
     not deeper into the newest tangent). If the deepest items are all BLOCKED on my
     questions, say so and recommend either answering the one question that unblocks the
     most, or abandoning the tangent and dropping back down toward the root.
   - **One recommendation, not a menu.** Do not re-list every item as choices for me to
     arbitrate — that hands me the sorting this gauge exists to do for me.

5. Do not modify the stack. This command is read-only.
