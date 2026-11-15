# Minimal client image via FULL_TOOLCHAIN flag — and make it THE image for nested-podman use of this project

**Status:** complete (superseded 2026-09-12)
**Completed:** 2026-09-10
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

> **Superseded:** `FULL_TOOLCHAIN` was removed 2026-09-12; the client is always the full toolchain and
> `NESTED_PODMAN` is run-time only. The phase-2 coupling below left nested sessions with no language
> servers. Why the two were decoupled: `tasks/archive/2026/09/13/decouple-full-toolchain-from-nested-podman.md`
> and `tasks/reference/nested-podman-vs-image-content.md`. This file records what was built before that.

## What this did

**Phase 1 (2026-08-29)** split the client image build into an always-installed minimal layer and the
existing ~430-package toolchain behind a new `FULL_TOOLCHAIN` flag (Makefile `?= 1`, Dockerfile
`ARG FULL_TOOLCHAIN=0`). The motivation: the 22 GB full image did not fit the dev sandbox's nested
store, so every image-level check (egress patch/flag build paths, crushrc/`shell.sh` wiring, runtime
egress checks) needed a real-machine visit; see
`tasks/archive/2026/08/29/implement-egress-patch-flags.md`, whose final gate waited on this.

**Phase 2 (2026-09-10)** made the minimal image the nested default, at the maintainer's request ("make it
the default for when it's being built in a nested container … the makefile can enforce it, correct? as
long as the NESTED_PODMAN flag is set"): `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` in
`client/Makefile`, the same shape as `PODMAN_RUN_FLAGS`.

## What was built

- `client/entrypoint/00-install-minimal.sh`: dnf guard + ca-certificates, git, git-lfs, golang,
  gnupg2, less, ripgrep, strace, tcpdump, which. Crush's runtime shell-outs were checked: `rg` (grep
  tool, optional, falls back to a slower Go path; kept for usability) and `gh` (optional); everything
  else runs in Crush's Go shell interpreter. `openssh-clients` was not needed in the container (the
  tunnel runs on the host).
- `client/Dockerfile`: `00-install-minimal.sh` ran always as the first, shared layer; the ARG gated
  `01-install-base.sh`, which stayed verbatim. The `mounts.conf` `RUN` was wrapped in an existence test,
  because that file only exists with the full toolchain (containers-common via podman).
- `client/Makefile`: the flag, threaded as `--build-arg`, documented in the `image` help line.
- Docs: `CLAUDE.md` ("Nested = the minimal image, automatically", with the expected no-LSP message),
  `tasks/reference/architecture.md` client section, and runClaudeInContainer's
  `tasks/reference/nested-podman-design.md` (staged there, not committed). README unchanged: the host
  `make image` behaviour did not change.

## Decisions

2026-08-29 (William Emerison Six <billsix@gmail.com>, via explicit Q&A):
1. **Flag shape `FULL_TOOLCHAIN`**, a positive feature flag per repo convention; the minimal set is a
   strict subset installed first, so dnf no-ops the overlap and the layer cache is shared.
2. **Same image tag (`crushcontainer`) for both variants**, the maintainer's call over a separate tag.
   Accepted consequence: a host minimal build replaces the full image until the next full rebuild.
3. **Minimal set = golang + git + small runtime utilities + strace + tcpdump**, so the minimal image
   doubled as the runtime egress-check environment for
   `tasks/archive/2026/09/22/decide-egress-verification.md`.

Rejected: a separate `Dockerfile.minimal` (duplication, drift) and a multi-stage build (complicates the
dnf-cache idiom and the self-contained-image story).

2026-09-10: **no language servers in the minimal image** (maintainer: "minimal should not have language
servers"). The crushrc's six `lsp add` lines stayed and failed to start harmlessly nested.

Notes: `gcc` is in the minimal image as a `golang` (cgo) dependency, so "is this minimal?" sentinels must
be clang/nodejs/emacs/cmake/python3, not gcc. The on-disk `client/vendor/crush` scratch tree had drifted
(leftover egress-patch edits) and was regenerated pristine with `go mod vendor` before the vendored build.

## Verification

- Phase 1, in-sandbox nested: `make image FULL_TOOLCHAIN=0 CRUSH_VENDORED=1` built a 1.65 GB image;
  Crush ran (`v0.89.0+dirty`); rg/strace/tcpdump/git/go present; the full-toolchain sentinels absent.
- Phase 2: `make -n image` three ways (`NESTED_PODMAN=1` → `FULL_TOOLCHAIN=0`; host-shaped → `1`; nested
  + explicit `FULL_TOOLCHAIN=1` → `1`). A flagless nested `make image` built the minimal image online
  (exit 0, ~10 min) with `ty`/`gopls` absent as decided. It was 3.16 GB, not 1.65 GB, because the online
  path left the Go module cache (`/root/go/pkg/mod`) in the layer; not fixed here.
- Real machine (maintainer, 2026-09-10): a plain host `make image` built the full image ("it worked, and
  it seemed like it pulled everything in").
