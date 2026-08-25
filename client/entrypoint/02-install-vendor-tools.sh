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
#   python3-huggingface-hub — provides the `hf` CLI, used by server/'s `make pull` to download
#                             the model GGUF from Hugging Face during vendoring.
#
# Optionless, single dnf: its own exit status is the gate (safe by shape).
set -eu

command -v dnf >/dev/null 2>&1 || {
	echo "02-install-vendor-tools: dnf not found (Fedora/dnf host required)" >&2
	exit 1
}

dnf install -y python3-huggingface-hub
