#!/usr/bin/env bash
# [ONLINE] Pre-fetch elan + the stable Lean 4 toolchain into a vendored ELAN_HOME so an
# airgap image build (CRUSH_VENDORED=1) can install Lean with NO network. Mirrors
# vendor-crush.sh. Run inside the image by `make vendor`; writes to $1 (the mounted
# /vendor/elan). The airgap image build copies that dir into /root/.elan — see
# entrypoint/install-lean.sh. Host-runnable too.
set -e
DEST="${1:?usage: vendor-lean.sh <dest-elan-home>}"
mkdir -p "$DEST"
export ELAN_HOME="$DEST"
curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
"$DEST/bin/elan" default stable
"$DEST/bin/lean" --version
echo "vendored elan + stable Lean toolchain into $DEST"
