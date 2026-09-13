# Decouple FULL_TOOLCHAIN from NESTED_PODMAN — client is always full toolchain

**Status:** Done (2026-09-12; verified 2026-09-13 by the host full-image build and Python LSP
working). Archived 2026-09-13.
**Priority:** 2
**Difficulty:** 4

## BLUF

The crush client's `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` had tied *image
content* to a *run-time capability* flag, so `make shell NESTED_PODMAN=1` on the host (typed to get
nested capability) silently rebuilt the minimal, toolchain-less image with no language servers. The
fix defaulted the client to the full toolchain, decoupled it from `NESTED_PODMAN`, removed the
now-purposeless minimal variant, and dropped the `shell:`/`shell-exec: image` dependencies so
`make shell` no longer rebuilds. `NESTED_PODMAN` became run-time launch flags only. Outcome:
`make image` builds the full toolchain regardless of `NESTED_PODMAN`, and `make shell NESTED_PODMAN=1`
runs that full image nested-capable — full toolchain and nested at once.

## Context

This implemented the decision recorded in `tasks/reference/nested-podman-vs-image-content.md`
(William Emerison Six <billsix@gmail.com>, 2026-09-12), which holds the full rationale, history, and
the mistake it undid.

**State before the change (client/):**
- `Makefile` — `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` (the coupling), and
  `shell: image` / `shell-exec: image` / `format: image` prerequisites.
- `Dockerfile` — `00-install-minimal.sh` always ran; `ARG FULL_TOOLCHAIN=0` then a
  `if [ "$FULL_TOOLCHAIN" = "1" ]; then 01-install-base.sh; fi` gate around the ~430-package toolchain
  (the six LSP servers).
- The `NESTED_PODMAN` launch-flag block (devices/caps/tmpfs) + `-e NESTED_PODMAN=$(NESTED_PODMAN)`,
  and `PODMAN_RUN_FLAGS`, were already run-time-only.

**Decision:** the agent's in-sandbox lean verification build (the minimal image's only user) was
dropped — a lean nested build exercised a different package set than the shipped full image, so it
was false-confidence anyway.

## What was done

1. **Decoupled + defaulted full.** Removed the `FULL_TOOLCHAIN` Makefile variable (left a breadcrumb
   comment) and its `--build-arg`; removed the Dockerfile `ARG FULL_TOOLCHAIN` and the `if`-gate so
   `01-install-base.sh` runs unconditionally.
2. **Removed the minimal variant.** `00-install-minimal.sh` stayed as the always-run base and
   `01-install-base.sh` now always layers the full toolchain on top, so the client is always the
   batteries-included image. The egress tools (`strace`/`tcpdump`) remained (they're in the full set);
   Crush still built (Go+git present unconditionally).
3. **Dropped `shell: image` and `shell-exec: image`** (parity with runClaudeInContainer, whose `shell`
   has no `image` prerequisite); left `format: image` alone. `make shell` now runs the last-built
   image and errors cleanly if none exists — the README says to run `make image` first.
4. **Updated docs:** `CLAUDE.md` (the "Nested = the minimal image, automatically" bullet), the README
   client quick-start, `tasks/reference/architecture.md` (the two-sizes section + the nested-build
   gotcha), `crush-lsp-integration.md` (LSP servers always present), and the baked
   `container-file-layout.md` twin, all cross-linking `nested-podman-vs-image-content.md`.
5. **Coordinated the fleet convention.** Paired with runClaudeInContainer
   `tasks/archive/2026/09/13/scope-lean-image-to-downstream-not-sandboxes.md`: the "lean when nested"
   standard was rescoped to downstream projects only, and `tasks/port-lean-image-nested-convention.md`
   was updated to note the client is no longer its reference implementation.

## Verification

- `make image` on the host (no `NESTED_PODMAN`) and `make image NESTED_PODMAN=1` both produced a
  **full** image — confirmed on the maintainer's host build (`command -v ty clangd gopls` resolve).
- `make shell NESTED_PODMAN=1` runs the full image and is nested-capable
  (`test -e /dev/fuse && podman info` succeeds inside).
- No `NESTED_PODMAN` reference remains around `FULL_TOOLCHAIN` (the variable was removed).
- LSP tools worked in the running client (2026-09-13) once the separate powernap fix also landed.

## Related

- `tasks/reference/nested-podman-vs-image-content.md` — the rationale/decision record.
- runClaudeInContainer `tasks/archive/2026/09/13/scope-lean-image-to-downstream-not-sandboxes.md` — the
  fleet-side rescope.
- `tasks/archive/2026/09/13/lsp-python-server-not-registering.md` and
  `tasks/lsp-add-root-markers-gate-startup.md` — independent LSP issues; this change was their
  prerequisite (no language servers existed until the client was always full).
- Superseded the lean-image framing in `tasks/port-lean-image-nested-convention.md`,
  `tasks/reference/architecture.md`, and `CLAUDE.md` (all updated).
