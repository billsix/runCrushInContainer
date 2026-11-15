Re-check `blocked` tasks: tasks with a `**Blocked on:**` external condition and a runnable
`**Recheck:**` (the "Blocked tasks" rule in `~/.config/crush/CLAUDE.md`, "Task documents").

Scope: `$SCOPE` — empty for the current repo (`git rev-parse --show-toplevel`, else the current
directory); `all` for every project mounted in this container (`/work` and any extra mounts).

Steps:

1. **Find the blocked tasks**: `tasks/*.md` (top level, not `tasks/archive/`) whose `**Status:**`
   contains `blocked` and that have a `**Recheck:**`. Collect repo, slug, `Blocked on:`, `Recheck:`.
   If none, say so and stop.
2. **List what you will check**, one line each, before running anything.
3. **Run each `Recheck:`** as written. It is one of:
   - a **command** → run it and read the exit status / output;
   - a **version/release comparison** → compare with a version-aware sort (`sort -V`,
     `git tag --sort=v:refname`), never lexically;
   - a **URL + signal** → fetch it with the web tool and look for the signal. This needs the
     with-internet launcher; in no-internet mode (`--network=none`) report it **unknown** and say
     the check needs internet;
   - a **human-gated step** → don't run it; report it is still waiting on me and name my action.
   A check that cannot run is **unknown**, not cleared.
4. **Report a table**: `CLEARED` / `still blocked` / `unknown`, one line of evidence each,
   cleared first.
5. **For each CLEARED task, offer to un-block it** (not unprompted): drop `Blocked on:` /
   `Recheck:`, set a real `**Status:**` and propose a fresh `**Priority:**`; on my go, edit and stage
   it. Leave the others untouched.
6. **Don't commit** — stage only.
