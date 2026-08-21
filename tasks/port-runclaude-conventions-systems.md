# Port the runClaudeInContainer conventions systems into runCrushInContainer

**Status:** Phases 0–4 IMPLEMENTED (2026-08-21); **Testing phase deferred** by maintainer — task
stays OPEN until the end-to-end test is run. Phases 0–2 live-verified on the real model; Phases 3
(slash commands) + 4 (Makefile polish) built and parse-checked. Note (2026-08-21): custom commands
appear under the `/` dialog's **"User" tab** (press `Tab`), and only after `make image` bakes them. Decisions: stack → **mounted host path**; delivery → **`@`-import**
(the patch works, so near-verbatim port); conventions **trimmed to a lean core** to fit the local
32k/64k window.
**Priority:** 4
**Difficulty:** 5
**Started:** 2026-08-18 · **Researched:** 2026-08-19 · **Phases 0–2:** 2026-08-21

## Implementation of Phases 0–2 (2026-08-21)

Delivery uses the **`@`-import patch** (now proven working), so the port is near-verbatim to
runClaudeInContainer: bake `CLAUDE.md` at `~/.config/crush/CLAUDE.md`, register it as the **one**
`option global-context-path` in `crushrc`, and let its `@`-import lines pull in the reference docs +
personal overlay. Verified by a `processFile` test on the real baked file — the `CLAUDE.md` body +
the personal overlay splice in, no literal `@`-lines left.

**Trim for the local-model context (2026-08-21):** the first cut ported the conventions verbatim →
~131 KB / ~32k tokens, which **overflowed the 32k server window** (a live `crush run` errored at ~50k
tokens = conventions + Crush's own ~18k-token system prompt/tools). Fixed two ways: (1) rewrote
`CLAUDE.md` as a **lean core** — the essential *rules* only (~11.5 KB / ~2.9k tokens), with the heavy
overused-phrases catalog and print-debugging recipes kept **baked but referenced on-demand**, not
`@`-imported; only the small personal overlay stays `@`-imported. (2) Raised the server window
`CTX 32768 → 65536` (+ matching crushrc `--context-window`) for working headroom. Net: always-loaded
conventions dropped ~11× and now fit with room for real work. See
`tasks/archive/2026/08/20/context-window-sizing.md` for the two-limit background.

- **P0.1/P0.2 (delivery):** `client/entrypoint/dotfiles/.config/crush/CLAUDE.md` baked to
  `/root/.config/crush/CLAUDE.md` (via the existing dotfiles `COPY`); `crushrc` registers it with
  `option global-context-path /root/.config/crush/CLAUDE.md`. **Deviation from the plan:** one
  global-context-path (the CLAUDE.md) + `@`-imports inside it, NOT one per doc — cleaner and matches
  the original's authoring style, enabled by the patch.
- **P1.1 (conventions body):** copied runClaudeInContainer's shared `CLAUDE.md` and adapted — fixed all
  `~/.claude/` → `~/.config/crush/` paths, rewrote the "Auto-imported references" section for Crush's
  mechanism, fixed the personal-overlay path/example. **Cut three sandbox-specific sections** that
  don't apply to the Crush client: "Running projects in a nested container", "The Bash tool runs
  through zsh", "Verification gates in nested containers". *(Residual: a few worked-example prose bits
  still say "runClaudeInContainer … mounted by the Makefile" — harmless, could be curated later.)*
- **P1.2 (reference docs):** **three** baked at `~/.config/crush/reference/` (agent-readable
  on-demand): `llm-overused-phrases.md`, `print-debugging.md` (2026-08-21), and
  **`sandbox-capability-map.md`** (adapted 2026-08-21 — the toolchain is byte-identical, so the
  inventory is valid; GUI/controller passthrough + nested specifics adjusted for the client).
  `nested-podman-design.md` was **ported as a project reference doc** in `tasks/reference/` (adapted).
  `claude-config-layering.md` (P1.3) is **not** ported — Crush's config model is already in
  `crush-capabilities.md` + `architecture.md`; a dedicated `crush-config-layering.md` remains optional
  (not written).
- **P1.4 (personal overlay):** blank `ai-coding-conventions.personal.md` + `.example.md` baked;
  Makefile mounts host `~/.ai-coding-conventions.personal.md` over the blank (unconditional + auto-touch).
- **P2.1/P2.2 (task + reference doc systems):** described in the conventions body; already in active use.
- **P2.3 (diversion stack):** **mounted host path** — `~/.config/crush/stack.md` on the host, mounted
  to `/root/.config/crush/stack.md` (Makefile, unconditional + mkdir/touch so it survives `--rm`). The
  conventions body references that path.
- **P2.4 (git-identity exports): SKIPPED** per maintainer (Crush doesn't need `CLAUDE_USER_*`).

Verified in-sandbox: `processFile` splices the `@`-imports; `crush models` loads the crushrc with the
`global-context-path` cleanly; `make -n shell` renders the personal-overlay + stack mounts.
**LIVE-VERIFIED end-to-end 2026-08-21** (real model, `CTX=65536`): a `crush run` answered with facts
that exist *only* in the loaded conventions — the diversion-stack path `~/.config/crush/stack.md` and
the "Confirm before acting" rule (list/find = information-only, wait for go-ahead). Conventions bake →
load → fit → steer the model. Phases 0–2 complete.

**Phases 3–4 (2026-08-21).** Slash commands: ported all 7
(`client/entrypoint/dotfiles/.config/crush/commands/`) — stripped the YAML frontmatter (Crush would
send it as literal text), renamed `$ARGUMENTS` → named tokens (`$SLUG` for new-task/new-reference/
archive-task, `$DIVERSION` for stack-push, `$ENTRY` for stack-drop; `stack`/`stack-pop` take none),
and fixed `~/.claude/` → `~/.config/crush/` (incl. the stack path). Baked via the dotfiles `COPY` to
`/root/.config/crush/commands/`. **Caveats (P3.4):** Crush commands are triggered by typing `/` in the
**interactive TUI** (not `crush run`); args are entered in a **dialog** and are **required** (no
`$ARGUMENTS` catch-all), so `stack-drop`'s formerly-optional arg is now a required `$ENTRY` (type a
number or "top"). They're **shortcuts** — the conventions already drive these behaviors autonomously.
Makefile (Phase 4): `image-export`/`image-import` targets + `client/crushcontainer-*.tar` gitignored;
`make format` + `client/entrypoint/format.sh` (shfmt, accumulate-status). P4.1 mounts were already
done; **P4.4 (nested-podman) — initially skipped, then implemented 2026-08-21** (the skip was wrong:
the client is a full dev sandbox and projects build/run nested) — see
`tasks/add-nested-podman-to-client.md`.

## Goal

Take as much of the runClaudeInContainer "working-method" machinery as possible —
task docs, reference docs, the diversion stack, the personal-overlay layering, the slash
commands, and the conventions body itself — and reimplement it for Crush, so this repo is a
first-class member of the same template family. The v1 bring-up deliberately shipped none of
it (`tasks/archive/2026/08/19/crush-local-llm-bringup.md`); this is that follow-up.

This plan is built on a **verified** Crush capability map:
`tasks/reference/crush-capabilities.md` (Crush `v0.89.0`, code-checked). Read that first —
it is what makes each "port action" below concrete rather than a guess.

## The one architectural decision everything hangs on

runClaudeInContainer delivers ALL its value through two Claude-Code features: **auto-loading
`~/.claude/CLAUDE.md`** and **recursive `@`-import** (which pulls the 5 reference docs + the
personal overlay into every session). Crush **has the first and lacks the second** (verified —
see the reference doc's finding 2). So the port's spine is:

- **Conventions body** → baked into the image at **`~/.config/crush/CLAUDE.md`** and registered
  as a **global context path** (`option global-context-path ~/.config/crush/CLAUDE.md`). Naming
  it `CLAUDE.md` matches the runClaudeInContainer family; putting it at the *global* path (not at
  the project cwd) means it loads no matter which dir Crush starts in, **and** a mounted project's
  own `/work/CLAUDE.md` still auto-loads on top of it — the two stack, mirroring the original's
  global-conventions + repo-`CLAUDE.md` split. *Verified nuance:* `CLAUDE.md` is auto-loaded from
  the **cwd** (`config.go:32`), but the **global** auto-defaults are only `CRUSH.md`/`AGENTS.md`
  (`load.go:548`) — so `~/.config/crush/CLAUDE.md` is NOT auto-loaded and DOES need the explicit
  `global-context-path` line. That one line is the whole cost.
- **Reference docs + personal overlay** (the `@`-import replacement) → registered as **global
  context paths** in `crushrc` (`option global-context-path /abs/path` per file). Crush loads and
  splices each into the system prompt — the same always-in-context effect, just explicit instead
  of `@`-import syntax. This is the single most important porting move; get it right first.

**Recommendation (Q1 below):** conventions body at `~/.config/crush/CLAUDE.md` + one
`global-context-path` line per always-loaded doc. Alternative considered — bake the conventions
at `/work/CLAUDE.md` (cwd, auto-loaded with zero config) — rejected: `/work` is the *mounted
user project*, so our file would either not be there or fight the project's own `CLAUDE.md`.
Alternative considered — concatenate everything into one big file at build time — rejected: it
destroys the shared-vs-personal file split and makes the personal overlay un-mountable per-user.

## Ordered port plan

Ordered by (a) dependency — the delivery mechanism must exist before content lands on it — then
(b) value × ease. Phases 0–2 are the bulk of the value and are almost entirely generic
markdown/shell; phase 3 needs the Crush command rewrite; phase 4 is container plumbing.

Feature IDs (F1–F43) reference the full inventory captured during research (kept in this doc's
history / the session that created it); each line says what it is and the concrete Crush action.

### Phase 0 — Delivery mechanism (unblocks everything) — Difficulty 3

- [x] **P0.1 Bake the conventions file.** Create `client/entrypoint/CLAUDE.md`, COPY it into the
      image at `/root/.config/crush/CLAUDE.md`, and register it with `option global-context-path
      /root/.config/crush/CLAUDE.md` in `crushrc` (required — the global auto-defaults are only
      `CRUSH.md`/`AGENTS.md`, so a `CLAUDE.md` there is not picked up without the line). This
      leaves the cwd `CLAUDE.md` slot free for a mounted project's own file, which stacks on top.
      *Verified:* `config.go:32` (cwd `CLAUDE.md`), `load.go:548` (global defaults).
- [x] **P0.2 Stand up the global-context-path delivery.** In `client/entrypoint/crushrc`, add one
      `option global-context-path /root/.config/crush/reference/<doc>.md` line per always-loaded
      doc, plus one for the personal overlay (same mechanism as P0.1). Bake the docs into the image
      under that dir. This replaces `@`-import (F19). *Verified:* `load.go:548`, extendable list.

### Phase 1 — The conventions content + reference docs (highest value, generic) — Difficulty 4

- [x] **P1.1 Port the conventions body (F18).** Adapt runClaudeInContainer's shared
      `.claude/CLAUDE.md` into `client/entrypoint/CLAUDE.md` (baked to
      `~/.config/crush/CLAUDE.md`). The *content* is agent-agnostic engineering/writing
      discipline and ports as-is; edit only the Claude-Code-specific delivery notes (the
      "Auto-imported references" section, `@`-import mentions, `~/.claude` paths, `/audit-repo`
      references) to describe Crush's mechanisms. Keep the opening "SHARED layer — personal goes
      in the overlay" instruction (F10) so the split stays self-maintaining.
- [x] **P1.2 Port the generic reference docs (F6) — DONE.** `llm-overused-phrases.md`,
      `print-debugging.md`, and `sandbox-capability-map.md` (adapted) baked at
      `~/.config/crush/reference/` (agent-readable on-demand); `nested-podman-design.md` ported to
      `tasks/reference/` as a project doc. See the Implementation summary for the per-doc detail.
- [ ] **P1.3 Config-layering doc — NOT ported (optional).** `claude-config-layering.md` is entirely
      about Claude Code's auth/config files, so it's not copied; a dedicated
      `tasks/reference/crush-config-layering.md` covering the *mount/bake* layering was judged optional
      (Crush's config model is already in `crush-capabilities.md` + `architecture.md`). Left unchecked
      as a deliberate skip, not a TODO.
- [x] **P1.4 Personal-overlay split (F9/F10).** Ship a **blank**
      `client/entrypoint/ai-coding-conventions.personal.md` baked into the image, register it as a
      global-context-path, and mount the host's `~/.ai-coding-conventions.personal.md` over it in
      the client `Makefile` (auto-`touch` if absent — the mount is unconditional so the context
      path always resolves). Add a `.personal.example.md` template + note it in a fork guide.
      *Note:* no `@`-import needed — it's just another context path, arguably cleaner than the
      Claude version.

### Phase 2 — The file-based systems (generic markdown conventions) — Difficulty 2

These are pure filing conventions; most are *described in the conventions body* (P1.1) and just
need their directories + the wording to point at Crush paths. The repo already has
`tasks/reference/` (from bring-up), so the reference-doc convention is half-present.

- [x] **P2.1 Task-doc system (F1–F4):** `tasks/<slug>.md` with Priority/Difficulty header,
      `tasks/archive/YYYY/MM/DD/`, `tasks/adhoc/<slug>/`. Pure files; already partly in use.
- [x] **P2.2 Reference-doc system (F5, F7):** `tasks/reference/` + the "harvest durable knowledge
      on archive" discipline. Already seeded (`architecture.md`, `crush-capabilities.md`).
- [x] **P2.3 Diversion stack (F8):** a plain-markdown stack file, read bottom-up. Retarget
      `~/.claude/stack.md` → a fixed Crush path (recommend `~/.config/crush/stack.md`, or a
      repo-agnostic host path mounted in). The *autonomous-maintenance* behavior rides on the
      conventions body (P1.1), so it works as soon as Crush loads `CRUSH.md`.
- [x] **P2.4 `CLAUDE_USER_NAME`/`EMAIL` from git config (F11):** port the `.extrabashrc` exports
      so per-session attribution works. Generic shell.

### Phase 3 — Slash commands (needs the Crush command rewrite) — Difficulty 4

Port the 7 commands (F12–F18) from `.claude/commands/*.md` to Crush's command dir
(`~/.config/crush/commands/`, baked into the image at `/root/.config/crush/commands/`). Per
`crush-capabilities.md` finding 3, each port =:

1. **Drop the YAML frontmatter** (`description:`/`argument-hint:` — Crush doesn't parse it; it
   would reach the model as literal text). Fold the description into a plain first line.
2. **Rename `$ARGUMENTS` → a named `$UPPERCASE` token** (e.g. `$SLUG`) — Crush auto-detects it as
   a required arg and prompts for it. Filename becomes the command name.
3. Keep the numbered procedure body as-is (it's just prompt text the agent follows).

- [x] **P3.1** `/new-task` (F12), `/new-reference` (F13) — straightforward `$SLUG` rewrites.
- [x] **P3.2** `/archive-task` (F14) — the richest; keep the harvest-to-reference + adhoc-triage
      steps.
- [x] **P3.3** `/stack`, `/stack-push`, `/stack-pop`, `/stack-drop` (F15–F18) — retarget the
      stack path to P2.3's choice.
- [x] **P3.4** Note the **behavior gap:** Crush prompts for required args in a dialog and has no
      `$ARGUMENTS` catch-all — a command that took free-form multi-word input (`/stack-push <what
      we divert to>`) becomes a single prompted `$DESCRIPTION` field. Acceptable; document it.

### Phase 4 — Container / Makefile machinery (generic podman/shell) — Difficulty 3

Mostly already present in `client/` (bring-up) or directly reusable from runClaudeInContainer.

- [x] **P4.1 Mounts:** add the personal-overlay mount (P1.4) and conditional host-config mounts
      (`~/.gitconfig`, `~/.tmux.conf`) via the `readlink -f` + existence-test idiom (F25). Keep
      the existing `--network=host` + `--security-opt label=disable`.
- [x] **P4.2 image-export / image-import (F23):** add the timestamped `podman save`/`load` target
      pair; gitignore `*.tar`.
- [x] **P4.3 format gate (F22):** a `make format` running `shfmt` over `entrypoint/*.sh` + the
      multi-step-failure-propagation shape.
- [x] **P4.4 nested-podman flags (F24) — DONE 2026-08-21** (the initial "skip" was wrong; the client
      is a full dev sandbox and projects build/run nested). `make shell NESTED_PODMAN=1` now works;
      full implementation + rationale: `tasks/add-nested-podman-to-client.md`.

### Phase T — Testing (run at the end, on the real setup)

Do these once, on the Linux host with the Mac server + SSH tunnel up. Rebuild first so everything
bakes in: **`cd client && make image`** (bakes the lean conventions, the reference docs, the 7
commands, the updated crushrc), and **`[MAC] make serve`** at `CTX=65536`.

- [ ] **Conventions load + steer (re-confirm the full set):** `make shell` → `crush run -q "Per your
      loaded conventions: where is the diversion stack kept, and can you make changes on a 'list'/'find'
      request?"` — expect `~/.config/crush/stack.md` + "no, info-only". (Passed 2026-08-21 for the lean
      core; re-run after any convention edit.)
- [ ] **No context overflow:** the above should NOT error with "exceeds context size". If it does, the
      conventions grew — trim, or raise `CTX`.
- [ ] **Slash commands appear:** in the TUI (`crush`, not `crush run`), type `/` — **the dialog opens on
      the "System" tab; press `Tab` to reach the "User" tab** where our 7 custom commands live
      (`new-task`, … `stack-drop`), prefixed `user:`. **GOTCHA:** the User tab only shows once the
      commands are baked — rebuild (`make image`) first, or you'll see only System commands. (Verified in
      source: `internal/ui/dialog/commands.go:34-36` System/User/MCP tabs; `:263` hides the tab selector
      when there are no user commands.)
- [ ] **A command with an arg runs:** `/new-task` → the dialog prompts for `$SLUG` → it scaffolds
      `tasks/<slug>.md`. Try `/stack-push` (prompts `$DIVERSION`) and `/stack` (no prompt, prints the
      stack).
- [ ] **Stack persists across `--rm`:** push something with `/stack-push`, exit the container, `make
      shell` again, `/stack` — the entry is still there (it's mounted from host `~/.config/crush/stack.md`).
- [ ] **Personal overlay:** put a line in host `~/.ai-coding-conventions.personal.md`, `make shell`,
      and confirm the agent knows it (it's `@`-imported into the conventions).
- [ ] **Makefile polish:** `make format` runs shfmt clean; `make image-export` writes a tar (gitignored)
      and `make image-import FILE=…` loads it.

### Phase 5 — Explicitly NOT ported (record, don't build)

- **Auth/persistence (F35–F40):** Crush's endpoint is a local, keyless llama-server behind SSH —
  no OAuth, no onboarding state, no `~/.claude.json` analogue. Drop all of it. Keep only the
  *pattern* "add `-e VAR` only when the host var is exported" if a token env var is ever needed.
- **Cross-session memory:** Crush has no analogue (reference doc). Not wanted.
- **User-defined named sub-agents:** Crush hardcodes `coder`+`task`; no `.claude/agents/*.md`
  port. Sub-agent *delegation* still works via the `agent` tool.

## What NOT to port (unchanged from the original task)

Auth plumbing (`~/.claude`/`~/.claude.json` mounts, `CLAUDE_CODE_OAUTH_TOKEN` passthrough) and
anything Claude-Code-binary-specific. See Phase 5.

## Notes / decisions

- **Delivery via `global-context-path`, not `@`-import** — decided on the research (2026-08-19),
  because Crush has no `@`-import (verified `prompt.go:99`). This is the crux of the whole port.
  **Alternative under investigation:** `tasks/archive/2026/08/21/patch-crush-for-at-imports.md` — patch Crush itself to
  add recursive `@`-splice, delivering a `git am`-able patch. If that lands and proves maintainable,
  `@`-import becomes available and the conventions body can port near-verbatim; global-context-path
  is the fallback if the patch is too costly to carry across Crush versions.
- **Conventions body → `~/.config/crush/CLAUDE.md`** (global, registered via
  `global-context-path`) — decided 2026-08-19. Matches the family naming; stacks with a mounted
  project's own cwd `CLAUDE.md` instead of colliding with it.
- Reference docs: **copy-and-adapt** into this repo, not shared across both repos — the two
  images and two agents differ enough (Q2, decided: copy). Revisit a shared source only if they
  converge.
- Two `CLAUDE.md`-cited commands (`/audit-repo`, `/findings-to-tasks`) have **no definition files**
  in runClaudeInContainer — don't port what isn't there; treat those citations as stale.

## Open questions

1. **Stack-file path — `~/.config/crush/stack.md` vs a mounted host path?** Recommend a **mounted
   host path** so the diversion stack survives the `--rm` container (it's global across repos by
   design); the baked-in default is only a fallback. Which host path do you want?
2. **Scope of this pass — do all of Phases 0–4, or stop after 0–2 (conventions + file systems,
   no commands/plumbing)?** Recommend **0–2 first** (the highest-value, lowest-risk 80%), then
   decide on commands (Phase 3) once the conventions are proven loading in a live Crush session.
