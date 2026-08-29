# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
.DEFAULT_GOAL := help

# ============================================================================
#  runCrushInContainer — CLIENT side.  A barebones Podman sandbox (the full
#  runClaudeInContainer toolchain) with Crush built from source at image-build
#  time.  Runs on LINUX; reaches the Mac's llama-server over an SSH tunnel.
#
#    make image                    build the image (full toolchain + pinned Crush)
#    make shell                    run Crush in an ephemeral container (mounts CWD)
#    make shell PROJECT=/path/app  mount a specific project at /work instead of CWD
#
#  Deferred on purpose (see ../tasks/): the task/stack/personal-config machinery and
#  any auth plumbing — the endpoint is a local, keyless llama-server behind SSH.
# ============================================================================

CONTAINER_CMD  = podman
CONTAINER_NAME = crushcontainer

# Latest stable Crush release (decision 2026-08-18). Override: make image CRUSH_TAG=vX.Y.Z
CRUSH_TAG ?= v0.89.0

# Full ~430-package dev toolchain vs a minimal image. Default 1 = the batteries-included image
# (Dockerfile ARG defaults to 0, so a bare `podman build` is lean — the usual convention).
# `make image FULL_TOOLCHAIN=0` builds a ~2 GB minimal image (golang/git/ripgrep + strace/tcpdump)
# that still builds Crush at any flag combination, runs it against the model, vendors, and hosts a
# runtime egress check — and fits the dev sandbox's nested-podman store for in-sandbox verification.
# Same CONTAINER_NAME for both (a minimal HOST build replaces the full image until the next full
# rebuild — accepted). See tasks/minimal-client-image.md.
FULL_TOOLCHAIN ?= 1

# Apply the local `@`-import patch to Crush at build time (client/patches/, see
# tasks/archive/2026/08/21/patch-crush-for-at-imports.md): makes a `@path` on its own line in a context file
# (CLAUDE.md/AGENTS.md/CRUSH.md) recursively splice that file's contents in. Default ON here;
# `make image CRUSH_AT_IMPORT=0` builds without the feature (the egress patches below still
# apply per their own flags). Re-verify the patch on every CRUSH_TAG bump (see the task doc).
CRUSH_AT_IMPORT ?= 1

# ---- Egress patch flags: one per decision, defaults encode the audit's disposition ----
# From the dependency network audit (../tasks/reference/dependency-network-audit.md, D1-D12).
# Each PATCH_OUT_<X> guards one patch in client/patches/, applied at BUILD time by
# entrypoint/03-build-crush.sh identically in both build modes (online clone and
# CRUSH_VENDORED=1) — the vendored tree stays complete and unpatched, so every flag
# combination builds, offline included.
#   1 = patched OUT by default  (unsolicited phone-home + out-of-design cloud providers)
#   0 = KEPT by default         (useful user-initiated online features)
# Flip any single decision, e.g.:
#   make image PATCH_OUT_WEB_TOOLS=1        # hardened build: no web tools
#   make image PATCH_OUT_GOOGLE_PROVIDER=0  # restore the Gemini/Vertex providers
PATCH_OUT_UPDATE_CHECK         ?= 1
PATCH_OUT_TELEMETRY            ?= 1
PATCH_OUT_UPDATE_PROVIDERS_CMD ?= 1
PATCH_OUT_WEB_TOOLS            ?= 0
PATCH_OUT_SOURCEGRAPH          ?= 0
PATCH_OUT_GOOGLE_PROVIDER      ?= 1
PATCH_OUT_BEDROCK_AWS          ?= 1
PATCH_OUT_AZURE                ?= 1
PATCH_OUT_OPENROUTER           ?= 1
PATCH_OUT_VERCEL               ?= 1
PATCH_OUT_HYPER                ?= 1
PATCH_OUT_COPILOT              ?= 1
PATCH_FLAGS = \
	--build-arg PATCH_OUT_UPDATE_CHECK=$(PATCH_OUT_UPDATE_CHECK) \
	--build-arg PATCH_OUT_TELEMETRY=$(PATCH_OUT_TELEMETRY) \
	--build-arg PATCH_OUT_UPDATE_PROVIDERS_CMD=$(PATCH_OUT_UPDATE_PROVIDERS_CMD) \
	--build-arg PATCH_OUT_WEB_TOOLS=$(PATCH_OUT_WEB_TOOLS) \
	--build-arg PATCH_OUT_SOURCEGRAPH=$(PATCH_OUT_SOURCEGRAPH) \
	--build-arg PATCH_OUT_GOOGLE_PROVIDER=$(PATCH_OUT_GOOGLE_PROVIDER) \
	--build-arg PATCH_OUT_BEDROCK_AWS=$(PATCH_OUT_BEDROCK_AWS) \
	--build-arg PATCH_OUT_AZURE=$(PATCH_OUT_AZURE) \
	--build-arg PATCH_OUT_OPENROUTER=$(PATCH_OUT_OPENROUTER) \
	--build-arg PATCH_OUT_VERCEL=$(PATCH_OUT_VERCEL) \
	--build-arg PATCH_OUT_HYPER=$(PATCH_OUT_HYPER) \
	--build-arg PATCH_OUT_COPILOT=$(PATCH_OUT_COPILOT)

# Offline/airgap vendoring (see tasks/vendor-build-sources-for-airgap-rebuild.md). `make vendor`
# (ONLINE) pre-fetches the Crush source + all its Go module deps into $(VENDOR_DIR)/crush; then
# `make image CRUSH_VENDORED=1` rebuilds the image from that with NO network. VENDOR_DIR is the
# host folder that gets zipped and carried to the airgap box. When CRUSH_VENDORED=1 the image build
# bind-mounts it read-only at /vendor/crush (podman build --volume) and the Dockerfile builds it
# with `GOPROXY=off go build -mod=vendor`. NOTE: only the internet-sourced Crush is vendored — the
# Fedora base image + dnf packages are the airgapped system's own (not vendored).
VENDOR_DIR     ?= $(CURDIR)/vendor
CRUSH_VENDORED ?= 0
# VENDOR_TOOLS bakes the `hf` CLI into the image — needed ONLY to run `make vendor` (the online
# GGUF download) inside the image. Default 0 so a normal/airgap `make image` does NOT install it
# (the airgap rebuild uses the vendored GGUF and never downloads). `vendor.sh` builds with =1.
VENDOR_TOOLS   ?= 0
ifeq ($(CRUSH_VENDORED),1)
# --volume mounts the vendored checkout into every build RUN step; :ro keeps it read-only. If an
# enforcing-SELinux host denies the mount, add ,z (e.g. :ro,z).
CRUSH_VENDOR_FLAGS := --volume $(VENDOR_DIR)/crush:/vendor/crush:ro --build-arg CRUSH_VENDORED=1
else
CRUSH_VENDOR_FLAGS :=
endif

# The project Crush works on, mounted at /work. Defaults to the dir you run make from.
PROJECT ?= $(CURDIR)

EXTRA_MOUNTS ?=

# --network=host (Linux) so 127.0.0.1:8080 in the container is the host's SSH-forwarded
# port. This is why the client is Linux-only for now.
NET_FLAGS ?= --network=host

# SELinux: run the container UNCONFINED, matching how the sibling runClaudeInContainer runs
# under NESTED_PODMAN=1. Without this, on an enforcing host the confined container is denied
# access to bind-mounted host dirs and — the case that bit us — cannot follow symlinks that
# jump out to a host path like /mnt/sda1 ("permission denied"), even with :z on the mount.
# This is a local dev sandbox reaching a local LLM, so the confinement buys little. To run
# confined instead, override with an empty value: `make shell SELINUX_OPT=`.
SELINUX_OPT ?= --security-opt label=disable

# Conditional host-config mounts (matching runClaudeInContainer): mount the user's tmux, git,
# and gnupg config into the container only when the host file/dir exists. `readlink -f` resolves
# symlinks; the `[ -f ]` / `[ -d ]` test skips a missing file so the run still works without it.
TMUX_FILE := $(HOME)/.tmux.conf
TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)

GITCONFIG_FILE := $(HOME)/.gitconfig
GITCONFIG_REAL_PATH := $(shell readlink -f $(GITCONFIG_FILE))
GITCONFIG_MOUNT := $(shell if [ -f $(GITCONFIG_REAL_PATH) ]; then echo "-v $(GITCONFIG_REAL_PATH):/root/.gitconfig:Z" ; fi)

GNUPG_FILE := $(HOME)/.gnupg
GNUPG_REAL_PATH := $(shell readlink -f $(GNUPG_FILE))
GNUPG_MOUNT := $(shell if [ -d $(GNUPG_REAL_PATH) ]; then echo "-v $(GNUPG_REAL_PATH):/root/.gnupg:Z" ; fi)

# Personal-overlay mount (UNCONDITIONAL): the baked conventions CLAUDE.md `@`-imports
# ai-coding-conventions.personal.md, so that path must always resolve. `touch` the host file at
# parse time (created blank if absent) and mount it over the baked blank default, so a maintainer's
# host overlay layers in while the tracked default stays generic. Host file is dotted; container
# path is un-dotted (matches runClaudeInContainer).
PERSONAL_FILE := $(HOME)/.ai-coding-conventions.personal.md
PERSONAL_MOUNT := $(shell touch $(PERSONAL_FILE) 2>/dev/null; echo "-v $(PERSONAL_FILE):/root/.config/crush/ai-coding-conventions.personal.md:Z")

# Diversion-stack mount (UNCONDITIONAL, persists across --rm): the conventions reference
# ~/.config/crush/stack.md; keep it on the HOST so the global-across-repos stack survives the
# ephemeral container. mkdir+touch at parse time so the mount always resolves.
STACK_FILE := $(HOME)/.config/crush/stack.md
STACK_MOUNT := $(shell mkdir -p $(HOME)/.config/crush 2>/dev/null; touch $(STACK_FILE) 2>/dev/null; echo "-v $(STACK_FILE):/root/.config/crush/stack.md:Z")

# Nested podman (opt-in: `make shell NESTED_PODMAN=1`): run podman INSIDE the client so Crush can
# build/run a project's own containers nested (make image/run/shell for container-per-project repos).
# Inner storage uses fuse-overlayfs (entrypoint/dotfiles/.config/containers/storage.conf). Every
# INNER `podman run` still needs `--cgroups=disabled` (the sandbox /sys/fs/cgroup is read-only).
# See tasks/reference/nested-podman-design.md. NOTE the client is often itself run nested, so a
# project build inside it is podman-in-podman-in-podman — run the client on the host (or an
# outer sandbox with NESTED_PODMAN=1) for a clean single level.
# The value is ALSO passed into the container as $NESTED_PODMAN (0/1, see the `run` below) so the
# agent can detect it directly — the make VARIABLE alone is host-side and invisible inside; pair
# `$NESTED_PODMAN` (intent) with `test -e /dev/fuse && podman info` (does it actually work).
NESTED_PODMAN ?= 0
NESTED_PODMAN_TMPFS_SIZE ?= 8g
ifeq ($(NESTED_PODMAN),1)
# label=disable is already always-on via SELINUX_OPT. unmask=ALL lets the inner rootful netavark
# write per-interface sysctls (bridged networking); net_admin is for its veth/bridge over netlink;
# /dev/fuse backs fuse-overlayfs; the tmpfs is the (RAM-backed) inner image store. No libpod-shadow
# tmpfs is needed here (unlike runClaudeInContainer) because the client does NOT mount the host's
# $XDG_RUNTIME_DIR, so there's no host podman state to collide with.
NESTED_PODMAN_FLAGS := --device /dev/fuse \
	--device /dev/net/tun \
	--security-opt unmask=ALL \
	--cap-add=sys_admin,mknod,net_admin \
	--tmpfs /var/lib/containers:rw,size=$(NESTED_PODMAN_TMPFS_SIZE)
else
NESTED_PODMAN_FLAGS :=
endif

.PHONY: all
all: image ## Build the image

.PHONY: image
image: ## build the client image: full toolchain + Crush built from source (pinned CRUSH_TAG). FULL_TOOLCHAIN=0 builds a minimal image; CRUSH_VENDORED=1 builds offline from ./vendor; PATCH_OUT_<X>=0/1 flips any egress patch (see the flag block above)
	$(CONTAINER_CMD) build -t $(CONTAINER_NAME) \
		--build-arg CRUSH_TAG=$(CRUSH_TAG) \
		--build-arg CRUSH_AT_IMPORT=$(CRUSH_AT_IMPORT) \
		--build-arg FULL_TOOLCHAIN=$(FULL_TOOLCHAIN) \
		--build-arg VENDOR_TOOLS=$(VENDOR_TOOLS) \
		$(PATCH_FLAGS) \
		$(CRUSH_VENDOR_FLAGS) .

.PHONY: vendor
vendor: image ## [ONLINE] pre-fetch Crush source + Go deps into $(VENDOR_DIR)/crush for an offline (CRUSH_VENDORED=1) rebuild
	@mkdir -p $(VENDOR_DIR)
	$(CONTAINER_CMD) run --rm --entrypoint /bin/bash \
		$(SELINUX_OPT) \
		-e CRUSH_TAG=$(CRUSH_TAG) \
		-e CRUSH_AT_IMPORT=$(CRUSH_AT_IMPORT) \
		-v $(VENDOR_DIR):/vendor:Z \
		$(CONTAINER_NAME) \
		-c '/usr/local/bin/vendor/vendor-crush.sh /vendor/crush'
	@echo "vendored Crush into $(VENDOR_DIR)/crush — carry the repo (with ./vendor and server/) to the airgap box, then: make image CRUSH_VENDORED=1"

# --- shell / shell-exec share ONE container invocation, defined here so the two
# targets can never drift. Scoped to this pair ONLY. See runClaudeInContainer
# tasks/add-shell-exec-target.md for the design.
SHELL_RUN_FLAGS = \
		--entrypoint /bin/bash \
		-v ./entrypoint/shell.sh:/shell.sh:Z \
		-e NESTED_PODMAN=$(NESTED_PODMAN) \
		$(SELINUX_OPT) \
		$(NET_FLAGS) \
		-v $(PROJECT):/work \
		$(TMUX_MOUNT) \
		$(GNUPG_MOUNT) \
		$(GITCONFIG_MOUNT) \
		$(PERSONAL_MOUNT) \
		$(STACK_MOUNT) \
		$(NESTED_PODMAN_FLAGS) \
		$(EXTRA_MOUNTS)

# In-container mount path of the driven PROJECT (matches -v $(PROJECT):/work).
REPO_MOUNT = /work

# shell-exec payload: cd to the project root (independent of shell.sh's own cd),
# then run the inline CMD, else the project-relative SCRIPT. Prefers CMD if both set.
SHELL_EXEC_ARGS = -c 'cd $(REPO_MOUNT) && $(if $(CMD),$(CMD),exec bash $(SCRIPT))'

.PHONY: shell
shell: image ## run Crush in an ephemeral container; mounts PROJECT at /work (NESTED_PODMAN=1 for podman-in-podman)
	$(CONTAINER_CMD) run -it --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) /shell.sh

.PHONY: shell-exec
shell-exec: image ## run a script/command in the container env (no TTY): make shell-exec SCRIPT=path | CMD='...'
	@[ -n "$(SCRIPT)$(CMD)" ] || { echo 'usage: make shell-exec SCRIPT=<path under PROJECT> | CMD="..."'; exit 2; }
	$(CONTAINER_CMD) run --rm $(SHELL_RUN_FLAGS) $(CONTAINER_NAME) /shell.sh $(SHELL_EXEC_ARGS)

.PHONY: format
format: image ## format the client shell scripts with shfmt (runs in the built image)
	$(CONTAINER_CMD) run --rm --entrypoint /bin/bash \
		$(SELINUX_OPT) \
		-v $(CURDIR):/src -w /src \
		$(CONTAINER_NAME) \
		/src/entrypoint/format.sh

.PHONY: image-export
image-export: ## save the built image to a timestamped tar (podman save)
	$(CONTAINER_CMD) save $(CONTAINER_NAME) -o $(CONTAINER_NAME)-$(shell date +%m-%d-%Y_%H-%M-%S).tar

.PHONY: image-import
image-import: ## load an image from a tar: make image-import FILE=foo.tar
	$(CONTAINER_CMD) load -i $(FILE)

.PHONY: help
help:
	@grep --extended-regexp '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'
