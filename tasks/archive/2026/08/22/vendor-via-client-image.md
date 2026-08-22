# Rewrite `vendor.sh` to podman+make only (vendor inside the client image); bake `hf`

**Status:** complete — `vendor.sh` runs both sides inside the client image (host needs only podman+make);
`python3-huggingface-hub` baked into the image (flag-gated via `VENDOR_TOOLS`); `server/Makefile` `pull`
prefers the system `hf`. Validated in-sandbox (parse/shfmt/`make -n` both hf branches/dnf name). Durable
design captured in `tasks/reference/architecture.md`; the real-machine offline check is tracked in
`tasks/verify-vendored-airgap-rebuild.md`.
**Completed:** 2026-08-22
**Priority:** 3
**Difficulty:** 3
**Started:** 2026-08-22

## Goal

Make the top-level `./vendor.sh` vendor **both sides inside the client image** via podman, so the online
host needs only **podman + make** — no host `go`/`git`/`python3`. Bake `huggingface_hub` into the client
image so the in-image server vendoring can download the GGUF with no venv/pip.

## Why this shape (decisions, 2026-08-22)

The turning point: **the maintainer cannot bring container image blobs into the airgap** (only sources +
the model file cross). So the airgap box **must rebuild the image from source** — `image-export`/`import`
is backup-only, not the transport path. Consequences:

1. **Vendor inside the CLIENT image — decided.** My earlier objection ("building the 22 GB image just to
   vendor is wasteful, you'd just export/import it") was **wrong** given the above: building the client
   image online is not redundant (you can't ship it), and the image already contains every tool. So
   vendoring in it needs only podman+make on the host and uses the *same* Go that builds Crush.
   - **Rejected — host-tools wrapper** (the first-cut `vendor.sh`, now replaced): needs host `go`/`git`/`python3`, which
     the maintainer does NOT guarantee (only podman+make); also off-philosophy (repo is container-centric).
   - **Rejected — small throwaway `golang:`/`python:` images:** the only reason to prefer them was to
     avoid the 22 GB image build; with that objection gone they're strictly worse (extra pulls, a
     different toolchain than the build).
2. **Bake `huggingface_hub` via dnf, but FLAG-GATED — decided (refined 2026-08-22).** `hf` is used
   ONLY to download the GGUF during *online* vendoring; the airgap rebuild uses the vendored GGUF and
   never calls it. So installing it unconditionally (my first cut, in `01-install-base.sh`) was wrong —
   it would force the airgap dnf mirror to carry a package the airgap never uses. Instead it lives in a
   gated group script **`client/entrypoint/02-install-vendor-tools.sh`**, dispatched by a Dockerfile
   **`ARG VENDOR_TOOLS`** (default **0**). `vendor.sh` builds with `VENDOR_TOOLS=1`; a normal/airgap
   `make image` leaves it 0 → **no hf, no airgap-mirror dependency on it**. Still dnf not pip (pip needs
   PyPI, absent on the airgap); `python3-huggingface-hub` verified in Fedora 44 `updates` v1.24.0,
   provides `/usr/bin/hf`. `git`/`make`/`python3`/`golang` are already in the always-installed base.
3. **`server/Makefile` `pull` prefers the system `hf`** (baked) and falls back to the venv — so server
   vendoring runs in the client image with no pip, while standalone macOS use still works via the venv.

## Plan

- [x] **Bake hf — flag-gated.** `client/entrypoint/02-install-vendor-tools.sh` (dnf
      `python3-huggingface-hub`, provides `/usr/bin/hf`), dispatched by Dockerfile `ARG VENDOR_TOOLS=0`;
      `client/Makefile` `VENDOR_TOOLS ?= 0` + `--build-arg`; `vendor.sh` builds with `VENDOR_TOOLS=1`.
      Verified: default/airgap `make image` → `VENDOR_TOOLS=0` (no hf); `make vendor` → `VENDOR_TOOLS=1`.
      (NOT in `01-install-base.sh` — the airgap must not depend on it.)
- [x] **`server/Makefile`** — `SYS_HF := $(shell command -v hf 2>/dev/null)`; `pull: $(if $(SYS_HF),,venv)`;
      recipe `$(if $(SYS_HF),hf,$(HF)) download …`. `venv`/`check-repo` unchanged for standalone Mac use.
      Verified both branches with `make -n` (no-hf → venv+pip; stub-hf → bare `hf download`).
- [x] **Rewrote `vendor.sh`** to podman+make only: `make -C client vendor` then `podman run --rm
      --security-opt label=disable -v server:/server:Z -w /server <CONTAINER_NAME> make vendor`. Reads
      `CONTAINER_NAME` from `client/Makefile`; dropped the host go/git/python3 checks.
- [x] **Docs** — README "Airgapped rebuild" (host = podman+make only) and `architecture.md` vendoring
      section updated.
- [x] **In-sandbox validation** — `bash -n` + shfmt clean; `CONTAINER_NAME` extraction = `crushcontainer`;
      both `pull` branches correct; `python3-huggingface-hub` confirmed in Fedora 44 (`/usr/bin/hf`). The
      full podman-run-in-client-image path is exercised on a real box by
      `tasks/verify-vendored-airgap-rebuild.md`.

## Cross-links

- `vendor.sh`, `client/entrypoint/vendor/vendor-crush.sh`, `client/Makefile` (`vendor` target),
  `client/entrypoint/01-install-base.sh`, `server/Makefile`.
- `tasks/archive/2026/08/22/vendor-build-sources-for-airgap-rebuild.md` — the original vendoring impl.
- `tasks/verify-vendored-airgap-rebuild.md` — real-machine verification (now: host needs only podman+make).
- `tasks/reference/architecture.md` — "Offline / airgap rebuild — vendoring".
