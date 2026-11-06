#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# 01b-install-binary-tools.sh -- install the two CLI tools the sandbox ships that are
# NO LONGER packaged in Fedora 45, from their upstream release binaries:
#
#   shfmt  (mvdan/sh)     -- shell formatter; dropped from Fedora 45 (it now survives
#                            only bundled inside nodejs-bash-language-server).
#   procs  (dalance/procs)-- modern `ps` replacement; dropped from Fedora 45.
#
# Both were plain `dnf install` entries in 01-install-base.sh under Fedora 44. Kept here,
# in their own script, so 01-install-base.sh stays a single pure `dnf install` call and so
# the same install works on a bare Fedora host/guest (not only during `podman build`).
# Pinned by version; bump the *_VERSION vars to update. x86_64 only (the sandbox is x86_64).
#
# Several steps, so accumulate the exit status rather than fail-fast.
set -uo pipefail

SHFMT_VERSION=v3.14.1
PROCS_VERSION=v0.14.12

for tool in curl unzip install; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "01b-install-binary-tools: needs '$tool', not found." >&2
        exit 1
    }
done

status=0
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# shfmt: a single statically-linked binary published per platform.
if curl -fsSL -o "$tmp/shfmt" \
      "https://github.com/mvdan/sh/releases/download/${SHFMT_VERSION}/shfmt_${SHFMT_VERSION}_linux_amd64"; then
    install -m 0755 "$tmp/shfmt" /usr/local/bin/shfmt
    shfmt --version || status=1
else
    echo "01b-install-binary-tools: failed to fetch shfmt ${SHFMT_VERSION}" >&2
    status=1
fi

# procs: published as a zip containing a single `procs` binary.
if curl -fsSL -o "$tmp/procs.zip" \
      "https://github.com/dalance/procs/releases/download/${PROCS_VERSION}/procs-${PROCS_VERSION}-x86_64-linux.zip"; then
    unzip -o -q "$tmp/procs.zip" -d "$tmp" && \
        install -m 0755 "$tmp/procs" /usr/local/bin/procs && \
        procs --version || status=1
else
    echo "01b-install-binary-tools: failed to fetch procs ${PROCS_VERSION}" >&2
    status=1
fi

exit $status
