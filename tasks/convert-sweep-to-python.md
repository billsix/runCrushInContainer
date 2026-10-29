# Convert sweep_egress_patch_combos.sh to Python

**Status:** in progress
**Priority:** 6
**Difficulty:** 3

## BLUF

`tools/sweep_egress_patch_combos.sh` enumerates patch combinations with
`(1 << n)` bit tests, a hand-rolled integer hash PRNG, and substring-match
canonical ordering — "advanced bash" that reads far more clearly as Python.
Rewrite it in Python, combination-sequence-identical, with a 2-line `.sh` shim at
the old path so the CRUSH_TAG-bump checklist and reference docs need no change.
Done = `sweep_egress_patch_combos.py` + `.sh` shim, the sweep still applies/reverses
every combination and verifies byte-identical restoration, and a `--list` dry run
reproduces the former bash's exact `== combo` sequence. Decided with the maintainer
2026-10-29 (William Emerison Six <billsix@gmail.com>): convert this one;
`check_launchers.sh` stays bash (it tests shell launcher signal/process-group
semantics — bash's home turf).

## Context

From a 2026-10-29 cross-repo sweep for `tools/` shell scripts whose advanced bash is
harder to read than Python. This one is the clearest win: the *logic* (power sets,
PRNG mixes, canonical ordering) is the point, and it's exactly what Python's plain
integer loops express cleanly; the git-apply/go-build parts port 1:1.

### Shim mechanism

`tools/sweep_egress_patch_combos.sh` is now:
```sh
#!/usr/bin/env bash
exec python3 "$(dirname "$0")/sweep_egress_patch_combos.py" "$@"
```
Keep the shim's `+x` bit (`git add --chmod=+x`). Callers (the CRUSH_TAG-bump
checklist, `tasks/reference/architecture.md`, `dependency-network-audit.md`) keep
using the `.sh` path unchanged.

## What was preserved exactly

- The combination SEQUENCE (verified byte-identical via `--list` vs the former bash
  run with git/go shimmed to no-ops): 43 combinations in the same order — 14 singles,
  3 build combos (default/all/none), three group power sets (8+4+4), 10 PRNG mixes.
  Including the `in_order` leading-space quirk in each `== combo` line.
- The apply order (canonical `ALL` order; `--unidiff-zero`), the reverse order, the
  sha256 touched-file manifest + byte-restoration assertion, the `GOPROXY=off GOFLAGS=
  go build -mod=vendor -o /dev/null .` build step, and abort-on-first-failure.
- Added only a harmless `--list` dry-run mode (prints the sequence, touches nothing) —
  used to prove the port; it does not change the real gate.

## Verification (done 2026-10-29)

- `--list` combo sequence byte-identical to the former bash (43 combos).
- Full run with real git (go shimmed) → all 43 combos apply, reverse, and verify
  byte-identical restoration: "SWEEP OK: 43 combinations ...".
- One real `go build` combo (DEFAULT) end-to-end: apply + build + reverse + restore OK.

## Left as bash (maintainer decision 2026-10-29)

`tools/check_launchers.sh` — a regression harness that tests the launcher LIFECYCLE
(`set -m` job control, process-group `kill -INT -- -$pid`, PATH shims mimicking
`ssh`/`make`). It exercises shell signal/process-group semantics; converting it would
mean re-implementing that in Python for no readability gain. Stays bash.

## Ad-hoc

Baseline + equivalence captures under `tasks/adhoc/convert-sweep-to-python/data/`;
`git rm` on archive.
