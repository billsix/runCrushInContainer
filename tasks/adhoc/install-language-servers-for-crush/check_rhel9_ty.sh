#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# Part 2 proof harness — the RHEL 9 Python-LSP path, in two throwaway steps that mirror the
# (commented-out) block in client/Dockerfile:
#
#   1. ONLINE:  build a tiny CentOS Stream 9 image with python3.11 (the RHEL 9 AppStream
#               interpreter the maintainer chose) and `pip download` the ty wheel into
#               $OUT/wheels — the artifact the airgap tarball must carry.
#   2. OFFLINE: `podman run --network=none` that image, create /venv with python3.11, install
#               ty from the wheel with `--no-index`, and run the initialize handshake — proving
#               the recipe needs no network once the wheel is present.
#
# Usage: check_rhel9_ty.sh [OUT_DIR]   (default: a `rhel9-out/` dir beside this script, gitignored
#        by nothing — delete it after reading; it is a scratch artifact, not a deliverable).
# TY_VERSION pins the wheel (default: latest at run time; the real pin lives in client/Makefile).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="${1:-$here/rhel9-out}"
mkdir -p "$out/wheels"
PODMAN_RUN_FLAGS="${PODMAN_RUN_FLAGS:-$([ "${NESTED_PODMAN:-0}" = 1 ] && echo --cgroups=disabled)}"
spec="ty${TY_VERSION:+==$TY_VERSION}"

# Step 1a: the base with python3.11 (one dnf transaction, network required).
podman build -q -t localhost/cs9-py311 - <<'EOF' || exit 1
FROM quay.io/centos/centos:stream9
RUN dnf install -y -q python3.11 python3.11-pip && dnf clean all
EOF

# Step 1b: fetch the wheel (network required). --only-binary refuses a source build, which is
# the point: ty is a prebuilt Rust binary and must arrive as a manylinux wheel.
# shellcheck disable=SC2086
podman run --rm $PODMAN_RUN_FLAGS -v "$out/wheels":/wheels:z localhost/cs9-py311 \
    python3.11 -m pip download -q --only-binary=:all: -d /wheels "$spec" || exit 1
echo "== wheel(s) downloaded:"
ls -l "$out/wheels"

# Step 2: the OFFLINE install + handshake. This is the airgap proof.
# shellcheck disable=SC2086
podman run --rm $PODMAN_RUN_FLAGS --network=none \
    -v "$out/wheels":/wheels:ro,z -v "$here":/adhoc:ro,z localhost/cs9-py311 bash -c '
    set -u
    python3.11 -m venv --system-site-packages /venv || exit 1
    /venv/bin/pip install -q --no-index --find-links /wheels ty || exit 1
    echo "== offline install OK: $(/venv/bin/ty --version)  (python $(/venv/bin/python --version 2>&1))"
    PATH=/venv/bin:$PATH python3 /adhoc/lsp_handshake.py python-rhel9 -- ty server
'
