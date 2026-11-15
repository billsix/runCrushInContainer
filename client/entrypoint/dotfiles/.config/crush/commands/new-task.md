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

   **Status:** proposed — needs go-ahead
   **Priority:** <1–10, 1=highest>
   **Difficulty:** <1–10, 1=easiest>
   **Created:** <today, YYYY-MM-DD> (<Name> <<email>>, from `git config`)

   ## BLUF

   <1–4 sentences: what this task IS and what "done" means — the bottom line, up front>

   ## Context

   <Cold-start orientation: what to read first (files, related/prior tasks, reference docs), the
   current state of the relevant code, and any decisions already made with their rationale —
   enough that a fresh reader can act without the conversation that produced this task.>

   ## Goal

   <one-paragraph statement of what we're trying to accomplish>

   ## Plan

   - [ ] <first step>

   ## Notes / decisions

   ## Open questions
   ```

   (`## BLUF` and `## Context` are the standing task-doc default — every task is written to be executed
   **cold**, so a fresh reader/session needs no prior conversation. Don't preface them with "this is
   self-contained" — just fill them in. Full BLUF write-up: `~/.config/crush/reference/bluf-bottom-line-up-front.md`.)

6. Ask me for the title and one-paragraph goal (don't invent them from the slug). Fill them in once I answer, then **draft the `## BLUF`** (1–4 sentences — what the task is and what "done" means) from the title/goal for me to tweak, and **populate `## Context`** with what you already know (files to read first, related/prior tasks and reference docs, current state of the relevant code, decisions already made with rationale — leave a stub prompting for it if you don't yet have enough). Also **propose a Priority and Difficulty** (1–10 each, per the scale in the "Task documents" section of `CLAUDE.md` — 1=highest priority / easiest, geometric ~1.5×/step) with a one-line rationale for each, and let me adjust before finalizing. Leave Plan/Notes/Open questions for me or for our work to populate.
7. If the task can't start until an **external condition** changes (an upstream release, a hands-on
   check only I can do), set `**Status:** blocked` instead, give it a high Priority number, and add
   `**Blocked on:**` (the condition, one line) and `**Recheck:**` (a cheap runnable check + the
   cleared signal) under the header, per "Blocked tasks" in `~/.config/crush/CLAUDE.md`.
8. Confirm the path of the created file.
