# Archiving is its own commit AFTER the work commit — stop bundling the archive into the work handoff

**Status:** complete
**Completed:** 2026-09-07

## What this did

Reworded the archiving guidance and the adhoc one-shot note in
`client/entrypoint/dotfiles/.config/crush/CLAUDE.md` (condensed), mirroring the runClaudeInContainer
fix (its twin is runClaudeInContainer `tasks/archive/2026/09/07/archive-is-its-own-commit-after-work.md`).
The old text told the agent to archive "in the same handoff as the unit's code and doc deltas", which
bundled the `git mv` into the work commit. The new text keeps archiving proactive and unasked, but
stages the archive set (the `git mv`, the reference-doc harvest, the one-shot adhoc `git rm`) as its
own commit after the work commit exists. Conventions change only, no code.

## The maintainer's workflow (2026-09-07)

*"tasks get added whenever, ideally in their own commit. work gets done, adhoc scripts are added as
part of that. a commit is done. archiving happens in a next commit, and adhoc scripts are deleted in
that commit. this way, when looking through git history, these things are all related."* And: *"you
shouldn't archive the task before I make the commit myself that was part of the work … don't stage
the archiving."*

So the lifecycle is three commits: (1) task-add; (2) work + adhoc scripts; (3) archive move + one-shot
adhoc `git rm`. By default the maintainer makes every commit and the agent only stages; when the
maintainer has authorized committing for that project and session (typically overnight), the agent
makes the same three commits in order, never one combined "work + archive".

## Cause

runClaudeInContainer's `7b33462 "archive at time of completion"` (2026-08-30), mirrored here, conflated
two things: (a) archive proactively without asking (the real point; the maintainer had been surprised
by a go/no-go question) and (b) stage it with the work. (b) was the bug; (a) was preserved.

## Rule encoded

"Don't ask" is about permission; the commit boundary is about timing. In default mode the agent stages
the work, reports, and stops; once the work commit exists it proactively stages the archive set as
commit 3. Until then the archive is an owed, tracked action, and the agent says so plainly ("I'll
archive it in its own commit once you've committed the work").

## Changes

1. The archiving paragraph: replaced "in the same handoff … `git mv`, stage" with the rule above,
   covering both commit modes.
2. The adhoc one-shot note: "trails the archive by one commit" became "the one-shot's `git rm` belongs
   in the archive commit", paired with the `git mv`.
3. `client/entrypoint/dotfiles/.config/crush/commands/archive-task.md` was already correct (`git mv` and
   one-shot `git rm` together, then "Do not commit") and was left alone.

## Decisions

- Memory update scope (maintainer: "whatever you recommend", 2026-09-07): the agent memory
  `archive-on-completion-no-asking` had its body corrected to the new timing, kept to one fact; the full
  lifecycle lives in the shared `CLAUDE.md`. That memory is outside this repo.

## Verification

Docs only, no gate. Re-read the changed paragraphs and confirmed no leftover "same handoff" phrasing
(a grep of the file today finds none).
