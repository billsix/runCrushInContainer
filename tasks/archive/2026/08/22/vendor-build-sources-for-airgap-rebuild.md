# Vendor all build sources so client + server rebuild on an airgapped system

**Status:** complete (2026-08-22) — implemented + core mechanism verified. The remaining real-machine
airgap verification is split out to `tasks/verify-vendored-airgap-rebuild.md` (can't run the 22 GB image
build in the dev sandbox). Durable design captured in `tasks/reference/architecture.md` ("Offline / airgap
rebuild — vendoring"). See "Implementation (2026-08-22)".
**Completed:** 2026-08-22
**Priority:** 3
**Difficulty:** 4
**Started:** 2026-08-22

## Goal (maintainer's words, 2026-08-22)

As part of the build, make **all downloaded sources accessible outside the container** and **vendored**,
so everything can be **zipped up, moved to an airgapped system, and rebuilt with no network**. Store the
vendored inputs in an **externally-mounted folder**; the build process **extracts what it needs from
there** instead of fetching from the network.

Explicitly named to vendor:

- **Crush** — the **full git repo (with history)**, checked out to the version we use (`CRUSH_TAG`), **plus
  all of its dependencies** (the Go modules pulled during `go install`/build).
- **llama.cpp** — the **full git repo (with history)**, checked out to the version we use (`LLAMACPP_TAG`).
  (Server-side / Mac build.)
- **The meta model** — the Muse Glimmer GGUF (server-side).

## Why this is more than the existing offline conventions

Three different "offline" ideas, don't conflate them:

1. **Exported image runs offline** (personal-overlay convention) — `image-export` → `image-import` → runs
   with no network. Already true. About *running*, not *rebuilding*.
2. **Offline nested project builds** (`tasks/offline-nested-podman-base-images.md`) — seeding base images
   so a project's own container builds *inside* the client work offline.
3. **THIS task: rebuild client + server on an airgapped box, with no INTERNET** — the airgapped system
   supplies the base OS + toolchain (dnf/base image already available there); we supply only the three
   internet-sourced artifacts from a vendored folder. The build reaches no public network.

## Scope — EXACTLY the three internet-sourced artifacts (maintainer, 2026-08-22)

Vendor **only** what the airgapped system cannot fetch itself — the three items above, all pulled from the
public internet today:

- **Crush git repo + Go module deps** — today `git clone --branch $CRUSH_TAG …` (GitHub) then `go install`
  (Go module proxy). → vendor the full repo at `CRUSH_TAG` + a `go mod vendor` (or module cache).
- **llama.cpp git repo** — today `make llama` clones from GitHub. → vendor the full repo (with history) at
  `LLAMACPP_TAG`, plus any submodules it pulls.
- **The Muse Glimmer GGUF** — today `make pull` from Hugging Face. → vendor the file.

**Explicitly OUT of scope (do NOT vendor):** the Fedora base image (`FROM fedora:44`) and the ~430 dnf
packages from `01-install-base.sh`. The airgapped system **already has these** — it can build the
container there (that's why the current crush compiles on it; `golang` is one of those dnf packages). Our
job is only to supply the three things that come from the internet; the base OS + toolchain are the
airgapped system's own. (This is why this is a much smaller task than a full "offline the entire build"
effort — and why it does NOT overlap `offline-nested-podman-base-images.md`, which is about base images.)

## Mechanism to design

- **Externally-mounted vendor folder** (host `vendor/`, gitignored). Holds `vendor/crush/` (repo +
  `go mod vendor`), `vendor/llama.cpp/` (repo), `vendor/models/` (GGUF).
- **Populate online, consume offline.** An online step writes the three artifacts into `vendor/`; the
  build then reads from there instead of the network. The GGUF is **server-side only** (a plain file
  `make serve` reads — never baked into an image), so it just rides in the folder for transport.
- **How the client build consumes vendored Crush:** the Dockerfile switches its `git clone` + `go install`
  block to build from the vendored checkout with `go build -mod=vendor` (offline). Via `COPY` from the
  build context or `RUN --mount=type=bind,source=vendor` — Open question 2. `CRUSH_AT_IMPORT`'s `git apply`
  of our patch still happens (against the vendored repo).
- **The transport artifact** — one zip/tarball of `vendor/` that goes to the airgapped box.

## This task comes FIRST; the Crush version bump waits on it (maintainer, 2026-08-22)

`tasks/bump-crush-to-v0.90.0.md` is **blocked on this task** — offline rebuild must work before we consider
changing the pinned version. Concretely:

- **Vendor against the CURRENT known-good version, `CRUSH_TAG=v0.89.0`.** The maintainer confirms **the
  current crush (v0.89.0) compiles with the Go on the airgapped system**, so v0.89.0 is a proven airgap
  baseline. Build and prove the offline rebuild against it — do **not** target v0.90.0 here.
- **Why not just jump to v0.90.0:** v0.90.0's `go.mod` requires **Go ≥1.26.6** (v0.89.0 does not). Bumping
  could break the airgap build if that system's Go is older, and would drag in a Go-toolchain-vendoring
  question. Keep that out of this task; it belongs to the later bump.
- **`CRUSH_TAG`/`LLAMACPP_TAG` keep their meaning** — after this task they select "which vendored checkout"
  rather than "what to fetch." (Both are cross-referenced in the "Conventions for changing this repo" note
  in `CLAUDE.md`.)
- **When the bump eventually happens** (after this lands), it re-vendors Crush at v0.90.0 and separately
  confirms the airgapped Go can build it (possibly vendoring a newer Go toolchain too).

## Decisions (2026-08-22)

- **Scope resolved:** vendor **only** Crush repo + Go deps, llama.cpp repo, and the GGUF. Base image + dnf
  are the airgapped system's own (not vendored). This task covers both client (Crush) and server
  (llama.cpp + GGUF) *source* artifacts — no toolchain vendoring on either side.
- **Structure resolved (maintainer: "sure", 2026-08-22):** Makefile targets delegating to
  `entrypoint/vendor/*.sh` scripts, matching the repo's target-hands-off-a-script idiom — a `make
  vendor`-style target populates `vendor/` (online), and the build reads from `vendor/` (offline). Not a
  single top-level script.
- **Left to implementer's discretion** (no strong preference stated): `go mod vendor` vs a GOMODCACHE
  tarball (lean: `go mod vendor`); `COPY`-from-context vs `RUN --mount=type=bind` for the vendored Crush
  (lean: bind-mount, to keep the build context small).

## Open questions

None open — ready to implement on go-ahead (still gated: this lands before the v0.90.0 bump).

## Implementation (2026-08-22)

- [x] **Client vendoring script** — `client/entrypoint/vendor/vendor-crush.sh`: full clone of Crush @
      `CRUSH_TAG` → `git apply` the `@`-import patch (when `CRUSH_AT_IMPORT=1`) → `go mod vendor`. Writes a
      build-ready, patch-applied, module-vendored checkout. `set -eu` (linear pipeline, fail-fast is
      correct); idempotent (`rm -rf` dest first); shfmt-clean; baked into the image so `make vendor` runs
      it in-container.
- [x] **Client `make vendor`** (`client/Makefile`, depends on `image`): runs the script in the built
      image with `-v $(VENDOR_DIR):/vendor:Z`, so the vendored tree lands on the host at
      `client/vendor/crush`. `VENDOR_DIR ?= $(CURDIR)/vendor`.
- [x] **Client offline build path** — `CRUSH_VENDORED ?= 0`; `make image CRUSH_VENDORED=1` adds
      `--volume $(VENDOR_DIR)/crush:/vendor/crush:ro --build-arg CRUSH_VENDORED=1`. The Dockerfile's new
      `CRUSH_VENDORED=1` branch `cp`s the mount to `/tmp/crush` and builds `GOPROXY=off go build
      -mod=vendor` (no network), version-stamped as before. Online branches (patched `go install` from a
      clone, or stock `go install …@tag`) unchanged.
- [x] **Server** (`server/Makefile`): `make vendor` clones llama.cpp (**full history** @ `LLAMACPP_TAG`)
      + `make pull` for the GGUF, without building. `make llama` now does a **full clone** (dropped
      `--depth 1`) and reuses an existing checkout — so on the airgap Mac it builds the pre-vendored tree
      in place. llama.cpp + the GGUF already persist in `server/llama.cpp` + `server/models`.
- [x] **Ignore rules** — `client/.dockerignore` keeps `client/vendor/` out of the online build context
      (offline build mounts it via `--volume` instead); `.gitignore` adds `client/vendor/`.
- [x] **Core mechanism verified** — in a scratch Crush checkout: `go mod vendor` then `GOPROXY=off go
      build -mod=vendor` produced a working `crush --version` with no network. (Proven on the v0.90.0 tree;
      version-agnostic — the default vendors v0.89.0.)
- [→] **Full offline IMAGE rebuild verification — MOVED** to `tasks/verify-vendored-airgap-rebuild.md`
      (real-machine only; can't run the 22 GB image build in the dev sandbox).
- [x] Updated `tasks/reference/architecture.md` with the vendor/offline-rebuild workflow.
- [x] README documents how to vendor and how to build vendored (section "Airgapped rebuild — vendoring
      the sources").

**Transport:** no separate archive target — the transport unit is the **repo directory itself** (its
gitignored `client/vendor/`, `server/llama.cpp`, `server/models` carry the sources). Zip/tar the repo
after `make vendor` on both sides.

## Cross-links

- `tasks/bump-crush-to-v0.90.0.md` — **blocked on this task**; vendor against current v0.89.0 (known-good
  with the airgapped Go), the bump re-vendors at v0.90.0 later.
- `tasks/offline-nested-podman-base-images.md` — **separate concern** (base images for *nested* project
  builds); this task does not touch base images.
- Personal-overlay convention "Self-contained images + live source" — the *run-offline* / offline-export
  test; this task extends the requirement from *run* to *rebuild* (of the three internet-sourced parts).
- `client/Dockerfile`, `client/entrypoint/01-install-base.sh`, `server/Makefile` — the build steps that
  fetch from the network today.
