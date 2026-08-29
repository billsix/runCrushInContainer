# Implement the egress patch/flag system from the dependency network audit

**Status:** proposed — needs go-ahead. (The audit's open questions were all answered 2026-08-29:
D2 keep-by-default; D8 and D9–D12 patch-out-by-default — nothing else blocks this task.)
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

- [ ] Rewrite `vendor-crush.sh`: clone + `go mod vendor` only, no patches; regenerate
      `client/vendor/crush`.
- [ ] Author the eleven new patch files (D1, D2, D4–D12 per the reference doc's file:line lists);
      keep the two existing ones. **Invariant: patches sharing files (`coordinator.go`,
      `agent.go` are touched by several) must apply cleanly in EVERY flag combination and in a
      fixed order** — verify with `git apply --check` sweeps over representative combinations,
      not just all-on/all-off.
- [ ] Move ALL patch application into `03-build-crush.sh`, flag-guarded, identical in both paths;
      thread ARGs/defaults through Dockerfile and Makefile (defaults per the flag index).
- [ ] Verify: default-flag build succeeds (nested, `--cgroups=disabled --network=host`); at least
      one non-default combination builds (e.g. `PATCH_OUT_WEB_TOOLS=1`); binary smoke-checks
      against a stub OpenAI endpoint; `git apply --check` passes for every patch against the fresh
      unpatched tree.
- [ ] Update the reference doc's flag index if any name/default shifted during implementation, and
      `CLAUDE.md`'s patches bullet (it currently documents the old vendor-time model).

## Notes / decisions

## Open questions

None — the audit's questions were all answered before this task became actionable (see the
decisions record in the archived audit task and the reference doc's §5 flag index).
