#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# Vendor the Crush source for an OFFLINE (airgapped) client-image rebuild.
#
# Clones the FULL Crush git repo (with history) at $CRUSH_TAG, applies the local
# patches (crush-no-update-check ALWAYS; crush-at-import when CRUSH_AT_IMPORT=1), and
# runs `go mod vendor` so the whole thing can later be built with
# `GOPROXY=off go build -mod=vendor` and NO network. The patches are baked into the
# vendored tree here so the offline `make image CRUSH_VENDORED=1` build applies none.
# The result (a build-ready checkout, patch already applied, its own vendor/ dir
# populated) is written to <dest-dir>.
#
# Run this ONLINE — it needs git + go + network. `client/Makefile`'s `make vendor`
# runs it inside the built client image (which ships both) with the destination
# bind-mounted, so the vendored tree lands on the host for transport to the airgap
# box. Then `make image CRUSH_VENDORED=1` rebuilds from it offline.
#
# Usage:  vendor-crush.sh <dest-dir>
# Env:
#   CRUSH_TAG        required — the tag to vendor (e.g. v0.89.0)
#   CRUSH_AT_IMPORT  0/1, default 1 — apply the local @-import patch
#   CRUSH_REPO       default https://github.com/charmbracelet/crush
#   PATCH_FILE       default /patches/crush-at-import.patch (baked into the image);
#                    for a host run, point it at client/patches/crush-at-import.patch
#   UPDATE_PATCH_FILE default /patches/crush-no-update-check.patch — ALWAYS applied
#                    (disable the startup update check); host run: client/patches/…
#
# Fail-fast (set -e) is correct here: this is a linear pipeline, not a
# report-everything gate — any failed step must abort the vendoring.
set -eu

DEST="${1:?usage: vendor-crush.sh <dest-dir>}"
CRUSH_TAG="${CRUSH_TAG:?set CRUSH_TAG (e.g. v0.89.0)}"
CRUSH_AT_IMPORT="${CRUSH_AT_IMPORT:-1}"
CRUSH_REPO="${CRUSH_REPO:-https://github.com/charmbracelet/crush}"
PATCH_FILE="${PATCH_FILE:-/patches/crush-at-import.patch}"
UPDATE_PATCH_FILE="${UPDATE_PATCH_FILE:-/patches/crush-no-update-check.patch}"

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

# Always disable the startup update check (no build flag) — a runCrush client never
# wants the unsolicited api.github.com call. See tasks/disable-crush-telemetry.md.
git -C "$DEST" apply "$UPDATE_PATCH_FILE"

if [ "$CRUSH_AT_IMPORT" = "1" ]; then
	git -C "$DEST" apply "$PATCH_FILE"
fi

# Populate $DEST/vendor with every Go module dependency's source, so the later build
# resolves imports from vendor/ with GOPROXY=off (the patch adds only a stdlib import,
# so it introduces no new module deps).
(cd "$DEST" && go mod vendor)

echo "vendored Crush $CRUSH_TAG -> $DEST  (patch=$CRUSH_AT_IMPORT, go mod vendor complete)"
