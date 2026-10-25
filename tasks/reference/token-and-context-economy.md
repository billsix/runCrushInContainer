<!-- SHARED, MIRRORED REFERENCE DOC -- keep the runClaudeInContainer and
     runCrushInContainer copies byte-identical. Canonical:
     runClaudeInContainer tasks/reference/token-and-context-economy.md
     (github.com/billsix/runClaudeInContainer). -->

# Token & context economy — what NOT to read, and when NOT to fork

How to not burn tokens. Written 2026-10-25 (William Emerison Six <billsix@gmail.com>) after a long hanoi
session spent ~1M+ tokens on subagents; this records the drivers and the rules that avoid them.

## The two dominant costs (measured, this fleet)

1. **Subagents re-ingest everything.** A **fork inherits the entire conversation transcript** plus the
   always-loaded instruction set; a fresh (non-fork) agent skips the transcript but still pays the
   instruction set. Measured: a single implementation **fork cost ~633K tokens**, and a 3-way audit
   fan-out ~400K — most of it ingest, before any useful work.
2. **The always-loaded instruction set is large and paid EVERY turn AND per subagent.** The mounted
   cross-project `CLAUDE.md` + the personal overlay + `stack.md` + memory total **~25K tokens** here.
   Over dozens of turns that is the floor; every subagent pays it again.

So the single biggest lever is **not spawning subagents you don't need**, followed by **keeping the
always-loaded docs lean**, then **not reading files you don't need to read**.

## When NOT to fork / fan out (the biggest lever)

- **Default to inline.** A fork earns its cost only on **large, independent, build-heavy** work where
  keeping verbose tool output (compiler/build logs) out of the main thread is worth re-ingesting the
  whole conversation. For a **small or presentation-layer task, do it inline** — the fork's re-ingestion
  costs far more than the build-log spam it avoids. (Lesson: forking a small Rust UI task cost more than
  doing it inline would have.)
- **Forking late in a long session is the worst case** — the transcript it inherits is already huge.
  Weigh that before forking the Nth time in a session.
- **Don't fan out N parallel agents when one pass or an inline `grep` would do** — each multiplies the
  instruction + transcript ingest. An audit/fan-out of 3 agents paid the ~25K instruction ingest ×3 on
  top of whole-file reads.
- **If you do spawn, brief tightly with pointers, not context.** A fresh agent needs the goal + the
  file/line pointers + what's already ruled out — not a re-derivation. The tighter the brief, the less it
  reads.

## What NOT to read (and how to read less)

- **Never read vendored / third-party / generated trees you won't edit** — `imgui/`, wxWidgets, SDL, a
  cargo registry, `node_modules`, `build/`/`build-web/`/`target/` output, `*.lock`, generated code. The
  **compiler/build validates them**; reading them to "understand before editing" is pure waste.
- **Don't read a file you're only going to compile, not change.** The build is the check, not your eyes
  — e.g., reviewing a whole C++/Rust source tree before a build you'll run anyway.
- **Need a region, not the file?** `rg -n`/`git grep -n` to the exact spot, then `Read` with
  `offset`/`limit`. Reserve whole-file reads for small files you'll actually edit end-to-end.
- **Don't pull build output into context.** Redirect verbose `cmake`/`cargo`/`emcc`/`make` output to a
  file and inspect the **exit status + a short `tail`**; never cat a full build log. A `make` target that
  rebuilds the image re-runs expensive layers — run the target's own `podman run`/build line against the
  existing image instead (see `nested-run-and-gates.md`).
- **Don't re-read a file you just edited to "confirm" it** — `Edit`/`Write` already error if they didn't
  apply, and the harness tracks file state.
- **Don't re-establish facts already in the conversation** — re-reading a doc or re-deriving a decision
  already made this session is repeated ingest.

## Keep the always-loaded set lean (it taxes every turn AND every subagent)

- Keep the cross-project `CLAUDE.md` terse; push detail to **read-on-demand** reference docs (this doc is
  one). Every inline word is paid every turn and by every fork.
- Keep **`stack.md` a short breadcrumb trail**, never a task log — a bloated stack is re-sent every turn
  and re-ingested by every fork. Reconcile it down at session end.
- Prune stale memory and archived-task detail out of the always-read path.

## Quick self-check before an expensive action

- *About to fork?* Is this big + independent + build-heavy enough that build-log isolation beats
  re-ingesting the whole transcript? If not, inline it.
- *About to `Read` a file?* Will I edit it, or only compile/skim it? Do I need the whole thing or a
  region? Is it vendored/generated (then don't)?
- *About to fan out agents?* Would one pass or a `grep` do?
