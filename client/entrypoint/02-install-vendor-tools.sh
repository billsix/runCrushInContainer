#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# Extra packages needed ONLY to run `make vendor` inside this image — i.e. online
# source-vendoring for an airgap rebuild. NOT needed by the image itself, and NOT needed by
# the offline airgap rebuild (which uses the already-vendored GGUF and never downloads).
#
# Gated behind the Dockerfile's VENDOR_TOOLS ARG (default 0): a normal or airgap `make image`
# does NOT install these, so the airgap dnf mirror never has to carry them. Dispatched only
# when the image is built with VENDOR_TOOLS=1 (which `vendor.sh` / `make ... vendor` does).
#
#   hf CLI (from huggingface_hub) — used by server/'s `make pull` to download the model GGUF
#   from Hugging Face during vendoring.
#
# Install strategy: PREFER the official dnf package `python3-huggingface-hub`; FALL BACK to pip
# when the enabled repos don't carry it (or ship a version too old to provide the `hf` command).
# Fedora has the package; RHEL9 does NOT — hence the fallback. This path only ever runs ONLINE
# (VENDOR_TOOLS builds), so pip reaching PyPI is fine and no airgap mirror needs huggingface_hub.
# The real gate is the final `command -v hf`, not any single install step; set -e aborts on
# genuine (non-fallback) errors.
set -eu

command -v dnf >/dev/null 2>&1 || {
	echo "02-install-vendor-tools: dnf not found (Fedora/RHEL/dnf host required)" >&2
	exit 1
}

# 1) Preferred: the distro package — but only if it exists AND actually provides `hf`. An old
#    huggingface-hub ships only `huggingface-cli`, so verifying `hf` (not just install success)
#    is what lets a too-old package fall through to pip instead of silently "succeeding".
if dnf install -y python3-huggingface-hub 2>/dev/null && command -v hf >/dev/null 2>&1; then
	echo "02-install-vendor-tools: installed hf via dnf (python3-huggingface-hub)"
else
	# 2) Fallback: pip. The dnf package is absent (e.g. RHEL9) or too old for `hf`. `python3-pip`
	#    itself IS in the RHEL9 repos, so install it here rather than assume it's present.
	echo "02-install-vendor-tools: python3-huggingface-hub unavailable/too old via dnf; using pip" >&2
	dnf install -y python3-pip
	# PEP 668: Fedora marks the system Python externally-managed and needs --break-system-packages;
	# RHEL9's older pip does not know that flag, so try it first and fall back to a plain install.
	# A system install is fine here — throwaway, online-only vendoring image, not a durable env.
	python3 -m pip install --break-system-packages huggingface_hub ||
		python3 -m pip install huggingface_hub
fi

# The contract: `hf` must be on PATH afterwards (server/'s make pull calls `hf download`).
command -v hf >/dev/null 2>&1 || {
	echo "02-install-vendor-tools: 'hf' CLI not found after install — need a huggingface_hub" \
		"version that ships the 'hf' entry point" >&2
	exit 1
}
echo "02-install-vendor-tools: hf ready ($(hf --version 2>/dev/null || echo 'version unknown'))"
