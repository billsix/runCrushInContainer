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

# Build Crush from source at a pinned tag, AT IMAGE-BUILD TIME (self-contained image:
# the compiled binary is baked into a layer, no runtime fetch). CRUSH_TAG defaults to the
# latest stable release; override with `make image CRUSH_TAG=vX.Y.Z`. `crush --version`
# fails the build if the install didn't produce a working binary.
#
# CRUSH_AT_IMPORT toggles the local `@`-import patch (see client/patches/ and
# tasks/patch-crush-for-at-imports.md): with a `@path` on its own line in a context file
# (CLAUDE.md/AGENTS.md/CRUSH.md), the patched Crush recursively splices that file's contents
# in — the feature Crush lacks upstream. A patched build CANNOT use `go install …@tag` (the
# module proxy is read-only), so we clone the tag, `git apply` the patch, and build from source,
# stamping internal/version.Version so `crush --version` still reports the tag. Set
# CRUSH_AT_IMPORT=0 for the stock upstream build.
ARG CRUSH_TAG=v0.89.0
ARG CRUSH_AT_IMPORT=0
ENV GOBIN=/usr/local/bin GOFLAGS=-trimpath
COPY patches/ /patches/
RUN set -eux; \
    if [ "$CRUSH_AT_IMPORT" = "1" ]; then \
        git clone --depth 1 --branch "$CRUSH_TAG" https://github.com/charmbracelet/crush /tmp/crush; \
        git -C /tmp/crush apply /patches/crush-at-import.patch; \
        ( cd /tmp/crush && go install -ldflags "-X github.com/charmbracelet/crush/internal/version.Version=${CRUSH_TAG}" . ); \
        rm -rf /tmp/crush; \
    else \
        go install "github.com/charmbracelet/crush@${CRUSH_TAG}"; \
    fi; \
    crush --version

# Baked default Crush config: a local llama.cpp provider. Crush auto-discovers the served
# model at runtime, so no model list / API key is needed. crushrc is the modern config
# format (crush.json is deprecated); ~/.config/crush/crushrc is the global location.
COPY entrypoint/crushrc /root/.config/crush/crushrc

COPY entrypoint/shell.sh /shell.sh
