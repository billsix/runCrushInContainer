#!/usr/bin/env bash
# Vendor everything for an OFFLINE / airgap rebuild. Runs the vendoring INSIDE the client
# image, so this online host needs only **podman + make** — no host go/git/python3. One
# command from the repo root:
#
#   ./vendor.sh
#
# Populates (all gitignored, all fetched from the public internet):
#   client/vendor/crush     Crush repo @ CRUSH_TAG, @-import patch applied, `go mod vendor`ed
#   server/llama.cpp        llama.cpp full history @ LLAMACPP_TAG (built later, on the Mac)
#   server/models/<gguf>    the Muse Glimmer model (downloaded with the image's baked `hf`)
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
podman run --rm \
	--security-opt label=disable \
	-v "$here/server":/server:Z \
	-w /server \
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
  [linux] cd client  && make image CRUSH_VENDORED=1
  [mac]   cd server  && make llama && make serve
EOF
