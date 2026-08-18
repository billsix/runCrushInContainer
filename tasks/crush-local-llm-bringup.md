# Bring up Crush against a local Muse Glimmer server (the basics)

**Status:** proposed — needs go-ahead to implement
**Priority:** 2
**Difficulty:** 6
**Started:** 2026-08-18

## Goal

Stand up the simplest working version of a two-machine local-coding-LLM setup:

- **Server (macOS, native):** run Meta's **Muse Glimmer 30B** coding model on a 36 GB
  Mac Studio via **llama.cpp** built for Apple Silicon (Metal), serving an
  OpenAI-compatible HTTP endpoint on loopback.
- **Client (Linux, containerized):** a Podman container — the full
  `runClaudeInContainer` toolchain — with **Crush** (Charm's terminal coding agent,
  `github.com/charmbracelet/crush`) built at image-build time, pointed at the server
  through an **SSH port-forward**.

First-run scope is deliberately minimal: *up and running*, nothing more. No task/stack/
personal-config machinery, no auth plumbing (it's all local). Those are deferred to
`tasks/port-runclaude-conventions-systems.md`.

This repo is meant to be a **template**: model, quant, and both pinned tool versions live
in Makefile variables so a fork can swap them.

## Architecture

```
  [MAC STUDIO]  llama-server (Metal)  --  loopback 127.0.0.1:8080  (OpenAI /v1)
        ▲
        │  ssh -N -L 8080:127.0.0.1:8080  you@mac-studio     (run ON the Linux host)
        │
  [LINUX HOST]  localhost:8080  ─────────────────────────────────┐
                                                                  │
  [CONTAINER]  crush  ->  http://127.0.0.1:8080/v1   (podman run --network=host)
```

The Mac binds llama-server to **127.0.0.1 only** (never the LAN); the sole path in is the
SSH tunnel. The client container uses `--network=host` (Linux-only, which fits) so
`127.0.0.1:8080` inside the container is the host's forwarded port. `host.containers.internal`
is the fallback if we later want to avoid host networking.

## Repo layout (to create)

```
runCrushInContainer/
├── CLAUDE.md              # project guidance (created with this task)
├── README.md              # user-facing + the SSH recipe (created with this task)
├── server/                # macOS-native, NOT containerized
│   ├── Makefile           # deps / llama / pull / serve / serve-mlx / run-fast
│   └── models/            # downloaded GGUF(s) — gitignored
└── client/                # Linux container
    ├── Dockerfile         # fedora:44 + full toolchain + crush built from source
    ├── Makefile           # image / shell
    └── entrypoint/        # shell.sh, 01-install-base.sh (kitchen sink), crush config
```

## Server design (`server/Makefile`)

Makefile variables (the swappable "template" surface):

- `LLAMACPP_TAG ?= b10353` — **minimum** for Muse Glimmer support (merged into llama.cpp
  2026-08-10, first shipped in release `b10353`). Pin a specific known-good tag ≥ this.
- `MODEL_REPO ?= meta-models/Muse-Glimmer-30B-GGUF`
- `MODEL_FILE ?= Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf`  (Q4_K_M, ~16.8 GB)
- `MODEL_DIR ?= ./models`
- `HOST ?= 127.0.0.1` · `PORT ?= 8080` · `CTX ?= 16384` · `NGL ?= 999` (offload all layers)

Targets:

1. `deps` — check for the Xcode command-line tools (`xcode-select -p`) and `cmake`; print
   `brew install cmake` guidance if missing. (Don't auto-install — the user runs macOS
   natively here.)
2. `llama` — `git clone --depth 1 --branch $(LLAMACPP_TAG)` llama.cpp, then
   `cmake -B build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release && cmake --build build -j`.
   Metal is on by default on macOS; set it explicitly so the intent is legible.
3. `pull` — download the GGUF from Hugging Face:
   `uv tool run --from huggingface_hub hf download $(MODEL_REPO) --include $(MODEL_FILE)
   --local-dir $(MODEL_DIR)` (or `pip install -U huggingface_hub` + `hf download`).
4. `serve` — `build/bin/llama-server -m $(MODEL_DIR)/$(MODEL_FILE) --host $(HOST)
   --port $(PORT) -ngl $(NGL) -c $(CTX)`. Exposes OpenAI-compatible `/v1`.
5. `serve-mlx` — the **MLX** alternative backend (often faster on Apple Silicon). Use
   `mlx-lm` (`uv tool run --from mlx-lm mlx_lm.server --model <mlx-repo> --port $(PORT)`)
   against an MLX quant such as `RadixArk/Muse-Glimmer-q4-MLX`, or Ollama's MLX engine
   (`ollama run muse-glimmer:30b-q4_K_M`). Document the trade-off, don't make it the default.
6. `run-fast` *(optional, later)* — speculative decoding with the **DFlash drafter** from
   the same repo (`--model-draft <drafter.gguf>`) for higher tok/s.
7. `all` — `llama pull`.

**Verify at implementation time** (these came from web search on 2026-08-18 and may drift):
the exact `MODEL_FILE` name, the repo path, and a concrete good `LLAMACPP_TAG` — check
`huggingface.co/meta-models/Muse-Glimmer-30B-GGUF/tree/main` and the llama.cpp releases
before hardcoding. Per the "never cite an artifact you haven't verified" rule, confirm the
GGUF filename resolves before writing it as a default.

### Quantization options (documented per request; default = Q4_K_M)

Binding constraint: on a 36 GB **unified-memory** Mac, weights + KV-cache (context) + the
OS share one pool, and Metal wires only a fraction by default (raise with
`sudo sysctl iogpu.wired_limit_mb=<mb>`). Safe GPU budget ≈ 24–28 GB.

| Quant | Size (30B) | Verdict on 36 GB |
| --- | --- | --- |
| **Q4_K_M** | ~16.8 GB | **Default.** Big context headroom, fast, no wired-limit tweak. |
| Q5_K_M | ~20–21 GB | Better quality, still comfortable. The natural step-up. |
| Q6_K | ~24–25 GB | Near-lossless but tight; smaller context, may need a higher wired limit. |
| Q8_0 | ~31–32 GB | Full quality but too tight here (swaps once KV-cache+OS added). Skip. |
| IQ4_XS / IQ3 | ~13–15 GB / less | Better quality-per-bit at the low end, slower. Only if you want a huge context. |

Extras in the official repo: an **`mmproj`** file (vision/perception encoder — needed only
for image input; a coding agent can skip it) and the **DFlash drafter** (speculative-decode
draft model, see `run-fast`).

## Client design (`client/`)

- **Dockerfile:** `FROM registry.fedoraproject.org/fedora:44`; run the **full kitchen-sink**
  `entrypoint/01-install-base.sh` (the same ~430-package toolchain as runClaudeInContainer —
  copy it in, keep it sorted); then **build Crush from source at a pinned tag**:
  `CRUSH_TAG ?= <pin>`, `go install github.com/charmbracelet/crush@$(CRUSH_TAG)` (or
  `git clone --branch $(CRUSH_TAG) … && go build`). Go is already in the toolchain.
- **Makefile:** `make image` (build), `make shell` (`podman run -it --rm --network=host
  -v $(pwd):/<proj>:Z <image>` then a shell / `crush`). No `~/.claude` mounts, no auth env,
  no layered conventions, no personal overlay, no nested-podman flags — barebones beyond the
  toolchain.
- **Crush provider config:** configure a custom **OpenAI-compatible** provider with
  `base_url = http://127.0.0.1:8080/v1`, a dummy API key, and the served model id. Ship a
  default crush config in `client/entrypoint/` baked into the image (later: mount it). Confirm
  Crush's exact config path/schema (`crush/AGENTS.md` in the repo) at implementation time.

## Explicitly deferred (do NOT build in v1)

Tracked in `tasks/port-runclaude-conventions-systems.md`: the task-doc system, the diversion
stack, the personal-overlay/`@`-import layering, the reference-doc conventions, and any auth
plumbing (not needed — the endpoint is a local, keyless llama-server behind SSH).

## Plan

- [ ] Server: `server/Makefile` with the variables + `deps`/`llama`/`pull`/`serve` targets.
- [ ] Server: verify the GGUF pull, the Metal build, and `serve` on the Mac; confirm the
      `/v1` endpoint answers a `curl` chat-completions probe.
- [ ] Server: add `serve-mlx` + document MLX vs llama.cpp; note `run-fast`/DFlash for later.
- [ ] Client: `client/Dockerfile` (full toolchain + pinned Crush) and `client/Makefile`.
- [ ] Client: bake a working Crush OpenAI-compatible provider config.
- [ ] Wire-up: document + test the `ssh -N -L 8080:127.0.0.1:8080` tunnel and
      `--network=host`; drive one real Crush session end-to-end against the Mac.
- [ ] `.gitignore` for `server/models/*.gguf`, `server/llama.cpp/`, build dirs.

## Notes / decisions

- Q1 (2026-08-18): one repo, `server/` + `client/`, Makefile-variable template. **Decided.**
- Q2: client runs on **Linux**, container reaches the Mac via `ssh -L` on the host +
  `--network=host`. **Decided.**
- Q3: default **Q4_K_M**, options documented above. **Decided.**
- Q4: scaffold **both** llama.cpp and MLX serve targets; document the trade-offs. **Decided.**
- Q5: **full** toolchain image, everything else barebones; conventions systems deferred.
  **Decided.**

## Open questions

1. **Exact llama.cpp pin.** Use `b10353` (the first release with Muse Glimmer support) or a
   later known-good tag? Recommend pinning a *specific* recent tag ≥ `b10353` at build time
   and recording it — verify against llama.cpp releases when we implement.
2. **Crush tag to pin.** Which Crush release tag? Recommend the latest stable tag at
   implementation time (checked against `github.com/charmbracelet/crush` releases), recorded
   in `CRUSH_TAG`.
