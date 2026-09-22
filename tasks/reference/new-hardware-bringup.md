# Bringing the server up on new hardware — probe, smoke, then size the knobs

**Reference document** — the short runbook for the first hour on a machine you have not served
from before (the airgap box, a bigger or smaller Mac, a Linux GPU host). It collects what is
otherwise scattered across `server/Makefile`'s comments, `glimmer-models-and-airgap-quant-selection.md`
and the archived `tasks/archive/2026/08/20/context-window-sizing.md`. Written 2026-09-10; the work
that wires it into the README is `tasks/new-hardware-bringup-runbook.md`. Commands are `[MAC]` or
`[ANY]` as marked; everything runs in `server/`.

## 0. What `probe` and `smoke` are, and why both

| Target | What it does | What a pass proves | What it cannot tell you |
|---|---|---|---|
| `make probe` `[ANY]` | `curl http://127.0.0.1:$PORT/v1/models` | the server process is up, the port is right, the model **alias** the client expects is what it reports (`muse-glimmer` on 8080, `gemma-4` on 8081), and the live `meta.n_ctx` | that it can generate at all |
| `make smoke` `[ANY]` | one `/v1/chat/completions` asking for the word `OK`, `max_tokens 16` | the model loaded fully and **generates** — weights, KV cache and the Metal/CUDA path all work | speed, or that a real context fits |

Run them in this order, every time, on every new box: `probe` first (cheap, catches wrong
port/alias/tunnel), then `smoke` (catches a model that lists but cannot run — an over-committed KV
cache fails *here*, not at `probe`). Both take `MODEL=glimmer|gemma` (default `glimmer`; the
port follows the model — 8080 / 8081).

## 1. The bring-up sequence

```sh
cd server
make deps                       # [MAC] Xcode CLT + cmake present
make llama                      # [MAC] build llama.cpp (reuses the vendored checkout offline)
make serve                      # [MAC] defaults: Q4_K_M, CTX=65536, NGL=999, NP=1, port 8080
make probe                      # [ANY] in another terminal — alias + n_ctx as expected?
make smoke                      # [ANY] does it say OK?
```

From the client host, the simplest end-to-end check is the launcher itself —
`client/runCrushNoInternet.sh you@mac-studio ""` from a project dir opens the forward, waits for it, and
drops you in the container, where `curl http://127.0.0.1:<port>/v1/models` is the `probe` through the
tunnel (`tasks/reference/client-network-modes-and-launchers.md`). By hand, the tunnel is one command
even for several models — `ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 you@mac-studio` (add an
`-L` per served port; an unserved port's forward is harmless).

Then read the **`llama-server` log** from `make serve` — three lines decide everything below:
the `load_tensors: … offloaded N/N layers to GPU` line (did all layers fit?), the KV-cache size
line (`llama_kv_cache: … size = X MiB`), and any `ggml_metal … wired limit` / out-of-memory
warning.

## 2. Sizing the four knobs to the box (in this order)

The budget is **weights + KV cache + a working margin**, all of it wired into GPU-accessible
memory on Apple Silicon.

1. **Which quant** — decided *before* transfer on an airgap box (bytes are expensive): the
   RAM/VRAM rule in `glimmer-models-and-airgap-quant-selection.md` (≤16 GB → `UD-Q4_K_XL`,
   ~24 GB → `Q4_K_M`, ~32 GB → `Q5_K_M`, ≥40 GB → `Q6_K`). Serve a different vendored file with
   `make serve MODEL_FILE=<file>`; the alias stays constant so the client needs no change.
2. **`NGL`** (layers offloaded) — keep `999` (all) if the offload line says N/N; if the log shows
   fewer layers offloaded or a Metal allocation failure, the weights do not fit: drop to a smaller
   quant rather than partial offload (CPU layers make a coding agent unusably slow).
3. **`CTX`** (context window) — the lever that trades RAM for room to work. Rule of thumb from the
   36 GB Mac Studio: Q4_K_M (16.8 GB) + `CTX=65536` sits at the edge of macOS's default
   **wired limit** (~24–28 GB); the fix is `sudo sysctl iogpu.wired_limit_mb=<mb>` (leave several
   GB for the OS), or `make serve CTX=32768`. Bigger box → raise `CTX` (the model trains to
   131072); smaller → 32768 is the safe floor for a real session (Crush's own prompt is ~18k
   tokens). **Whatever you pick, set the client's `--context-window` in
   `client/entrypoint/crushrc` to the same number** — Crush compacts at ~80% of it.
4. **`NP`** (parallel slots) — stay at `1`: one Crush, one slot, so prompt caching works and the
   context is not split. Raise only for multiple concurrent clients, and divide `CTX` by `NP` in
   your head when you do.

## 3. Then measure, once, and write it down

- **Generation speed**: the `smoke` reply is too short; ask Crush for a paragraph and read the
  server log's `eval time … tokens per second`. Under ~10 tok/s the agent feels broken; 20+ is
  comfortable. Speed is the argument for a smaller quant or (later) the Gemma 4 26B-A4B MoE.
- **Prompt processing**: the log's `prompt eval time` on a fresh 30–50k-token turn — this is what
  every compaction and every new session costs.
- **Peak memory**: Activity Monitor's *Memory Used* / `sudo powermetrics --samplers gpu_power` on
  macOS, `nvidia-smi` on CUDA, during a long turn. If it swaps, drop `CTX` first.

Record the box, the quant, the four knobs and those three numbers in
`tasks/reference/architecture.md` › "Verification status" — the next box starts from the last.

## 4. The two silent failures worth knowing in advance

- **`probe` passes, `smoke` hangs or 500s** → the KV cache did not fit at load or on first use.
  Lower `CTX`; check the wired limit.
- **Everything passes, Crush "loses" context early** → the crushrc `--context-window` is bigger
  than the server's `CTX`; Crush thinks it has room it does not. `probe`'s `meta.n_ctx` is the
  truth; make the crushrc match.

## Sources

`server/Makefile` (knob comments on `CTX`/`NGL`/`NP`/`MODEL_FILE`; `probe`, `smoke`);
`glimmer-models-and-airgap-quant-selection.md` (quant rule); `tasks/archive/2026/08/20/context-window-sizing.md`
(the wired-limit finding and the KEEP IN SYNC rule); `README.md` § Server.
