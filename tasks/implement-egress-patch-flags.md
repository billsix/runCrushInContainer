# Implement the egress patch/flag system from the dependency network audit

**Status:** IMPLEMENTED (2026-08-29) — all thirteen patches authored and combination-tested, both
scripts rewritten, flags wired through Dockerfile + Makefile, docs reconciled. **Remaining before
archive:** one real-machine `make image` with default flags (the ~22 GB image exceeds the sandbox's
nested-podman RAM store) — same machine visit as `tasks/verify-vendored-airgap-rebuild.md`, which
now exercises exactly this build path; a live-chat smoke test rides along there too.
**Priority:** 3
**Difficulty:** 6
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

## BLUF

Turn the completed dependency-network audit's decisions (D1–D12, all maintainer-confirmed
2026-08-29) into working code: rewrite the vendor/build scripts to the
**vendor-complete-unpatched + patch-at-build-time** model, author the **eleven new** per-concern
patch files (D1–D2 kept-but-present, D4–D12 applied by default; D3 is the existing
update-check patch gaining a flag), and wire one defaulted `PATCH_OUT_<X>` build-arg per patch
through Makefile → Dockerfile → `03-build-crush.sh` (both build paths). Done = a client image
builds with the default flag set, any flag flips cleanly, and the flag index in the reference doc
matches the wiring.

## Context

Read first, in order:

1. **`tasks/reference/dependency-network-audit.md`** — the audit findings this implements.
   Sections 1–2 define the twelve decisions (D1–D12, plus the existing `CRUSH_AT_IMPORT`),
   section 5 is the flag index (defaults + patch filenames), section 4 has every `file:line` a
   patch must touch.
2. **`tasks/archive/2026/08/29/audit-dependency-network-egress.md`** — the archived investigation
   task: the maintainer's policy, the confirmed decisions (including the patch-model revision this
   implements), and the answered borderline questions.
3. The machinery to change: `client/entrypoint/vendor/vendor-crush.sh` (currently clones + applies
   patches + `go mod vendor` — must STOP pre-patching), `client/entrypoint/03-build-crush.sh`
   (gains all flag-guarded `git apply` steps, both vendored and clone paths),
   `client/Dockerfile` (new ARGs, passed explicitly to the build script), `client/Makefile`
   (flag defaults `?=`, threaded as `--build-arg`s, shown in `make help`), `client/patches/`
   (the two existing patches + eleven new ones).

Key mechanics established by the audit (do not re-derive):

- Vendor the COMPLETE unpatched tree; `go build -mod=vendor` tolerates unused vendored modules
  (checks `modules.txt` vs `go.mod`, not imports) — so removal patches just leave dep source
  unused in `vendor/`. No `go mod tidy` at vendor time.
- D5 (Google) and D6 (AWS) require patching **vendored `charm.land/fantasy`**, not just Crush —
  the SDK imports live there (audit §4.1 cuts A+B, §4.2). D7 (Azure) is a Crush-only cut, and its
  `coordinator.go:414` shared case is **edited, not deleted**.
- The local-model chain (audit §4.4) must survive every flag combination — after each patch is
  authored, grep it against the "do not touch" file list there.
- The vendored tree on disk predates `crush-no-update-check.patch` (recorded in
  `tasks/verify-vendored-airgap-rebuild.md`) — regenerating it with the new no-patch `vendor.sh`
  fixes that drift as a side effect.

## Plan

- [x] Rewrite `vendor-crush.sh`: clone + `go mod vendor` only, no patches. The on-disk
      `client/vendor/crush` was restored to pristine by reverting the old baked-in patches and
      then regenerated via `go mod vendor` from the hash-verified module cache (gitignored, so
      nothing to commit).
- [x] Author the eleven new patch files; keep the two existing ones. Each was authored by editing
      the pristine tree, compiling (`GOPROXY=off go build -mod=vendor`), capturing `git diff`, and
      reverting — so every patch alone is compile-proven.
- [x] Move ALL patch application into `03-build-crush.sh`, flag-guarded, identical in both modes
      (the online mode now runs `go mod vendor` after clone so vendored-dep patches apply there
      too); ARGs/defaults threaded through Dockerfile + Makefile per the flag index.
- [x] Verify: `tasks/adhoc/implement-egress-patch-flags/sweep_patch_combos.sh` — 42 flag
      combinations applied + reversed + byte-identical (all singles; none/default/all compiled;
      the full power sets of the three file-sharing patch groups compiled; 10 random mixes).
      `03-build-crush.sh` run end-to-end in vendored mode with default flags: builds offline,
      `crush --version` reports v0.89.0, `--help` runs; default binary 113.8 MB vs 131.6 MB
      pristine (the cloud SDK families un-compiled). Both scripts shellcheck-clean.
- [x] Docs reconciled: reference doc §§1–2/5 ("implemented as" notes + invariants), CLAUDE.md
      patches bullet, `architecture.md` (patch/flag system section), `crush-capabilities.md`.
- [ ] Real-machine `make image` with default flags + a live-chat smoke test (with
      `tasks/verify-vendored-airgap-rebuild.md`).

## Notes / decisions

- **Patch shapes deviate from the audit's cut lists, deliberately** (recorded per-decision in the
  reference doc §2): D5/D6/D7 patch **vendored fantasy only** (stub/guard; Crush untouched) —
  the SDK imports live there, and the audit's Crush-side lists missed that the tool files/name
  constants and hyper/copilot wiring are load-bearing for the UI. D1/D2 cut registrations, not
  files. D9/D10 are `New()` guards (no SDK weight to shed). D11/D12 guard the egress chokepoint
  functions.
- **Patch-authoring invariant learned the hard way:** a bare-deletion hunk's REVERSE is an
  unanchored insertion — with zero-context hunks, `git apply -R` mis-ordered re-added adjacent
  import lines, silently corrupting the tree (caught by the sweep's byte-identity check; the
  first sweep runs failed nondeterministically because their baselines had captured the corrupted
  state). Fix: never bare-delete a line in a shared file — replace it with a unique marker
  comment, so both directions anchor. The vendor tree was then regenerated from the module cache
  to guarantee pristine.
- The `crush --version` output carries a `+dirty` suffix (Go VCS stamping sees the patched
  worktree). The old model had the same behavior (patches were applied before vendoring); cosmetic.

## Open questions

None — the audit's questions were all answered before this task became actionable (see the
decisions record in the archived audit task and the reference doc's §5 flag index).
