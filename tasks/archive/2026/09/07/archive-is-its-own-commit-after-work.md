# Archiving is its own commit AFTER the work commit — stop bundling the archive into the work handoff

**Status:** DONE 2026-09-07 — reworded the archiving guidance + adhoc One-shot note in this repo's
`CLAUDE.md` (condensed), mirroring the runClaudeInContainer fix; the agent memory was corrected
alongside. Verified: no leftover "same handoff" phrasing.
**Priority:** 3
**Difficulty:** 2

## BLUF

The maintainer's task/adhoc lifecycle is a **three-commit sequence**, and the
agent has been collapsing two of them. This repo's shared `CLAUDE.md`
(`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`) tells the agent to archive a
finished task **"in the same handoff as the unit's code and doc deltas"** and to
stage the `git mv` alongside the work. That bundles the archive into the **work**
commit, so `git log` no longer shows "work + its scripts" and "archive + script
deletion" as two related, self-contained points. Fix: reword the archiving
guidance so the archive (the `git mv`, the reference-doc harvest, and the one-shot
adhoc `git rm`) is staged as its **own** set **after the work commit exists** —
never bundled with the work — while **keeping** the "proactive, unprompted,
don't-make-me-ask" intent. **Conventions/doc change only — no code.**

(Twin fix: runClaudeInContainer carries the same guidance and the same fix, archived
at its own `tasks/archive/2026/09/07/archive-is-its-own-commit-after-work.md` — the two
are separate projects and each tracks its own `CLAUDE.md`; kept consistent, but this doc
stands alone.)

## Context — read these first

- **The maintainer's workflow, in his words (2026-09-07):** *"tasks get added
  whenever, ideally in their own commit. work gets done, adhoc scripts are added as
  part of that. a commit is done. archiving happens in a next commit, and adhoc
  scripts are deleted in that commit. this way, when looking through git history,
  these things are all related."* And: *"you shouldn't archive the task before I
  make the commit myself that was part of the work … don't stage the archiving."*

  As three commits:
  1. **task-creation commit** — the task doc added, ideally standalone, whenever.
  2. **work commit** — the change done + the adhoc scripts added, together.
  3. **archive commit** — the `git mv` to `tasks/archive/…` **and** the one-shot
     adhoc `git rm` together, in a separate commit **after** the work commit.

  The adhoc script's whole visible lifetime runs from commit 2 (added with the
  work) to commit 3 (deleted with the archive); pairing the delete with the
  archive-move keeps history legible.

- **Who makes the commits (2026-09-07):** by default **the maintainer makes every
  commit** — the agent only ever *stages* (the standing "Git: I commit, you don't —
  but you DO stage" rule). The sole exception is when the maintainer has
  **explicitly authorized the agent to commit for that session**, granted
  **per-project and per-session** (it does not carry over) — normally when he's
  going to bed and the agent runs long unattended (the quick-save-then-squash mode,
  "only when I authorize committing"). So the three commits above are the
  **maintainer's** by default; in the authorized session mode the **agent** makes
  them itself, still as the same three separate commits in order. The commit
  *boundaries* are identical either way — only *who* runs `git commit` differs.

- **What changed / the culprit:** runClaudeInContainer's `7b33462 "archive at time
  of completion"` (2026-08-30) added the "Archiving is yours to do … in the same
  handoff … the `git mv` just joins the staged set" guidance, which this repo's
  condensed CLAUDE.md mirrors. It conflated two separate goods: **(a)** archive
  proactively without asking (the real point — its origin was the maintainer being
  surprised the agent *didn't* archive and instead asked go/no-go), and **(b)**
  stage it *with the work*. (b) is the bug; (a) must be preserved.

- **Where the bad guidance lives in THIS repo:**
  - `client/entrypoint/dotfiles/.config/crush/CLAUDE.md` **~L105-107**, the
    archiving paragraph: *"yours to do at the moment of completion, unprompted
    (2026-08-31): … `git mv`, stage) in the same handoff as the unit's code and doc
    deltas; don't ask, and don't hold because staged…"*.
  - `…/CLAUDE.md` **~L172**, the adhoc One-shot note: *"the removal trails the
    archive by one commit."*

- **Already correct — leave alone:** `…/commands/archive-task.md`. It does `git mv`
  (step 9) **and** the one-shot `git rm` (step 10) **together** and ends (step 11)
  with *"Do not commit — leave staging to me."* — which is exactly commit 3. Only
  the free-prose "same handoff as the work" guidance is wrong. (Optional hardening:
  note in the command that a one-shot `git rm` is safe only once the script's work
  commit exists.)

- **Interplay with "Git: I commit, you don't — but you DO stage":** unchanged in
  spirit — the agent still stages, the maintainer commits (default). This task only
  fixes *what belongs in which staged set*: the archive is its own set, gated on the
  work commit having landed.

## The operating rule to encode (how "proactive" and "separate commit" coexist)

"Don't ask" is about *permission*; the commit boundary is about *timing*. At task
completion the agent still acts proactively and without a go/no-go question — but
what it does next depends on the session's commit mode.

**Default mode (the maintainer commits — the normal case):**

1. Stage the **work + adhoc scripts**, report the handoff, and **stop**. Do **not**
   `git mv` the task doc or `git rm` any adhoc script yet.
2. The maintainer makes the **work commit**.
3. **Once that commit exists** (agent detects it — HEAD moved / the work files are
   no longer pending), the agent **proactively** stages the **archive set**: the
   `git mv` to `tasks/archive/…`, the reference-doc harvest, and the one-shot adhoc
   `git rm` — together — for the maintainer to commit as commit 3. Still no
   permission asked.

At completion the archive is an **owed** action, tracked (in the task doc's status
and/or the stack), executed after the work commit — same session if the maintainer
commits then, else next session. The agent says so plainly (*"task is complete and
staged; I'll archive it in its own commit once you've committed the work"*), and
never presents a go/no-go archive question.

**Authorized-to-commit mode (commit access granted this session, per-project — the
overnight/quick-save case):** same boundaries, agent runs the commits: stage +
**commit** the work (+ adhoc scripts); then, as a **separate** commit, `git mv` the
archive and `git rm` the one-shot scripts and **commit** that. Two commits, in
order, both by the agent — never one combined "work + archive" commit. (Slots into
the quick-save-then-squash rhythm; the archive stays its own logical commit through
the squash.)

## Proposed changes (do NOT apply until approved)

1. **`…/CLAUDE.md` ~L105-107** — keep "archiving is yours to do, proactively,
   unprompted — don't present go/no-go candidates", but replace "in the same
   handoff … `git mv`, stage" with the operating rule above (archive is its own set
   after the work commit; never bundled into the work handoff; it is commit 3;
   cover both commit modes).
2. **`…/CLAUDE.md` ~L172** — reword "trails the archive by one commit" → "goes **in
   the archive commit** (paired with the `git mv`), which follows the work commit."
3. **Optional:** add a one-line "the lifecycle is three commits: task-add /
   work+adhoc / archive+adhoc-delete" statement near the archiving guidance or in
   "Git: I commit, you don't".

## Decisions made

- **Memory-update scope (maintainer: "whatever you recommend", 2026-09-07):** the
  agent memory `archive-on-completion-no-asking` gets its body corrected to the new
  timing (proactive yes; archive is its own commit after the work commit, never
  bundled; note the who-commits default/authorized split). Kept one-fact; the full
  three-commit lifecycle lives in the shared `CLAUDE.md`. (The memory lives in the
  agent's config, not this repo — handled alongside the runClaude edit.)

No open questions remain — ready to implement on the maintainer's go-ahead.

## Verification

Docs-only; no gate. After editing, re-read the changed paragraphs for one coherent
story (no leftover "same handoff" phrasing), and confirm this repo's condensed
guidance says the same thing as runClaude's fuller version. Stage by path; the
maintainer commits (unless he has authorized committing this session — the exact
split this fix is about).
