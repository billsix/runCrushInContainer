# A host-run script to query the server and recommend context settings

**Status:** proposed — fuller "server health + context advisor" drafted below; **do NOT place yet**
(maintainer: "not yet", 2026-08-20). Nothing created in the repo.
**Priority:** 4
**Difficulty:** 2
**Started:** 2026-08-20

## Goal

The maintainer can't answer the context-sizing questions in `tasks/context-window-sizing.md` by hand,
**especially on an airgapped system** where the only way to learn the numbers is to query the running
server. So: a small script that runs **outside the container**, hits the local llama-server **through
the SSH port-forward**, and prints the current/maximum context plus **one or two concrete
recommendations** — turning "I don't know" into "here's what to set."

It runs wherever the tunnel's local end lives (the Linux host, or the Mac directly) — anywhere that can
reach `127.0.0.1:8080`. **Not** inside this agent's sandbox (that's on a bridged network and can't reach
the host loopback tunnel — see `tasks/suppress-embedded-provider-catalog.md`, the reachability note).

## What it does (v1 scope — a compact server-health + context advisor)

1. **Reachability check** — curl `/v1/models`; on failure, print the exact `ssh -fN -L …` reminder and
   exit non-zero (so a down tunnel is an obvious, actionable error, not silence).
2. **Read the facts** — parse `meta` from `/v1/models`: `n_ctx` (current server window = live `-c`/`CTX`),
   `n_ctx_train` (model's trained maximum = the ceiling), `size` (weights bytes), `ftype` (quant),
   `n_params`.
3. **Health probes** (the "fuller advisor" additions):
   - **`/props`** (best-effort — some builds may not expose it): read `total_slots` and the per-slot
     `default_generation_settings.n_ctx`.
   - **Generation smoke test** — one tiny `/v1/chat/completions` round-trip. Confirms the model actually
     *generates* (not just lists), and reports **tokens/sec from the server's own `timings` field**
     (`predicted_per_second`) — no fragile client-side clock (stock macOS `date` has no `%N`, so we do
     NOT wall-clock it; if the server omits `timings`, we report "OK" without a rate rather than guess).
4. **Report + recommend** — a short health block, then:
   - **R1 (free, do first):** set the crushrc model's `--context-window` to the server's `n_ctx` so
     Crush stops auto-summarizing early (the most likely "feels small" cause — see the sizing task).
   - **R2 (enlarge, if headroom):** if `n_ctx < n_ctx_train`, suggest `make serve CTX=<2×, capped at max>`
     with the RAM caveat, then match `--context-window`. If already at the max, say so.
   - **R3 (only if `total_slots > 1`):** warn that `--parallel N` splits the KV cache (each client gets
     ~`n_ctx/N`, not the full window) and to use `--parallel 1` (server Makefile `NP=1`) for a single
     Crush client. This is the concrete, live-detected version of the `architecture.md` `--parallel`
     note.

Dependencies: `bash`, `curl`, `python3` (for JSON parsing — present wherever `make pull` runs; the
server Makefile already relies on python3). No `jq` needed (not on stock macOS).

**KV-RAM estimate (decision on Q3): best-effort, no fabricated precision.** A real KV-cache byte figure
needs `n_layer` / `n_embd_kv` (GQA-reduced), which **neither `/v1/models` nor `/props` reliably expose**,
so the script does NOT print a made-up number. It surfaces whatever memory-relevant facts the endpoints
*do* give (context size, slot split) and keeps the honest qualitative rule: "KV RAM grows ~linearly with
context; test before growing." If a future need justifies it, `/metrics` (Prometheus) or the server's
startup "KV cache size = … MiB" log line are the only sources of a true figure — out of scope for v1.

## Drafted script (ready to place as `server/context-advisor.sh`)

```bash
#!/usr/bin/env bash
# context-advisor.sh -- query the local llama-server (through the SSH port-forward) and
# report server health + recommend context-window settings for the server and for Crush.
#
# RUN OUTSIDE THE CONTAINER, on the host where the SSH tunnel's local end lives. The tunnel
# must be up first:
#     ssh -fN -L 8080:127.0.0.1:8080 you@mac-studio
#     ./context-advisor.sh                 # or: HOST=127.0.0.1 PORT=8080 ./context-advisor.sh
#
# Needs: bash, curl, python3 (for JSON parsing). No jq (not on stock macOS).
set -uo pipefail

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"
BASE="http://${HOST}:${PORT}"

fetch() { curl -sS --max-time "${2:-8}" "$1" 2>/dev/null; }

models_json="$(fetch "${BASE}/v1/models")" || true
if [ -z "${models_json:-}" ]; then
    echo "ERROR: could not reach ${BASE}/v1/models." >&2
    echo "Is the server up and the SSH port-forward running on THIS host?" >&2
    echo "  ssh -fN -L ${PORT}:127.0.0.1:${PORT} you@mac-studio" >&2
    exit 1
fi

props_json="$(fetch "${BASE}/props")"   # best-effort; may be empty on some builds

# Generation smoke test: one tiny round-trip. Ask llama.cpp to include per-token timings so
# we can report tokens/sec from the SERVER's own clock (portable; no `date +%N`, absent on macOS).
smoke_req='{"messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":16,"temperature":0,"timings_per_token":true}'
smoke_json="$(curl -sS --max-time 30 "${BASE}/v1/chat/completions" -H 'Content-Type: application/json' -d "$smoke_req" 2>/dev/null)" || true

MODELS_JSON="$models_json" PROPS_JSON="$props_json" SMOKE_JSON="$smoke_json" python3 - <<'PY'
import json, os
def load(name):
    s = os.environ.get(name, "") or ""
    try: return json.loads(s) if s.strip() else {}
    except Exception: return {}
models, props, smoke = load("MODELS_JSON"), load("PROPS_JSON"), load("SMOKE_JSON")

data = models.get("data", [])
if not data:
    print("No models reported at /v1/models -- is a model loaded?"); raise SystemExit(1)
m = data[0]; meta = m.get("meta", {})
mid    = m.get("id", "?")
n_ctx  = int(meta.get("n_ctx", 0) or 0)         # current server window (-c / CTX)
n_max  = int(meta.get("n_ctx_train", 0) or 0)   # model's trained maximum
size   = int(meta.get("size", 0) or 0)          # weights bytes
ftype  = meta.get("ftype", "?")
params = int(meta.get("n_params", 0) or 0)
gib = lambda b: b / (1024**3)

# health from /props (best-effort)
slots = props.get("total_slots")
dgs = props.get("default_generation_settings", {}) if isinstance(props, dict) else {}
slot_ctx = dgs.get("n_ctx") if isinstance(dgs, dict) else None

# smoke -> did it generate, and tokens/sec (from server timings only)
choices = smoke.get("choices", [])
generated = bool(choices)
tps = (smoke.get("timings") or {}).get("predicted_per_second")

print("Server health")
print("-------------")
print(f"Model:          {mid}")
print(f"Quant:          {ftype}   params: {params/1e9:.1f}B   weights: {gib(size):.1f} GiB")
print(f"Server window:  n_ctx = {n_ctx}        (the live -c / CTX)")
print(f"Model maximum:  n_ctx_train = {n_max}  (ceiling you can raise -c to)")
if slots is not None:
    extra = f", ~{slot_ctx}/slot" if slot_ctx else ""
    print(f"Parallel slots: {slots}{extra}")
rate = f"  (~{float(tps):.1f} tok/s)" if tps else ""
print(f"Generation:     {'OK' + rate if generated else 'FAILED -- reachable but did not generate'}")
print()

print("Recommendations")
print("---------------")
print("1. FREE, do first -- make Crush agree with the server so it stops trimming early:")
print(f"     crushrc:  model add muse-glimmer/<id> --context-window {n_ctx}")
if n_max and n_ctx and n_ctx < n_max:
    suggest = min(n_ctx * 2, n_max)
    print(f"2. To ENLARGE the real window (headroom to {n_max}):")
    print(f"     server:   make serve CTX={suggest}   (then match --context-window={suggest})")
    print(f"   Larger context ~= linearly more KV-cache RAM. With a ~{gib(size):.0f} GiB Q4 model on")
    print(f"   36 GB, {n_ctx} is comfortable; test {suggest} and watch memory/throughput before more.")
else:
    print(f"2. Already at the model maximum ({n_max}); no headroom to grow the window.")
if isinstance(slots, int) and slots > 1:
    per = n_ctx // slots if n_ctx else "?"
    print(f"3. WARNING: --parallel {slots} splits the KV cache -- each client gets ~{per} tokens, not")
    print(f"   the full {n_ctx}. For a single Crush client use --parallel 1 (server Makefile NP=1).")
PY
```

(Verified against the real `/v1/models` output captured 2026-08-20: `meta` carries `n_ctx=32768`,
`n_ctx_train=131072`, `size`, `ftype`, `n_params` — so the parse holds today. On that data it prints:
32k of a 131k max, generation OK (+tok/s if the server returns `timings`), slots line if `/props`
answers, R1 = `--context-window 32768`, R2 = `CTX=65536`. `/props` and `timings` are best-effort — the
report degrades gracefully to "still shows context + recommendations" if a build omits them.)

## Placement & wiring (proposed)

- **Where:** `server/context-advisor.sh` — it's a host-native tool that queries the server, so it sits
  with the other server-side host scripts. (Alternative: a top-level `tools/` dir if we start one.)
- **Optional make target:** add to `server/Makefile`:
  ```make
  .PHONY: advise
  advise: ## query the running server and recommend context settings
  	@./context-advisor.sh
  ```
  Then `make advise` (with the tunnel up) is the one-liner. Keep it `##`-documented per the help
  convention. It's read-only (curl + parse), so no gate/CI concerns.

## Open questions

1. **Place it as `server/context-advisor.sh` + a `make advise` target?** DEFERRED (maintainer: "not
   yet", 2026-08-20). The script is fully drafted above; when you say go I'll create the file and wire
   the `make advise` target (and nothing else). This is the one decision still open.

Resolved (2026-08-20):
- **Scope → fuller "server health" advisor** (maintainer: "sure, add more"): now includes the
  generation smoke test + tokens/sec and the `--parallel > 1` KV-split warning, on top of the context
  recommendations. Speced in "What it does" and the drafted script.
- **KV-RAM estimate → best-effort, no fabricated precision** (maintainer: "whatever you recommend"):
  a true KV byte figure needs `n_layer`/`n_embd_kv` that the HTTP endpoints don't reliably expose, so
  the script surfaces what `/props` gives (context, slot split) and keeps the qualitative "~linear,
  test before growing" guidance rather than printing a made-up number. `/metrics` or the startup log
  are the only real sources — out of scope for v1.

## Cross-links

- `tasks/context-window-sizing.md` — the findings this script operationalizes (the two limits, how
  compaction works, how to change each).
- `tasks/suppress-embedded-provider-catalog.md` — shares the `model add … --context-window` line.
