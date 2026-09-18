# Bulk operations: shell-first discovery → data-file worklog → iterate → verify

**Status:** ready — decisions taken 2026-09-18; implementation awaits go-ahead
**Priority:** 3
**Difficulty:** 4
Created 2026-09-18 (William Emerison Six <billsix@gmail.com>).

> **Decisions (William Emerison Six <billsix@gmail.com>, 2026-09-18):**
> 1. Data-file location: **per-slug `tasks/adhoc/<slug>/data/`** (removed with the script).
> 2. **The primary purpose is the worklog** — a list to iterate over so the model isn't reading
>    every file front-to-back to decide what to do next. **Idempotency is a nice-to-have, NOT
>    required.** Content/marker-matching and bottom-up processing stay as *correctness* advice (don't
>    edit the wrong line via a stale offset), not an idempotence mandate. The data file is a
>    snapshot/audit worklog, never a line-number replay driver.
> 3. Reference-doc home: **new focused `tasks/reference/bulk-edit-shell-first.md`** (this repo has no
>    shell doc), NOT the fuller ported doc.
> 4. Scope: this is the Crush agent's baked convention layer — it directs how the agent develops any
>    project, which is the point of the image (coordinated with the runClaude sibling task).

## BLUF

Add a convention: when a task is a **bulk operation** (find many instances of something, then fix
each), the first move is a **Linux shell discovery command** (`rg` / `git grep` / `grep -Rn`) that
logs the matches to a committed **data file**, followed by an **iterate-and-fix** pass and a
**re-grep verification** — instead of defaulting to a Python ad-hoc script that walks the tree
blindly. Motivation is concrete and citable: the local coding model here (Muse Glimmer 30B) has a
**small context window** (nested `CLAUDE.md:4–6`), so it should not spend that budget reading files
one-by-one to find matches when one `rg` call returns just the hits. "Done" = the nested `CLAUDE.md`
ad-hoc section is amended and a new reference doc carries the idioms, with the skip-one-liner and
idempotence/stale-line tensions resolved in-text. **Coordinate with the sibling runClaude task**
(`runClaudeInContainer` `tasks/bulk-ops-shell-first-discovery.md`) so the two repos' wording matches
— that repo carries the shared cross-project copy; this repo carries the Crush-flavored copy.

## Context (cold-start)

**The existing ad-hoc-script convention** here lives in ONE place (verified 2026-09-18): the
baked/nested `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, "## Ad-hoc scripts
(`tasks/adhoc/<task-slug>/`)", **lines 195–214** — the file delivered into a Crush session. The root
`CLAUDE.md` and `README.md` do NOT restate it. This repo has **no** `shell-and-gate-scripts.md`
reference doc, and `tasks/reference/python-coding-standard.md` is Python-style only (one `pathlib`
mention, nothing on shell tools) — so the reference-doc side is greenfield.

The existing section already: saves substantive scripts under `tasks/adhoc/<slug>/`; **skips
one-liners** (`:197`, verbatim: *"Skip one-liners."*); requires codemods **idempotent, proven by
run-twice → zero changes** (`:198`); sanctions writing outputs/logs **under the repo** (`:197–198`);
and states the three-commit lifecycle + `.keep` rule (`:204–214`). The multi-step-failure-propagation
rule (`status=0; cmd || status=1; exit $status`, never `set -e`) is at `CLAUDE.md:292–296`.

**Repo mount fact:** the project is at **`/work`** (`container-file-layout.md:29`; `-v $(PROJECT):/work`),
and any other repo path came from `EXTRA_MOUNTS` and is "invisible to these docs" (`:31–34`) — which is
exactly why saved shell commands must be repo-root/`/work`-relative, never `/foo/opt/...`.

**Tooling guaranteed present** (`client/entrypoint/01-install-base.sh`): `ripgrep` (`rg`, :361),
plus `gawk`/`perl`/`sed`/findutils; the minimal install even notes *"Crush's grep tool shells out to
`rg`"* (`00-install-minimal.sh:38`). Linux/GNU only, so GNU idioms are fine (note BSD-`sed` in one
line for copy-paste safety).

> **Verify before writing the reference doc:** does the Crush agent's shell tool run through **zsh**
> (like runClaude's Bash tool) or bash? If zsh, the reference doc must carry the `bash -c '…'`
> wrapping rule for glob/`[[ ]]`/heredoc-bearing discovery commands. Check the client image's login
> shell; don't assume.

## The convention to add

Same workflow as the runClaude task (do not let the two drift): **discover with a shell tool → log
matches to a committed data file (a snapshot worklog, not a replay input) → save the discovery
command as `discover.sh` → iterate-and-fix matching on content/marker (not saved line numbers),
bottom-up if line count changes → verify by re-grep = zero matches.**

### Edit 1 — nested `CLAUDE.md:195–214` (terse rule, ~3–4 lines)

Add after the "Skip one-liners" sentence, and amend it:

> **Bulk op (find-many → fix-each)? Discover with a shell tool, don't tree-walk in Python** — one
> `rg -n`/`git grep -n` returns just the matches instead of spending the model's small context
> reading files. Log them to `tasks/adhoc/<slug>/data/` (a committed *snapshot* worklog, git-rm'd
> with the script) and save the discovery command as `discover.sh` — a bulk discovery command IS
> substantive (its output drove the diff), so it's exempt from "skip one-liners". The fix matches on
> **content/marker, not saved line numbers** (they rot as edits shift lines — a correctness measure,
> not an idempotence mandate); process bottom-up if it changes line count. The worklog exists so the
> model works a list instead of reading every file front-to-back; idempotency is a bonus, not
> required. Verify by re-grep = zero.

### Edit 2 — new reference doc `tasks/reference/bulk-edit-shell-first.md`

Create it (this repo has no shell reference doc). Contents = the idiom appendix below + the tension
resolutions + the repo-root/`/work`-relative rule + (if the shell is zsh) the `bash -c` wrapping
rule. Give `tasks/reference/` a `.keep` if missing. Optionally add a one-line read-on-demand pointer
where the nested `CLAUDE.md` indexes its reference docs.

## Tensions to resolve IN THE TEXT

Identical to the runClaude task — resolve all of these in the amended wording:
1. **"Skip one-liners" (`:197`) vs saving `discover.sh`** — carve the exception: an exploratory
   one-liner is skipped, but a bulk operation's discovery command (with a committed data file) is
   substantive and saved.
2. **Stale line numbers vs "idempotent, prove run-twice → zero" (`:198`)** — the data file is a
   snapshot/audit worklog, never the driver; the fix re-derives location by content/marker or
   processes bottom-up. (Mirrors the repo's own "cite by stable anchor, never a line number — they
   rot" LoD rule.)
3. **Idempotence is OPT-IN, not mandatory** (2026-09-18 decision) — the worklog's job is to give the
   model a list to iterate, so a bulk fix need not be idempotent; keep the run-twice proof welcome
   where a fix happens to be a clean codemod, and keep content/marker-matching as *correctness*
   advice (don't edit the wrong line via a stale offset). Say so, so a reader doesn't think it's
   required.
4. **Don't over-apply the "reproduce diff from original" proof (`:198`)** — that's for a scripted
   codemod; when the workflow is "iterate the worklog and fix each by judgment," the audit trail is
   `discover.sh` + the data file + the diff. Where a fix IS a codemod, the data file should be
   regenerable via `discover.sh`.
5. **Clutter** — three artifacts per bulk task (`discover.sh` + `data/` + fix) are justified as the
   mechanical "how" behind a large diff; keep them in one slug dir, removed together at archive.

## Lifecycle fit

Data file rides **commit 2** (work + adhoc) beside `discover.sh` and the fix script; **`git rm`'d in
commit 3** (archive) with the slug dir. If the fix is promoted to `tools/`, the one-shot data file is
**not** promoted — delete it. `.keep` rule unaffected.

## Idiom appendix (fold into the new reference doc; web research 2026-09-18, sources at end)

**Discovery** — `rg -n --column 'PAT' src/` (`file:line:col:text`); `rg --vimgrep` for exactly one
row per match; `rg -l` filenames-only; `rg --json` structured. `git grep -n 'PAT' -- '*.py'` for
tracked-files-only (no gitignore blind spot). Reusable-script guard: `command -v rg || …grep -R
fallback`. NUL-safe: `grep -rlZ … | xargs -0`, `find … -print0 | xargs -0`, `rg -0 -l`.

**Stale line numbers** — bottom-up when line count changes: `grep -n 'PAT' f | sort -t: -k1,1 -rn |
while IFS=: read -r n _; do sed -i "${n}s/old/new/" f; done` (`tac` is the base primitive). Preferred
— match by content, no saved offset: `sed -i 's/exact_old/new/' f` or `sed -i '/anchor/s/old/new/'
f`. Idempotent: anchor to a field that stops matching (`sed -i 's/^\(version:\).*/\1 2/' f`); guard
`grep -q 'PAT' f && sed -i …`; beware `s/foo/foobar/g` re-matching.

**Applying edits** — `sed -i` (GNU here; BSD needs `-i ''`, moot on Linux). Multi-line →
`perl -0777 -pi -e 's/old/new/gs' f`. Field/column → `gawk -i inplace '{…}' f`. `find … -exec cmd
{} +` batches like `xargs -0`. Greedy trap: use `[^>]*`, not `.*` (sed has no `.*?`).

**Worklog / iterate** — `while IFS= read -r line; do …; done < matches.txt` (`IFS=` keeps
whitespace, `-r` keeps backslashes, **redirect from file** so counters survive the subshell; `< <(cmd)`
to consume a command; `|| [ -n "$line" ]` for a last unterminated line). Resume: move done rows to
`matches.done.txt`, remaining = `grep -vFf matches.done.txt matches.txt`.

**Verify** — `rg -l 'PAT' src/` empty = clean; before/after `rg -c 'PAT' src/` + `diff`; `git diff
-U0` for tight review (catches greedy over-match).

**Gotchas** — skip binaries (`grep -I`; rg default); prefer plain `find` over `find -L` for a source
sweep (symlink-loop slowness); `LC_ALL=C` = byte-wise (fast/safe for pure-ASCII, wrong for
Unicode-sensitive edits); never `grep … f | sed -i … f` on one file in a single pipeline — two
phases.

## Sources (from the 2026-09-18 web research; include the ones the reference doc leans on)

ripgrep man/README (`--vimgrep`, `--json`, gitignore behavior, `-uuu`); git-grep docs (tracked-only);
GNU grep manual (`-Z`, `-I`, `--binary-files`); sed GNU-vs-BSD `-i` trap write-ups; "Better sed with
perl" / multiline-search-replace (`perl -0777 -pi -e`); GNU awk inplace extension; BashFAQ/001
(`while IFS= read -r`, pipe-subshell pitfall); find `-exec +` vs `xargs -0`; sed locale
considerations (`LC_ALL=C`); non-greedy-in-sed (`[^X]*`). (Full URL list in the runClaude sibling
task's idiom appendix — reproduce the subset the doc actually cites.)

## Open questions

None — all resolved in the Decisions block at the top (2026-09-18): per-slug data dir; worklog-first
with idempotency optional; new focused `bulk-edit-shell-first.md`. One thing to **verify at
execution** (not a user decision): whether the Crush agent's shell tool runs through zsh (→ include
the `bash -c` wrapping rule) or bash. Implementation awaits a go-ahead.
