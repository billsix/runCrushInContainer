# Decouple FULL_TOOLCHAIN from NESTED_PODMAN — client is always full toolchain

**Status:** complete
**Completed:** 2026-09-13

Removed the crush client's `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` coupling, which
had tied image *content* to a run-time capability flag: `make shell NESTED_PODMAN=1` on the host
silently rebuilt a minimal image with no language servers. The client is now always the full
toolchain, `NESTED_PODMAN` is launch flags only, and `make shell` no longer rebuilds. The rationale
and history live in `tasks/reference/nested-podman-vs-image-content.md` (William Emerison Six
<billsix@gmail.com>, 2026-09-12).

## What was done

1. **Decoupled and defaulted full.** Removed the `FULL_TOOLCHAIN` Makefile variable (left a
   breadcrumb comment) and its `--build-arg`; removed the Dockerfile `ARG FULL_TOOLCHAIN` and its
   `if`-gate, so `01-install-base.sh` (the ~430-package toolchain with the six LSP servers) runs
   unconditionally on top of the always-run `00-install-minimal.sh`.
2. **Removed the minimal variant.** Decided to drop the agent's in-sandbox lean verification build
   (the minimal image's only user), because it exercised a different package set than the shipped
   image and so gave false confidence. The egress tools (`strace`/`tcpdump`) and Crush's Go+git build
   deps stayed, being in the full set.
3. **Dropped `shell: image` and `shell-exec: image`** for parity with runClaudeInContainer; left
   `format: image`. `make shell` runs the last-built image and errors cleanly if none exists (the
   README says to run `make image` first).
4. **Updated docs:** `CLAUDE.md`, the README client quick-start, `tasks/reference/architecture.md`,
   `tasks/reference/crush-lsp-integration.md`, and the baked `container-file-layout.md` twin, all
   cross-linking `tasks/reference/nested-podman-vs-image-content.md`.
5. **Coordinated the fleet convention** with runClaudeInContainer
   `tasks/archive/2026/09/13/scope-lean-image-to-downstream-not-sandboxes.md` (the "lean when nested"
   standard rescoped to downstream projects), and noted in
   `tasks/archive/2026/11/15/port-lean-image-nested-convention.md` that the client was no longer its
   reference implementation.

## Verification

- `make image` with and without `NESTED_PODMAN=1` both produced a full image on the maintainer's
  host build (`command -v ty clangd gopls` resolved).
- `make shell NESTED_PODMAN=1` ran the full image nested-capable (`test -e /dev/fuse && podman info`
  succeeded inside).
- LSP tools worked in the running client (2026-09-13) once the separate powernap fix also landed.

## Related

- `tasks/reference/nested-podman-vs-image-content.md` — the decision record.
- `tasks/archive/2026/09/13/lsp-python-server-not-registering.md` and
  `tasks/lsp-add-root-markers-gate-startup.md` — independent LSP issues this change unblocked (no
  language servers existed until the client was always full).
