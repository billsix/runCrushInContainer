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
curl -fsSL "https://raw.githubusercontent.com/leanprover/elan/${ELAN_VERSION:-v4.2.4}/elan-init.sh" | sh -s -- -y --default-toolchain none
"$DEST/bin/elan" default "${LEAN_TOOLCHAIN:-leanprover/lean4:v4.35.0}"
"$DEST/bin/lean" --version
echo "vendored elan + Lean ${LEAN_TOOLCHAIN:-leanprover/lean4:v4.35.0} into $DEST"
