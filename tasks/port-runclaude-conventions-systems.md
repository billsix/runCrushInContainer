# Port the runClaudeInContainer conventions systems (tasks / stack / personal config)

**Status:** proposed — deferred until the basics work (see `tasks/crush-local-llm-bringup.md`)
**Priority:** 6
**Difficulty:** 4
**Started:** 2026-08-18

## Goal

Once `runCrushInContainer` is up and running (the bring-up task), bring over the reusable
*working-method* machinery from `runClaudeInContainer` so this repo is a first-class member
of the same template family — **not** in the v1 bring-up, on purpose.

The deliberate v1 omission (2026-08-18): the user wanted the beginning to be the basics, so
none of the below was built into the first cut. This task is the follow-up.

## What to port (from github.com/billsix/runClaudeInContainer)

- **Task-doc system:** the `tasks/` conventions, `/new-task` + `/archive-task`, the
  Priority/Difficulty triage, `tasks/archive/<YYYY>/<MM>/<DD>/`.
- **Reference-doc system:** `tasks/reference/`, `/new-reference`, the "durable knowledge"
  distinction.
- **Diversion stack:** `~/.claude/stack.md` + the `/stack`, `/stack-push`, `/stack-pop`,
  `/stack-drop` commands.
- **Personal-overlay layering:** the portable-`CLAUDE.md` + `@`-imported
  `ai-coding-conventions.personal.md` split, the blank baked default, the host-file mount, and
  `FORKING.md`.
- **Reference docs worth reusing verbatim:** `llm-overused-phrases.md`,
  `print-debugging.md`; and a Crush-specific analogue of `sandbox-capability-map.md` /
  `nested-podman-design.md` if this image diverges from the Claude one.

## What NOT to port

- **Auth plumbing** (`~/.claude` / `~/.claude.json` mounts, `CLAUDE_CODE_OAUTH_TOKEN`
  passthrough). The Crush endpoint is a local, keyless llama-server reached over SSH — there
  is no interactive login to persist. Crush's *own* provider config (endpoint URL, model,
  dummy key) is the only "auth", and it's baked into the image / mounted, not an OAuth dance.
- Anything Claude-Code-binary-specific.

## Open questions

1. **Does Crush read a `CLAUDE.md`-style conventions file, and from where?** Crush documents
   an `AGENTS.md` / project-context mechanism — confirm the path and format before deciding
   whether the portable conventions attach the same way they do for Claude Code, or need a
   Crush-shaped wrapper.
2. **Share the reference docs across both repos, or copy?** Recommend copy-and-adapt for now
   (the two images differ); revisit a shared source if they converge.
