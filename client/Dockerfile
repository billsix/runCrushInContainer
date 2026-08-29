# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
FROM registry.fedoraproject.org/fedora:44

RUN --mount=type=cache,target=/var/cache/libdnf5 \
    --mount=type=cache,target=/var/lib/dnf \
    echo "keepcache=True" >> /etc/dnf/dnf.conf && \
    dnf upgrade -y

# The MINIMAL package set — ALWAYS installed (first, so it's a shared base layer): just
# what's needed to build Crush from source, run it against the local model, run
# `make vendor`, and host a runtime egress check (golang, git, ripgrep, strace, tcpdump …).
# See entrypoint/00-install-minimal.sh and tasks/minimal-client-image.md.
COPY entrypoint/00-install-minimal.sh /usr/local/bin/
RUN --mount=type=cache,target=/var/cache/libdnf5 \
    --mount=type=cache,target=/var/lib/dnf \
    /usr/local/bin/00-install-minimal.sh

# The full runClaudeInContainer toolchain (~430 packages) — same host-runnable install
# script, copied verbatim from the sibling repo. Gated behind FULL_TOOLCHAIN: it is a
# SUPERSET of the minimal set above, so with FULL_TOOLCHAIN=1 the two RUNs together give
# the batteries-included dev image; with =0 the image stays minimal (~2 GB) and fits the
# dev sandbox's nested-podman store for in-sandbox verification. The minimal set already
# provides the Go toolchain + git that build Crush below, so the build works either way.
ARG FULL_TOOLCHAIN=0
COPY entrypoint/01-install-base.sh /usr/local/bin/
RUN --mount=type=cache,target=/var/cache/libdnf5 \
    --mount=type=cache,target=/var/lib/dnf \
    if [ "$FULL_TOOLCHAIN" = "1" ]; then /usr/local/bin/01-install-base.sh; fi

# Vendoring-only tools (the `hf` CLI), gated behind VENDOR_TOOLS (default 0 — Makefile turns it
# ON only for `make vendor`). These are needed ONLY to run `make vendor` inside this image while
# ONLINE; the image itself and the OFFLINE airgap rebuild do not use them, so a normal/airgap
# build never installs them and the airgap dnf mirror never needs them. See
# tasks/vendor-via-client-image.md.
ARG VENDOR_TOOLS=0
COPY entrypoint/02-install-vendor-tools.sh /usr/local/bin/
RUN --mount=type=cache,target=/var/cache/libdnf5 \
    --mount=type=cache,target=/var/lib/dnf \
    if [ "$VENDOR_TOOLS" = "1" ]; then /usr/local/bin/02-install-vendor-tools.sh; fi

# Silence podman's RHEL subscription-secrets mount. containers-common ships
# /usr/share/containers/mounts.conf = "/usr/share/rhel/secrets:/run/secrets", which podman tries to
# inject into EVERY container it runs. That path is empty on Fedora and the mount fails under the
# nested/label-disabled setup, so every INNER `podman run` prints a harmless "Failed to mount
# subscriptions" WARN and skips it. Emptying the file removes the noise (we do no subscription builds).
# Guarded: the file only exists when containers-common is present (the full toolchain, which pulls
# podman). The minimal image (FULL_TOOLCHAIN=0) has neither the file nor a nested-podman use case.
RUN if [ -e /usr/share/containers/mounts.conf ]; then : > /usr/share/containers/mounts.conf; fi

# Build Crush from source at a pinned tag, at IMAGE-BUILD time (self-contained image: the
# binary is baked into a layer, no runtime fetch). The build LOGIC — why from source, the
# patch system, the vendored-vs-clone modes, the -ldflags version stamp — lives in
# entrypoint/03-build-crush.sh (also runnable on a bare host). Here we only declare the
# flags and wire them in:
#   CRUSH_TAG        the tag to build (override: `make image CRUSH_TAG=vX.Y.Z`)
#   CRUSH_AT_IMPORT  1 = apply the @-import feature patch; 0 = build without it
#   CRUSH_VENDORED   1 = OFFLINE/airgap build. `make image CRUSH_VENDORED=1` adds
#                    `--volume ./vendor/crush:/vendor/crush:ro --build-arg CRUSH_VENDORED=1`
#                    so the script reads the pre-vendored checkout at /vendor/crush; produce
#                    it ONLINE first with `make vendor` (entrypoint/vendor/, baked in below).
#   PATCH_OUT_<X>    one flag per egress decision from the dependency network audit
#                    (tasks/reference/dependency-network-audit.md, D1-D12); each guards one
#                    patch in /patches, applied by the build script in BOTH modes. Defaults
#                    here mirror the Makefile's — they are SEMANTIC (encode the audit's
#                    disposition: 1 = phone-home/out-of-design patched out, 0 = useful
#                    online feature kept), deliberately unlike the usual lean-bare-build
#                    ARG=0 convention, so a bare `podman build` gets the audited posture.
ARG CRUSH_TAG=v0.89.0
ARG CRUSH_AT_IMPORT=0
ARG CRUSH_VENDORED=0
ARG PATCH_OUT_UPDATE_CHECK=1
ARG PATCH_OUT_TELEMETRY=1
ARG PATCH_OUT_UPDATE_PROVIDERS_CMD=1
ARG PATCH_OUT_WEB_TOOLS=0
ARG PATCH_OUT_SOURCEGRAPH=0
ARG PATCH_OUT_GOOGLE_PROVIDER=1
ARG PATCH_OUT_BEDROCK_AWS=1
ARG PATCH_OUT_AZURE=1
ARG PATCH_OUT_OPENROUTER=1
ARG PATCH_OUT_VERCEL=1
ARG PATCH_OUT_HYPER=1
ARG PATCH_OUT_COPILOT=1
# Disable Crush's PostHog usage telemetry (endpoint data.charm.land). Crush has a built-in
# opt-out (internal/cmd/root.go shouldEnableMetrics), so an env var is enough — no source patch.
# Both are set belt-and-suspenders: CRUSH_DISABLE_METRICS is Crush's own switch, DO_NOT_TRACK is
# the cross-tool https://donottrack.sh convention. Env is launch-independent (covers `crush`,
# `crush run`, `crush stats`) and survives a mounted-config override. The baked crushrc also sets
# `option metrics false` for visibility. See tasks/disable-crush-telemetry.md.
ENV CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1
ENV GOBIN=/usr/local/bin GOFLAGS=-trimpath
COPY patches/ /patches/
COPY entrypoint/vendor/ /usr/local/bin/vendor/
RUN chmod +x /usr/local/bin/vendor/*.sh
COPY entrypoint/03-build-crush.sh /usr/local/bin/
# Build Crush from source (vendored or clone+vendor, then flag-guarded patches);
# see entrypoint/03-build-crush.sh. ARGs aren't inherited by a child process, so
# every flag is passed to the script explicitly.
RUN CRUSH_TAG="$CRUSH_TAG" CRUSH_VENDORED="$CRUSH_VENDORED" CRUSH_AT_IMPORT="$CRUSH_AT_IMPORT" \
    PATCH_OUT_UPDATE_CHECK="$PATCH_OUT_UPDATE_CHECK" \
    PATCH_OUT_TELEMETRY="$PATCH_OUT_TELEMETRY" \
    PATCH_OUT_UPDATE_PROVIDERS_CMD="$PATCH_OUT_UPDATE_PROVIDERS_CMD" \
    PATCH_OUT_WEB_TOOLS="$PATCH_OUT_WEB_TOOLS" \
    PATCH_OUT_SOURCEGRAPH="$PATCH_OUT_SOURCEGRAPH" \
    PATCH_OUT_GOOGLE_PROVIDER="$PATCH_OUT_GOOGLE_PROVIDER" \
    PATCH_OUT_BEDROCK_AWS="$PATCH_OUT_BEDROCK_AWS" \
    PATCH_OUT_AZURE="$PATCH_OUT_AZURE" \
    PATCH_OUT_OPENROUTER="$PATCH_OUT_OPENROUTER" \
    PATCH_OUT_VERCEL="$PATCH_OUT_VERCEL" \
    PATCH_OUT_HYPER="$PATCH_OUT_HYPER" \
    PATCH_OUT_COPILOT="$PATCH_OUT_COPILOT" \
    /usr/local/bin/03-build-crush.sh

# Baked dotfiles (prompt, ls alias, GPG_TTY): /root/.extrabashrc, sourced from ~/.bashrc.
# Host ~/.tmux.conf / ~/.gitconfig / ~/.gnupg are mounted conditionally by the Makefile.
COPY entrypoint/dotfiles/ /root/
RUN echo "source ~/.extrabashrc" >> ~/.bashrc

# Baked default Crush config: a local llama.cpp provider with the model pinned explicitly and
# the built-in catalog suppressed (see tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md).
# crushrc is the modern config format (crush.json is deprecated); ~/.config/crush/crushrc is the
# global location.
COPY entrypoint/crushrc /root/.config/crush/crushrc

COPY entrypoint/shell.sh /shell.sh
