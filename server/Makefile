.DEFAULT_GOAL := help

# ============================================================================
#  runCrushInContainer — SERVER side.  Runs NATIVELY on macOS (Apple Silicon),
#  NOT in a container.  Builds llama.cpp for Metal, pulls the Muse Glimmer GGUF
#  from Hugging Face, and serves an OpenAI-compatible endpoint on loopback.
#
#    make deps      [MAC] check Xcode CLT + cmake are present
#    make llama     [MAC] clone + build llama.cpp for Metal (pinned)
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

# The model.  Q4_K_M (~16.8 GB) is the default quant for a 36 GB Mac (see the task doc
# tasks/crush-local-llm-bringup.md for the full quant ladder).  VERIFY the repo path and
# file name resolve on Hugging Face before relying on them — they came from a web search
# and may differ.  The mmproj (vision) file is NOT needed for a coding agent; skip it.
MODEL_REPO ?= meta-models/Muse-Glimmer-30B-GGUF
MODEL_FILE ?= Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf
MODEL_DIR  ?= ./models

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
CTX  ?= 32768        # KV-cache / context window. Bigger = room for a coding agent's growing
                     # context AND for prompt-cache restore to succeed (a too-small window is
                     # why llama-server logged "failed to restore kv cache" and reprocessed
                     # the prompt each turn). Costs some RAM for the KV cache — fine on 36 GB
                     # with Q4. Dial back with `make serve CTX=16384`.
                     # KEEP IN SYNC with the client's crushrc `--context-window` (see
                     # client/entrypoint/crushrc) — Crush auto-summarizes at ~80% of that
                     # number, so if they disagree Crush trims history early or overruns.
                     # Going bigger (e.g. CTX=65536) roughly doubles KV RAM and may exceed
                     # Metal's default wired limit (~24-28 GB); raise it first with
                     # `sudo sysctl iogpu.wired_limit_mb=<mb>`. See tasks/archive/2026/08/20/context-window-sizing.md.
NGL  ?= 999          # offload all layers to the GPU (Metal)
NP   ?= 1            # parallel slots. 1 = the whole KV cache serves ONE client (Crush), so
                     # prompt caching works and the context isn't split across slots. Raise
                     # only to serve multiple concurrent clients.

# Python venv for the Hugging Face CLI (portable — no Metal needed).
VENV ?= .venv
PY   ?= python3
HF   := $(VENV)/bin/hf

# ---------------------------------------------------------------------------

.PHONY: deps
deps: ## [MAC] check that the Xcode command-line tools and cmake are installed
	@xcode-select -p >/dev/null 2>&1 || { echo "Missing Xcode CLT — run: xcode-select --install"; exit 1; }
	@command -v cmake >/dev/null 2>&1 || { echo "Missing cmake — run: brew install cmake"; exit 1; }
	@echo "deps OK (xcode-select + cmake present)"

.PHONY: llama
llama: ## [MAC] clone + build llama.cpp for Metal, pinned to LLAMACPP_TAG
	@test -d $(LLAMACPP_DIR) || git clone --depth 1 --branch $(LLAMACPP_TAG) $(LLAMACPP_REPO) $(LLAMACPP_DIR)
	cmake -S $(LLAMACPP_DIR) -B $(LLAMACPP_DIR)/build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
	cmake --build $(LLAMACPP_DIR)/build -j
	@echo "built $(SERVER_BIN)"

# The venv holds the `hf` CLI (huggingface_hub).  Built once; `pull` depends on it.
$(HF):
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip huggingface_hub

.PHONY: venv
venv: $(HF) ## create the python venv with the Hugging Face CLI (huggingface_hub)

.PHONY: pull
pull: venv ## download the GGUF from Hugging Face into MODEL_DIR (portable)
	$(HF) download $(MODEL_REPO) --include "$(MODEL_FILE)" --local-dir $(MODEL_DIR)
	@echo "model at $(MODEL_DIR)/$(MODEL_FILE)"

.PHONY: check-repo
check-repo: venv ## verify MODEL_REPO/MODEL_FILE resolve on Hugging Face WITHOUT downloading
	$(VENV)/bin/python -c "from huggingface_hub import HfApi; \
	    info = HfApi().model_info('$(MODEL_REPO)'); \
	    files = [s.rfilename for s in info.siblings]; \
	    print('repo OK:', '$(MODEL_REPO)'); \
	    print('MODEL_FILE present:', '$(MODEL_FILE)' in files); \
	    print('n files:', len(files))"

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
