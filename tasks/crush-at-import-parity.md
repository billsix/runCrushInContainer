# Bring the Crush `@`-import patch to full Claude-Code parity

**Status:** proposed — follow-up to the MVP patch; needs go-ahead
**Priority:** 6
**Difficulty:** 4
**Started:** 2026-08-19

## Relationship / origin

Follow-up to `tasks/patch-crush-for-at-imports.md`, which delivered a **working MVP** `@`-import
patch for Crush (`client/patches/crush-at-import.patch`, against `CRUSH_TAG` v0.89.0). The MVP was
scoped deliberately (decision 2026-08-19: MVP now, parity later). This task closes the gap between
that MVP and Claude Code's actual `@`-import semantics — only if/when the gap matters in practice.

## Goal

Extend the MVP splice (`expandContextImports` in `internal/agent/prompt/prompt.go`) so its behavior
matches Claude Code's `@`-import closely enough that a conventions file authored for Claude Code
behaves identically under patched Crush — then regenerate the patch file and its tests.

## Parity gaps to close (from the MVP's recorded scope reductions)

- [ ] **`$VAR` / `$(cmd)` expansion in import paths.** MVP expands `~` only. Wire the import-path
      resolution through Crush's existing `expandPath` (`prompt.go:139`, which uses
      `store.Resolver()`), so `@$SOMEDIR/x.md` resolves. Cost: `processFile` currently has no
      `ConfigStore` — either thread `store` into `processFile`/`processContextPath` (small
      signature change, 2 call sites) or resolve at a layer that has it. Weigh the patch-size
      increase against real need.
- [ ] **Confirm Claude's exact line/inline rules** and match them: does Claude allow trailing text
      after `@path` on the same line? multiple `@refs` per line? `@` escaped as `\@` or inside
      fenced code blocks / inline code spans (Claude skips code spans)? The MVP matches only a
      whole-line `@path`; verify whether Claude is looser and decide whether to widen.
- [ ] **Duplicate-import policy.** MVP leaves a second import of the same file (within one chain)
      literal via the visited-set. Confirm Claude imports-once vs. imports-each-occurrence and match.
- [ ] **Missing-target policy.** MVP leaves the literal `@path`. Confirm that matches Claude (it
      appears to) and keep, or change if Claude drops/warns.
- [ ] **Depth-cap parity.** MVP caps at 5 hops. Confirm Claude's actual cap (~5) and align the
      constant + behavior at the boundary.

## Method

Same as the MVP task: modify the crush clone, extend `at_import_test.go` with parity fixtures
(escapes, code spans, `$VAR`, multi-ref lines), `go test` + `go build`, `git commit`, then
`git format-patch <CRUSH_TAG>` to **replace** `client/patches/crush-at-import.patch`. Re-verify the
patch `git am`s cleanly onto a fresh checkout. Update `tasks/reference/crush-capabilities.md` if the
semantics change.

## Open questions

1. **Is parity even needed, or is the MVP enough?** The MVP already handles the real runCrushInContainer
   case (`~`-rooted whole-line imports). Recommend **deferring this task until a concrete conventions
   file actually trips an MVP limitation** — parity for its own sake is low-value churn on a patch we
   must re-apply every Crush bump. Do this only when a real file needs it.
