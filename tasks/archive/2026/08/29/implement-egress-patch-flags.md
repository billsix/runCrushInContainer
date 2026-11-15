# Implement the egress patch/flag system from the dependency network audit

**Status:** complete
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>) · **Completed:** 2026-08-29

Turned the dependency-network audit's twelve maintainer-confirmed decisions (D1-D12, 2026-08-29) into
working code: the vendor/build scripts moved to a **vendor-complete-unpatched, patch-at-build-time**
model; eleven new per-concern patch files were authored (thirteen patches in total with the two existing
ones); and one defaulted `PATCH_OUT_<X>` build-arg per patch was wired through `client/Makefile`,
`client/Dockerfile` and `client/entrypoint/03-build-crush.sh` in both build paths. A default-flag
`make image` built on the real machine and Crush connected to the local model. The audit and flag index
are in `tasks/reference/dependency-network-audit.md`; the investigation is
`tasks/archive/2026/08/29/audit-dependency-network-egress.md`.

## What was done

- **`client/entrypoint/vendor/vendor-crush.sh`**: now clone + `go mod vendor` only, no patches. The
  on-disk `client/vendor/crush` was restored to pristine by reverting the old baked-in patches, then
  regenerated with `go mod vendor` from the hash-verified module cache. This also fixed the drift recorded
  in `tasks/verify-vendored-airgap-rebuild.md` (the vendored tree had predated
  `crush-no-update-check.patch`).
- **Eleven new patches in `client/patches/`**: each authored by editing the pristine tree, compiling
  (`GOPROXY=off go build -mod=vendor`), capturing `git diff` and reverting, so every patch compiles alone.
  D1/D2 are kept-but-present; D3 is the existing update-check patch gaining a flag; D4-D12 apply by
  default.
- **All patch application moved into `03-build-crush.sh`**, flag-guarded and identical in both modes.
  The online mode now runs `go mod vendor` after the clone so vendored-dep patches apply there too. The
  ARGs and `?=` defaults were threaded through the Dockerfile and Makefile per the flag index and shown
  in `make help`.
- **Docs**: reference doc §§1-2/5 ("implemented as" notes and invariants), the `CLAUDE.md` patches
  bullet, `tasks/reference/architecture.md` (patch/flag system section),
  `tasks/reference/crush-capabilities.md`.
- The combination sweep was promoted to `tools/sweep_egress_patch_combos.sh`, to be re-run on every
  `CRUSH_TAG` bump.

## Decisions and lessons

- **`go build -mod=vendor` tolerates unused vendored modules** (it checks `modules.txt` against
  `go.mod`, not imports), so removal patches just leave dep source unused in `vendor/`; no
  `go mod tidy` at vendor time.
- **Patch shapes deviate from the audit's cut lists, deliberately** (recorded per decision in the
  reference doc §2). D5 (Google), D6 (AWS) and D7 (Azure) patch **vendored `charm.land/fantasy` only**
  (stub/guard, Crush untouched), because the SDK imports live there and the UI depends on the Crush-side
  tool files, name constants and hyper/copilot wiring that the audit's lists would have cut. D1/D2 cut
  registrations, not files. D9/D10 are `New()` guards (no SDK weight to shed). D11/D12 guard the egress
  chokepoint functions.
- **Never bare-delete a line in a shared file.** A bare-deletion hunk's reverse is an unanchored
  insertion; with zero-context hunks, `git apply -R` mis-ordered re-added adjacent import lines and
  silently corrupted the tree. The sweep's byte-identity check caught it (the first sweep runs failed
  nondeterministically because their baselines had captured the corrupted state). The fix is to replace
  the line with a unique marker comment so both directions anchor; the vendor tree was then regenerated
  from the module cache to guarantee it was pristine.
- The local-model chain (audit §4.4) had to survive every flag combination; each patch was grepped
  against that section's "do not touch" file list.
- `crush --version` carries a `+dirty` suffix (Go VCS stamping sees the patched worktree), as it did
  under the old model. Cosmetic.

## Verification

- `tools/sweep_egress_patch_combos.sh`: 42 flag combinations applied, reversed and byte-identical (all
  singles; none/default/all compiled; the full power sets of the three file-sharing patch groups compiled;
  10 random mixes).
- `03-build-crush.sh` end-to-end in vendored mode with default flags: built offline, `crush --version`
  reported v0.89.0, `--help` ran. Default binary 113.8 MB vs 131.6 MB pristine (the cloud SDK families
  are no longer compiled). Both scripts shellcheck-clean.
- Real machine (William Emerison Six <billsix@gmail.com>, 2026-08-29): a default-flag `make image` built,
  Crush ran and connected to the local model. The offline vendored rebuild stayed its own gate in
  `tasks/verify-vendored-airgap-rebuild.md`.
