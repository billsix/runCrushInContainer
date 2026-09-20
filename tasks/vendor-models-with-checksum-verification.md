# Vendor the models with pinned checksums; verify on pull, fail loudly on mismatch

**Status:** proposed — needs go-ahead. Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>).
**Depends on** the model set from
[country-gated-model-selection.md](country-gated-model-selection.md) (which models get vendored).
**Priority:** 5
**Difficulty:** 4

## BLUF

`make pull` downloads the model GGUFs from Hugging Face into `./models` with **no integrity check** — a
corrupted download, a truncated file, or a silently-changed upstream file would be served without notice.
Add **pinned per-file checksums** and verify them at **two points** — **`make pull`/vendor** (fail the
download on mismatch) **and `make serve`** (before launching llama-server, re-verify the selected model's
file(s) and **exit with an error, without serving,** if they don't match). Each failure prints a clear
error (which file, expected vs actual, and *why* — "corrupt or tampered; do not serve"). This is
supply-chain + corruption defense, locks the airgapped/vendored copy to exactly the bytes that were
reviewed, and guarantees a mismatched or bit-rotted file is **never served**. "Done" = a checksum manifest
covering every vendored file, both `pull` and `serve` verifying against it, and a proven **loud failure /
refusal to serve** when a file doesn't match.

## Context (cold-start)

- **The pull mechanism** (`server/Makefile`): `MODELS := glimmer gemma` (grows with the country task), each
  row = `MODEL_REPO_<m>` (HF repo), `MODEL_FILE_<m>` (exact GGUF filename), `MODEL_ALIAS_<m>`,
  `MODEL_PORT_<m>`. `make pull` walks all rows and `hf download --include`s the files into
  `MODEL_DIR ?= ./models`. Opt-in extras: `MODEL_FILES` (the quant ladder — `*.gguf`, mmproj), and
  `FULL_MODEL_FILES` (full-precision `*.safetensors`). `vendor.sh` wraps this (incl. a `FULL=1` preset).
- **"Multiple checksums of each model"** = a checksum **per file**: a model isn't one file — it's the
  default GGUF **plus** whatever quant-ladder / mmproj / full-weight files get vendored. Each pinned file
  gets its own checksum. (Optionally also a second hash algorithm per file for defense in depth — open
  question 2.)
- **No checksum today** — grep confirms `server/Makefile`/`vendor.sh` have no `sha256`/`checksum` step.

## Plan

1. **A pinned checksum manifest** — e.g. `server/models.sha256` (or per-model `<file>.sha256`), one line per
   vendored file: `<sha256>  <repo>/<filename>`. Covers each model's vendored GGUF(s) + any mmproj/full
   weights that are part of the vendored set.
2. **Populate authoritatively.** Hugging Face stores each LFS file's **SHA-256 in its pointer metadata**
   (the `git lfs`/`hf` API exposes `sha256:<hash>`) — pull *those* as the source of truth (no
   trust-on-first-use gap), rather than only computing from a local download. A `make checksums-refresh`
   target re-derives the manifest from HF so a pin/quant change is a **reviewable diff** (a silently-changed
   upstream file shows up as a checksum change to eyeball, not a silent swap).
3. **Verify on pull** — in `make pull`/`vendor.sh`, after each file downloads, verify it against the
   manifest (`sha256sum -c`, or compute + compare). On **match**, proceed. On **mismatch**, FAIL:
   - print a clear error: the **filename**, the **expected** vs **actual** SHA-256, and **why** ("refusing:
     this file does not match its pinned checksum — it may be corrupted in transit or tampered upstream; it
     will NOT be served"),
   - exit **nonzero**, and don't leave the bad file where `make serve` would load it (remove it or move it
     aside), so a failed vendor can't silently serve a wrong model.
4. **Unpinned files** (a pulled file not in the manifest — e.g. a new quant via `MODEL_FILES=*.gguf`):
   decide fail-vs-warn (open question 5) — recommend **warn + list** so ad-hoc quant exploration isn't
   blocked, while the *vendored set* stays fully pinned.
5. **Serve-time gate (`make serve`).** Before launching `llama-server`, verify the **selected** model's
   file(s) (`MODEL_FILE_<m>` + any it loads, e.g. an mmproj) against the manifest. On mismatch, print the
   same clear error and **exit nonzero WITHOUT starting llama-server** — so a file that was corrupted or
   swapped *after* vendoring (on-disk bit-rot, a bad copy, tampering) can never be served. On match, serve
   as normal. (Make this a prerequisite/guard of the `serve` and `serve-mlx` targets; keep it fast — hash
   only the file(s) about to be loaded, not the whole `./models` dir.)

## Verify (prove the failure path)
- Good pull of a pinned file → verify passes, `make serve` works.
- **Corrupt on purpose** (truncate or flip a byte of a vendored GGUF), then:
  - `make pull` (or re-verify) **fails loudly** — filename + expected/actual + reason, exits nonzero, bad
    file not left servable; AND
  - `make serve` **refuses to start** llama-server, prints the same error, exits nonzero.
- `make checksums-refresh` after a deliberate quant change produces a reviewable manifest diff.

## Open questions
1. **Checksum source** — HF LFS `sha256` pointer metadata (authoritative, recommended) vs compute-on-first-
   trusted-pull (has a TOFU gap). Recommend HF-provided where available, compute as fallback.
2. **One algorithm or multiple.** SHA-256 per file is standard; add a second (SHA-512/BLAKE2) per file for
   defense in depth? Recommend SHA-256 only to start; note the option.
3. **Manifest location/format** — one `server/models.sha256` (simple, `sha256sum -c`-compatible) vs
   per-model files. Recommend the single `sha256sum`-compatible file.
4. **Scope** — checksum only the *vendored* files (the default GGUF + explicitly-vendored extras), or the
   whole upstream repo? Recommend only what's vendored (what actually gets served).
5. **Unpinned pulled file** — hard-fail vs warn. Recommend warn (see plan step 4).

## Related
- Which models to vendor: [country-gated-model-selection.md](country-gated-model-selection.md).
- Mechanism: `server/Makefile` (`make pull`, `MODEL_REPO_<m>`/`MODEL_FILE_<m>`, `MODEL_FILES`,
  `FULL_MODEL_FILES`), `vendor.sh`, `tasks/reference/glimmer-models-and-airgap-quant-selection.md`, the
  archived `tasks/archive/2026/08/22/vendor-multiple-glimmer-quants.md`.
