# Patch Crush to recursively splice `@`-imports in context files

**Status:** in-progress (kept open per maintainer, 2026-08-20) — patch delivered, wired into the
image build, and nested-build-verified. **Held open until the remaining checks are done:** (1) a
live end-to-end Crush session splicing a real `@ref.md` against the Mac's llama-server (needs the
Mac + tunnel), and (2) a full default-flags `make image` gate (only the isolated build stanza was
exercised here). Parity gaps tracked in `tasks/crush-at-import-parity.md`.
**Priority:** 5
**Difficulty:** 5
**Started:** 2026-08-19 · **MVP delivered:** 2026-08-19

**Decisions (2026-08-19, William Emerison Six <billsix@gmail.com>):** (1) build the **MVP**
`@`-import (line-anchored, relative-to-file, 5-hop cap + cycle guard, silent-skip on missing);
**at the end of this task, create a follow-up task for strict Claude parity** →
`tasks/crush-at-import-parity.md`. (2) Start the investigation now (clone/modify/commit permission
granted).

**Implementation notes / deliberate MVP scope reductions (parity task tracks these):**
- **`~` expanded, `$VAR` NOT** — real `@`-imports use `~` (e.g. `@~/.config/crush/reference/x.md`),
  so `home.Long()` covers the actual case; `$VAR`/`$(cmd)` expansion (which Crush's `expandPath`
  does for context *paths*) was left out to keep the patch tiny and dependency-free (`processFile`
  has no `ConfigStore`). Parity item.
- **Missing/unreadable target left as literal text** (not removed) — matches Claude and is
  non-destructive; "silent-skip" resolved to "keep the literal line."
- **Same file imported twice in one chain → second stays literal** (the visited-set dedups within a
  chain). Acceptable; note for parity.

## Relationship to the main port task

Child of `tasks/port-runclaude-conventions-systems.md`. That task works *around* Crush's
missing `@`-import by registering each reference doc / the personal overlay as a
**global-context-path** (verified as the native replacement). **This task is the alternative:
patch Crush itself so a `@path` written inside a loaded `CLAUDE.md`/`AGENTS.md` is expanded
recursively — restoring the exact Claude-Code authoring model.** If this patch lands and proves
maintainable, it becomes the preferred delivery mechanism (the conventions body can `@`-import
its reference docs the same way runClaudeInContainer's does, a near-verbatim port); if it proves
too costly to carry across Crush versions, the main task's global-context-path approach stands as
the fallback. The two are mutually exclusive *for delivery* but both can coexist in the plan until
this investigation resolves which we use.

Background facts (verified, do not re-derive): `tasks/reference/crush-capabilities.md`, finding 2
— Crush `v0.89.0` `processFile` (`internal/agent/prompt/prompt.go:99`) is a bare `os.ReadFile`
with no `@` scanning; context files are spliced into the system prompt via `data.ContextFiles`.

## Goal

Produce a **`git format-patch` patch file** (committed at `client/patches/`) that, applied with
`git am` at image-build time against the pinned Crush tag, makes Crush recursively read and splice
`@path` references found inside its loaded context files — and a clear writeup of how hard it was,
how faithful to Claude's semantics it is, and the cross-version maintenance cost.

**Definition of done:** (a) the patch applies cleanly to `CRUSH_TAG` (v0.89.0), (b) a patched
build demonstrably splices an `@sub.md` reference into the assembled prompt, (c) the patch lives in
the repo and the Dockerfile change to `git am` it is drafted (not necessarily merged), (d) this doc
records the difficulty verdict + the re-verify-on-bump procedure.

## VERDICT (2026-08-19): easy patch, low code-risk, ongoing cost is re-apply-on-bump

**It was easy.** The whole feature is ~50 lines in one function's neighborhood. Crush routes
every context file through a single reader, `processFile` (`internal/agent/prompt/prompt.go:99`),
whose `.Content` is spliced into the system-prompt template with no transformation in between —
so one helper called from there covers all context files (`CLAUDE.md`/`AGENTS.md`/`CRUSH.md`,
`.cursor/rules/`, global context paths) uniformly. Patch: **prompt.go +55 lines** (one import +
`expandContextImports` helper + a call in `processFile`), plus a **119-line test**. Total
`173 insertions, 1 deletion`, 2 files.

**Verified:**
- New unit tests (recursion, relative-to-file resolution, cycle guard, missing-target &
  mid-line-`@mention` left literal, depth cap) — **pass**; full `internal/agent/prompt` package —
  **no regressions**; whole binary **builds** (`crush version v0.89.0+dirty`, Go 1.26.5).
- **Patch re-applies cleanly:** `git am client/patches/crush-at-import.patch` onto a fresh
  `v0.89.0` checkout applied with no fuzz, and the feature test passed there.
- The unit test is at the authoritative layer — `processFile` is the sole producer of every
  `ContextFile`; nothing rewrites its output before the template prints `.Content`. A live
  Crush-session eyeball (a real `~/.config/crush/CLAUDE.md` with `@ref.md`) is deferred until the
  Mac endpoint is up — cheap to add, not required to trust the result.

**Deliverable:** `client/patches/crush-at-import.patch` (commit `051a535` on the crush clone,
`git format-patch v0.89.0`). Applied at image build with `git am`.

**License:** Crush is **FSL-1.1-MIT** (Functional Source License 1.1, converts to MIT after 2
years). It permits use/modification/redistribution for any non-"Competing Use"; using Crush as our
own coding tool and carrying a local patch is within the grant, and the patch distributes only our
~50-line diff. (Engineering read, not legal advice.)

**Cost is maintenance, not code.** The one recurring tax is re-applying across Crush version bumps
(see "Re-verify on `CRUSH_TAG` bump"). Risk is low: the patched function is small and stable, and
the change is additive (a helper + one call site) so a refactor would have to move `processFile`
itself to break the hunk.

**Recommendation:** worth adopting as the delivery mechanism for the main port — it restores the
verbatim Claude authoring model. Keep the main task's global-context-path approach documented as
the zero-maintenance fallback in case a future Crush refactor makes the patch expensive to carry.

### Dockerfile wiring — DONE and verified (2026-08-20)

Merged into `client/Dockerfile` + `client/Makefile`, gated on **`CRUSH_AT_IMPORT`** (Dockerfile
ARG defaults `0` = stock, so a bare `podman build` stays lean; Makefile defaults `1`, so `make
image` applies the patch). The patched path clones the tag, `git apply`s the patch (not `git am` —
no committer identity needed in the build), and `go install`s from source with a `-ldflags -X
…internal/version.Version=$CRUSH_TAG` stamp so `crush --version` still reports the tag.
`make image CRUSH_AT_IMPORT=0` builds stock upstream Crush.

**Verified (nested podman):** a throwaway image mirroring the exact `CRUSH_AT_IMPORT=1` stanza on a
clean `fedora:44` **built successfully**, and because the `RUN` executes `go test
./internal/agent/prompt/ -run TestAtImport` under `set -e` *before* `crush --version`, the green
build proves the shipped binary's `@`-import tests pass. `make -n image` confirms the build args.
(A full `make image` — the 22.3 GB toolchain image — was not re-run for this one stanza; the
isolated build exercises the only new step. The reference-doc RAM-store caveat still applies to the
full build.)

**Cosmetic note:** the patched binary reports `crush version v0.89.0+dirty` — the `+dirty` is Go's
build-VCS stamp flagging the `git apply`-modified tree; it is honest (the tree *is* patched). To get
a clean `v0.89.0`, either commit the patch in the clone (`git am`, needs a build-time git identity)
or add `-buildvcs=false`. Left as-is: `+dirty` usefully signals "this Crush carries the local patch."

### The drafted stanza (as merged)

The current build cannot be patched — `go install …@tag` pulls a read-only module from the proxy.
A patched build must build from a git checkout instead. Gated on a build arg so the unpatched path
still works:

```dockerfile
ARG CRUSH_TAG=v0.89.0
ARG CRUSH_AT_IMPORT=1          # 0 = stock upstream build (go install), 1 = apply the @-import patch
ENV GOBIN=/usr/local/bin GOFLAGS=-trimpath
COPY patches/ /patches/
RUN set -eux; \
    if [ "$CRUSH_AT_IMPORT" = "1" ]; then \
        git clone --depth 1 --branch "$CRUSH_TAG" https://github.com/charmbracelet/crush /tmp/crush; \
        git -C /tmp/crush am /patches/crush-at-import.patch; \
        ( cd /tmp/crush && go install ./... ); \
        rm -rf /tmp/crush; \
    else \
        go install "github.com/charmbracelet/crush@${CRUSH_TAG}"; \
    fi; \
    crush --version
```

(`git am` needs a committer identity in the build env, or use `git apply` instead of `git am` to
sidestep that — `git apply /patches/crush-at-import.patch` applies the diff without making a commit,
which is simpler for a Dockerfile. Switch the draft to `git apply` if we don't care about preserving
the commit in the image.)

### Re-verify on `CRUSH_TAG` bump (maintenance procedure)

When `client/Makefile`'s `CRUSH_TAG` changes: (1) `git clone --branch <newtag>` + `git am
client/patches/crush-at-import.patch`; (2) if it applies, `go test ./internal/agent/prompt/ -run
TestAtImport` + `go build ./` — if green, regenerate the patch against the new tag and update
`crush-capabilities.md`'s banner; (3) if `git am` FAILS to apply, `processFile`/`processContextPath`
moved — re-locate the splice point, re-apply the ~50-line change by hand, re-run the tests, and
`git format-patch <newtag>` to replace the patch file. This mirrors the versioned-dependency
discipline in `tasks/reference/crush-capabilities.md`.

## Investigation plan

- [x] **Reproduce the build.** `git clone --branch v0.89.0 https://github.com/charmbracelet/crush`,
      `go build ./...` / `go install` (Go 1.26.x, already in the client toolchain). Confirm a clean
      baseline `crush version v0.89.0` before touching anything.
- [x] **Confirm the splice point.** Re-read `internal/agent/prompt/prompt.go` around `processFile`
      (:99) and `processContextPath` (:110), and how `ContextFile.Content` reaches the system-prompt
      template (`promptData` / `data.ContextFiles`, ~:170). Decide the injection layer: expand inside
      `processFile` (simplest — every loaded context file gets expansion) vs. a dedicated pass.
- [x] **Design the `@`-import semantics** (the fiddly part — see Open questions). MVP target:
      - Recognize `@path` at line start (or after leading whitespace); ignore `@` mid-token
        (emails, code). Match Claude's rule closely enough to be unsurprising.
      - Resolve `path` **relative to the importing file's directory** (Claude does this), with `~`
        and `$VAR` expansion to match Crush's existing `expandPath` (`prompt.go:139`).
      - **Recurse** with a **depth cap** (Claude ≈ 5 hops) and a **cycle guard** (a visited-set of
        absolute paths) so `a→b→a` can't loop.
      - Splice the imported content **inline where the `@line` sat** (best matches Claude), or, if
        simpler and acceptable, append imported files as additional `ContextFile`s.
      - Missing import target: skip silently or leave the literal `@path`? (decide — Claude leaves
        it; silent-skip is safer for a splice.)
- [x] **Implement** the smallest change that satisfies the above. Keep it self-contained (one helper
      + a call site) so the patch is small and survives minor upstream drift.
- [x] **Verify at the prompt-assembly layer, not via a full model round-trip.** A live Crush session
      needs the Mac's llama-server; instead prove it cheaply: a Go unit test (or a tiny debug harness)
      that calls the context-loading path on a fixture `CLAUDE.md` containing `@sub.md` and asserts
      `sub.md`'s text appears in the assembled `ContextFiles`/system prompt. Add a nested `@a→@b`
      fixture to exercise recursion + the cycle guard. (If Crush exposes a prompt-dump/debug flag, use
      that as a second check.)
- [x] **Commit on the clone** (authorized: a commit the maintainer did not make), then
      `git format-patch v0.89.0 --stdout > client/patches/crush-at-import.patch` (or a numbered
      series). Verify `git am` re-applies it cleanly onto a fresh v0.89.0 checkout.
- [x] **Draft the Dockerfile switch.** The current step `go install github.com/charmbracelet/crush@${CRUSH_TAG}`
      pulls from the module proxy and **cannot be patched** — a patched build must instead
      `git clone --branch ${CRUSH_TAG} … && git -C crush am /patches/*.patch && go install ./...`
      (or `go build`). Draft this as an *optional* path (e.g. gated so an unpatched build still works),
      don't silently rewrite the working build.
- [x] **Write the verdict:** how many lines the patch touches, how brittle it is to upstream refactors,
      and the **re-verify-on-bump** procedure (mirrors the versioned-dependency discipline: on any
      `CRUSH_TAG` change, re-`git am` onto the new tag, rebuild, re-run the fixture test; if it fails
      to apply, the splice point moved — re-locate and regenerate the patch).

## Risks / things to watch (inline, at the step they bite)

- **The proxy-vs-source build switch is mandatory for patching** (see the Dockerfile step) — this is
  a real change to a *working* v1 build, so it needs its own go-ahead and a fallback to the unpatched
  path.
- **Cross-version fragility is the main cost, not the code.** A ~30-line splice is easy; keeping it
  applying across a fast-moving young project is the recurring tax. The verdict must weigh this
  honestly against the zero-maintenance global-context-path workaround.
- **Semantics divergence:** if the patch's `@`-rules differ from Claude's, a conventions file authored
  for Claude Code could splice differently here — aim to match, and document any divergence in
  `crush-capabilities.md`.
- **License check:** confirm Crush's license permits building a locally-modified binary and shipping a
  patch (a patch file distributes only our diff, not Crush's source — low risk, but verify before
  committing the approach). Charm projects are typically FSL/MIT-family; confirm the actual `LICENSE`
  at v0.89.0.
- **Upstream option:** the feature may be PR-able to Crush (or already on their roadmap — `docs/*/FUTURE.md`
  mentions hook `context_files`). Note whether upstreaming is worth pursuing so we're not carrying a
  fork forever.

## Open questions

All resolved. (1) **MVP** chosen, parity deferred to `tasks/crush-at-import-parity.md`;
(2) investigation done; (3) Dockerfile wiring merged behind `CRUSH_AT_IMPORT` (default on via
`make`) and nested-build-verified 2026-08-20. Nothing blocking.

Remaining, non-blocking: a live end-to-end eyeball (a real `~/.config/crush/CLAUDE.md` with an
`@ref.md`, driven by an actual Crush session) once the Mac's llama-server + tunnel are up — the
code path is already proven at the unit + clean-build level, so this is confirmation, not a gate.
