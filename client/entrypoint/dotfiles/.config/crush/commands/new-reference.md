Create a new **reference document** (durable knowledge that isn't tracked work — a
comparison, survey, investigation's findings, design rationale, capability/gap analysis, or
domain notes) for the project we're currently in. See the "Reference documents" section of
`~/.config/crush/CLAUDE.md` for what qualifies and how these differ from task docs.

Slug: `$SLUG`

Steps:

1. Determine the repo root — prefer `git rev-parse --show-toplevel` if it's a git repo; otherwise use the current working directory.
2. If `$SLUG` is empty or not kebab-case, stop and ask me for a valid slug.
3. **Sanity-check that this really wants to be a reference doc, not a task.** Apply the test: *"will this still be worth reading after the current work is finished, and does it state what is TRUE rather than what to DO?"* If it looks like tracked work (a goal with steps and a done-state), say so and suggest `/new-task` instead — but proceed if I confirm.
4. Ensure `<repo-root>/tasks/reference/` exists; create it if missing.
5. If `tasks/reference/$SLUG.md` already exists, stop and tell me — show me what it covers and ask whether I want to update the existing note instead of clobbering it. Do not overwrite. (Reference docs are updated in place, never archived.)
6. Otherwise, create `tasks/reference/$SLUG.md` with this skeleton:

   ```markdown
   # <Title>

   **Reference document** — <one-line statement of what this maps / compares / records>.
   Not a task: nothing here is "to do." Update it in place as things change or as items get
   promoted into real `tasks/`. Last updated <today, YYYY-MM-DD>.

   ## What this is

   <one-paragraph purpose: what question it answers and why it's worth keeping>

   ## Scope & assumptions

   -

   ## Findings

   <the body — the durable content this doc exists to hold>

   ## Follow-ups / promote to tasks

   <rows/items here that could become real `tasks/` docs; note when one has been promoted>
   ```

7. Ask me for the title and the one-paragraph "What this is" (don't invent them from the slug). Fill them in once I answer. Leave the rest for me or for our work to populate.
8. Confirm the path of the created file, and remind me it lives in `tasks/reference/` and is never archived.
