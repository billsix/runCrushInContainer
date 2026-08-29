#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# Vendor the Crush source for an OFFLINE (airgapped) client-image rebuild.
#
# Clones the FULL Crush git repo (with history) at $CRUSH_TAG and runs
# `go mod vendor` so the whole thing can later be built with
# `GOPROXY=off go build -mod=vendor` and NO network.
#
# This script applies NO patches. The vendored tree is the COMPLETE, UNPATCHED
# source of truth: every local patch (telemetry, update check, provider
# removals, @-import — see client/patches/) is applied at BUILD time by
# entrypoint/03-build-crush.sh, guarded by its own PATCH_OUT_<X> build flag.
# That way the airgap box can build ANY flag combination, and revert any
# decision, from this one tree. (Decided 2026-08-29 — see
# tasks/reference/dependency-network-audit.md and
# tasks/implement-egress-patch-flags.md. Before that date this script baked the
# patches in at vendor time; if you have an old vendored tree, regenerate it.)
#
# The result (an unpatched checkout at the tag, its own vendor/ dir populated)
# is written to <dest-dir>.
#
# Run this ONLINE — it needs git + go + network. `client/Makefile`'s
# `make vendor` runs it inside the built client image (which ships both) with
# the destination bind-mounted, so the vendored tree lands on the host for
# transport to the airgap box. Then `make image CRUSH_VENDORED=1` rebuilds
# from it offline.
#
# Usage:  vendor-crush.sh <dest-dir>
# Env:
#   CRUSH_TAG        required — the tag to vendor (e.g. v0.89.0)
#   CRUSH_REPO       default https://github.com/charmbracelet/crush
#
# Fail-fast (set -e) is correct here: this is a linear pipeline, not a
# report-everything gate — any failed step must abort the vendoring.
set -eu

DEST="${1:?usage: vendor-crush.sh <dest-dir>}"
CRUSH_TAG="${CRUSH_TAG:?set CRUSH_TAG (e.g. v0.89.0)}"
CRUSH_REPO="${CRUSH_REPO:-https://github.com/charmbracelet/crush}"

command -v git >/dev/null 2>&1 || {
	echo "vendor-crush: git not found" >&2
	exit 1
}
command -v go >/dev/null 2>&1 || {
	echo "vendor-crush: go not found" >&2
	exit 1
}

# Start from a clean destination so the script reproduces its own output when re-run
# (idempotent — a second run yields the same tree, not an incremental mess).
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"

# FULL clone — history kept (the airgap requirement), working tree checked out at the
# tag. (No --depth 1, unlike a throwaway build clone.)
git clone --branch "$CRUSH_TAG" "$CRUSH_REPO" "$DEST"

# Populate $DEST/vendor with every Go module dependency's source, so the later build
# resolves imports from vendor/ with GOPROXY=off. The dep set is vendored COMPLETE —
# no `go mod tidy` — so build-time removal patches can drop imports while their dep
# source stays in vendor/ (unused vendored modules are fine for `go build -mod=vendor`),
# keeping every PATCH_OUT_<X> flag combination buildable offline.
(cd "$DEST" && go mod vendor)

echo "vendored Crush $CRUSH_TAG -> $DEST  (UNPATCHED tree; patches apply at build time, go mod vendor complete)"
