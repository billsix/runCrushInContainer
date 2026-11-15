# Patch Crush to recursively splice `@`-imports in context files

**Status:** complete
**Started:** 2026-08-19 · **MVP delivered:** 2026-08-19 · **Completed:** 2026-08-21

Wrote a local Crush patch, `client/patches/crush-at-import.patch`, that makes Crush recursively
splice `@path` references found inside its loaded context files (`CLAUDE.md`/`AGENTS.md`/`CRUSH.md`,
`.cursor/rules/`, global context paths), restoring the Claude-Code authoring model. Wired it into the
image build behind `CRUSH_AT_IMPORT` and verified it by unit tests, a clean nested build, and a live
end-to-end run against the model. Parity gaps with Claude are tracked in
`tasks/crush-at-import-parity.md`.

## Background

Child of `tasks/port-runclaude-conventions-systems.md`, which worked around Crush's missing
`@`-import by registering each reference doc as a global context path. This task was the alternative
(patch Crush itself); the global-context-path approach stays documented as the zero-maintenance
fallback if a future Crush refactor makes the patch expensive to carry. Verified fact
(`tasks/reference/crush-capabilities.md`, finding 2): at `v0.89.0`, `processFile` in
`internal/agent/prompt/prompt.go` is a bare `os.ReadFile` with no `@` scanning, and its `.Content`
reaches the system-prompt template via `data.ContextFiles` untransformed.

## Decisions (2026-08-19, William Emerison Six <billsix@gmail.com>)

1. Build the **MVP** `@`-import (line-anchored, relative-to-file, 5-hop cap + cycle guard), and create
   a follow-up task for strict Claude parity (`tasks/crush-at-import-parity.md`).
2. Start the investigation immediately (clone/modify/commit on the Crush clone authorized).

MVP semantics and deliberate scope reductions (the parity task tracks them):

- `@path` is recognized at line start (after optional whitespace); a mid-line `@mention` (emails,
  code) stays literal. Paths resolve relative to the importing file's directory.
- **`~` expanded, `$VAR` not.** Real imports use `~` (`@~/.config/crush/reference/x.md`), so
  `home.Long()` covers the actual case; `$VAR`/`$(cmd)` expansion (which Crush's `expandPath` does for
  context paths) was left out because `processFile` has no `ConfigStore`.
- **A missing or unreadable target stays as literal text**, matching Claude and non-destructive.
- **A file imported twice in one chain**: the second occurrence stays literal (the visited set dedups).
- Expansion lives inside `processFile`, so every context file gets it uniformly.

## What was done

- **The patch**: `prompt.go` +55 lines (one import, an `expandContextImports` helper, one call in
  `processFile`) plus a 119-line test; 173 insertions, 1 deletion, 2 files. Produced from commit
  `051a535` on the Crush clone with `git format-patch v0.89.0`.
- **Dockerfile wiring (2026-08-20)**: in `client/Dockerfile` + `client/Makefile`, gated on
  `CRUSH_AT_IMPORT` (Dockerfile ARG default `0` = stock, Makefile default `1`). Patching requires
  building from a git checkout, since `go install …@tag` pulls a read-only module from the proxy. The
  patched path clones the tag, `git apply`s the patch (not `git am`, which would need a committer
  identity in the build), runs `go test ./internal/agent/prompt/ -run TestAtImport` under `set -e`, and
  `go install`s with `-ldflags -X …internal/version.Version=$CRUSH_TAG` so `crush --version` reports
  the tag. `make image CRUSH_AT_IMPORT=0` builds stock upstream Crush.
- **Kept the `+dirty` version suffix**: the patched binary reports `crush version v0.89.0+dirty` (Go's
  build-VCS stamp on the `git apply`-modified tree). Left as-is because it honestly signals the local
  patch; `-buildvcs=false` or a build-time `git am` would remove it.

## Verdict

Easy patch, low code risk; the ongoing cost is re-applying across Crush version bumps. The change is
additive (a helper plus one call site in a small, stable function), so only a refactor that moves
`processFile` itself would break the hunk. License: Crush is **FSL-1.1-MIT**, which permits
modification and redistribution for non-"Competing Use"; using Crush as our own tool and shipping only
our diff is within the grant (engineering read, not legal advice). Whether to upstream the feature was
not pursued.

## Verification

- Unit tests (recursion, relative resolution, cycle guard, missing target and mid-line `@` left
  literal, depth cap) passed; the full `internal/agent/prompt` package had no regressions; the binary
  built (Go 1.26.5).
- `git am client/patches/crush-at-import.patch` onto a fresh `v0.89.0` checkout applied with no fuzz,
  and the feature test passed there.
- A throwaway nested image mirroring the `CRUSH_AT_IMPORT=1` stanza on clean `fedora:44` built
  successfully, which proves the shipped binary's `@`-import tests pass. `make -n image` confirmed the
  build args. The full 22.3 GB `make image` was not re-run for this one stanza.
- **Live end-to-end (2026-08-21)**: a real `CLAUDE.md` containing `@secret.md` was spliced in, and
  `crush run` against the live model returned the import-only secret (PASS). The one-shot harness
  (`tools/at-import-live-test/`: `CLAUDE.md`, `secret.md`, `run-live-test.sh`) was later removed from
  the tree; it is recoverable from commit `0f9548f`.

## Re-verify on a `CRUSH_TAG` bump

1. `git clone --branch <newtag>` and `git am client/patches/crush-at-import.patch`.
2. If it applies: `go test ./internal/agent/prompt/ -run TestAtImport` and `go build ./`; if green,
   regenerate the patch against the new tag and update `tasks/reference/crush-capabilities.md`'s
   banner.
3. If it fails to apply, `processFile`/`processContextPath` moved: re-locate the splice point, re-apply
   the ~50-line change by hand, re-run the tests, and `git format-patch <newtag>` to replace the file.
4. Optional live re-check: recover the harness with `git show 0f9548f:tools/at-import-live-test/run-live-test.sh`
   and run it on the host with the server and tunnel up.
