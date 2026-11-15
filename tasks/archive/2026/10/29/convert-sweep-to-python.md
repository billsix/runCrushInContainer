# Convert sweep_egress_patch_combos.sh to Python

**Status:** complete
**Completed:** 2026-10-29

Rewrote `tools/sweep_egress_patch_combos.sh` (power sets via `(1 << n)` bit tests, a hand-rolled
integer-hash PRNG, substring-match canonical ordering) as `tools/sweep_egress_patch_combos.py`,
combination-sequence-identical, and left a 2-line shim at the old path so the CRUSH_TAG-bump
checklist, `tasks/reference/architecture.md` and `tasks/reference/dependency-network-audit.md` need
no change. Committed as `f8feda0`.

Decided with the maintainer 2026-10-29 (William Emerison Six <billsix@gmail.com>), from a cross-repo
sweep for `tools/` shell scripts whose bash reads worse than Python: convert this one, because its
logic (power sets, PRNG mixes, canonical ordering) is the point and Python's integer loops express it
plainly. `tools/check_launchers.sh` stays bash: it tests launcher lifecycle semantics (`set -m` job
control, process-group `kill -INT -- -$pid`, PATH shims for `ssh`/`make`), bash's home turf.

## Shim

```sh
#!/usr/bin/env bash
exec python3 "$(dirname "$0")/sweep_egress_patch_combos.py" "$@"
```
The shim keeps its `+x` bit.

## Preserved exactly

- The combination sequence: 43 combinations in the same order (14 singles, 3 build combos
  default/all/none, three group power sets 8+4+4, 10 PRNG mixes), including the `in_order`
  leading-space quirk in each `== combo` line.
- Apply order (canonical `ALL` order; `--unidiff-zero`), reverse order, the sha256 touched-file
  manifest and byte-restoration assertion, the `GOPROXY=off GOFLAGS= go build -mod=vendor -o /dev/null .`
  step, and abort-on-first-failure.
- Added only a `--list` dry-run mode (prints the sequence, touches nothing), used to prove the port.

## Verification (2026-10-29)

- `--list` output byte-identical to the former bash run with git/go shimmed to no-ops (43 combos).
- Full run with real git (go shimmed): "SWEEP OK: 43 combinations ...", every combo applied,
  reversed and restored byte-identical.
- One real `go build` combo (DEFAULT) end-to-end: apply + build + reverse + restore OK.
- The baseline and equivalence captures under `tasks/adhoc/convert-sweep-to-python/data/` were
  removed at archive.
