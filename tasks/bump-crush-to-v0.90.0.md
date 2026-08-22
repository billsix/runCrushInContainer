# Bump Crush v0.89.0 → v0.90.0 (and re-verify the `@`-import patch)

**Status:** proposed — **BLOCKED on `tasks/vendor-build-sources-for-airgap-rebuild.md`.** Do NOT implement
this bump until the offline/vendoring task is implemented (maintainer, 2026-08-22). Investigation is
complete (the `@`-import patch ports to v0.90.0 unchanged, builds + tests pass), but the actual upgrade is
not done and needs go-ahead **that comes only after offline rebuild works**. `CRUSH_TAG` stays v0.89.0
until then. Nothing in the repo has been changed by this task except this doc.
**Priority:** 4
**Difficulty:** 2
**Started:** 2026-08-22
**Blocked by:** `tasks/vendor-build-sources-for-airgap-rebuild.md` (offline rebuild must land first).

## Goal

Move the client's pinned Crush from **v0.89.0** to the new stable **v0.90.0** (released 2026-08-19),
confirming our local `@`-import patch still ports and works.

## Investigation findings (2026-08-22)

- **New release exists:** `v0.90.0`, published **2026-08-19** (one day after the v0.89.0 pin decision).
  Verified via the GitHub releases API; it is the latest tag.
- **The patch ports with ZERO changes.** `client/patches/crush-at-import.patch` `git apply --check`s
  **clean** against a fresh `v0.90.0` checkout — because `internal/agent/prompt/prompt.go` (the only
  non-test file it touches) is **byte-identical** between v0.89.0 and v0.90.0 (`git diff v0.89.0 v0.90.0
  -- internal/agent/prompt/prompt.go` is empty). No regenerate needed.
- **It builds and tests pass on v0.90.0.** With the patch applied to the v0.90.0 tree:
  - `go build ./...` — **exit 0** (whole binary compiles, not just the prompt package).
  - `go test -run TestAtImport ./internal/agent/prompt/` — **all 5 pass** (Recursive, RelativeToFileDir,
    Cycle, MissingAndMidlineLiteral, DepthCap).
  - (Done in the runClaude sandbox with `GOTOOLCHAIN=auto` — v0.90.0's `go.mod` needs Go ≥1.26.6; the
    sandbox has 1.26.5, so the toolchain was auto-fetched. The client image's own Go is current, so a
    real `make image` build is unaffected.)

Conclusion: the port is a one-line pin bump; the patch is unchanged.

## Plan

- [x] Confirm v0.90.0 is the latest release. *(investigation — done)*
- [x] Confirm the patch applies cleanly + builds + tests pass on v0.90.0 (above). *(investigation — done)*
- [ ] **Bump the pin (NEEDS GO-AHEAD)** — `client/Makefile` `CRUSH_TAG ?= v0.90.0` and `client/Dockerfile`
      `ARG CRUSH_TAG=v0.90.0`.
- [ ] **Update docs that state the current default pin (NEEDS GO-AHEAD)** — `tasks/reference/architecture.md`
      (default `CRUSH_TAG`) and the repo `CLAUDE.md`'s "the pins" description. Leave historical verification
      records (e.g. "verified crush v0.89.0 runs") and archived task logs as-is — they record what was true
      then.
- [ ] **Rebuild + live verify (maintainer, real machine):** `make image` (builds Crush from source at
      v0.90.0 with the patch via `git apply`), then in `make shell` confirm `crush --version` reports
      v0.90.0 and a `@path`-import in a context file still splices live. This is the full "does it work"
      gate; the patch/unit-level test above is already green.
- [ ] **`crush-capabilities.md` re-sync decision (Open question 1):** that doc is a version-pinned map
      "verified against v0.89.0" with a re-sync tripwire ("if `CRUSH_TAG` no longer reads v0.89.0,
      re-clone and re-verify"). The bump fires that tripwire. Decide whether to re-verify the doc against
      v0.90.0 now or defer — left at v0.89.0 for now (not silently rewritten, which would falsely claim
      re-verification).

## Dependency — the airgap-vendoring task must land FIRST (maintainer, 2026-08-22)

This bump is **gated on `tasks/vendor-build-sources-for-airgap-rebuild.md`** — offline rebuild has to
work before we even consider changing the pinned version. The ordering matters for two concrete reasons:

- **Go-toolchain constraint (the decisive one).** v0.90.0's `go.mod` requires **Go ≥1.26.6**; v0.89.0
  does not. The maintainer confirms **the current crush (v0.89.0) compiles with the Go on the airgapped
  system** — so v0.89.0 is a known-good airgap baseline, and bumping to v0.90.0 could break the airgap
  build if that system's Go is < 1.26.6. So: get the offline rebuild solid on v0.89.0 first; only then
  bump — and the bump must separately ensure the airgapped Go can build v0.90.0 (up to vendoring a newer
  Go toolchain), not just that our online sandbox can.
- **Shared build machinery.** The vendoring task reworks the exact Dockerfile lines a bump would touch
  (the `git clone`/`go install` block → extract-from-vendor). Vendoring against the settled current
  version (v0.89.0) avoids re-vendoring churn; `CRUSH_TAG`/`LLAMACPP_TAG` keep their meaning — they become
  "which vendored checkout," not "what to fetch." When this bump is eventually done, it must **re-vendor
  Crush at v0.90.0** (and confirm the Go-toolchain point above).

Net: **vendoring builds/targets v0.89.0; this bump waits until that works, then re-vendors + re-verifies
the Go-toolchain fit at v0.90.0.**

## Open questions

1. **Re-sync `crush-capabilities.md` to v0.90.0 now, or defer?** It's a one-minor-release delta and
   `prompt.go` was unchanged, but the doc covers many features (permissions, hooks, context-window,
   provider discovery) not individually re-checked here. Recommend **defer** to its own task — bumping
   the pin doesn't require the capabilities map to be re-verified in the same change, and the tripwire
   banner already flags it. (This also intersects `tasks/auto-allow-local-file-tools.md`, which will
   re-read the permissions/tool surface anyway — fold the re-sync into that work.)

## Cross-links

- `client/patches/crush-at-import.patch` — the patch (unchanged; applies clean to v0.90.0).
- `tasks/archive/2026/08/21/patch-crush-for-at-imports.md` — the original patch work (the "re-verify on
  every CRUSH_TAG bump" instruction this task satisfies).
- `tasks/crush-at-import-parity.md` — the separate semantics-parity follow-up (its "against v0.89.0"
  wording now also covers v0.90.0, prompt.go being identical).
- `tasks/reference/crush-capabilities.md` — the version-pinned map whose re-sync tripwire this bump
  fires (Open question 1).
