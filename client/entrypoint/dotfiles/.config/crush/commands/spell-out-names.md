Plan a spelled-out-names sweep for the project we're currently in.

Scope: `$SCOPE` (empty means the whole repo).

This command **writes task docs and stops**. It does not rename anything, and it does not start
the work: the tasks wait for my answers and my go-ahead like any other task.

Steps:

1. Read `~/.config/crush/reference/spelled-out-names-sweep.md` first. It holds the method, the
   situation checks and the policy questions this command turns into a task.
2. Determine the repo root (`git rev-parse --show-toplevel`) and read the repo's `CLAUDE.md`, its
   `README`, and `tasks/` (not the archive) for anything that already covers names or a rename.
   If an open task already covers this, stop and show it to me instead of writing a second one.
3. **Run the situation checks** from the reference doc's "Step 1" against this repo, by looking,
   not by assuming: `git remote -v` and any upstream-sync task (upstream merges), patch queues,
   whether the code is a library others pin (consumers), the generators and what they feed, mirrors
   (ports, bindings), configurations the default build skips, and other contracts on the code. If
   the repo is an upstream-only checkout, say so and stop. Each check ends up either as a fact in
   the task's `## Context` (with what showed it) or as a numbered open question.
4. **Take a first sample of the vocabulary** to size the work: list the scope's declared names with
   a quick tool pass (not the full codemod), split them into words, and note roughly how many
   distinct abbreviations there are and a dozen examples with their likely meanings. This is
   investigation; save the discovery command under `tasks/adhoc/<slug>/discover.sh` and its output
   under `tasks/adhoc/<slug>/data/`.
5. **Write the tasks**, using the `/new-task` skeleton (`## BLUF`, `## Context`, Goal, Plan, Notes,
   Open questions), each `**Status:** proposed — needs go-ahead`, with Priority and Difficulty:
   - one task for the primary code (`tasks/spelled-out-names-<scope-slug>.md`), whose Plan follows
     the reference doc's Steps 2–5 and whose Notes list the exemptions found so far;
   - one task per mirror (port, binding), each `Depends on:` the primary task and reusing its
     rename table;
   - when there are three or more, an umbrella per the step-task convention.
   Put the reference doc's policy questions (domain acronyms, name by meaning or by the manual's
   name, the keep-list of familiar acronyms, library-habit names, mathematical names) in the
   primary task's Open questions, each with my options and your recommendation for this repo, plus
   every open situation check from step 3.
6. Report in chat: the paths created, any situation check that argues against the sweep, and the
   open questions as one numbered list (one ask per item). Then stop.
