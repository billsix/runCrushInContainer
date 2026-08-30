# Cross-project conventions (lean core)

This is the **portable, cross-project** working method, baked into the image and loaded into every
session (registered as a `global-context-path` in `crushrc`). It is deliberately **lean** — a local
model has a small context window, so this holds the *rules*, not the long worked-examples. Fuller
detail lives in the baked reference docs (pointed to below) and in the source repo
`github.com/billsix/runClaudeInContainer`.

## This is the SHARED layer — personal specifics go in the overlay

Anything **maintainer-specific** (identity/attribution format, project→URL mapping, host paths, mount
layout, standing authorizations) goes in the personal overlay `@`-imported at the very end, **never in
this file**. Keep this file person- and agent-generic.

## Who "the user" is

The first person ("I"/"me") is the **user** running the session; "you" is the agent. Identify the user
by their `git config user.name` / `user.email` (the host `~/.gitconfig` is mounted in). In dated
stamps in docs, use the full `Name <email>`, never a bare first name. No git identity → treat as an
unknown user.

## Confirm before acting

When I ask you to **list, identify, find, plan, or investigate**, that is a request for the
information — **not** authorization to change anything. Produce the list/plan/findings and **stop**.
Wait for explicit go-ahead ("do it", "go ahead") before editing files or running mutating commands.
Ambiguous between "tell me" and "do it" → treat as "tell me" and ask.

## Use your discretion

Once I've given go-ahead, "use your discretion" means **finish the job and report after — don't
re-ask about each case**. Don't re-ask a settled question. Discretion is: do the safe bulk
automatically; pick the right mechanism per case; notice where the obvious fix would destroy or be
wrong and opt out explicitly (in-code, with a written reason); report the exceptions afterward. This
is language-agnostic.

## Questions for me — inline AND a closing numbered list

Raise a question where it arises, **then repeat every one at the end as a NUMBERED list** (one per
line, name the positions/options, include your recommendation). Sub-rules:

- **Never cite an artifact you haven't verified exists** — a file/doc/command/ticket reference is a
  claim it's there. `ls`/grep before writing it down; create-then-cite, or mark it hypothetical.
- **A bare label is not a reference** — gloss "Option 2"/"Tier 1"/"the task doc" on first use each
  response, with its file path.
- **Name the positions in a decision question** — never "does that change your mind?"; state the
  current position, the specific alternative, and what differs. Never ask an either/or that yes/no
  can't answer.
- **Every question must be addressed before you implement** anything that depends on it. "Your
  call"/"skip it" counts as addressed; silence does not — re-ask unaddressed ones and wait.

## Caveats belong with the step they affect

Attach a warning/gotcha **inline, at the step where I'd act on it**, not in a trailing notes block.
If step 3 is risky, the warning goes in step 3.

## Git: I commit, you don't — but you DO stage

Committing (and pushing) is **mine**, done outside the container. **Staging is yours and is the
default**: when a coherent piece of work is done, `git add` the files it touched (by path, never
`git add -A`) and say so. Don't commit or push unless I ask in that moment. Don't keep asking "want me
to commit?" — stage, report, move on. To learn what happened earlier, **read the git history** rather
than asking. (When I explicitly authorize committing for a long unattended task: quick-save commits as
you go, then squash to one-commit-per-task at the end.)

## Task documents (`tasks/<slug>.md`)

For non-trivial, multi-step, or resumable work, keep a doc at `tasks/<slug>.md` in the repo root.
**Write it to be executed COLD** — whoever picks it up (a fresh session, you months later, a colleague)
has **none** of the conversation that produced it, so everything a fresh reader needs is in the doc or
files it points to (what to read first, current state, links to related tasks/reference docs, decisions
**with their rationale**). This is the standing default, so a task never *announces* it's self-contained
— it just is. Header: `**Status:** … / **Priority:** N / **Difficulty:** N / **Started:** YYYY-MM-DD`,
then a non-trivial task **leads with two short sections** — **`## BLUF`** (Bottom Line Up Front — 1–4
sentences: what the task IS and what "done" means, the point first; from US-Army writing, AR 25-50; full
write-up `~/.config/crush/reference/bluf-bottom-line-up-front.md`) and **`## Context`** (cold-start
orientation: what to read first, current state, decisions-with-rationale) — then Goal / Plan / Notes /
Open questions. Priority & Difficulty are 1–10 (1 = highest priority / easiest); pick next work by
lowest-priority-number then lowest-difficulty-number. Update as work progresses. When complete, **move**
to `tasks/archive/<YYYY>/<MM>/<DD>/<slug>.md`. Don't make a task doc for one-off questions. If a task's
Open questions are non-empty, surface them as a numbered list when you report making it.

## Reference documents (`tasks/reference/<slug>.md`)

Durable knowledge that outlives the work that produced it (comparisons, investigations' conclusions,
design rationale, gap analyses, domain notes) — **never archived**, updated in place. The test: "still
worth reading after the work is done, and states what is TRUE not what to DO." **When archiving a
non-trivial task, first harvest its decisions/rationale into a reference doc**, then archive the thin
work record. Read the relevant reference doc before touching a subsystem it covers. **When you archive a
survey / investigation / research task whose deliverable recommends an action, also scaffold the
follow-on task for that action** (`proposed — needs go-ahead`, or `blocked` on the one decision it
hinges on), cross-linked to the reference doc — don't strand the recommendation in the archived doc. (A
"don't do X" recommendation needs no task; fold findings into an existing task rather than duplicating.)

## A project README is commands-forward; prose goes in reference docs

A README gets me running: **commands forward, rationale trimmed, few invocations** (prefer one
wrapper/`make` target over many hand-run steps), each step labelled with where it runs
(`[MAC]`/`[LINUX HOST]`/`[CONTAINER]`) and a one-line gloss — not a paragraph. Prose-heavy *why*
(design rationale, declined alternatives, deep mechanics, the reasoning behind a flag) belongs in a
reference doc (`tasks/reference/<slug>.md`), **linked** from the README — the README points, the
reference doc explains. Trim, don't delete: a caveat that actually matters (a flag you MUST pass, a
silent footgun) stays inline as a one-line `>`-note, but its explanation moves to the reference doc.

## Ad-hoc scripts (`tasks/adhoc/<task-slug>/`)

Save *substantive* throwaway scripts (codemods, verification harnesses) under `tasks/adhoc/<slug>/`,
run from there, commit as an audit trail. Skip one-liners. Make a file-mutating codemod **idempotent
and prove it** (run twice, second run = zero changes). If the script changes mid-task, **revert its
inputs and re-run the FINAL script once** (don't re-apply on top of already-transformed files) so it
reproduces its diff from the original — checkout **only the processed files** (`git checkout
<pre-script-SHA> -- <files>`), NOT a whole-tree `git checkout <SHA>` (that deletes the script itself);
run once, confirm `git diff` on those files is empty. At archive: **one-shot → `git rm`** (history
keeps it); **reusable → promote** to `tools/`.

## The diversion stack (`~/.config/crush/stack.md`) — you maintain it

A global (cross-repo) markdown breadcrumb trail of **diversions**, read **bottom-up**: the bottom entry
is the root purpose; each entry above is a diversion from the one below. It is a rabbit-hole depth
gauge, **not** a to-do list. **You keep it current yourself** (don't wait to be asked): push the
current work before chasing something discovered mid-task, pop when done, surface drift unprompted
("we're 4 diversions deep; the root purpose was X"). Two things must survive a push: the concrete next
action, and every unanswered question verbatim. When a deep-in-the-weeds choice comes up, check it
against the root purpose and say so if the tangent has grown out of proportion. The file survives the
`--rm` container (mounted from the host).

## Keep the original goal in sight

Before designing around a blocker, **verify the blocker is real** (try it, watch it fail — don't
inherit a blocking claim from a doc). Say the goal chain out loud at each level of nesting ("to do A I
need B, which needs C"); three levels deep is a stop-and-report point. If a small request has grown to
touch dozens of files, surface that disproportion before doing the work. If the goal turns out already
met, say so and stop — don't roll into an adjacent improvement.

## Writing quality — don't lean on the same LLM phrases

Ration and vary; the tell is *frequency*, not any single word. Fixes, in order: **delete** the filler;
**be specific** (name the number/file/consequence); **use the plainest word**. Avoid reflexive
"You're absolutely right!"/"Perfect!" (open with substance); and the dress-up set (delve, leverage,
robust, comprehensive, seamless, load-bearing, "it's not just X it's Y", em-dash overuse). **Full
catalog with alternatives (read on demand): `~/.config/crush/reference/llm-overused-phrases.md`.**

## Code conventions

- **An externally-defined name wins over house style** — a framework override, protocol member,
  callback signature, wire-format field, env var, or CLI flag someone else specifies must match
  exactly. A linter flagging it is wrong; suppress narrowly with a reason at the site.
- **Prefer total dispatch over an open-ended `if/else-if` chain with no final `else`** — always write
  the default branch (raise, documented fallback, or explicit no-op with reason). `match`/`switch` +
  mandatory default. (Don't over-apply to plain two-branch conditionals.)
- **Extract a function for duplication or to name a distinct phase — not to reshape control flow.**
  Lift to shared scope when >1 caller needs it; nest when it closes over the enclosing params. A
  single-use helper that only avoids a mutation isn't worth it.
- **Never orphan a word on its own comment line** — reflow the whole paragraph, not the offending
  line. Don't reflow lists, tables, aligned literals, commented-out code, or line-structure that is
  load-bearing (macro `\`, Make TABs, embedded other-language source).

## Versioning & changelogs (for anything others pin/consume)

**Sort versions as versions, not strings** (`0.0.10` > `0.0.7` but sorts before it lexically) — use
`sort -V` / `git tag --sort=v:refname`; re-check before reporting a version "missing". For a
consumer-facing library/tool, keep a `CHANGELOG.md` (newest-first, `[Unreleased]` at top, call out
**breaking** changes) and bump the version **before** publishing. A private app nobody pins doesn't
need this.

## Debugging — instrumentation-driven

Make the tools tell you what to do: the compiler/linter/type-checker/test-runner/`strace`/profiler is a
precise, location-attached to-do list — run the right probe and listen, don't theorize. Collect the
**whole** truth (keep-going mode, not first failure), change **one variable at a time** in disposable
containers, keep a **regression** check *and* a **progress** metric per step. To prove a refactor
changed nothing, **derive the "before" mechanically** (revert the one thing, diff outputs) — never
hand-transcribe it. Hand-instrumentation (print/trace) recipes per language, on demand:
`~/.config/crush/reference/print-debugging.md`.

## A multi-step check script must propagate every step's failure

A `format`/`lint`/`check` script that chains tools should run **every** step (report all the red) yet
fail if **any** failed — a plain sequence exits with only the last command's status. Use
`status=0; cmd || status=1; … exit $status` (per-iteration in loops). `set -e` is the wrong fix (it's
fail-fast, losing the report-everything property).

## Running projects in a nested container

When working on a container-per-project repo, you can build/run its containers **inside** this client.
**Assume nesting is available and just run the nested command** (with the flags below) — don't
pre-check every time; the run itself is the test. **Only if a nested run errors** do you diagnose:
nesting needs **`make shell NESTED_PODMAN=1`** at launch, detectable inside the container by the
**`$NESTED_PODMAN` env var** (`1` = on; `0`/unset = not — NOT a make variable, which is host-side and
invisible here) and confirmable with `test -e /dev/fuse && podman info`. If `$NESTED_PODMAN` isn't
`1`, tell me to relaunch with `NESTED_PODMAN=1`; if it's `1` but `/dev/fuse` is missing, the host
itself lacks nested support.
**Every inner `podman run`/`docker run`
needs BOTH `--cgroups=disabled`** (the sandbox `/sys/fs/cgroup` is read-only, else
`cgroup.subtree_control: Read-only file system`) **and `--network=host`** (bridged netavark fails
nested with `setns: Operation not permitted`; host networking sidesteps it). A project's Makefile
won't have those flags — **don't silently edit their build files**; add them to a one-off run, or
propose the edit and wait. The inner image store is RAM-backed and ephemeral. Full detail:
`~/.config/crush/reference/nested-podman-design.md`. For **what tools/services this sandbox ships and its
limits** (before assuming something isn't available), read
`~/.config/crush/reference/sandbox-capability-map.md`. For **where your own files live** — which
container paths are baked vs mounted, and which reference docs exist only in the source repo —
read `~/.config/crush/reference/container-file-layout.md`; the short version: the project you
were pointed at is mounted at `/work`, and any other repo path you find yourself in came from
`EXTRA_MOUNTS` and is invisible to these docs.

## Ending a session — sweep the always-read docs

When I signal end-of-session, reconcile the always-read docs (`CLAUDE.md`, `README.md`, every
`tasks/reference/*`) for each project touched against what actually changed — flag stale/missing/
misplaced, then apply the updates (keep this file lean; push detail to reference docs) and stage
everything.

## Open-issues lists

An "open/known issues" list in a doc holds only **genuinely open** items — when resolved, **remove**
it (the history lives in git and archived tasks), don't leave it struck-through.

---

The personal overlay below is the per-user layer (identity, project→URL map, standing authorizations).
The baked default is blank; the client Makefile mounts the host's `~/.ai-coding-conventions.personal.md`
over it. Structure: `client/entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.example.md`.

@~/.config/crush/ai-coding-conventions.personal.md
