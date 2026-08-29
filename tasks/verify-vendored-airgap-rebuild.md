# Verify the vendored offline rebuild on a real airgapped system

**Status:** proposed — real-machine verification, cannot be done in the dev sandbox (22 GB image; no
airgapped box here). Split out 2026-08-22 from the now-implemented vendoring work
(`tasks/archive/2026/08/22/vendor-build-sources-for-airgap-rebuild.md`).
**Priority:** 3
**Difficulty:** 3
**Started:** 2026-08-22

## Goal

Confirm the **vendoring is complete and offline-buildable** on a real airgapped box: the client image
rebuilds with no network, and the vendored server sources (llama.cpp + GGUF) are present and buildable
for the box's own hardware. Scope note: **the airgap box needn't be a Mac** (may be NVIDIA/Linux), and
building/running the *server* there is the operator's own concern — this task verifies what the vendoring
*provides*, not a specific serve setup. The core mechanism (`go mod vendor` + `GOPROXY=off go build
-mod=vendor`) is already proven in isolation; this is the full-system, real-hardware proof.

**Finding (2026-08-29, from the dependency-audit work): the on-disk `client/vendor/crush` tree
predates `crush-no-update-check.patch` (added 2026-08-27) — only the `@`-import patch is applied
(`git status` in the tree shows just `internal/agent/prompt/prompt.go` modified).** Under the
current build model (vendored path applies no patches), a `make image CRUSH_VENDORED=1` from this
tree builds a Crush **with** the startup update check. Resolution: the patch-model revision decided
in `tasks/archive/2026/08/29/audit-dependency-network-egress.md` (vendor unpatched, apply ALL patches flag-guarded at
build time) fixes this class of drift; until that lands, re-run `make vendor` before an airgap
rebuild, or accept the update-check call (it fails harmlessly offline).

## Steps

1. **[ONLINE] Vendor.** From the repo root: `./vendor.sh` — runs the vendoring **inside the client
   image**, so the host needs only **podman + make**. Populates `client/vendor/crush`, `server/llama.cpp`
   (full history), `server/models/` GGUF. (Per-side equivalents: `make -C client vendor`, `make -C server
   vendor`.)
2. **Transport.** Plain `tar`/`zip` the whole repo (its gitignored `client/vendor/`, `server/llama.cpp`,
   `server/models` ride along — NOT `git archive`); move it to the airgapped box.
3. **[AIRGAP] Client rebuild, no network.** `cd client && make image CRUSH_VENDORED=1`. Ideally with the
   network physically cut, to prove no `git`/`go` fetch happens. Confirm the build succeeds and
   `crush --version` reports the pinned tag.
   - **SELinux gotcha:** if the `--volume …:/vendor/crush:ro` build mount is denied on an enforcing host,
     switch `CRUSH_VENDOR_FLAGS` in `client/Makefile` to `:ro,z`.
4. **[AIRGAP] Server sources present + buildable (operator's own build).** Confirm `server/llama.cpp` is a
   full checkout and `server/models/<gguf>` is present, and that llama.cpp builds offline for the local
   backend (e.g. `cmake -S server/llama.cpp -B build -DGGML_CUDA=ON && cmake --build build`). The exact
   backend/build/run is yours — this step only checks the vendored sources suffice with no network.

## Done when

- The client image builds on the airgapped box from `client/vendor/` with no network, `crush` runs.
- The vendored `server/llama.cpp` builds offline for the box's backend and the vendored GGUF is present.
- If any step reaches for the network, capture what and where — that's a vendoring gap to fix (feed it
  back into the archived vendoring task's approach).

## Cross-links

- `tasks/archive/2026/08/22/vendor-build-sources-for-airgap-rebuild.md` — the implementation this verifies.
- `tasks/reference/architecture.md` — "Offline / airgap rebuild — vendoring".
- `tasks/bump-crush-to-v0.90.0.md` — blocked until this verification confirms offline rebuild works
  (then the bump re-vendors at v0.90.0 and re-checks the airgapped Go can build it).
