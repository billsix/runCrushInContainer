#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# Vendor everything for an OFFLINE / airgap rebuild. Runs the vendoring INSIDE the client
# image, so this online host needs only **podman + make** — no host go/git/python3.
#
#   ./vendor.sh            DEFAULT: Crush + llama.cpp source + ONE model quant (Q4_K_M)
#   FULL=1 ./vendor.sh     FULL:    the above + ALL quant GGUFs + the full-precision weights
#
# Populates (all gitignored, all fetched from the public internet):
#   client/vendor/crush     Crush repo @ CRUSH_TAG, @-import patch applied, `go mod vendor`ed
#   server/llama.cpp        llama.cpp full history @ LLAMACPP_TAG
#   server/models/<gguf…>   the model — one Q4_K_M by default; all quants + full weights with FULL=1
#
# Finer control (instead of FULL=1): set MODEL_FILES / FULL_MODEL_FILES / FULL_MODEL_REPO in the env
# and they're forwarded to the server vendor step (same meaning as in server/Makefile). Verify the
# repo/filenames on Hugging Face — the model repo path is a best-effort default. `make check-repo`
# (in server/) lists the repo's real GGUF filenames.
#
# The client image is the toolbox: it already ships go, git, python3 and (baked)
# huggingface_hub, so both the client and server vendoring run in it. You CANNOT carry the
# image blob into the airgap — that's why the airgap box rebuilds from these vendored sources;
# building the image here is expected, not wasted. Transport: tar the repo (the three folders
# above ride along) — see README "Airgapped rebuild".
#
# Prereqs on THIS (online) host: podman + make, and network. Nothing else.
#
# Fail-fast (set -e): a linear pipeline, any failed step must abort.
set -eu

here="$(cd "$(dirname "$0")" && pwd)"

# The client image name — read from client/Makefile so it stays the single source of truth.
name="$(sed -n 's/^CONTAINER_NAME *[:?]*= *//p' "$here/client/Makefile" | head -1)"
: "${name:?could not read CONTAINER_NAME from client/Makefile}"

# Model selection for the server vendor step. FULL=1 is the easy "everything" switch; otherwise the
# server/Makefile defaults apply (one Q4_K_M quant). Explicit MODEL_FILES/FULL_MODEL_FILES/
# FULL_MODEL_REPO in the env still win over the FULL=1 presets.
if [ "${FULL:-0}" = "1" ]; then
	MODEL_FILES="${MODEL_FILES:-*.gguf}"                               # all quant GGUFs
	FULL_MODEL_FILES="${FULL_MODEL_FILES:-*.safetensors}"              # full-precision weights
	FULL_MODEL_REPO="${FULL_MODEL_REPO:-meta-models/Muse-Glimmer-30B}" # base (non-GGUF) repo; verify on HF
fi
# Forward only the vars that are actually set, so unset ones fall through to server/Makefile's
# defaults (an empty `-e MODEL_FILES=` would wrongly blank the default).
model_env=()
[ -n "${MODEL_FILES:-}" ] && model_env+=(-e "MODEL_FILES=$MODEL_FILES")
[ -n "${FULL_MODEL_FILES:-}" ] && model_env+=(-e "FULL_MODEL_FILES=$FULL_MODEL_FILES")
[ -n "${FULL_MODEL_REPO:-}" ] && model_env+=(-e "FULL_MODEL_REPO=$FULL_MODEL_REPO")

# 1) Client: build the image and vendor Crush INSIDE it. VENDOR_TOOLS=1 bakes the `hf` CLI into
#    this image (needed by the server step below); it propagates to the `image` prerequisite, so
#    the one image built here serves both steps. `make -C client vendor` runs `vendor-crush.sh`
#    in the image with client/vendor bind-mounted (host make → host podman). Handles CRUSH_TAG /
#    CRUSH_AT_IMPORT from client/Makefile.
echo ">> [client] building vendoring image (with hf) + vendoring Crush -> client/vendor/crush"
make -C "$here/client" vendor VENDOR_TOOLS=1

# 2) Server: vendor llama.cpp (full history) + the GGUF INSIDE the same image, writing to the
#    bind-mounted server/ tree. server/Makefile's `vendor` uses the image's baked `hf` (no
#    venv/pip) and git. label=disable matches how the client runs (avoids SELinux mount denials).
echo ">> [server] vendoring llama.cpp + the model -> server/ (inside the client image)"
if [ "${FULL:-0}" = "1" ]; then echo "   FULL=1: all quant GGUFs + full-precision weights"; fi
podman run --rm \
	--security-opt label=disable \
	-v "$here/server":/server:Z \
	-w /server \
	${model_env[@]+"${model_env[@]}"} \
	"$name" \
	make vendor

cat <<EOF

vendored OK (all inside the '$name' image — host needed only podman + make).
  client/vendor/crush   (Crush, patched, go-mod-vendored)
  server/llama.cpp      (full history)
  server/models/        (GGUF)

Transport — tar the repo (the three folders above ride along), e.g.:
  tar czf runCrushInContainer-airgap.tgz -C '$(dirname "$here")' '$(basename "$here")'

On the airgapped box (no network):
  client:  cd client && make image CRUSH_VENDORED=1
  server:  build llama.cpp from server/llama.cpp for your backend (e.g. -DGGML_CUDA=ON) + serve a
           server/models/ GGUF — your hardware, your call.
EOF
