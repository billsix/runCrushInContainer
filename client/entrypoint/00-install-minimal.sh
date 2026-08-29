#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# 00-install-minimal.sh -- the MINIMAL package set: everything the client image needs
# to build Crush from source (at any PATCH_OUT_<X> flag combination, online or from the
# vendored tree), run it against the local model, run `make vendor` inside the image,
# and host a runtime egress check. This ALWAYS runs (both the full and the minimal
# image start from it); the ~430-package full toolchain (01-install-base.sh) is layered
# on top only when FULL_TOOLCHAIN=1.
#
# Every package here is a strict subset of 01-install-base.sh, installed first, so the
# full image is "minimal + more": dnf no-ops the overlap and the two variants share this
# base layer. See tasks/minimal-client-image.md.
#
# Extracted per the "host-agnostic setup belongs in a script" convention: the same set
# can be installed on a bare Fedora host, not only during `podman build`. Optionless
# (which optional groups get added is the Dockerfile's decision, via FULL_TOOLCHAIN).
#
# Single dnf call, so its own exit status is this script's exit status.
set -uo pipefail

if ! command -v dnf >/dev/null 2>&1; then
    echo "00-install-minimal.sh: needs 'dnf' (this installs Fedora packages), not found." >&2
    echo "Run on a Fedora host/guest, or inside the project's Fedora-based image." >&2
    exit 1
fi

# Keep alphabetical. What each is for:
#   ca-certificates  - TLS roots, so the ONLINE build's `git clone` + `go mod` reach GitHub/proxy
#   git              - clone Crush at CRUSH_TAG; git apply the patches
#   git-lfs          - Crush's go deps / some repos use LFS; harmless and cheap
#   golang           - the Go toolchain that builds Crush (the whole point)
#   gnupg2           - git commit signing if the user mounts ~/.gnupg (parity with full image)
#   less             - pager; Crush and interactive shell expect one present
#   ripgrep          - Crush's grep tool shells out to `rg` (exec.LookPath("rg"),
#                      internal/agent/tools/rg.go); it degrades to a slower Go path if absent,
#                      so this is for a usable dev experience, not correctness
#   strace           - runtime egress check (observe connect/sendto syscalls)
#   tcpdump          - runtime egress check (watch the bridge) — pairs with strace for
#                      tasks/decide-egress-verification.md; the minimal image is that env
#   which            - PATH lookups in scripts and the interactive shell
dnf install -y --setopt=install_weak_deps=False \
    ca-certificates \
    git \
    git-lfs \
    golang \
    gnupg2 \
    less \
    ripgrep \
    strace \
    tcpdump \
    which
