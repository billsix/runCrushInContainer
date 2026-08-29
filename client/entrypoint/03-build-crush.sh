#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# Build Crush from source at a pinned tag and install it to /usr/local/bin/crush.
# Invoked by the client Dockerfile at IMAGE-BUILD time (self-contained image: the
# compiled binary is baked into a layer, no runtime fetch), and runnable on a bare
# host too (needs go + git, plus network for the non-vendored path). The final
# `crush --version` fails if the install didn't produce a working binary.
#
# WHY build from source (not `go install …@tag`): two local patches must be applied
# to the source tree, and the module proxy is read-only so it can't serve a patched
# tag. So every non-vendored build clones the tag and builds from source, stamping
# internal/version.Version via -ldflags so `crush --version` still reports the tag.
#
# The two patches (in client/patches/, mounted at /patches by the Dockerfile):
#   - crush-no-update-check.patch — ALWAYS applied (no flag). Removes the unconditional
#     `go app.checkForUpdates(ctx)` so Crush never GETs api.github.com on startup — a
#     runCrush client never wants that unsolicited egress (privacy + airgap). See
#     tasks/disable-crush-telemetry.md. (data.charm.land telemetry is disabled separately
#     via the CRUSH_DISABLE_METRICS/DO_NOT_TRACK env set in the Dockerfile.)
#   - crush-at-import.patch — applied only when CRUSH_AT_IMPORT=1: a `@path` on its own
#     line in a context file (CLAUDE.md/AGENTS.md/CRUSH.md) is recursively spliced in —
#     a feature Crush lacks upstream. CRUSH_AT_IMPORT=0 means "source build WITHOUT the
#     @-import patch" (the update-check patch is still applied), not a plain upstream build.
#
# Two build MODES under CRUSH_VENDORED (this is one cohesive build, so the script owns the
# branch rather than the Dockerfile — the flag picks the METHOD, not an optional package group):
#   - CRUSH_VENDORED=0 (default, ONLINE): clone the tag, apply the patch(es), `go install`
#     (GOBIN=/usr/local/bin, set in the Dockerfile, puts the binary at /usr/local/bin/crush).
#   - CRUSH_VENDORED=1 (OFFLINE/airgap): read a pre-vendored, PATCH-ALREADY-APPLIED,
#     `go mod vendor`-ed checkout from /vendor/crush (a read-only `podman build --volume`
#     mount added by `make image CRUSH_VENDORED=1`; produce it first, ONLINE, with `make
#     vendor` → entrypoint/vendor/vendor-crush.sh) and build it with `GOPROXY=off go build
#     -mod=vendor`, NO network. **This branch applies NO patches** — they are already baked
#     into the vendored tree by vendor-crush.sh; re-applying would double-apply and fail.
#
# Env (passed explicitly by the Dockerfile RUN so a child process reliably sees them):
#   CRUSH_TAG        required — the tag to build (e.g. v0.89.0)
#   CRUSH_VENDORED   0/1, default 0 — offline vendored build vs online clone
#   CRUSH_AT_IMPORT  0/1, default 0 — apply the @-import patch (non-vendored path only)
#
# Fail-fast + trace: this is a linear build, any failed step must abort; -x traces into
# the build log.
set -eux

CRUSH_TAG="${CRUSH_TAG:?set CRUSH_TAG (e.g. v0.89.0)}"
CRUSH_VENDORED="${CRUSH_VENDORED:-0}"
CRUSH_AT_IMPORT="${CRUSH_AT_IMPORT:-0}"

LDFLAGS="-X github.com/charmbracelet/crush/internal/version.Version=${CRUSH_TAG}"

if [ "$CRUSH_VENDORED" = "1" ]; then
    # /vendor/crush is a read-only build volume — copy it out to a writable dir first.
    cp -r /vendor/crush /tmp/crush
    ( cd /tmp/crush && GOPROXY=off go build -mod=vendor -ldflags "$LDFLAGS" -o /usr/local/bin/crush . )
else
    git clone --depth 1 --branch "$CRUSH_TAG" https://github.com/charmbracelet/crush /tmp/crush
    git -C /tmp/crush apply /patches/crush-no-update-check.patch
    if [ "$CRUSH_AT_IMPORT" = "1" ]; then git -C /tmp/crush apply /patches/crush-at-import.patch; fi
    ( cd /tmp/crush && go install -ldflags "$LDFLAGS" . )   # GOBIN=/usr/local/bin -> /usr/local/bin/crush
fi

rm -rf /tmp/crush
crush --version
