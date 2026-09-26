#!/usr/bin/env bash
# Install Lean 4 (https://lean-lang.org) — the open-source theorem prover / proof
# assistant — via elan, its official toolchain manager. Two modes, mirroring the Crush
# build (see 03-build-crush.sh):
#   - OFFLINE/airgap: if /vendor/elan exists (mounted read-only by `make image
#     CRUSH_VENDORED=1`; pre-produced ONLINE by `make vendor` → vendor/vendor-lean.sh),
#     copy it into $HOME/.elan — NO network.
#   - ONLINE (default): fetch elan + the stable toolchain with the official curl
#     installer (the network-at-build style the online image build already uses).
# Either way the stable Lean toolchain (lean + lake) ends up baked in $HOME/.elan; the
# Dockerfile adds $HOME/.elan/bin to PATH. Host-runnable.
set -e
if [ -d /vendor/elan ]; then
    echo "install-lean: using vendored elan from /vendor/elan (offline)"
    cp -r /vendor/elan "$HOME/.elan"
    # default toolchain already set + present from `make vendor` — no network needed.
else
    echo "install-lean: online elan install"
    curl -fsSL https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
    export PATH="$HOME/.elan/bin:$PATH"
    elan default stable
fi
export PATH="$HOME/.elan/bin:$PATH"
lean --version
