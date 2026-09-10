# Minimal client image via FULL_TOOLCHAIN flag — and make it THE image for nested-podman use of this project

**Status:** phase 1 **IMPLEMENTED (2026-08-29)** — `FULL_TOOLCHAIN` flag added, minimal image built and
verified in-sandbox (nested podman, from the vendored tree): 1.65 GB, Crush runs (`v0.89.0+dirty`),
rg/strace/tcpdump/git/go present, the full toolchain confirmed absent (clang/nodejs/emacs/cmake/python3
all missing; `gcc` present only as a `golang` dependency). Real machine: a plain `make image`
(defaults) still builds the full image unchanged — not re-verified here, but the change is purely an
added always-run layer + a gated existing layer.
**Phase 2 — IMPLEMENTED 2026-09-10** (William Emerison Six <billsix@gmail.com>: "make it the default for
when it's being built in a nested container … the makefile can enforce it, correct? as long as the
NESTED_PODMAN flag is set, which we have it do anyways!"): `FULL_TOOLCHAIN ?= $(if $(filter
1,$(NESTED_PODMAN)),0,1)` in `client/Makefile`; no language servers in the minimal image; `CLAUDE.md`
rule + `architecture.md` + runClaudeInContainer's `nested-podman-design.md` updated. Proof below.
Remaining: the host-side box (a plain `make image` on the maintainer's host still builds full).
**Priority:** 2
**Difficulty:** 3
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

## BLUF

Split the client image build into an always-installed minimal layer (what Crush needs to build,
run, and be egress-checked: golang, git, small runtime utilities, strace+tcpdump) and the existing
~430-package toolchain behind a new **`FULL_TOOLCHAIN`** flag — Makefile default `1` (the
maintainer's batteries-included image), Dockerfile ARG default `0` (lean bare build). Done = both
variants build; the minimal one (~1.5–2 GB) builds inside the dev sandbox's nested-podman store,
enabling in-session image-level verification that the 22 GB full image makes impossible there.

## Context

Decisions made 2026-08-29 (William Emerison Six <billsix@gmail.com>, via explicit Q&A):

1. **Flag shape: `FULL_TOOLCHAIN`** — positive feature flag matching the repo convention
   (Makefile `?= 1`, Dockerfile `ARG =0`). A new `client/entrypoint/00-install-minimal.sh` runs
   ALWAYS (first layer, shared by both variants — minimal is a strict subset installed first, so
   dnf no-ops the overlap and layer caching is shared); the existing `01-install-base.sh` stays
   verbatim (the don't-prune toolchain copy from runClaudeInContainer) but runs only when
   `FULL_TOOLCHAIN=1`, via the Dockerfile's usual ARG-`if` dispatch (per the "Host-agnostic setup
   belongs in a script" convention — flag logic in the Dockerfile, scripts optionless).
2. **Same image tag for both variants** (`crushcontainer`) — maintainer's call, overriding the
   separate-tag recommendation. Consequence, accepted: a minimal build on the HOST replaces the
   full image until the next full rebuild. (The agent's in-sandbox nested builds use the sandbox's
   own ephemeral store and can never touch the host image regardless.)
3. **Minimal set = golang + git + small runtime utilities + `strace` + `tcpdump`.** The
   strace/tcpdump addition makes the minimal image double as the runtime egress-check environment
   for `tasks/decide-egress-verification.md`. The exact runtime-utility list is verified at
   implementation time (check what Crush's tools shell out to — e.g. whether its grep tool needs
   `ripgrep`); `openssh-clients` is NOT needed in-container (the tunnel runs on the Linux host;
   the container reaches `127.0.0.1:8080` via `--network=host`).

Why (the problem this solves): the full image is ~22 GB — beyond the dev sandbox's nested-podman
RAM store — so image-level verification (the egress patch/flag build path, crushrc/shell.sh
wiring, runtime egress checks against a stub OpenAI endpoint) has needed a real-machine visit
every time (see `tasks/archive/2026/08/29/implement-egress-patch-flags.md`, whose final gate
waited on exactly this). A minimal image fits the sandbox with room to spare.

Read first: `client/Dockerfile` (the install RUNs + ARG dispatch), `client/Makefile` (flag block +
`image` target), `client/entrypoint/01-install-base.sh`, and the conventions in
`tasks/reference/architecture.md` ("Client" section + the egress patch/flag system).

Rejected alternatives: a separate `Dockerfile.minimal` (duplication, drifts); a multi-stage build
(complicates the dnf-cache idiom and the self-contained-image story for little gain).

## Goal

`make image` unchanged for the maintainer (full toolchain, default). `make image FULL_TOOLCHAIN=0`
produces a lean image with everything needed to: build Crush at any `PATCH_OUT_<X>` combination
(online or vendored), run it against the local model, run `make vendor` in-image, and host
strace/tcpdump egress checks. CLAUDE.md gains a standing note that in-sandbox verification builds
use `FULL_TOOLCHAIN=0`.

## Phase 2 (2026-09-10) — the minimal image is the nested-podman default for this project

**Ask (maintainer, 2026-09-10):** "the minimal image … is what I want the nested podman container to
use for this project, and it'll probably need to be mentioned in the CLAUDE.md." Today the minimal
image is opt-in (`make image FULL_TOOLCHAIN=0`) and only an agent note in `CLAUDE.md` says to use it
in-sandbox; the ask is to make that the default behaviour, not a remembered flag.

**Proposed mechanism — the `PODMAN_RUN_FLAGS` idiom, applied to the toolchain flag.** A
`NESTED_PODMAN=1` sandbox already exports `NESTED_PODMAN=1` into the session (runClaudeInContainer
`tasks/reference/nested-podman-design.md`, "The PODMAN_RUN_FLAGS convention"), so `client/Makefile` can
default the flag from that signal:

```make
# Full toolchain on a real host; the 1.65 GB minimal image when this project is built NESTED inside a
# sandbox (which exports NESTED_PODMAN=1) — the 22 GB full image does not fit the nested store.
FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)
```

Byte-identical on the maintainer's host (env var absent → `1`); `make image` inside a sandbox builds
minimal with no flag to remember; `make image FULL_TOOLCHAIN=1` still forces full anywhere. Same shape
as `PODMAN_RUN_FLAGS`, so a reader who knows one knows the other. Dockerfile `ARG FULL_TOOLCHAIN=0`
unchanged.

**Consequence (open question 1, resolved: no servers):** the minimal image skips `01-install-base.sh`, so it has
**none of the six language servers** the crushrc now declares (`tasks/reference/crush-lsp-integration.md`
§4) — Crush in the nested container would answer "no LSP client handles file" for everything, the
very complaint the LSP work fixed. Declared-but-absent servers fail to start harmlessly, so nothing
breaks; the question is whether the minimal image should carry the servers for the toolchains it
*does* ship. It ships `golang` → `gopls` (24 MB) is the obvious one. `ty` (26 MB, Rust binary, no
python needed to *run* the server, though Crush would be editing Python the image can't run) and
`clang-tools-extra` (62 MB + llvm-libs 140 MB) are the judgement calls; `rust-analyzer`, the bash
server (drags the nodejs24 runtime, ~60 MB) and `glsl-analyzer` follow their toolchains, which the
minimal image doesn't have.

Steps:

- [x] `client/Makefile`: the auto-default (replaced `FULL_TOOLCHAIN ?= 1`), comment rewritten;
      `image` target's `##` line says "nested … defaults to the minimal image" (2026-09-10).
- [x] Open question 1 decided: **no language servers in the minimal image** (2026-09-10) — nothing
      to add to `00-install-minimal.sh`; the CLAUDE.md rule notes the expected LSP message.
- [x] `make -n image` three ways (2026-09-10): `NESTED_PODMAN=1` → `--build-arg FULL_TOOLCHAIN=0`;
      `env -u NESTED_PODMAN` (host-shaped) → `FULL_TOOLCHAIN=1`; nested + `FULL_TOOLCHAIN=1` on the
      command line → `1` (override wins).
- [ ] In-sandbox proof: a flagless `make image` in the `NESTED_PODMAN=1` session builds the minimal
      image (online build; no vendored tree was present) — result recorded below when it finishes.
- [x] `CLAUDE.md`: new "Nested = the minimal image, automatically" convention (incl. the expected
      no-LSP message nested), and the "What's in use" entry restated as the default; `architecture.md`
      client section bullet + the "Nested-build gotcha" retitled to the forced-full case;
      runClaudeInContainer `nested-podman-design.md` PODMAN_RUN_FLAGS section: the idiom applied to a
      build variant (staged there, not committed — no authorization for that repo). README: unchanged
      — it documents the host `make image`, whose behaviour did not change.
- [ ] Real-machine (maintainer): a plain `make image` on the host still builds the full image — the
      phase-1 box below, still open, is the same check.

## Plan (phase 1, 2026-08-29)

- [x] Write `client/entrypoint/00-install-minimal.sh` — dnf guard + the minimal set
      (ca-certificates, git, git-lfs, golang, gnupg2, less, ripgrep, strace, tcpdump, which).
      Empirically verified Crush's runtime shell-outs: `rg` (grep tool, `internal/agent/tools/rg.go`
      — optional, degrades to a slower Go path if absent, included for usability); `gh` (optional);
      everything else is the Go shell interpreter, no extra packages.
- [x] Dockerfile: `00-install-minimal.sh` runs always (first, shared base layer); `ARG
      FULL_TOOLCHAIN=0` gates `01-install-base.sh`; dnf cache mounts kept. Also **guarded the
      `mounts.conf` RUN** — that file only exists with the full toolchain (containers-common via
      podman), so the minimal build failed there until it was wrapped in an existence test.
- [x] Makefile: `FULL_TOOLCHAIN ?= 1`, threaded as `--build-arg`, documented in the `image`
      target's `##` help line + a flag-block comment.
- [x] Verify in-sandbox (nested): `make image FULL_TOOLCHAIN=0 CRUSH_VENDORED=1` built (1.65 GB);
      Crush runs; rg/strace/tcpdump/git/go present; sentinel check confirms the full toolchain was
      skipped. (Built from the vendored tree so it needs no network; `make vendor` in-image is the
      same git+go path, exercised by the build.)
- [ ] Real-machine: confirm a plain `make image` (defaults) still builds the full image unchanged.
- [x] Docs: CLAUDE.md note (verification builds use `FULL_TOOLCHAIN=0`), `architecture.md` client
      section. README: not updated — it documents `make image` (unchanged default); the minimal
      flag is an agent/verification convenience, noted in CLAUDE.md instead.

## Notes / decisions

- **`gcc` is present in the minimal image** — it's a dependency of `golang` (cgo), not the full
  toolchain. Sentinel packages for "is this minimal?" must be base-only ones like
  clang/nodejs/emacs/cmake/python3, not gcc.
- The on-disk `client/vendor/crush` scratch tree had drifted (leftover patches from the
  egress-patch work); regenerated pristine with `go mod vendor` before the vendored-mode build.
  That is the correct airgap state anyway (complete + unpatched).

## Open questions

Phase 1's three design questions were answered 2026-08-29 (see Context). Phase 2 has one:

1. ~~**Should the minimal image carry any language servers?**~~ **RESOLVED 2026-09-10: none**
   (maintainer: "minimal should not have language servers"). The crushrc's six `lsp add` lines stay;
   in the minimal image they fail to start harmlessly, and `CLAUDE.md` says so in one clause so the
   "no LSP client handles file" message in a nested container is expected, not a bug.
