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
# WHY build from source (not `go install …@tag`): local patches must be applied to
# the source tree — including to VENDORED DEPENDENCY source under vendor/ — and the
# module proxy is read-only, so a patched tag can't come from it. Both build modes
# therefore converge on one flow: obtain a `go mod vendor`-ed checkout of the tag,
# apply the flag-selected patches, and build offline from vendor/.
#
# Two ways to obtain that checkout, under CRUSH_VENDORED (one cohesive build — the
# script owns the branch; the flag picks the METHOD, not an optional package group):
#   - CRUSH_VENDORED=0 (default, ONLINE): clone the tag and run `go mod vendor`
#     (fetches the deps from the network).
#   - CRUSH_VENDORED=1 (OFFLINE/airgap): copy the pre-vendored, UNPATCHED checkout
#     from /vendor/crush (a read-only `podman build --volume` mount added by
#     `make image CRUSH_VENDORED=1`; produce it first, ONLINE, with `make vendor`
#     → entrypoint/vendor/vendor-crush.sh). No network at all.
#
# THE PATCH SYSTEM (decided 2026-08-29; see tasks/reference/dependency-network-audit.md
# for what each decision is and why, and client/patches/*.patch for the diffs):
# every patch below is its own decision with its own PATCH_OUT_<X> flag, applied
# IDENTICALLY in both build modes. The DEFAULT of each flag encodes the audit's
# disposition: 1 = patched out by default (unsolicited phone-home and out-of-design
# cloud providers), 0 = kept by default (useful user-initiated online features).
# Flip any flag at `make image PATCH_OUT_<X>=…` — the vendored tree is complete and
# unpatched, so every combination builds, offline included. Patches use zero-context
# hunks where several touch the same file, hence `git apply --unidiff-zero`.
#
# The local-model link (fantasy openai/openaicompat -> openai-go -> 127.0.0.1:8080)
# is untouched by every patch — it is the essential core of this setup.
#
# Env (passed explicitly by the Dockerfile RUN so a child process reliably sees them):
#   CRUSH_TAG        required — the tag to build (e.g. v0.89.0)
#   CRUSH_VENDORED   0/1, default 0 — offline pre-vendored tree vs online clone+vendor
#   PATCHES_DIR      default /patches (the Dockerfile COPYs client/patches/ there);
#                    for a bare-host run point it at client/patches
#   CRUSH_AT_IMPORT               0/1, default 0 — local @-import FEATURE patch (adds
#                                 recursive `@path` splicing to context files)
#   PATCH_OUT_UPDATE_CHECK        0/1, default 1 — no startup api.github.com release check
#   PATCH_OUT_TELEMETRY           0/1, default 1 — PostHog/data.charm.land unreachable at
#                                 build level (on top of the env/config opt-outs)
#   PATCH_OUT_UPDATE_PROVIDERS_CMD 0/1, default 1 — remove `crush update-providers`
#                                 (the one ungated catwalk.charm.land path)
#   PATCH_OUT_WEB_TOOLS           0/1, default 0 (KEPT) — strip web_search/web_fetch/
#                                 agentic_fetch/fetch/download when 1
#   PATCH_OUT_SOURCEGRAPH         0/1, default 0 (KEPT) — strip the sourcegraph.com tool
#   PATCH_OUT_GOOGLE_PROVIDER     0/1, default 1 — Google/Vertex providers gone; genai +
#                                 cloud.google.com/* + grpc + OTel un-compiled
#   PATCH_OUT_BEDROCK_AWS         0/1, default 1 — Bedrock gone; all aws-sdk-go-v2 +
#                                 smithy-go un-compiled (incl. the IMDS probe)
#   PATCH_OUT_AZURE               0/1, default 1 — Azure provider gone; azcore un-compiled
#   PATCH_OUT_OPENROUTER          0/1, default 1 — openrouter.ai provider errors out
#   PATCH_OUT_VERCEL              0/1, default 1 — Vercel AI-gateway provider errors out
#   PATCH_OUT_HYPER               0/1, default 1 — hyper.charm.land (proxy/OAuth/catalog/
#                                 credits/x-crush-id) egress guarded out
#   PATCH_OUT_COPILOT             0/1, default 1 — GitHub Copilot device-flow OAuth and
#                                 token exchange guarded out
#
# Fail-fast + trace: this is a linear build, any failed step must abort; -x traces into
# the build log.
set -eux

CRUSH_TAG="${CRUSH_TAG:?set CRUSH_TAG (e.g. v0.89.0)}"
CRUSH_VENDORED="${CRUSH_VENDORED:-0}"
PATCHES_DIR="${PATCHES_DIR:-/patches}"

CRUSH_AT_IMPORT="${CRUSH_AT_IMPORT:-0}"
PATCH_OUT_UPDATE_CHECK="${PATCH_OUT_UPDATE_CHECK:-1}"
PATCH_OUT_TELEMETRY="${PATCH_OUT_TELEMETRY:-1}"
PATCH_OUT_UPDATE_PROVIDERS_CMD="${PATCH_OUT_UPDATE_PROVIDERS_CMD:-1}"
PATCH_OUT_WEB_TOOLS="${PATCH_OUT_WEB_TOOLS:-0}"
PATCH_OUT_SOURCEGRAPH="${PATCH_OUT_SOURCEGRAPH:-0}"
PATCH_OUT_GOOGLE_PROVIDER="${PATCH_OUT_GOOGLE_PROVIDER:-1}"
PATCH_OUT_BEDROCK_AWS="${PATCH_OUT_BEDROCK_AWS:-1}"
PATCH_OUT_AZURE="${PATCH_OUT_AZURE:-1}"
PATCH_OUT_OPENROUTER="${PATCH_OUT_OPENROUTER:-1}"
PATCH_OUT_VERCEL="${PATCH_OUT_VERCEL:-1}"
PATCH_OUT_HYPER="${PATCH_OUT_HYPER:-1}"
PATCH_OUT_COPILOT="${PATCH_OUT_COPILOT:-1}"

LDFLAGS="-X github.com/charmbracelet/crush/internal/version.Version=${CRUSH_TAG}"

# --- obtain a go-mod-vendored checkout at /tmp/crush ------------------------------
if [ "$CRUSH_VENDORED" = "1" ]; then
    # /vendor/crush is a read-only build volume — copy it out to a writable dir first.
    cp -r /vendor/crush /tmp/crush
else
    git clone --depth 1 --branch "$CRUSH_TAG" https://github.com/charmbracelet/crush /tmp/crush
    ( cd /tmp/crush && go mod vendor )
fi

# --- apply the flag-selected patches (identical for both modes) -------------------
# apply_patch <flag-value> <patch-file>: applies when the flag is 1. --unidiff-zero
# permits the zero-context hunks used where several patches edit the same file.
apply_patch() {
    if [ "$1" = "1" ]; then
        git -C /tmp/crush apply --unidiff-zero "$PATCHES_DIR/$2"
    fi
}
apply_patch "$CRUSH_AT_IMPORT"                "crush-at-import.patch"
apply_patch "$PATCH_OUT_UPDATE_CHECK"         "crush-no-update-check.patch"
apply_patch "$PATCH_OUT_TELEMETRY"            "no-telemetry.patch"
apply_patch "$PATCH_OUT_UPDATE_PROVIDERS_CMD" "no-update-providers-cmd.patch"
apply_patch "$PATCH_OUT_WEB_TOOLS"            "no-web-tools.patch"
apply_patch "$PATCH_OUT_SOURCEGRAPH"          "no-sourcegraph.patch"
apply_patch "$PATCH_OUT_GOOGLE_PROVIDER"      "no-google-provider.patch"
apply_patch "$PATCH_OUT_BEDROCK_AWS"          "no-bedrock-aws.patch"
apply_patch "$PATCH_OUT_AZURE"                "no-azure.patch"
apply_patch "$PATCH_OUT_OPENROUTER"           "no-openrouter.patch"
apply_patch "$PATCH_OUT_VERCEL"               "no-vercel.patch"
apply_patch "$PATCH_OUT_HYPER"                "no-hyper.patch"
apply_patch "$PATCH_OUT_COPILOT"              "no-copilot.patch"

# --- build offline from vendor/ (both modes; the online mode already fetched) -----
( cd /tmp/crush && GOPROXY=off go build -mod=vendor -ldflags "$LDFLAGS" \
    -o "${GOBIN:-/usr/local/bin}/crush" . )

rm -rf /tmp/crush
crush --version
