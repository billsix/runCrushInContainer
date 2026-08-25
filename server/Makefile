# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
.DEFAULT_GOAL := help

# ============================================================================
#  runCrushInContainer — SERVER side.  Runs NATIVELY on macOS (Apple Silicon),
#  NOT in a container.  Builds llama.cpp for Metal, pulls the Muse Glimmer GGUF
#  from Hugging Face, and serves an OpenAI-compatible endpoint on loopback.
#
#    make deps      [MAC] check Xcode CLT + cmake are present
#    make llama     [MAC] clone + build llama.cpp for Metal (pinned)
#    make vendor    [ONLINE] pre-fetch llama.cpp (full history) + the GGUF for an offline rebuild
#    make pull      download the GGUF from Hugging Face (portable: needs only python3)
#    make serve     [MAC] run llama-server on 127.0.0.1 (OpenAI /v1)
#    make serve-mlx [MAC] run the MLX backend instead (often faster on Apple Silicon)
#    make probe     curl the running server to confirm it answers
#
#  Only `deps`, `llama`, `serve`, `serve-mlx` require macOS/Metal.  `pull` and the
#  venv it uses are plain python3 and run anywhere (handy for testing the download).
# ============================================================================

# ---- Template knobs (override on the command line, e.g. `make serve CTX=32768`) ----

# llama.cpp: pin the NEWEST known-good release >= b10353 (the first release with Muse
# Glimmer support, merged 2026-08-10).  Decision (2026-08-18): a later known-good tag,
# not the b10353 floor.  Confirm the concrete tag against the llama.cpp releases page
# before trusting it — this value drifts.
LLAMACPP_TAG  ?= b10353
LLAMACPP_REPO ?= https://github.com/ggml-org/llama.cpp
LLAMACPP_DIR  ?= ./llama.cpp
SERVER_BIN    ?= $(LLAMACPP_DIR)/build/bin/llama-server

# The model(s).  MODEL_FILES is the DOWNLOAD set (space-separated; each entry is passed to
# `hf download --include`, so an entry may be an exact filename OR a glob like '*Q5_K_M*.gguf').
# Default is the single Q4_K_M GGUF, so behavior is unchanged unless you add more.  To vendor a
# quant ladder, list several — run `make check-repo` FIRST to see the repo's real GGUF filenames
# (don't guess; the repo path/names came from a web search — VERIFY on Hugging Face).  The quant
# ladder is documented in tasks/reference/architecture.md.  mmproj (vision) / dflash (drafter) are
# not needed for a coding agent.
MODEL_REPO  ?= meta-models/Muse-Glimmer-30B-GGUF
MODEL_FILES ?= Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf
MODEL_DIR   ?= ./models
# Which downloaded file to SERVE (single).  Defaults to the first of MODEL_FILES; override to serve a
# different quant you vendored, e.g. `make serve MODEL_FILE=<file>`.  (Must be an exact filename, not a
# glob.)  The --alias is constant regardless of quant, so the client crushrc still matches.
MODEL_FILE  ?= $(firstword $(MODEL_FILES))

# OPT-IN full-precision weights (OFF by default — leave FULL_MODEL_FILES empty).  Set it to also vendor
# the full/unquantized model (F16/BF16 GGUF and/or the original BF16 safetensors), from FULL_MODEL_REPO
# if the full weights live in a different repo than the GGUFs (e.g. the base `…-30B` repo vs `…-GGUF`).
# These are archival/conversion artifacts; whether any given precision can be SERVED is the operator's
# concern on their hardware. See tasks/vendor-multiple-glimmer-quants.md.
FULL_MODEL_REPO  ?= $(MODEL_REPO)
FULL_MODEL_FILES ?=

# Stable model ID reported at /v1/models. WITHOUT --alias, llama-server reports the raw -m
# path (e.g. "./models/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"), which changes whenever
# MODEL_FILE changes and is awkward to reference. --alias pins a clean, constant ID so the
# client's crushrc can hardcode `model add muse-glimmer/$(MODEL_ALIAS)` without re-editing on
# a quant/file swap. Keep this in sync with client/entrypoint/crushrc.
MODEL_ALIAS ?= muse-glimmer

# MLX alternative backend (Apple-Silicon-only).
MLX_REPO ?= RadixArk/Muse-Glimmer-q4-MLX

# Serving.
HOST ?= 127.0.0.1
PORT ?= 8080
CTX  ?= 65536        # KV-cache / context window. Raised 32768 -> 65536 (2026-08-21) so the
                     # always-loaded conventions + Crush's own ~18k-token system prompt/tools leave
                     # comfortable room for an actual coding session (the 32k window overflowed —
                     # request was ~50k tokens). The model supports up to n_ctx_train=131072.
                     # COST: bigger KV cache RAM. On the 36 GB Mac with Q4 (~16.8 GB weights) 64k
                     # should fit but may exceed Metal's default wired limit (~24-28 GB) — if the
                     # serve log warns or it swaps, raise it: `sudo sysctl iogpu.wired_limit_mb=<mb>`.
                     # Dial back with `make serve CTX=32768`. KEEP IN SYNC with the client's crushrc
                     # `--context-window` (Crush auto-summarizes at ~80% of it). See
                     # tasks/archive/2026/08/20/context-window-sizing.md.
NGL  ?= 999          # offload all layers to the GPU (Metal)
NP   ?= 1            # parallel slots. 1 = the whole KV cache serves ONE client (Crush), so
                     # prompt caching works and the context isn't split across slots. Raise
                     # only to serve multiple concurrent clients.

# Hugging Face CLI. Prefer a system-installed `hf` (the client image bakes python3-huggingface-hub,
# so `./vendor.sh` runs the download inside that image with no venv); fall back to a local venv for
# standalone macOS use. SYS_HF is empty when no system `hf` is on PATH.
VENV   ?= .venv
PY     ?= python3
HF     := $(VENV)/bin/hf
SYS_HF := $(shell command -v hf 2>/dev/null)
# Resolved CLIs: prefer the system install (client image / dnf python3-huggingface-hub) when present,
# else the venv. If system `hf` exists so does system huggingface_hub, so system python3 can run HfApi.
HF_BIN := $(if $(SYS_HF),hf,$(HF))
PYBIN  := $(if $(SYS_HF),$(PY),$(VENV)/bin/python)

# ---------------------------------------------------------------------------

.PHONY: deps
deps: ## [MAC] check that the Xcode command-line tools and cmake are installed
	@xcode-select -p >/dev/null 2>&1 || { echo "Missing Xcode CLT — run: xcode-select --install"; exit 1; }
	@command -v cmake >/dev/null 2>&1 || { echo "Missing cmake — run: brew install cmake"; exit 1; }
	@echo "deps OK (xcode-select + cmake present)"

.PHONY: llama
llama: ## [MAC] clone + build llama.cpp for Metal, pinned to LLAMACPP_TAG
	@# FULL clone (history kept, checked out at the tag) so the checkout doubles as the vendored
	@# source for an offline rebuild. Reused if $(LLAMACPP_DIR) already exists — so on the airgap
	@# box a pre-vendored checkout is built in place with no network.
	@test -d $(LLAMACPP_DIR) || git clone --branch $(LLAMACPP_TAG) $(LLAMACPP_REPO) $(LLAMACPP_DIR)
	cmake -S $(LLAMACPP_DIR) -B $(LLAMACPP_DIR)/build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
	cmake --build $(LLAMACPP_DIR)/build -j
	@echo "built $(SERVER_BIN)"

.PHONY: vendor
vendor: ## [ONLINE] pre-fetch llama.cpp (full history @ LLAMACPP_TAG) + the GGUF, for an offline rebuild/serve
	@# Populates the two server-side internet-sourced artifacts WITHOUT building (the Metal build
	@# happens later on the airgap Mac via `make llama`, which reuses this checkout). See
	@# tasks/vendor-build-sources-for-airgap-rebuild.md.
	@test -d $(LLAMACPP_DIR) || git clone --branch $(LLAMACPP_TAG) $(LLAMACPP_REPO) $(LLAMACPP_DIR)
	$(MAKE) pull
	@echo "vendored: $(LLAMACPP_DIR) (full history @ $(LLAMACPP_TAG)) + $(MODEL_DIR)/: $(MODEL_FILES) $(FULL_MODEL_FILES)"
	@echo "carry the repo (server/llama.cpp + server/models) to the airgap box; build llama.cpp there for your backend + serve the GGUF (your hardware, your call)"

# The venv holds the `hf` CLI (huggingface_hub).  Built once; `pull` depends on it.
$(HF):
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip huggingface_hub

.PHONY: venv
venv: $(HF) ## create the python venv with the Hugging Face CLI (huggingface_hub)

.PHONY: pull
pull: $(if $(SYS_HF),,venv) ## download MODEL_FILES (+ opt-in FULL_MODEL_FILES) into MODEL_DIR (system `hf` if present, else venv)
	@for f in $(MODEL_FILES); do \
	    echo ">> $(MODEL_REPO)  $$f"; \
	    $(HF_BIN) download $(MODEL_REPO) --include "$$f" --local-dir $(MODEL_DIR) || exit 1; \
	done
	@if [ -n "$(strip $(FULL_MODEL_FILES))" ]; then \
	    for f in $(FULL_MODEL_FILES); do \
	        echo ">> [full] $(FULL_MODEL_REPO)  $$f"; \
	        $(HF_BIN) download $(FULL_MODEL_REPO) --include "$$f" --local-dir $(MODEL_DIR) || exit 1; \
	    done; \
	fi
	@echo "models in $(MODEL_DIR): $(MODEL_FILES) $(FULL_MODEL_FILES)"

.PHONY: check-repo
check-repo: $(if $(SYS_HF),,venv) ## list MODEL_REPO's GGUF files on Hugging Face (discovery for MODEL_FILES; no download)
	@$(PYBIN) -c "from huggingface_hub import HfApi; \
	    info = HfApi().model_info('$(MODEL_REPO)'); \
	    ggufs = sorted(s.rfilename for s in info.siblings if s.rfilename.endswith('.gguf')); \
	    print('repo OK: $(MODEL_REPO) (%d GGUFs)' % len(ggufs)); \
	    [print('  ', f) for f in ggufs]"

.PHONY: serve
serve: ## [MAC] run llama-server on loopback with an OpenAI-compatible /v1 endpoint
	$(SERVER_BIN) -m $(MODEL_DIR)/$(MODEL_FILE) --alias $(MODEL_ALIAS) --host $(HOST) --port $(PORT) \
		-ngl $(NGL) -c $(CTX) --parallel $(NP)

.PHONY: serve-mlx
serve-mlx: ## [MAC] run the MLX backend instead of llama.cpp (Apple-Silicon-only)
	@# mlx-lm installs/runs only on Apple Silicon; kept in its own venv so it can't
	@# interfere with the huggingface_hub venv above.
	@test -d .venv-mlx || $(PY) -m venv .venv-mlx
	.venv-mlx/bin/pip install --upgrade pip mlx-lm
	.venv-mlx/bin/mlx_lm.server --model $(MLX_REPO) --host $(HOST) --port $(PORT)

.PHONY: probe
probe: ## curl the running server (list models) to confirm it answers
	curl -sS http://$(HOST):$(PORT)/v1/models

.PHONY: smoke
smoke: ## one chat-completion round-trip — confirms the model actually GENERATES, not just lists
	curl -sS http://$(HOST):$(PORT)/v1/chat/completions \
		-H 'Content-Type: application/json' \
		-d '{"messages":[{"role":"user","content":"Reply with exactly the word: OK"}],"max_tokens":16,"temperature":0}'
	@echo

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'
