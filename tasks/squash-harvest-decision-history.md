# Convention: on "I'm going to squash", harvest the full decision history into the task doc first

**Status:** proposed — needs go-ahead
**Priority:** 3
**Difficulty:** 2

## BLUF

Add a standing convention (to **both sandboxes'** nested conventions CLAUDE.md — this repo's
`client/entrypoint/dotfiles/.config/crush/CLAUDE.md` and runClaudeInContainer's
`entrypoint/dotfiles/.claude/CLAUDE.md`): **when the maintainer says they're about to squash**, the agent first
walks **every commit from the remote-tracked branch tip to HEAD** (the unpushed range), reads both the
**task-doc changes** and the **code changes** across them, and **updates the task doc with a chronological record**
of every decision made — what changed and why, what was rejected and why, what each step discovered. Then the
squash collapses the commits, and the task doc still carries the play-by-play. The point: after squashing the
granular git history is gone, so the archived task doc must already hold "everything that happened and why" for
whoever reads it later. "Done" = the convention is in both repos' nested CLAUDE.md, next to the squash mention.

## Context

- **runCrush copy of a shared decision.** The maintainer wants this convention in the nested CLAUDE.md of **both**
  sandboxes; the runClaudeInContainer copy of this task is
  `runClaudeInContainer/tasks/squash-harvest-decision-history.md`. Keep the wording in sync.
- Where it goes in THIS repo: `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, by the existing squash line
  ("quick-save commits as you go, then squash to one-commit-per-task at the end", ~line 67-68) and the
  **"Task documents"** section (~line 70, which already requires decisions recorded *with rationale*). This new
  rule bridges them: squashing must *feed* the task doc's decision record before the granular commits vanish.
- General working practice (not maintainer identity/URLs), so it belongs in the conventions layer, not a personal
  overlay.

## The convention to add (draft wording — keep identical in both repos)

> **Before a squash, harvest the commit history into the task doc.** When I say I'm going to squash: walk every
> commit in `<upstream>..HEAD` (the unpushed range — find `<upstream>` via the remote-tracked branch,
> `git rev-parse --abbrev-ref @{u}`), reading the task-doc AND code diffs at each. Then update the task doc so it
> records, in order, every decision we made and **why** — what changed, what we rejected and why, what each step
> discovered. The squash then collapses the commits; the task doc keeps the chronological account, because after
> the squash the per-commit trail is gone and the archived task doc becomes the only record of the reasoning. Do
> this as part of the squash, unprompted (like staging).

## Open questions

1. **Wording** — use the draft above verbatim in both files, or adjust per repo's terser style? *Recommend the
   same wording in both, trimmed to match each file's density.* Harvest target = the task doc during squash;
   reference-doc harvest stays at archive time (per the existing "harvest to reference docs" rule).
