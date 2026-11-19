# Trim the always-loaded context files (done)

**Done:** 2026-11-18 (William Emerison Six <billsix@gmail.com>). Spans three repos: this one,
github.com/billsix/runClaudeInContainer, and github.com/billsix/dotfiles (the personal overlay).

The always-loaded conventions layer (cross-project conventions, `@`-imported reference docs, the
personal overlay) is paid on every turn of every session, in both sandboxes. How Crush assembles it,
and how to measure it: `tasks/reference/crush-context-assembly.md`.

## What was done

- **Lever 1 (2026-09-13/14):** per-project `CLAUDE.md` trims in every repo; work record
  `tasks/archive/2026/09/14/trim-claude-md.md` here, and the same in each project repo.
- **Decision 1 (2026-09-14):** runClaude's conventions `CLAUDE.md` condensed 133.5 KB → 49.9 KB
  (−63%). Every rule stayed inline; rationale and examples moved verbatim into 10 topic reference
  docs plus `print-debugging.md`. runCrush's baked conventions were already the lean port then.
- **Decision 2 (2026-09-14):** the five `@`-imported reference docs in runClaude's conventions became
  triggered read-on-demand pointers (~18.5K tok/session), as Crush already did.
- **Decision 3 (2026-11-18):** parked by the maintainer on 2026-09-14, un-parked after
  `tools/measure_context.py` showed the overlay had grown from 32 KB to 66.7 KB
  (`tasks/archive/2026/11/18/measure-preseeded-context.md`). The overlay's "My project layout (the
  container-per-project template)" section (59 KB, ~14.7K tok) moved verbatim to a new dotfiles file,
  `.ai-coding-conventions.personal.template.md`. The overlay keeps a one-paragraph summary and a
  trigger saying when to read it (creating, conforming or reviewing a project's container files, or
  when a new project is mounted). The `client/Makefile` here and runClaude's `Makefile` touch and
  mount host `~/.ai-coding-conventions.personal.template.md` beside the overlay (`~/.config/crush/`
  and `~/.claude/`); it is not `@`-imported. Both `FORKING.md` files and runClaude's conventions
  "My project layout" section name the new file.

## Result

`python3 tools/measure_context.py --overlay <dotfiles overlay>`: the Crush global layer went from
44,799 to **30,237 tokens (68% → 46% of the 65,536 window)**; the overlay from 16,681 to 2,118
tokens. Claude Code sessions drop the same ~14.6K. The largest remaining sections are the baked
conventions' "Code conventions" (2,436 tok) and a handful near 1K, listed in the measure task's
recommendation 2 (not done; no task yet).

**Host step the change needs:** copy both dotfiles files to the host home
(`~/.ai-coding-conventions.personal.md` and `~/.ai-coding-conventions.personal.template.md`) and
relaunch the sandbox. Until then the Makefiles mount an empty template file.
