# Apply the naming and scope rules, per language (Python, bash)

**Status:** proposed — needs go-ahead
**Priority:** 7 (a readability sweep with no deadline)
**Difficulty:** 5 (33 tracked files in the languages below; the judgment is in which leads to leave alone)
**Created:** 2026-11-25 (William Emerison Six <billsix@gmail.com>: "make a task in all of my repos for my projects in /mnt/sda1 to apply them, per language", and the same day "make a task for all of them, but only start work on hanoi and spimulator").
**Source:** github.com/billsix/towersofhanoi `tasks/apply-naming-and-scope-rules-per-language-across-repositories.md` (the fleet task that wrote this one).

## BLUF

Five naming and scope rules are written for every language in the shared coding standards. This task applies them to the code in github.com/billsix/runCrushInContainer that the maintainer wrote: survey for leads, apply by discretion, record what was left alone and why, and pass the repository's own gate. Done means each language in the table has been surveyed and either changed or recorded as left alone, with the gate green.

## Context

**The five rules:** inline a binding used once (a comment above the expression names it); a binding used twice does not automatically earn a name; declare a name at the point of use; nest a helper with one caller inside that caller, where the language has a nested function; shadow deliberately when nesting, where the language allows it. Each language's standard says how the rule reads there and which bindings must stay.

**Languages here** (tracked files, counted 2026-11-25 with `git ls-files`; paths matching `elpa/|/imgui/|doctest/|vendor|third_party|node_modules|^builddir/` left out; a `.h` file counts as C even in a C++ tree):

| Language | Files | Where (top-level directory, files) | Section in github.com/billsix/runClaudeInContainer `tasks/reference/` | What differs from Python |
|---|---|---|---|---|
| Python | 16 | `tasks` 7, `tools` 5, `client` 3, `server` 1 | `python-coding-standard.md`, "Inline a value used once…" and "What earns an extraction" | the baseline; `nest_one_caller.py --dry-run` lists and then nests the one-caller helpers |
| bash | 17 | `client` 10, `tools` 4, `tasks` 3 | `shell-and-gate-scripts.md`, "Names and scope in bash" | rule 4 does not apply (functions are global); `local` at the point of use |

**Read first:** this repository's `CLAUDE.md` if it has one (its gate, its vendored and generated trees, whose code each tree is), then the standard's section for each language above.

**Whose code.** The cross-project rule is to sweep code the maintainer wrote and to leave another author's code alone: book examples, a game's original source, a vendored library and generated files are out of scope even when tracked. The first plan step settles this per tree.

**The pattern to copy** is the Python batch of 2026-11-25, github.com/billsix/towersofhanoi `tasks/archive/2026/11/25/apply-2026-11-06-naming-and-scope-rules.md`: it surveyed first, applied by discretion, left GUI and GL construction blocks and tests alone, kept helpers that a test imports or that name a step of a teaching method, and recorded each group it left with the reason.

**The survey tool.** `python3 ~/.claude/reference/survey_names_and_scope.py [--language rust] [--exclude REGEX]` (canonical in github.com/billsix/runClaudeInContainer `tasks/reference/`; Crush: `~/.config/crush/reference/`) lists functions named exactly twice and locals named exactly twice inside their function, for Rust, C++, C, Haskell, bash and JavaScript. Its counts are textual: a callback passed by name, a trait method and a name repeated in a comment are miscounted, so read every lead. For Python, `python3 ~/.claude/reference/nest_one_caller.py --dry-run FILE ...` lists the one-caller helpers and why it would skip each.

## Plan

- [ ] Settle scope: list the trees that are the maintainer's own code, and write the excluded ones here with the reason.
- [ ] Per language: run the survey, save its output under `tasks/adhoc/apply-naming-and-scope-rules-per-language/data/`, and read the leads.
- [ ] Per language: apply the rules by discretion, one commit-sized unit per language, keeping the bindings the standard lists (guards and RAII objects, out-parameter targets, values read before their source changes, calls made for a side effect, test inputs and case tables, names that carry the lesson in teaching code).
- [ ] Run the formatter on the changed files only, then the repository's gate (format, type-check or build, tests), and record the result.
- [ ] Write the done-record: what changed, what was left alone and why, per language.

## Open questions

None recorded. Scope (the first plan step) is the executor's call under the whose-code rule; ask only if a tree's authorship is unclear.
