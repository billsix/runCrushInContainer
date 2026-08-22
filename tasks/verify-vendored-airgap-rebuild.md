# Verify the vendored offline rebuild on a real airgapped system

**Status:** proposed — real-machine verification, cannot be done in the dev sandbox (22 GB image; no
airgapped box here). Split out 2026-08-22 from the now-implemented vendoring work
(`tasks/archive/2026/08/22/vendor-build-sources-for-airgap-rebuild.md`).
**Priority:** 3
**Difficulty:** 3
**Started:** 2026-08-22

## Goal

Confirm end-to-end that the vendoring machinery actually yields a **network-free rebuild** of both the
client image and the server, on a genuinely airgapped machine. The implementation is done and the core
mechanism (`go mod vendor` + `GOPROXY=off go build -mod=vendor`) is proven in isolation; this task is the
full-system, real-hardware proof.

## Steps

1. **[ONLINE] Vendor both sides.** From the repo root: `./vendor.sh` — runs the vendoring **inside the
   client image**, so the host needs only **podman + make**. Builds the image if needed, then populates
   `client/vendor/crush`, `server/llama.cpp` (full history), `server/models/` GGUF. (Per-side equivalents:
   `make -C client vendor` and `make -C server vendor`.)
2. **Transport.** Zip/tar the whole repo (its gitignored `client/vendor/`, `server/llama.cpp`,
   `server/models` ride along); move it to the airgapped box.
3. **[AIRGAP / LINUX] Client rebuild, no network.** `cd client && make image CRUSH_VENDORED=1`. To prove
   no network is touched during the Crush build, ideally cut networking for the build (e.g. verify with
   the network physically down, or watch that no `git`/`go` proxy fetch happens). Confirm the build
   succeeds and `crush --version` reports the pinned tag.
   - **SELinux gotcha:** if the `--volume …:/vendor/crush:ro` build mount is denied on an enforcing host,
     switch `CRUSH_VENDOR_FLAGS` in `client/Makefile` to `:ro,z`.
4. **[AIRGAP / MAC] Server rebuild, no network.** `cd server && make llama` (reuses the pre-vendored
   `server/llama.cpp`, builds in place — confirm it does NOT try to clone) → `make serve` serves the
   vendored GGUF. Confirm `make probe` / `make smoke` answer.
5. **[AIRGAP] End-to-end.** Bring up the tunnel + `make shell` and confirm Crush drives the local model.

## Done when

- The client image builds on the airgapped box from `client/vendor/` with no network, `crush` runs.
- The server builds llama.cpp from the vendored checkout + serves the vendored GGUF, no network.
- If any step reaches for the network, capture what and where — that's a vendoring gap to fix (feed it
  back into the archived vendoring task's approach).

## Cross-links

- `tasks/archive/2026/08/22/vendor-build-sources-for-airgap-rebuild.md` — the implementation this verifies.
- `tasks/reference/architecture.md` — "Offline / airgap rebuild — vendoring".
- `tasks/bump-crush-to-v0.90.0.md` — blocked until this verification confirms offline rebuild works
  (then the bump re-vendors at v0.90.0 and re-checks the airgapped Go can build it).
