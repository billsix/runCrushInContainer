# Vendor the models with pinned checksums; verify on pull, fail loudly on mismatch

**Status:** complete
**Completed:** 2026-09-20
Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>). Depended on the model set from
`tasks/archive/2026/09/20/country-gated-model-selection.md`.

`make pull` had downloaded the model GGUFs from Hugging Face with no integrity check, so a corrupt,
truncated or silently-changed file would have been served. Added pinned multi-hash checksums verified
at both `make pull` and `make serve`; a mismatch fails loudly and is never served. Implemented and
failure-path-proven in-sandbox; the real `make serve` runs on the Mac. Durable design:
**`tasks/reference/model-registry-country-gate-and-checksums.md`**.

## What was built

- **`server/tools/checksum.py`** (stdlib-only, fully type-annotated, ruff + ty clean) computes
  **MD5 + SHA-256 + BLAKE2b** in one pass; a file passes only if all three and the size match.
- **`server/models.CHECKSUMS`** (Gentoo-Manifest style, tracked) pins all five GGUFs.
- **`make pull`** runs `checksums-verify` after download: any mismatch exits nonzero and quarantines
  the file as `<file>.corrupt` so `make serve` cannot load it.
- **`make serve`** re-verifies only the selected model's file before launch and refuses to start
  llama-server on mismatch (or on a missing/empty manifest). `serve-mlx` has no gate, since it
  serves from `MLX_REPO`, not the vendored GGUF.
- **`make checksums-refresh`** regenerates the manifest for the active files as a reviewable diff.

## Decisions (2026-09-20)

1. **Multiple algorithms per file, Gentoo-style: SHA-256 + BLAKE2b + MD5**, all of which must match.
   SHA-256 + BLAKE2b carry the strength; MD5 is a legacy extra the maintainer asked for.
2. **Manifest:** one tracked `server/models.CHECKSUMS` holding all three hashes per file, not the
   `sha256sum`-compatible `server/models.sha256` first proposed (which was never created).
3. **Source:** the manifest is computed from the downloaded files by `checksums-refresh`; fetching
   HF's LFS `sha256` pointer as the source of truth was proposed but not built. Gemma's SHA-256 was
   cross-checked against its HF LFS pointer and matched.
4. **Scope:** only the vendored, active files (what actually gets served), not whole upstream repos.
5. **Unpinned files** (e.g. a new quant via `MODEL_FILES`) **warn, not fail** (`--warn-unpinned`),
   so ad-hoc quant exploration isn't blocked while the vendored set stays pinned.

## Verification

- All five real checksums generated and re-verified OK.
- Failure path proven end-to-end: a byte-flip made both the pull and serve gates fail loudly with
  nonzero exit, and llama-server was never reached.

## Related
- `server/Makefile` (`pull`, `checksums-verify`, `checksums-refresh`, `serve`), `vendor.sh`,
  `tasks/reference/glimmer-models-and-airgap-quant-selection.md`,
  `tasks/archive/2026/08/22/vendor-multiple-glimmer-quants.md`.
