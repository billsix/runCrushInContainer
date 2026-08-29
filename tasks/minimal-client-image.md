# Minimal client image via FULL_TOOLCHAIN flag (full by default, lean for in-sandbox verification)

**Status:** proposed — needs go-ahead.
**Priority:** 4
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

## Plan

- [ ] Write `client/entrypoint/00-install-minimal.sh` (dnf guard + the minimal set; verify Crush's
      runtime shell-out needs empirically in the minimal container).
- [ ] Dockerfile: install minimal always; gate `01-install-base.sh` on `ARG FULL_TOOLCHAIN=0`;
      keep the dnf cache mounts.
- [ ] Makefile: `FULL_TOOLCHAIN ?= 1`, thread as `--build-arg`, document in the `image` target's
      `##` help line.
- [ ] Verify in-sandbox (nested): `make image FULL_TOOLCHAIN=0` builds; run Crush in it against a
      stub OpenAI endpoint on loopback; confirm `make vendor` works in-image; sentinel-package
      check both ways (full image has a toolchain package the minimal lacks — proves the gating).
- [ ] Real-machine: one plain `make image` (defaults) still builds the full image unchanged.
- [ ] Docs: CLAUDE.md note ("verification builds: FULL_TOOLCHAIN=0"), `architecture.md` client
      section, README if it names the image build.

## Notes / decisions

## Open questions

None — the three design questions were answered 2026-08-29 (see Context).
