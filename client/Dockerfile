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
ARG CRUSH_TAG=v0.89.0
ENV GOBIN=/usr/local/bin GOFLAGS=-trimpath
RUN go install github.com/charmbracelet/crush@${CRUSH_TAG} && crush --version

# Baked default Crush config: a local llama.cpp provider. Crush auto-discovers the served
# model at runtime, so no model list / API key is needed. crushrc is the modern config
# format (crush.json is deprecated); ~/.config/crush/crushrc is the global location.
COPY entrypoint/crushrc /root/.config/crush/crushrc

COPY entrypoint/shell.sh /shell.sh
