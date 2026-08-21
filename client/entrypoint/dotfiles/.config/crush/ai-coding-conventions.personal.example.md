# Personal conventions — TEMPLATE

Copy this file's *structure* into `~/.ai-coding-conventions.personal.md` on your host and
fill in your own specifics. `make shell` mounts that host file over
`~/.claude/ai-coding-conventions.personal.md`, which the tracked `CLAUDE.md` `@`-imports — so everything
below layers on top of the portable conventions without editing the tracked file.

Delete any section you don't need. Nothing here is required; an empty personal file is
a valid setup.

---

## Who I am

<!-- The portable CLAUDE.md identifies "the user" by `git config` each session. Pin
     your own identity/attribution format here so dated stamps in docs are unambiguous. -->

I am `<Your Name> <you@example.com>`. When you write a dated attribution or decision
stamp, identify me as `<Your Name> <you@example.com>` — never a bare first name.

## Reference my projects by their canonical URL, not the container path

<!-- The portable rule (in CLAUDE.md) says: in committed docs, reference a project by
     its canonical remote URL, not the container-absolute mount path; read the URL from
     the right remote, and ask if you can't confirm it. Record YOUR specifics here. -->

- My projects are local checkouts bind-mounted at container paths; each has a remote.
- **Read the URL from the remote named `<your-remote-name, e.g. github or origin>`**,
  not by guessing from the directory name (a dir name can differ from the repo name).
- **Confirmed mappings (local dir → canonical URL):**
  - `<dir>` → `<https://…/…>`
  - `<dir-that-differs>` → `<https://…/…>`  (dir ≠ repo name)
- If a project's URL can't be confirmed, say so rather than inventing one.

## My project layout / template

<!-- If you keep your projects on a shared template (a common Dockerfile/Makefile/
     entrypoint shape), describe it here so the agent can spot-check conformance and
     know where things live. Otherwise delete this section — per-project specifics can
     live in each project's own CLAUDE.md instead. -->

- Template shape: `<describe, or delete>`
- Per-project detail belongs in that project's own `CLAUDE.md`.

## Multi-repo mount layout

<!-- If your sandbox mounts several repos at once, list where, so the agent internalizes
     each repo's conventions. The portable CLAUDE.md already covers the general "scan the
     mounts and read each CLAUDE.md" mechanism. -->

- I mount projects at `<e.g. /foo/opt/...>`; scan those and read each repo's CLAUDE.md.

## Standing authorizations

<!-- Any blanket permissions you want to grant the agent up front (things it may do
     without asking each time). Be explicit about scope and limits. Examples you might
     grant: transient build-file edits to make nested runs work; committing during
     long unattended tasks. Delete if you grant none. -->

- `<authorization, with scope and limits — or delete this section>`
