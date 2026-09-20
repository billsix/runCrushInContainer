# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
.DEFAULT_GOAL := help

# ============================================================================
#  runCrushInContainer — SERVER side.  Runs NATIVELY on macOS (Apple Silicon),
#  NOT in a container.  Builds llama.cpp for Metal, pulls the model GGUFs from
#  Hugging Face, and serves an OpenAI-compatible endpoint on loopback.
#
#  FIVE models, ONE way to run each: `MODEL=<m>` where <m> is glimmer (default),
#  gemma, granite, devstral or qwen.  Each has a FIXED, non-configurable port
#  (8080..8084) so the client discovers whichever is live -- see the table below.
#
#  Which models are pulled/served/offered is gated by MODEL_COUNTRIES, a country
#  allowlist (default `US`; override `US,FR` or `ALL`).  See the MODEL_COUNTRIES block.
#
#    make deps               [MAC] check Xcode CLT + cmake are present
#    make llama              [MAC] clone + build llama.cpp for Metal (pinned)
#    make vendor             [ONLINE] pre-fetch llama.cpp (full history) + the ACTIVE GGUFs for an offline rebuild
#    make pull               download the ACTIVE models' GGUFs from Hugging Face (portable: needs only python3)
#    make checksums-refresh  compute the MD5+SHA-256+BLAKE2b manifest for the downloaded GGUFs
#    make serve MODEL=<m>    [MAC] verify the model's checksum, then run llama-server on 127.0.0.1:<its port> (OpenAI /v1)
#    make serve-mlx          [MAC] run the MLX backend instead (Glimmer only; often faster on Apple Silicon)
#    make probe MODEL=<m>    curl that model's server to confirm it answers
#    make smoke MODEL=<m>    one chat round-trip -- confirms it GENERATES
#
#  "ACTIVE" = the models whose country is in MODEL_COUNTRIES (default US -> glimmer, gemma, granite).
#  Only `deps`, `llama`, `serve`, `serve-mlx` require macOS/Metal.  `pull`, `checksums-*` and the
#  venv `pull` uses are plain python3 and run anywhere (handy for testing the download).
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

# ---- The models: a table keyed by MODEL, gated by MODEL_COUNTRIES (country allowlist) ----
# `MODEL=` selects ONE row for serve/probe/smoke/check-repo; pull/vendor walk the ACTIVE rows
# (whose country is in MODEL_COUNTRIES -- see the MODEL_COUNTRIES block below).  Per row: the
# Hugging Face repo, the exact GGUF filename (an `hf download --include` pattern), the alias
# llama-server reports at /v1/models, the FIXED port, and the model's country of origin
# (org HQ, ISO-3166 alpha-2).  Ports are deliberately not knobs: the client probes the range and
# offers whichever are live, so nobody has to remember which model is on which port.  KEEP IN SYNC
# with client/entrypoint/crushrc (the port list its probe walks + model IDs) and
# client/entrypoint/shell.sh (the LOCALHOST_ONLY socket-bridge port list).
#
# Every model here is OSI-approved (Apache-2.0 *weights*) BY CONSTRUCTION -- enforced at SELECTION
# time (a model whose weights carry use restrictions, e.g. DeepSeek/Llama-license, is not added),
# so there is no runtime license flag; country is the runtime axis (MODEL_COUNTRIES).  Each row's
# repo/filename was confirmed via the Hugging Face API on 2026-09-20 -- re-VERIFY with
# `make check-repo MODEL=<m>`.  Sizes are the Q4_K_M download (each fits the 36 GB Mac one-at-a-time).
#
# glimmer:  Meta's Muse Glimmer 30B, Q4_K_M (~16.8 GB), Apache-2.0.  US.  Quant ladder in
#           tasks/reference/architecture.md; mmproj/dflash extras not needed.
# gemma:    Google's Gemma 4 26B-A4B (MoE, 3.8B active), OFFICIAL QAT Q4_0 GGUF (~14.4 GB),
#           Apache-2.0 (Gemma 1-3 are NOT -- never substitute a gemma-3 repo).  US.
# granite:  IBM Granite 34B Code Instruct (8k ctx), Q4_K_M (~21.4 GB), Apache-2.0.  US.  The US
#           coder that makes the MODEL_COUNTRIES=US default useful beyond the two general models.
# devstral: Mistral's Devstral Small (2507, ~24B), Q4_K_M (~14.3 GB), Apache-2.0.  FR.  Purpose-built
#           agentic coder (OpenHands/SWE-bench) from the OFFICIAL mistralai repo; the top France pick.
# qwen:     Alibaba's Qwen3-Coder-30B-A3B-Instruct (MoE, ~3.3B active), Q4_K_M (~18.6 GB),
#           Apache-2.0.  CN.  Strong agentic coder; the ~30B MoE variant (the 480B flagship won't fit).
MODELS := glimmer gemma granite devstral qwen
MODEL  ?= glimmer

MODEL_REPO_glimmer    := meta-models/Muse-Glimmer-30B-GGUF
MODEL_FILE_glimmer    := Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf
MODEL_ALIAS_glimmer   := muse-glimmer
MODEL_PORT_glimmer    := 8080
MODEL_COUNTRY_glimmer := US

MODEL_REPO_gemma    := google/gemma-4-26B-A4B-it-qat-q4_0-gguf
MODEL_FILE_gemma    := gemma-4-26B_q4_0-it.gguf
MODEL_ALIAS_gemma   := gemma-4
MODEL_PORT_gemma    := 8081
MODEL_COUNTRY_gemma := US

MODEL_REPO_granite    := ibm-granite/granite-34b-code-instruct-8k-GGUF
MODEL_FILE_granite    := granite-34b-code-instruct.Q4_K_M.gguf
MODEL_ALIAS_granite   := granite-code
MODEL_PORT_granite    := 8082
MODEL_COUNTRY_granite := US

MODEL_REPO_devstral    := mistralai/Devstral-Small-2507_gguf
MODEL_FILE_devstral    := Devstral-Small-2507-Q4_K_M.gguf
MODEL_ALIAS_devstral   := devstral
MODEL_PORT_devstral    := 8083
MODEL_COUNTRY_devstral := FR

MODEL_REPO_qwen    := unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF
MODEL_FILE_qwen    := Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf
MODEL_ALIAS_qwen   := qwen3-coder
MODEL_PORT_qwen    := 8084
MODEL_COUNTRY_qwen := CN

# ---- MODEL_COUNTRIES: the country allowlist that gates pull / vendor / serve TOGETHER ----
# A comma-separated allowlist of countries.  DEFAULT `US` when unset (safe default: only US-origin
# models are pulled/served/offered -- opt into others explicitly).  Special value `ALL` = every
# country (no filter).  Friendly aliases normalize to ISO-3166 alpha-2: USA->US, France->FR,
# China->CN (canonical US/FR/CN pass through).  Examples:
#   make pull                       -> US only (glimmer, gemma, granite)
#   make pull MODEL_COUNTRIES=US,FR -> adds Devstral (FR)
#   make pull MODEL_COUNTRIES=ALL   -> all five
MODEL_COUNTRIES ?= US

comma := ,
empty :=
space := $(empty) $(empty)
# Split MODEL_COUNTRIES on commas, then normalize each token's friendly alias to its alpha-2 code.
_countries_raw := $(subst $(comma),$(space),$(MODEL_COUNTRIES))
normalize_country = $(subst USA,US,$(subst France,FR,$(subst China,CN,$(1))))
_COUNTRIES := $(foreach c,$(_countries_raw),$(call normalize_country,$(c)))

# ACTIVE_MODELS = the models whose country is in the allowlist (ALL disables the filter).
# pull/vendor/checksums walk this list; serve/serve-mlx refuse a MODEL= outside it (per-recipe).
ifeq ($(filter ALL,$(_COUNTRIES)),ALL)
ACTIVE_MODELS := $(MODELS)
else
ACTIVE_MODELS := $(strip $(foreach m,$(MODELS),$(if $(filter $(MODEL_COUNTRY_$(m)),$(_COUNTRIES)),$(m))))
endif
ACTIVE_FILES := $(strip $(foreach m,$(ACTIVE_MODELS),$(MODEL_FILE_$(m))))

# Guard: an unknown MODEL= names the valid values instead of silently serving nothing.  (Country
# gating of serve/probe/smoke is enforced PER-RECIPE below, NOT here, so pull/vendor/checksum
# targets run regardless of the default MODEL under any MODEL_COUNTRIES.)
ifeq ($(filter $(MODEL),$(MODELS)),)
$(error MODEL=$(MODEL) is not one of: $(MODELS))
endif

# The selected row.  These are the names the rest of the file (and the docs) use.  A
# command-line override still wins over `:=`, so `make serve MODEL_FILE=<other downloaded
# quant>` serves a different Glimmer quant under the same alias/port (must be an exact filename).
MODEL_REPO    := $(MODEL_REPO_$(MODEL))
MODEL_FILE    := $(MODEL_FILE_$(MODEL))
MODEL_ALIAS   := $(MODEL_ALIAS_$(MODEL))
MODEL_COUNTRY := $(MODEL_COUNTRY_$(MODEL))
override PORT := $(MODEL_PORT_$(MODEL))
MODEL_DIR   ?= ./models

# ---- Checksum manifest (multi-hash: MD5 + SHA-256 + BLAKE2b per vendored file) ----
# `make pull`/vendor verify each downloaded ACTIVE file against this manifest (fail loudly on
# mismatch, quarantine the bad file); `make serve` re-verifies the selected model's file before
# launching llama-server (refuse to serve on mismatch).  `make checksums-refresh` regenerates it
# -> a reviewable diff.  Stdlib-only tool (no venv needed), so the serve gate runs on the Mac.
CHECKSUMS     ?= models.CHECKSUMS
CHECKSUM_TOOL ?= tools/checksum.py

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
	@# An existing checkout is moved to LLAMACPP_TAG (2026-09-10: a tag bump used to be silently
	@# ignored — the target only cloned when the dir was missing). Try the local checkout first
	@# (works offline when the vendored full-history clone already has the tag); only if the tag is
	@# unknown locally, fetch it — that path needs the network and is the online box's job.
	@git -C $(LLAMACPP_DIR) checkout -q $(LLAMACPP_TAG) 2>/dev/null || \
	    { git -C $(LLAMACPP_DIR) fetch -q --tags origin && git -C $(LLAMACPP_DIR) checkout -q $(LLAMACPP_TAG); }
	@echo "llama.cpp at $$(git -C $(LLAMACPP_DIR) describe --tags --always)"
	@# A stale build/CMakeCache.txt from an earlier configure can fail the configure step (seen
	@# 2026-09-10 on the Mac: cpp-httplib "OpenSSL::SSL target not found"); `rm -rf` the build dir.
	cmake -S $(LLAMACPP_DIR) -B $(LLAMACPP_DIR)/build -DGGML_METAL=ON -DCMAKE_BUILD_TYPE=Release
	cmake --build $(LLAMACPP_DIR)/build -j
	@echo "built $(SERVER_BIN)"

.PHONY: vendor
vendor: ## [ONLINE] pre-fetch llama.cpp (full history @ LLAMACPP_TAG) + the ACTIVE models' GGUFs, for an offline rebuild/serve
	@# Populates the two server-side internet-sourced artifacts WITHOUT building (the Metal build
	@# happens later on the airgap Mac via `make llama`, which reuses this checkout). Only the
	@# ACTIVE models (MODEL_COUNTRIES) are fetched. See tasks/vendor-build-sources-for-airgap-rebuild.md.
	@test -d $(LLAMACPP_DIR) || git clone --branch $(LLAMACPP_TAG) $(LLAMACPP_REPO) $(LLAMACPP_DIR)
	$(MAKE) pull
	@echo "vendored: $(LLAMACPP_DIR) (full history @ $(LLAMACPP_TAG)) + $(MODEL_DIR)/: $(ACTIVE_FILES) $(FULL_MODEL_FILES)"
	@echo "carry the repo (server/llama.cpp + server/models) to the airgap box; build llama.cpp there for your backend + serve an ACTIVE GGUF with make serve MODEL=<$(ACTIVE_MODELS)> (your hardware, your call)"

# The venv holds the `hf` CLI (huggingface_hub).  Built once; `pull` depends on it.
$(HF):
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip huggingface_hub

.PHONY: venv
venv: $(HF) ## create the python venv with the Hugging Face CLI (huggingface_hub)

.PHONY: pull
pull: $(if $(SYS_HF),,venv) ## download the ACTIVE models' GGUFs (+ opt-in MODEL_FILES / FULL_MODEL_FILES) into MODEL_DIR, then verify checksums
	@# One download per ACTIVE_MODELS row (gated by MODEL_COUNTRIES); $(foreach) expands each
	@# row's repo/file at make time.  After each file, verify its multi-hash checksum (see below).
	@$(foreach m,$(ACTIVE_MODELS),echo ">> [$m] $(MODEL_REPO_$m)  $(MODEL_FILE_$m)" && \
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
	@echo "models in $(MODEL_DIR): $(ACTIVE_FILES) $(MODEL_FILES) $(FULL_MODEL_FILES)"
	@# Integrity gate: verify every downloaded ACTIVE file against models.CHECKSUMS.  A mismatch of
	@# ANY algorithm fails the pull and quarantines the bad file so `make serve` can't load it.
	@# Unpinned files (a new quant, or before the manifest exists) warn but don't block ad-hoc work.
	$(MAKE) checksums-verify

.PHONY: check-repo
check-repo: $(if $(SYS_HF),,venv) ## list the selected MODEL's repo GGUF files on Hugging Face (make check-repo MODEL=gemma; no download)
	@$(PYBIN) -c "from huggingface_hub import HfApi; \
	    info = HfApi().model_info('$(MODEL_REPO)'); \
	    ggufs = sorted(s.rfilename for s in info.siblings if s.rfilename.endswith('.gguf')); \
	    print('repo OK: $(MODEL_REPO) (%d GGUFs)' % len(ggufs)); \
	    [print('  ', f) for f in ggufs]"

.PHONY: checksums-refresh
checksums-refresh: ## compute MD5+SHA-256+BLAKE2b for the ACTIVE models' downloaded GGUFs -> update models.CHECKSUMS (reviewable diff)
	@$(PY) $(CHECKSUM_TOOL) write $(CHECKSUMS) $(foreach f,$(ACTIVE_FILES),$(MODEL_DIR)/$(f))
	@echo "wrote $(CHECKSUMS) ($(words $(ACTIVE_FILES)) active file(s)); review the diff and commit it"

.PHONY: checksums-verify
checksums-verify: ## verify the ACTIVE models' downloaded GGUFs against models.CHECKSUMS (fail loudly + quarantine on mismatch)
	@# Verify all three hashes for each ACTIVE file.  A mismatch of ANY algorithm exits nonzero and
	@# renames the bad file to <file>.corrupt so it can't be served.  An unpinned file (a new quant,
	@# or before `make checksums-refresh` has ever run) warns but does not block.
	@$(PY) $(CHECKSUM_TOOL) verify --warn-unpinned --quarantine $(CHECKSUMS) $(foreach f,$(ACTIVE_FILES),$(MODEL_DIR)/$(f))

# Guard shared by serve/serve-mlx: refuse a MODEL= whose country is not in MODEL_COUNTRIES.
.PHONY: serve-country-guard
serve-country-guard:
	@case " $(ACTIVE_MODELS) " in \
	  *" $(MODEL) "*) : ;; \
	  *) echo "REFUSING: MODEL=$(MODEL) (country $(MODEL_COUNTRY)) is not in MODEL_COUNTRIES=$(MODEL_COUNTRIES)."; \
	     echo "  active models: $(ACTIVE_MODELS)"; \
	     echo "  to serve it, include its country, e.g. make serve MODEL=$(MODEL) MODEL_COUNTRIES=$(MODEL_COUNTRY)"; \
	     exit 1 ;; \
	esac

.PHONY: serve
serve: serve-country-guard ## [MAC] verify checksum + run llama-server for MODEL=<glimmer|gemma|granite|devstral|qwen> on its port (OpenAI /v1)
	@# Integrity gate: re-verify the selected model's file against models.CHECKSUMS BEFORE launching.
	@# On a mismatch (on-disk bit-rot, a bad copy, tampering) this exits nonzero and llama-server is
	@# never started.  Fast: it hashes only the one file about to be loaded.
	@$(PY) $(CHECKSUM_TOOL) verify --warn-unpinned $(CHECKSUMS) $(MODEL_DIR)/$(MODEL_FILE)
	$(SERVER_BIN) -m $(MODEL_DIR)/$(MODEL_FILE) --alias $(MODEL_ALIAS) --host $(HOST) --port $(PORT) \
		-ngl $(NGL) -c $(CTX) --parallel $(NP)

.PHONY: serve-mlx
serve-mlx: serve-country-guard ## [MAC] run the MLX backend instead of llama.cpp (Apple-Silicon-only; Glimmer only)
	@# mlx-lm installs/runs only on Apple Silicon; kept in its own venv so it can't
	@# interfere with the huggingface_hub venv above.  Glimmer-only: no MLX repo was
	@# selected for Gemma 4 (a separate decision); refuse rather than serve the wrong model.
	@# (No checksum gate here: MLX serves from MLX_REPO, not the vendored GGUF.)
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
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
