# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
.DEFAULT_GOAL := help

# ============================================================================
#  runCrushInContainer — SERVER side.  Runs NATIVELY on macOS (Apple Silicon),
#  NOT in a container.  Builds llama.cpp for Metal, pulls the model GGUFs from
#  Hugging Face, and serves an OpenAI-compatible endpoint on loopback.
#
#  TWO models, ONE way to run them: `MODEL=glimmer` (default) or `MODEL=gemma`.
#  Each has a FIXED, non-configurable port -- Glimmer 8080, Gemma 8081 -- so the
#  client crushrc and the SSH tunnel never have to be told which is which.
#
#    make deps               [MAC] check Xcode CLT + cmake are present
#    make llama              [MAC] clone + build llama.cpp for Metal (pinned)
#    make vendor             [ONLINE] pre-fetch llama.cpp (full history) + BOTH GGUFs for an offline rebuild
#    make pull               download BOTH GGUFs from Hugging Face (portable: needs only python3)
#    make serve MODEL=<m>    [MAC] run llama-server for one model on 127.0.0.1:<its port> (OpenAI /v1)
#    make serve-mlx          [MAC] run the MLX backend instead (Glimmer only; often faster on Apple Silicon)
#    make probe MODEL=<m>    curl that model's server to confirm it answers
#    make smoke MODEL=<m>    one chat round-trip -- confirms it GENERATES
#
#  Only `deps`, `llama`, `serve`, `serve-mlx` require macOS/Metal.  `pull` and the
#  venv it uses are plain python3 and run anywhere (handy for testing the download).
# ============================================================================

# ---- Template knobs (override on the command line, e.g. `make serve CTX=32768`) ----

# llama.cpp: pin the NEWEST known-good release.  Floors: b10353 (2026-08-10, first Muse
# Glimmer support) and, for Gemma 4, anything after PR #28335 (2026-09-04, Gemma 4 vision
# handling; the Gemma 4 conversion fix #26882 is 2026-08-12).  Bumped b10353 -> b10883
# (2026-09-09, newest at the time) on 2026-09-10 for Gemma 4 -- the maintainer's decision
# (tasks/reference/gemma-4-alongside-glimmer.md §6).  "Known-good" means it built and `make smoke`d
# on the Mac for BOTH models; until that run, roll back per-invocation with
# `make llama LLAMACPP_TAG=b10353` if Glimmer misbehaves.  Confirm the concrete tag against
# the llama.cpp releases page before trusting it -- this value drifts.
LLAMACPP_TAG  ?= b10883
LLAMACPP_REPO ?= https://github.com/ggml-org/llama.cpp
LLAMACPP_DIR  ?= ./llama.cpp
SERVER_BIN    ?= $(LLAMACPP_DIR)/build/bin/llama-server

# ---- The two models: a table keyed by MODEL (glimmer | gemma) ----
# `MODEL=` selects ONE row for serve/probe/smoke/check-repo; pull/vendor walk BOTH rows.
# Per row: the Hugging Face repo, the exact GGUF filename (an `hf download --include` pattern),
# the alias llama-server reports at /v1/models, and the FIXED port.  Ports are deliberately
# not knobs: the client crushrc hardcodes them and the SSH tunnel forwards both, so nobody
# ever has to remember which model is on which port.  KEEP IN SYNC with
# client/entrypoint/crushrc (base-url ports + model IDs) and client/entrypoint/shell.sh.
#
# glimmer: Meta's Muse Glimmer 30B, Q4_K_M (~16.8 GB), Apache-2.0.  Repo path/filename came
#          from a web search -- VERIFY on Hugging Face (`make check-repo`); the quant ladder is
#          documented in tasks/reference/architecture.md.  mmproj/dflash extras not needed.
# gemma:   Google's Gemma 4 26B-A4B (MoE, 3.8B active), the OFFICIAL QAT Q4_0 GGUF (~14.4 GB),
#          Apache-2.0 (Gemma 1-3 are NOT -- never substitute a gemma-3 repo).  Chosen 2026-09-10
#          over the 31B dense for speed and for fitting beside Glimmer; the mmproj (vision) file
#          in the same repo is not needed for a coding agent.  Filenames verified via the HF API
#          on 2026-09-10 (tasks/reference/gemma-4-alongside-glimmer.md).
MODELS := glimmer gemma
MODEL  ?= glimmer

MODEL_REPO_glimmer  := meta-models/Muse-Glimmer-30B-GGUF
MODEL_FILE_glimmer  := Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf
MODEL_ALIAS_glimmer := muse-glimmer
MODEL_PORT_glimmer  := 8080

MODEL_REPO_gemma  := google/gemma-4-26B-A4B-it-qat-q4_0-gguf
MODEL_FILE_gemma  := gemma-4-26B_q4_0-it.gguf
MODEL_ALIAS_gemma := gemma-4
MODEL_PORT_gemma  := 8081

# Guard: an unknown MODEL= names the two valid values instead of silently serving nothing.
ifeq ($(filter $(MODEL),$(MODELS)),)
$(error MODEL=$(MODEL) is not one of: $(MODELS))
endif

# The selected row.  These are the names the rest of the file (and the docs) use.  A
# command-line override still wins over `:=`, so `make serve MODEL_FILE=<other downloaded
# quant>` serves a different Glimmer quant under the same alias/port (must be an exact filename).
MODEL_REPO  := $(MODEL_REPO_$(MODEL))
MODEL_FILE  := $(MODEL_FILE_$(MODEL))
MODEL_ALIAS := $(MODEL_ALIAS_$(MODEL))
override PORT := $(MODEL_PORT_$(MODEL))
MODEL_DIR   ?= ./models

# OPT-IN extra downloads from the SELECTED model's repo (empty by default): exact filenames or
# `hf --include` globs, pulled in addition to the row's GGUF.  `make pull MODEL_FILES="*.gguf"`
# grabs every Glimmer quant (the vendor.sh FULL=1 preset); `make pull MODEL=gemma
# MODEL_FILES="*mmproj*"` adds Gemma's vision projector.  `make check-repo` lists real filenames.
MODEL_FILES ?=

# OPT-IN full-precision weights (OFF by default -- leave FULL_MODEL_FILES empty).  Set it to also
# vendor the full/unquantized model (F16/BF16 GGUF and/or the original BF16 safetensors), from
# FULL_MODEL_REPO if the full weights live in a different repo than the GGUFs (e.g. the base
# `...-30B` repo vs `...-GGUF`).  These are archival/conversion artifacts; whether any given
# precision can be SERVED is the operator's concern on their hardware.  Glimmer-only today.
FULL_MODEL_REPO  ?= $(MODEL_REPO_glimmer)
FULL_MODEL_FILES ?=
# MLX alternative backend (Apple-Silicon-only).
MLX_REPO ?= RadixArk/Muse-Glimmer-q4-MLX

# Serving.  (PORT is NOT a knob -- it comes from the MODEL row above.)
HOST ?= 127.0.0.1
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
vendor: ## [ONLINE] pre-fetch llama.cpp (full history @ LLAMACPP_TAG) + BOTH models' GGUFs, for an offline rebuild/serve
	@# Populates the two server-side internet-sourced artifacts WITHOUT building (the Metal build
	@# happens later on the airgap Mac via `make llama`, which reuses this checkout). See
	@# tasks/vendor-build-sources-for-airgap-rebuild.md.
	@test -d $(LLAMACPP_DIR) || git clone --branch $(LLAMACPP_TAG) $(LLAMACPP_REPO) $(LLAMACPP_DIR)
	$(MAKE) pull
	@echo "vendored: $(LLAMACPP_DIR) (full history @ $(LLAMACPP_TAG)) + $(MODEL_DIR)/: $(MODEL_FILE_glimmer) $(MODEL_FILE_gemma) $(FULL_MODEL_FILES)"
	@echo "carry the repo (server/llama.cpp + server/models) to the airgap box; build llama.cpp there for your backend + serve either GGUF with make serve MODEL=glimmer|gemma (your hardware, your call)"

# The venv holds the `hf` CLI (huggingface_hub).  Built once; `pull` depends on it.
$(HF):
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip huggingface_hub

.PHONY: venv
venv: $(HF) ## create the python venv with the Hugging Face CLI (huggingface_hub)

.PHONY: pull
pull: $(if $(SYS_HF),,venv) ## download BOTH models' GGUFs (+ opt-in MODEL_FILES / FULL_MODEL_FILES) into MODEL_DIR (system `hf` if present, else venv)
	@# One download per MODELS row; $(foreach) expands each row's repo/file at make time.
	@$(foreach m,$(MODELS),echo ">> [$m] $(MODEL_REPO_$m)  $(MODEL_FILE_$m)" && \
	    $(HF_BIN) download $(MODEL_REPO_$m) --include "$(MODEL_FILE_$m)" --local-dir $(MODEL_DIR) || exit 1;)
	@for f in $(MODEL_FILES); do \
	    echo ">> [$(MODEL) extra] $(MODEL_REPO)  $$f"; \
	    $(HF_BIN) download $(MODEL_REPO) --include "$$f" --local-dir $(MODEL_DIR) || exit 1; \
	done
	@if [ -n "$(strip $(FULL_MODEL_FILES))" ]; then \
	    for f in $(FULL_MODEL_FILES); do \
	        echo ">> [full] $(FULL_MODEL_REPO)  $$f"; \
	        $(HF_BIN) download $(FULL_MODEL_REPO) --include "$$f" --local-dir $(MODEL_DIR) || exit 1; \
	    done; \
	fi
	@echo "models in $(MODEL_DIR): $(MODEL_FILE_glimmer) $(MODEL_FILE_gemma) $(MODEL_FILES) $(FULL_MODEL_FILES)"

.PHONY: check-repo
check-repo: $(if $(SYS_HF),,venv) ## list the selected MODEL's repo GGUF files on Hugging Face (make check-repo MODEL=gemma; no download)
	@$(PYBIN) -c "from huggingface_hub import HfApi; \
	    info = HfApi().model_info('$(MODEL_REPO)'); \
	    ggufs = sorted(s.rfilename for s in info.siblings if s.rfilename.endswith('.gguf')); \
	    print('repo OK: $(MODEL_REPO) (%d GGUFs)' % len(ggufs)); \
	    [print('  ', f) for f in ggufs]"

.PHONY: serve
serve: ## [MAC] run llama-server for MODEL=glimmer (8080, default) or MODEL=gemma (8081) on loopback, OpenAI /v1
	$(SERVER_BIN) -m $(MODEL_DIR)/$(MODEL_FILE) --alias $(MODEL_ALIAS) --host $(HOST) --port $(PORT) \
		-ngl $(NGL) -c $(CTX) --parallel $(NP)

.PHONY: serve-mlx
serve-mlx: ## [MAC] run the MLX backend instead of llama.cpp (Apple-Silicon-only; Glimmer only)
	@# mlx-lm installs/runs only on Apple Silicon; kept in its own venv so it can't
	@# interfere with the huggingface_hub venv above.  Glimmer-only: no MLX repo was
	@# selected for Gemma 4 (a separate decision); refuse rather than serve the wrong model.
	@test "$(MODEL)" = glimmer || { echo "serve-mlx supports MODEL=glimmer only"; exit 1; }
	@test -d .venv-mlx || $(PY) -m venv .venv-mlx
	.venv-mlx/bin/pip install --upgrade pip mlx-lm
	.venv-mlx/bin/mlx_lm.server --model $(MLX_REPO) --host $(HOST) --port $(PORT)

.PHONY: probe
probe: ## curl the selected MODEL's server (list models) to confirm it answers -- make probe MODEL=gemma
	curl -sS http://$(HOST):$(PORT)/v1/models

.PHONY: smoke
smoke: ## one chat-completion round-trip against the selected MODEL -- confirms it actually GENERATES, not just lists
	curl -sS http://$(HOST):$(PORT)/v1/chat/completions \
		-H 'Content-Type: application/json' \
		-d '{"messages":[{"role":"user","content":"Reply with exactly the word: OK"}],"max_tokens":16,"temperature":0}'
	@echo

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'
