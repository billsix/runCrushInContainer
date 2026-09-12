# Decouple FULL_TOOLCHAIN from NESTED_PODMAN — client is always full toolchain

**Status:** proposed — needs go-ahead
**Priority:** 2
**Difficulty:** 4

## BLUF

The crush client's `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` ties *image
content* to a *run-time capability* flag, so `make shell NESTED_PODMAN=1` on the host (asked
for to get nested capability) silently rebuilds the minimal, toolchain-less image with no
language servers. Fix: **default the client to the full toolchain, decouple it from
`NESTED_PODMAN`, remove the now-purposeless minimal variant, and drop the `shell: image`
dependency** so `make shell` never rebuilds. `NESTED_PODMAN` becomes run-time launch flags
only. **Done = `make image` builds the full toolchain regardless of `NESTED_PODMAN`, and
`make shell NESTED_PODMAN=1` runs that full image nested-capable (full toolchain + nested at
once), with docs updated.**

## Context

**Read first:** `tasks/reference/nested-podman-vs-image-content.md` — the full rationale,
history, and the mistake this undoes. This task is the implementation of that decision
(William Emerison Six <billsix@gmail.com>, 2026-09-12).

**Current state (client, all under `client/`):**
- `Makefile:37` — `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` (the coupling).
- `Makefile:281/285/290` — `shell: image`, `shell-exec: image`, `format: image`.
- `Dockerfile:14-17` — `00-install-minimal.sh` always runs (Go+git+ripgrep+curl+strace/tcpdump —
  enough to build Crush).
- `Dockerfile:25-29` — `ARG FULL_TOOLCHAIN=0` then `RUN … if [ "$FULL_TOOLCHAIN" = "1" ]; then
  01-install-base.sh; fi` (the ~430-package toolchain incl. the six LSP servers).
- `Makefile:202-217` — the `NESTED_PODMAN` launch-flag block (devices/caps/tmpfs) + `-e
  NESTED_PODMAN=$(NESTED_PODMAN)` at `:261`; `PODMAN_RUN_FLAGS` at `:147`.

**Decision:** drop the agent's in-sandbox lean verification build entirely (its only use) —
confirmed 2026-09-12; a lean nested build verifies a different package set than the full image
shipped, so it was false-confidence anyway.

## Work

1. **Decouple + default full:** change `Makefile:37` to `FULL_TOOLCHAIN ?= 1` (no `NESTED_PODMAN`
   reference). Keep `--build-arg FULL_TOOLCHAIN=$(FULL_TOOLCHAIN)` on the `build` line.
2. **Remove the minimal variant** (recommended end-state, since its only user is dropped):
   fold `00-install-minimal.sh` into the always-run base so the client is always the full
   toolchain, and remove the `ARG FULL_TOOLCHAIN` gate around `01-install-base.sh` — OR, if a
   lean option is wanted kept dormant, leave the `FULL_TOOLCHAIN=0` path but decoupled and
   default-1. **Recommend full removal** (cleanest; eliminates the false-confidence path).
   Preserve the egress-check tools (`strace`/`tcpdump`) — they're in the full set too.
   Confirm Crush still builds (Go+git present unconditionally).
3. **Drop `shell: image` and `shell-exec: image`** (parity with runClaudeInContainer, whose
   `shell` has no `image` prerequisite). Leave `format: image` decision to the maintainer
   (the template contract says a runner shouldn't reformat; `format` is separate). `make
   shell` then runs the last-built image; if none exists it errors cleanly — document "run
   `make image` first" in the README.
4. **Update docs:** `CLAUDE.md` ("Nested = the minimal image, automatically" → gone),
   `tasks/reference/architecture.md` (§"Two sizes" + nested-build gotcha), the README client
   quick-start, and cross-link `tasks/reference/nested-podman-vs-image-content.md`. Note in
   `crush-lsp-integration.md` that LSP servers are now always present (no nested caveat).
5. **Coordinate the fleet convention:** this pairs with runClaudeInContainer
   `tasks/scope-lean-image-to-downstream-not-sandboxes.md` — the "lean when nested" standard
   is rescoped to downstream projects only. Drop/rescope `tasks/port-lean-image-nested-convention.md`
   accordingly.
6. **Stage** the changes.

## Verification

- `make image` on the host (no `NESTED_PODMAN`) and `make image NESTED_PODMAN=1` both produce
  a **full** image: `podman run --rm crushcontainer bash -lc 'command -v ty clangd gopls rust-analyzer'`
  prints paths in both.
- `make shell NESTED_PODMAN=1` runs the full image **and** is nested-capable
  (`test -e /dev/fuse && podman info` succeeds inside).
- `grep FULL_TOOLCHAIN client/Makefile` shows no `NESTED_PODMAN` reference.
- (After the separate LSP task lands) LSP tools work in the running client.

## Related

- `tasks/reference/nested-podman-vs-image-content.md` — rationale/decision record.
- runClaudeInContainer `tasks/scope-lean-image-to-downstream-not-sandboxes.md` — the fleet rescope.
- `tasks/lsp-python-server-not-registering.md`, `tasks/lsp-add-root-markers-gate-startup.md` —
  independent LSP bugs that bite even a correct full image; this task is a prerequisite for
  them mattering (no servers at all until the client is full).
- Supersedes the lean-image framing in `tasks/port-lean-image-nested-convention.md`,
  `tasks/reference/architecture.md`, `CLAUDE.md`.
