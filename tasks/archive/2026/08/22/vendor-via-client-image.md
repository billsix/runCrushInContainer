# Rewrite `vendor.sh` to podman+make only (vendor inside the client image); bake `hf`

**Status:** complete
**Started:** 2026-08-22 · **Completed:** 2026-08-22

Rewrote the top-level `./vendor.sh` so both sides vendor inside the client image via podman, leaving the
online host needing only podman + make (no host `go`/`git`/`python3`). Baked `python3-huggingface-hub`
into the client image behind `VENDOR_TOOLS`, and made `server/Makefile` `pull` prefer the system `hf`.
Validated in-sandbox; the real-machine offline check was tracked in
`tasks/verify-vendored-airgap-rebuild.md`. The durable design is in `tasks/reference/architecture.md`
("Offline / airgap rebuild — vendoring").

## Decisions (2026-08-22)

The turning point: the maintainer **cannot bring container image blobs into the airgap** (only sources
and the model file cross), so the airgap box must rebuild the image from source and
`image-export`/`image-import` is backup only.

1. **Vendor inside the client image.** An earlier objection (building the 22 GB image just to vendor is
   wasteful when you could export it) was wrong given the above: the online image build is not redundant,
   it already contains every tool, and it uses the same Go that builds Crush.
   - Rejected: the first-cut host-tools `vendor.sh`, which needed host `go`/`git`/`python3` (the
     maintainer guarantees only podman + make) and was off-philosophy for a container-centric repo.
   - Rejected: small throwaway `golang:`/`python:` images, which only made sense to avoid the 22 GB build
     and otherwise add pulls and a different toolchain.
2. **`hf` via dnf, flag-gated.** `hf` is used only to download the GGUF during online vendoring; the
   airgap rebuild uses the vendored GGUF. Installing it unconditionally in `01-install-base.sh` (the first
   cut) would have forced the airgap dnf mirror to carry an unused package, so it moved to the gated group
   script `client/entrypoint/02-install-vendor-tools.sh`, dispatched by Dockerfile `ARG VENDOR_TOOLS`
   (default `0`). dnf rather than pip because the airgap has no PyPI. `python3-huggingface-hub` was
   verified in Fedora 44 `updates` (v1.24.0, provides `/usr/bin/hf`).
3. **`server/Makefile` `pull` prefers the system `hf`** and falls back to the venv, so server vendoring
   runs in the client image with no pip while standalone macOS use still works.

## What was done

- `client/entrypoint/02-install-vendor-tools.sh`; Dockerfile `ARG VENDOR_TOOLS=0`; `client/Makefile`
  `VENDOR_TOOLS ?= 0` plus `--build-arg`; `vendor.sh` builds with `VENDOR_TOOLS=1`.
- `server/Makefile`: `SYS_HF := $(shell command -v hf 2>/dev/null)`, `pull: $(if $(SYS_HF),,venv)`, and
  the recipe runs `$(if $(SYS_HF),hf,$(HF)) download …`. `venv`/`check-repo` unchanged.
- `vendor.sh` runs `make -C client vendor`, then
  `podman run --rm --security-opt label=disable -v server:/server:Z -w /server <CONTAINER_NAME> make vendor`,
  reading `CONTAINER_NAME` from `client/Makefile`; the host go/git/python3 checks were dropped.
- README "Airgapped rebuild" (host = podman + make only) and the `architecture.md` vendoring section were
  updated.

## Verification (in-sandbox)

`bash -n` and shfmt clean; `CONTAINER_NAME` extraction gave `crushcontainer`; a default `make image`
passed `VENDOR_TOOLS=0` and `make vendor` passed `VENDOR_TOOLS=1`; `make -n` showed both `pull` branches
correct (no hf: venv + pip; stub hf: bare `hf download`); the dnf package name was confirmed. The full
podman-run-in-client-image path was left to `tasks/verify-vendored-airgap-rebuild.md`.

## Related

- `vendor.sh`, `client/entrypoint/vendor/vendor-crush.sh`, `client/Makefile` (`vendor` target),
  `client/entrypoint/01-install-base.sh`, `server/Makefile`.
- `tasks/archive/2026/08/22/vendor-build-sources-for-airgap-rebuild.md`: the original vendoring work.
- `tasks/archive/2026/08/25/hf-install-dnf-or-pip-fallback.md`: the later dnf-or-pip fallback for `hf`.
