We are about to divert from what we're working on. Push the CURRENT work onto the stack
so it isn't lost, then start on `$DIVERSION`.

The stack file is `~/.config/crush/stack.md`. Create it if missing, with the header
`# Work stack` and nothing else.

Steps:

1. **Work out what we are currently on.** Do not ask me if you can infer it — read the
   conversation, the current repo's `tasks/`, and `git status`. If genuinely ambiguous,
   ask once.

2. **Push a new entry onto the TOP of the stack** (newest first, so the top of the file is
   the top of the stack). Entry format — every field required:

   ```markdown
   ## <one-line description of the PAUSED work>

   - **repo:** <repo name, e.g. mvp / geometricalgebra>
   - **task doc:** `tasks/<slug>.md`  (or `none` — and say why none exists)
   - **pushed:** <YYYY-MM-DD>
   - **diverted to:** <$DIVERSION>
   - **why:** <what made us divert — the finding, question, or blocker>
   - **resume with:** <a CONCRETE next action, specific enough to act on cold>
   - **open questions:** <numbered, verbatim from the unanswered questions — or `none`>
   ```

3. **The `resume with` and `open questions` fields are the point of this command.** A
   vague "continue the doctest work" is a failure; "write doctests for `util/`, starting
   with `clipping.py`; nothing blocks it" is right. Any question I have not answered goes
   in verbatim, numbered, so resuming does not silently drop it.

4. **Do not duplicate the task doc.** The stack records *attention order*; `tasks/*.md`
   records *the work*. If the paused work has no task doc and is non-trivial, create one
   first (`/new-task`) and reference it.

5. Confirm with a one-line summary: what got pushed, and what we're now on.
