# Bulk operations: shell-first discovery → data-file worklog → iterate → verify

**Status:** complete
**Completed:** 2026-09-18
Created 2026-09-18 (William Emerison Six <billsix@gmail.com>).

## What this did

Added a convention for **bulk operations** (find many instances, then fix each) to the Crush agent's
baked conventions: discover with one shell command (`rg -n` / `git grep -n`), log the matches to a
committed data file as a worklog, save the discovery command as `discover.sh`, fix each match by content
or marker (not saved line numbers), and verify by re-grep = zero. The motivation: the local model's
small context window should not be spent reading files one by one when one `rg` call returns only the
hits. Coordinated with the runClaude sibling, runClaudeInContainer
`tasks/archive/2026/09/18/bulk-ops-shell-first-discovery.md`, which carries the shared cross-project
copy; this repo carries the Crush-flavoured one.

## What changed

1. `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, "Ad-hoc scripts" section: a bulk-op paragraph
   (shell-first discovery, `discover.sh` + `tasks/adhoc/<slug>/data/` worklog, content-matching fix,
   idempotency optional, POSIX-sh portability note).
2. New baked reference doc `client/entrypoint/dotfiles/.config/crush/reference/bulk-edit-shell-first.md`
   (delivered at `~/.config/crush/reference/`, cited from the baked CLAUDE.md): the discovery /
   apply / worklog-iteration / verify idioms, the gotchas, and the sources from the 2026-09-18 web
   research.

The baked files are `COPY`'d into the image, so they reach the agent after a `make -C client image`.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-09-18)

1. **Data-file location:** per-slug `tasks/adhoc/<slug>/data/`, removed with the script at archive.
2. **The worklog is the point; idempotency is a nice-to-have, not required.** Content/marker matching
   and bottom-up processing stay as correctness advice (don't edit the wrong line via a stale offset).
   The data file is a snapshot worklog, never a line-number replay driver.
3. **Reference-doc home:** a new focused doc in the baked set, not `tasks/reference/` (which holds docs
   *about* runCrush) and not a copy of the fuller ported doc.
4. **Scope:** the baked convention layer, since it directs how the agent develops any project.

Tensions resolved in the text: a bulk discovery command is substantive (its output drove the diff), so
it is exempt from "skip one-liners"; the run-twice idempotency proof applies to a scripted codemod, while
a judgment-driven worklog pass is audited by `discover.sh` + data file + diff; the three artifacts per
bulk task live in one slug dir and are removed together.

## Verification

Checked at implementation: Crush's bash tool runs an embedded POSIX-sh interpreter
(`internal/shellconfig/load.go` in the Crush source), not zsh, so the doc says "keep commands
POSIX-portable" instead of carrying runClaude's zsh `bash -c` wrapping rule. `ripgrep`, `gawk`, `perl`,
`sed` and findutils are in `client/entrypoint/01-install-base.sh`.
