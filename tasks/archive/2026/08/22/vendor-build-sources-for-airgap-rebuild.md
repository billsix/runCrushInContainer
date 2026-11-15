# Vendor all build sources so client + server rebuild on an airgapped system

**Status:** complete
**Started:** 2026-08-22 · **Completed:** 2026-08-22

Made the three internet-sourced build inputs (Crush repo + Go module deps, llama.cpp repo, the Muse
Glimmer GGUF) vendorable into gitignored folders, so the repo can be zipped, moved to an airgapped box,
and rebuilt with no network. Verified the core offline Go build; the full real-machine image rebuild was
split out to `tasks/verify-vendored-airgap-rebuild.md` (the 22 GB image build cannot run in the dev
sandbox). The durable design is in `tasks/reference/architecture.md` ("Offline / airgap rebuild —
vendoring").

## Goal (maintainer, 2026-08-22)

Make all downloaded sources accessible outside the container and vendored, so everything can be zipped
up, moved to an airgapped system and rebuilt offline, with the build extracting what it needs from an
externally mounted folder. Named: Crush (full git repo with history at `CRUSH_TAG`, plus its Go module
deps), llama.cpp (full repo with history at `LLAMACPP_TAG`), and the GGUF.

This differs from two other "offline" ideas: an exported image that *runs* offline (already true via
`image-export`/`image-import`), and seeding base images for offline *nested* project builds
(`tasks/offline-nested-podman-base-images.md`, a separate concern). This task is about *rebuilding*
client and server with no internet.

## Decisions (2026-08-22)

- **Scope: exactly the three internet-sourced artifacts.** The Fedora base image and the ~430 dnf
  packages from `client/entrypoint/01-install-base.sh` are not vendored; the airgapped system already has
  them (that is why the current Crush compiles there; `golang` is one of the dnf packages). No toolchain
  vendoring on either side.
- **Vendor against `CRUSH_TAG=v0.89.0`, not v0.90.0.** The maintainer confirmed v0.89.0 compiles with the
  airgapped system's Go. v0.90.0's `go.mod` requires Go ≥1.26.6, which could break the airgap build and
  would drag in a Go-toolchain-vendoring question, so `tasks/bump-crush-to-v0.90.0.md` waits on this task
  and will re-vendor at its new tag.
- **Structure (maintainer: "sure"):** Makefile targets delegating to `entrypoint/vendor/*.sh` scripts,
  matching the repo's target-hands-off-a-script idiom, rather than one top-level script.
- **Implementer's discretion, chosen:** `go mod vendor` over a GOMODCACHE tarball; a build-time
  `--volume` mount of the vendored Crush over `COPY`-from-context, to keep the build context small.
- `CRUSH_TAG`/`LLAMACPP_TAG` keep their meaning; they now also select which vendored checkout is built.
- **No separate archive target**: the transport unit is the repo directory itself, whose gitignored
  `client/vendor/`, `server/llama.cpp` and `server/models` carry the sources. Zip/tar the repo after
  `make vendor` on both sides.

## What was done

- **`client/entrypoint/vendor/vendor-crush.sh`**: full clone of Crush at `CRUSH_TAG`, `git apply` of the
  `@`-import patch when `CRUSH_AT_IMPORT=1`, then `go mod vendor`, producing a build-ready, patch-applied,
  module-vendored checkout. `set -eu` (a linear pipeline, so fail-fast is right); idempotent (`rm -rf`
  of the destination first); shfmt-clean; baked into the image so `make vendor` runs it in-container.
- **Client `make vendor`** (`client/Makefile`, depends on `image`): runs the script with
  `-v $(VENDOR_DIR):/vendor:Z`, landing the tree at `client/vendor/crush`. `VENDOR_DIR ?= $(CURDIR)/vendor`.
- **Client offline build**: `CRUSH_VENDORED ?= 0`; `make image CRUSH_VENDORED=1` adds
  `--volume $(VENDOR_DIR)/crush:/vendor/crush:ro --build-arg CRUSH_VENDORED=1`. The Dockerfile's
  `CRUSH_VENDORED=1` branch copies the mount to `/tmp/crush` and runs `GOPROXY=off go build -mod=vendor`,
  version-stamped as before. The online branches were unchanged.
- **`server/Makefile`**: `make vendor` clones llama.cpp with full history at `LLAMACPP_TAG` and runs
  `make pull` for the GGUF, without building. `make llama` now does a full clone (dropped `--depth 1`)
  and reuses an existing checkout, so the airgap Mac builds the pre-vendored tree in place.
- **Ignore rules**: `client/.dockerignore` keeps `client/vendor/` out of the online build context;
  `.gitignore` adds `client/vendor/`.
- Updated `tasks/reference/architecture.md` and the README section "Airgapped rebuild — vendoring the
  sources".

## Verification

In a scratch Crush checkout, `go mod vendor` then `GOPROXY=off go build -mod=vendor` produced a working
`crush --version` with no network. This was proven on the v0.90.0 tree; the mechanism is
version-agnostic and the default vendors v0.89.0. The full offline image rebuild was moved to
`tasks/verify-vendored-airgap-rebuild.md`.

## Related

- `tasks/bump-crush-to-v0.90.0.md`: waited on this task.
- `tasks/offline-nested-podman-base-images.md`: base images for nested builds, untouched here.
- The personal-overlay "Self-contained images + live source" convention: this extends its run-offline
  requirement to rebuild-offline for the three internet-sourced parts.
- `client/Dockerfile`, `client/entrypoint/01-install-base.sh`, `server/Makefile`.
