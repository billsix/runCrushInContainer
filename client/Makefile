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

# Apply the local `@`-import patch to Crush at build time (client/patches/, see
# tasks/archive/2026/08/21/patch-crush-for-at-imports.md): makes a `@path` on its own line in a context file
# (CLAUDE.md/AGENTS.md/CRUSH.md) recursively splice that file's contents in. Default ON here;
# `make image CRUSH_AT_IMPORT=0` builds stock upstream Crush instead. A patched build compiles
# Crush from a git checkout rather than `go install …@tag` (which can't be patched); expect a
# longer build. Re-verify the patch on every CRUSH_TAG bump (see the task doc).
CRUSH_AT_IMPORT ?= 1

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

.PHONY: all
all: image ## Build the image

.PHONY: image
image: ## build the client image: full toolchain + Crush built from source (pinned CRUSH_TAG)
	$(CONTAINER_CMD) build -t $(CONTAINER_NAME) \
		--build-arg CRUSH_TAG=$(CRUSH_TAG) \
		--build-arg CRUSH_AT_IMPORT=$(CRUSH_AT_IMPORT) .

.PHONY: shell
shell: image ## run Crush in an ephemeral container; mounts PROJECT at /work
	$(CONTAINER_CMD) run -it --rm \
		--entrypoint /bin/bash \
		$(SELINUX_OPT) \
		$(NET_FLAGS) \
		-v $(PROJECT):/work \
		$(TMUX_MOUNT) \
		$(GNUPG_MOUNT) \
		$(GITCONFIG_MOUNT) \
		$(PERSONAL_MOUNT) \
		$(STACK_MOUNT) \
		$(EXTRA_MOUNTS) \
		$(CONTAINER_NAME) \
		/shell.sh

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
