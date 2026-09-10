#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# Part 1 proof harness: in a throwaway fedora:44 container, dnf-install the six language
# servers the client crushrc declares, show which binary each package provides, and run one
# LSP `initialize` handshake against each (lsp_handshake.py) to record its capability set.
# No repo files are touched; the point is a cheap check before the 22 GB image rebuild.
#
# Run from anywhere: `tasks/adhoc/install-language-servers-for-crush/check_fedora_servers.sh`.
# Needs podman (nested is fine; PODMAN_RUN_FLAGS is honoured like the project Makefiles).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PODMAN_RUN_FLAGS="${PODMAN_RUN_FLAGS:-$([ "${NESTED_PODMAN:-0}" = 1 ] && echo --cgroups=disabled)}"

# shellcheck disable=SC2086  # PODMAN_RUN_FLAGS is deliberately word-split
podman run --rm $PODMAN_RUN_FLAGS -v "$here":/adhoc:ro,z registry.fedoraproject.org/fedora:44 bash -c '
    set -u
    dnf install -y -q python3 ty gopls rust-analyzer clang-tools-extra nodejs-bash-language-server glsl-analyzer >/dev/null || exit 1
    echo "== binaries per package"
    for p in ty gopls rust-analyzer clang-tools-extra nodejs-bash-language-server glsl-analyzer; do
        printf "%-28s %s   %s\n" "$p" "$(rpm -q --qf "%{version}" "$p")" "$(rpm -ql "$p" | grep -E "^/usr/bin/" | tr "\n" " ")"
    done
    echo "== handshakes"
    status=0
    python3 /adhoc/lsp_handshake.py python -- ty server                      || status=1
    python3 /adhoc/lsp_handshake.py go     -- gopls                          || status=1
    python3 /adhoc/lsp_handshake.py c      -- clangd                         || status=1
    python3 /adhoc/lsp_handshake.py rust   -- rust-analyzer                  || status=1
    python3 /adhoc/lsp_handshake.py sh     -- bash-language-server start     || status=1
    python3 /adhoc/lsp_handshake.py glsl   -- glsl_analyzer                  || status=1
    exit $status
'
