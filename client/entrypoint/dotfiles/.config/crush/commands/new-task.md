Create a new task document for the project we're currently in.

Slug: `$SLUG`

Steps:

1. Determine the repo root — prefer `git rev-parse --show-toplevel` if it's a git repo; otherwise use the current working directory.
2. If `$SLUG` is empty or not kebab-case, stop and ask me for a valid slug.
3. Ensure `<repo-root>/tasks/` exists; create it if missing.
4. If `tasks/$SLUG.md` already exists, stop and tell me — show me its current status and ask whether I want to resume the existing task instead of clobbering it. Do not overwrite.
5. Otherwise, create `tasks/$SLUG.md` with this skeleton:

   ```markdown
   # <Title>

   **Status:** in-progress
   **Priority:** <1–10, 1=highest>
   **Difficulty:** <1–10, 1=easiest>
   **Started:** <today, YYYY-MM-DD>

   ## Goal

   <one-paragraph statement of what we're trying to accomplish>

   ## Plan

   - [ ] <first step>

   ## Notes / decisions

   ## Open questions
   ```

6. Ask me for the title and one-paragraph goal (don't invent them from the slug). Fill them in once I answer. Also **propose a Priority and Difficulty** (1–10 each, per the scale in the "Task documents" section of `CLAUDE.md` — 1=highest priority / easiest, geometric ~1.5×/step) with a one-line rationale for each, and let me adjust before finalizing. Leave Plan/Notes/Open questions for me or for our work to populate.
7. Confirm the path of the created file.
