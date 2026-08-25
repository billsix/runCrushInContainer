# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
FROM registry.fedoraproject.org/fedora:44

RUN --mount=type=cache,target=/var/cache/libdnf5 \
    --mount=type=cache,target=/var/lib/dnf \
    echo "keepcache=True" >> /etc/dnf/dnf.conf && \
    dnf upgrade -y

# The full runClaudeInContainer toolchain (~430 packages) — same host-runnable install
# script, copied verbatim from the sibling repo. Provides the Go toolchain that builds
# Crush below, plus git + openssh-clients for the SSH tunnel to the Mac.
COPY entrypoint/01-install-base.sh /usr/local/bin/
RUN --mount=type=cache,target=/var/cache/libdnf5 \
    --mount=type=cache,target=/var/lib/dnf \
    /usr/local/bin/01-install-base.sh

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
RUN : > /usr/share/containers/mounts.conf

# Build Crush from source at a pinned tag, AT IMAGE-BUILD TIME (self-contained image:
# the compiled binary is baked into a layer, no runtime fetch). CRUSH_TAG defaults to the
# latest stable release; override with `make image CRUSH_TAG=vX.Y.Z`. `crush --version`
# fails the build if the install didn't produce a working binary.
#
# CRUSH_AT_IMPORT toggles the local `@`-import patch (see client/patches/ and
# tasks/archive/2026/08/21/patch-crush-for-at-imports.md): with a `@path` on its own line in a context file
# (CLAUDE.md/AGENTS.md/CRUSH.md), the patched Crush recursively splices that file's contents
# in — the feature Crush lacks upstream. A patched build CANNOT use `go install …@tag` (the
# module proxy is read-only), so we clone the tag, `git apply` the patch, and build from source,
# stamping internal/version.Version so `crush --version` still reports the tag. Set
# CRUSH_AT_IMPORT=0 for the stock upstream build.
#
# CRUSH_VENDORED toggles the OFFLINE/airgap build (see tasks/vendor-build-sources-for-airgap-rebuild.md).
# When 1, Crush is NOT fetched from the network: the build reads a pre-vendored, patch-applied,
# `go mod vendor`-ed checkout bind-mounted at /vendor/crush (via `podman build --volume …`, added by
# `make image CRUSH_VENDORED=1`) and builds it with `GOPROXY=off go build -mod=vendor`. Produce that
# checkout ONLINE first with `make vendor`. `entrypoint/vendor/` is baked in so `make vendor` can run
# the vendoring script inside this image.
ARG CRUSH_TAG=v0.89.0
ARG CRUSH_AT_IMPORT=0
ARG CRUSH_VENDORED=0
ENV GOBIN=/usr/local/bin GOFLAGS=-trimpath
COPY patches/ /patches/
COPY entrypoint/vendor/ /usr/local/bin/vendor/
RUN chmod +x /usr/local/bin/vendor/*.sh
RUN set -eux; \
    if [ "$CRUSH_VENDORED" = "1" ]; then \
        cp -r /vendor/crush /tmp/crush; \
        ( cd /tmp/crush && GOPROXY=off go build -mod=vendor -ldflags "-X github.com/charmbracelet/crush/internal/version.Version=${CRUSH_TAG}" -o /usr/local/bin/crush . ); \
        rm -rf /tmp/crush; \
    elif [ "$CRUSH_AT_IMPORT" = "1" ]; then \
        git clone --depth 1 --branch "$CRUSH_TAG" https://github.com/charmbracelet/crush /tmp/crush; \
        git -C /tmp/crush apply /patches/crush-at-import.patch; \
        ( cd /tmp/crush && go install -ldflags "-X github.com/charmbracelet/crush/internal/version.Version=${CRUSH_TAG}" . ); \
        rm -rf /tmp/crush; \
    else \
        go install "github.com/charmbracelet/crush@${CRUSH_TAG}"; \
    fi; \
    crush --version

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
