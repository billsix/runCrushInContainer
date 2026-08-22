# Vendor all build sources so client + server rebuild on an airgapped system

**Status:** proposed — needs go-ahead. Captured from maintainer 2026-08-22; not started.
**Priority:** 3
**Difficulty:** 7
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
3. **THIS task: offline REBUILD of client + server from source** — reconstruct the images/binaries from
   vendored sources on an airgapped box. The strongest requirement: the *build* itself must need no
   network.

## What actually needs network at build today (the real vendoring scope)

The named items are necessary but **not sufficient** for a truly offline *client image* build — the
Dockerfile has more build-time network dependencies. Enumerate and decide (Open question 1):

- **Crush git repo + Go module deps** — `git clone --branch $CRUSH_TAG …` then `go install` (module
  proxy). → vendor the repo + a Go module cache / `go mod vendor`.
- **llama.cpp git repo** (+ its own submodules/deps) — server-side `make llama`. → vendor the repo with
  history at `LLAMACPP_TAG` (and any submodules).
- **The Muse Glimmer GGUF** — server-side `make pull` from Hugging Face. → vendor the file.
- **The Fedora base image** — `FROM registry.fedoraproject.org/fedora:44` needs a registry. → vendor it
  (skopeo copy to a dir / `podman save`). *(Overlaps `offline-nested-podman-base-images.md`.)*
- **~430 dnf packages** — `01-install-base.sh` does `dnf install` from Fedora mirrors. → vendor a local
  dnf repo (downloaded RPMs + repodata) and point dnf at it offline. This is the largest and fiddliest
  piece; a rebuild that stops at `dnf install` isn't airgap-capable.

## Mechanism to design

- **Externally-mounted vendor folder.** `podman build` can't bind-mount arbitrary host dirs by default —
  options: (a) put the vendor tree in the **build context** and `COPY` from it; (b) `RUN
  --mount=type=bind,source=…` (BuildKit/buildah); (c) a two-step "hydrate a local cache, then build
  offline." Decide per input (a giant GGUF and a dnf repo probably shouldn't live in the build context).
- **Extract-what-it-needs at build.** The Dockerfile/Makefile switch from fetch-from-network to
  read-from-vendor, gated so an online box can still refresh the vendor set.
- **The transport artifact** — one zip/tarball of the vendor folder that goes to the airgapped box.

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

## Open questions

1. **Scope — vendor ONLY the three named items (Crush+deps, llama.cpp, GGUF), or the FULL offline-build
   set** (also the `fedora:44` base image and the ~430 dnf packages)? Recommend **the full set** — a
   rebuild that still needs a registry for `FROM` or Fedora mirrors for `dnf install` is not actually
   airgap-capable, which defeats the goal. The dnf-repo mirroring is the bulk of the work; flagging it now
   so it's a decision, not a surprise.
2. **Coordinate with / absorb `tasks/offline-nested-podman-base-images.md`?** Both need the `fedora:44`
   base vendored. Recommend keep them separate but share the base-image-vendoring mechanism (that task is
   about *nested* project builds; this is about *rebuilding the client/server themselves*).
3. **Build-context vs bind-mount for the big artifacts** (GGUF ~16.8 GB, dnf repo, module cache)? Needs a
   quick spike; recommend `RUN --mount=type=bind` from an external vendor dir over stuffing multi-GB into
   the build context.

## Cross-links

- `tasks/bump-crush-to-v0.90.0.md` — **blocked on this task**; vendor against current v0.89.0 (known-good
  with the airgapped Go), the bump re-vendors at v0.90.0 later.
- `tasks/offline-nested-podman-base-images.md` — shares the base-image-vendoring need (nested layer).
- Personal-overlay convention "Self-contained images + live source" — the *run-offline* / offline-export
  test; this task extends the requirement from *run* to *rebuild*.
- `client/Dockerfile`, `client/entrypoint/01-install-base.sh`, `server/Makefile` — the build steps that
  fetch from the network today.
