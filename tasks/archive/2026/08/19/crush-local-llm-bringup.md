# Bring up Crush against a local Muse Glimmer server (the basics)

**Status:** complete
**Completed:** 2026-08-19 — end-to-end confirmed: Crush generates against the local Muse
Glimmer model over the SSH tunnel. Durable design/operations knowledge lives in
`tasks/reference/architecture.md` (the living copy); this file is the work record. One
spot-check left for later: a multi-step *tool-using* Crush edit (does the local model drive
the agent loop, not just chat). Deferred conventions: `tasks/port-runclaude-conventions-systems.md`.
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

- [x] Server: `server/Makefile` with the variables + `deps`/`llama`/`pull`/`serve`/`serve-mlx`
      /`probe`/`check-repo` targets, plus repo-root `.gitignore`. (2026-08-19)
- [x] Server: verify the **download plumbing** on Linux (portable, no Mac needed) — venv +
      `huggingface_hub` install, `hf` CLI, `check-repo` resolves the repo, and the real
      `hf download --include` command pulls a file into `models/`. (2026-08-19)
- [ ] Server: verify the **Metal build** (`make llama`) and `serve` — Mac-only, cannot be
      done from the Linux sandbox. Confirm the `/v1` endpoint answers a `curl` probe on the Mac.
- [x] Server: `serve-mlx` target added; MLX vs llama.cpp documented (quant table + Notes).
      `run-fast`/DFlash noted for later.
- [x] Client: `client/Dockerfile` (full toolchain + Crush from source, pinned `v0.89.0`) and
      `client/Makefile` (`image`/`shell`, `--network=host`, `PROJECT=` mount). (2026-08-19)
- [x] Client: bake a working Crush provider config — `crushrc` with a `llamacpp` provider
      (model auto-discovered), parse-verified against the real binary. (2026-08-19)
- [ ] Wire-up: drive one real Crush session end-to-end against the Mac (needs the Mac + the
      `ssh -N -L 8080:127.0.0.1:8080` tunnel up). The config path is verified; only the live
      run remains.
- [x] `.gitignore` for models / `llama.cpp/` / venvs / build dirs. (2026-08-19)
- [x] Real gate: nested build of the client image **passed** — image `crushcontainer`
      **22.3 GB**, in-image `crush version v0.89.0`, baked `crushrc` read by `crush dirs`.
      (2026-08-19; needed the nested RAM store grown 32→50 GB to fit the commit — see log.)

## Notes / decisions

- Q1 (2026-08-18): one repo, `server/` + `client/`, Makefile-variable template. **Decided.**
- Q2: client runs on **Linux**, container reaches the Mac via `ssh -L` on the host +
  `--network=host`. **Decided.**
- Q3: default **Q4_K_M**, options documented above. **Decided.**
- Q4: scaffold **both** llama.cpp and MLX serve targets; document the trade-offs. **Decided.**
- Q5: **full** toolchain image, everything else barebones; conventions systems deferred.
  **Decided.**

### Bring-up log (2026-08-19, server side, verified on the Linux sandbox)

Built `server/Makefile` + repo `.gitignore`. Verified everything that does **not** need a
Mac; flagged what does.

- **Download path proven end-to-end (portable, Linux):** `make venv` builds `.venv` with
  `huggingface_hub` 1.28.0; `make check-repo` resolves `meta-models/Muse-Glimmer-30B-GGUF`
  and confirms `MODEL_FILE` is present; `hf download … --include README.md` (the exact
  `make pull` shape) pulled into `models/`. Model card: Apache-2.0, Meta, released Aug 2026,
  `pipeline_tag: image-text-to-text` (multimodal — hence the mmproj).
- **Actual repo contents (sizes):** `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` **16.76 GB**
  (our default ✓); `…-KQuant-Dynamic-Q4_K_XL.gguf` **19.65 GB** (a higher-quality dynamic
  4-bit — still fits 36 GB, a good Q5-adjacent step-up without leaving 4-bit);
  `mmproj-…-Q4_K_M.gguf` 1.40 GB (vision, skip for coding); `dflash-…-Q4_K_M.gguf` 1.63 GB
  (the DFlash drafter for `run-fast` speculative decoding); + README/LICENSE/USAGE_POLICY.
- **NOT verifiable here (Mac-only):** `make llama` (Metal build) and `make serve` — no Metal
  in the Linux sandbox. Must be run on the Mac Studio.
- **`LLAMACPP_TAG`:** left at the `b10353` floor as a conservative, honest default. Per the
  Q1 decision ("later known-good tag"), bump it to the newest llama.cpp release *verified to
  build+serve Muse Glimmer on Metal* when building on the Mac — a "later" tag isn't
  "known-good" until it's actually run there, so it's a build-time pick, not a guess from here.

### Bring-up log (2026-08-19, client side, verified on the Linux sandbox)

Built `client/{Dockerfile,Makefile,entrypoint/{01-install-base.sh,crushrc,shell.sh}}`.
Because the client target IS Linux, more was verifiable here than for the server:

- **Crush build proven for real:** `go install github.com/charmbracelet/crush@v0.89.0`
  (Go 1.26.5) built cleanly → `crush version v0.89.0`. That is the exact Dockerfile step.
- **Latest stable tag = `v0.89.0`** (2026-08-12) per the Go module proxy; module path
  `github.com/charmbracelet/crush` confirmed. Set as `CRUSH_TAG` default.
- **Config format corrected + verified.** The README-summary claim that JSON is the format
  was misleading: the modern format is **`crushrc`** (`crush.json` is deprecated), global
  path `~/.config/crush/crushrc` (confirmed by `crush dirs`). Baked a `crushrc` declaring a
  **`llamacpp`**-type provider (a real provider type in `schema.json`) with the model list
  omitted so Crush **auto-discovers** the served model. `crush models` loaded the crushrc
  with no parse error.
- **`base_url` has no `/v1`.** Crush source `internal/discover/llamacpp.go:44` appends
  `/v1/models` to `base_url` itself, so `base_url = http://127.0.0.1:8080` is correct
  (a trailing `/v1` would double to `/v1/v1/models`). Matches what llama-server exposes.
- **Toolchain** `01-install-base.sh` is a byte-identical copy of runClaudeInContainer's
  (has `golang`, `git`, `openssh-clients`). `make help` / `make -n image|shell` validate.
- **Nested image build now DONE and verified** (2026-08-19). The client `crushcontainer`
  image builds and runs: `crush version v0.89.0` on PATH, Go 1.26.5 + `ssh` present, baked
  `crushrc` at `/root/.config/crush/crushrc` read by `crush dirs`. Image size **22.3 GB**.
  - **Gotcha for the reference docs:** the build first FAILED at the layer-*commit* with
    `no space left on device` — the 22.3 GB rootfs (Swift, TeX Live, full toolchain) needs
    base+diff+temp at once, overflowing the default nested RAM store. Fix here:
    `mount -o remount,size=50g /var/lib/containers` (this sandbox had 55 GB RAM). On a real
    host `make image` has no such ceiling. This is a concrete data point for the open
    `dir-backed-nested-podman-storage.md` task (disk-backed store would remove the RAM cap).
- **Only the live end-to-end Crush→llama-server session remains** (needs the Mac serving +
  the SSH tunnel). Everything buildable/verifiable on Linux is done.

- Pin (2026-08-18): `LLAMACPP_TAG` = a **later known-good tag** ≥ `b10353` (not the `b10353`
  floor itself) — pick the newest release verified to build+run Muse Glimmer on Metal at
  implementation time, and record it. **Decided.**
- Pin (2026-08-18): `CRUSH_TAG` = the **latest stable Crush release tag** at implementation
  time (checked against `github.com/charmbracelet/crush` releases). **Decided.**

## Open questions

None open. Both pins (llama.cpp, Crush) are resolved above — they resolve to "newest
known-good at implementation time," so confirm the concrete tags against the upstream release
pages when we build, per the verify-before-hardcode note under Server design.
