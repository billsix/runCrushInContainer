Archive a completed task in the current repo.

Slug: `$SLUG`

Steps:

1. Determine the repo root — prefer `git rev-parse --show-toplevel`, else current working directory.
2. **Port-check for legacy flat archives.** Look for any files directly under `tasks/archive/*.md` (depth 1 only — anything already nested in `<YYYY>/<MM>/<DD>/` is fine). For each one found:
   - Determine its archive date via `git log -1 --format=%ad --date=format:%Y/%m/%d -- <file>`.
   - If the file has no git history (untracked or never committed), fall back to its mtime (`date -r <file> +%Y/%m/%d`) and flag this as a fallback when surfacing it.
   - Show the user the full list (file → proposed destination, with fallback flags) and ask whether to port them. If yes, `git mv` each into `tasks/archive/<Y>/<M>/<D>/<slug>.md` (or plain `mv` if untracked), creating intermediate dirs as needed. If no, continue without porting — note that the prompt will recur next run, since there's no state to suppress it.
3. If `$SLUG` is empty, stop and ask me which task to archive. List the contents of `tasks/` (top level only, not `archive/`) so I can pick.
4. Verify `tasks/$SLUG.md` exists. If not, stop, list what's actually in `tasks/`, and ask me to pick the right slug.
5. Compute today's date as `<YYYY>/<MM>/<DD>` (zero-padded). Ensure `tasks/archive/<YYYY>/<MM>/<DD>/` exists; create it (with intermediate dirs) if missing.
6. If `tasks/archive/<YYYY>/<MM>/<DD>/$SLUG.md` already exists, stop and ask whether to overwrite or pick a different destination name.
7. **Harvest durable knowledge into a reference doc, and reconcile existing ones** (per the "Reference documents" convention in `~/.config/crush/CLAUDE.md` — reference docs are an expanded, agent-facing `CLAUDE.md`, and archiving otherwise buries decisions in a don't-trawl bucket). Read the task's content and decide:
   - Does it hold **durable decisions / rationale / rejected alternatives / how-it-actually-works** that outlive the work? If so, **extract that into `tasks/reference/<topic>.md`** (create it, or update an existing reference doc it belongs to), **slim the task to a lean work record that points to the reference**, and cross-link both. Keep the *work log* (what was done, which gates passed) in the task.
   - Independently, **double-check the other `tasks/reference/*` docs** (and, if relevant, `CLAUDE.md` / `README.md`): does completing this task make any of them **stale** (a claim no longer true) or **incomplete** (a decision/subsystem now missing)? Update as appropriate.
   - Surface what you extracted/updated, concisely. If the task is purely mechanical with nothing durable to harvest and nothing to reconcile, say so and skip.
8. Edit the file in place before moving: set `**Status:** complete` and add a `**Completed:** <today, YYYY-MM-DD>` line directly under it if not already present. Leave the rest of the content alone.
9. Move the file. If we're in a git repo, use `git mv`. Otherwise plain `mv`.
10. **Triage the task's ad-hoc scripts — promote or remove** (per the "Ad-hoc scripts" convention in `~/.config/crush/CLAUDE.md`). If `tasks/adhoc/$SLUG/` exists, go through each script and decide:
    - **Reusable** — a checker / linter / report / proof-harness you would run again against future changes → **promote it**: move it to the repo's tools location (`tools/` if present — create it, or **fold it into an existing tool** — not a new invented dir) with a **light cleanup** (repo-relative, self-contained, a docstring saying *when to run it*); **update the relevant `tasks/reference/*` doc** to note it (what it checks, when to run it); and **investigate the repo's `Makefile`, `Dockerfile`, and entrypoint scripts** to see whether it should run as a make target — an existing gate (`format`/`check-*`/`test`), a new `## `-documented target, an **in-container step after setup** (checks needing generated/populated files live in `entrypoint.sh`, not a host-side target), and/or a Dockerfile dependency. Then **propose** the specific wiring, shaped to the gate conventions (a multi-step check script must propagate every step's failure; the real gate runs in the container) — but do **not** wire it in; leave that for me to approve. "Manual tool, documented, not gated" is a valid outcome (an informational audit shouldn't fail the build).
    - **One-shot** — a codemod / bulk edit whose job is done → **remove from version control**: `git rm -r` it if tracked (history survives in the work commits — `git log`/`git show` still recover it); `rm -rf` if untracked (note it had no history to preserve).
    - **Default to remove; promote only when the ongoing-use case is clear, and ask me when borderline.**
    After triaging every script you know about, the `tasks/adhoc/$SLUG/` dir **should be empty** — drop it. Treat that emptiness as a **spot-check**: **if anything is left over, it's a file you didn't account for — flag it to me, don't silently delete it.** If the dir didn't exist, skip silently. Report what you promoted (with any gate-wiring proposals) and what you removed.
11. Confirm the destination path (any reference-doc created/updated in step 7; any tool promoted / reference-doc updated / gate-wiring proposed in step 10; and any `tasks/adhoc/` removal). Do not commit — leave staging to me.
