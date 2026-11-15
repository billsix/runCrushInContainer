# Vendor multiple Glimmer model quants (not just one)

**Status:** complete
**Started:** 2026-08-22 · **Implemented:** 2026-08-22 · **Completed:** 2026-08-22

Let the server's `pull`/`vendor` download several Muse Glimmer weights at different precisions, so an
airgap box can carry a quant ladder (Q4_K_M, Q5_K_M, Q6_K, Q4_K_XL, optionally Q8_0) and the operator
can trade quality against RAM later without network. Implemented in `server/Makefile` (validated with
`make -n`) and documented in `README.md` ("Download several quants (or the full weights)").

> **Superseded (2026-09-20):** with the five-model table, each row has its own `MODEL_FILE_<m>`, and
> `MODEL_FILES` became an empty-by-default list of extra files pulled *in addition to* the active row's
> GGUF. See `tasks/reference/model-registry-country-gate-and-checksums.md`.

## What was done (2026-08-22)

- **`MODEL_FILES`**: a space-separated download set (exact names or `hf --include` globs such as
  `*Q5_K_M*.gguf`), replacing the single `MODEL_FILE` for downloading. It defaulted to the one Q4_K_M
  GGUF, so behavior was unchanged unless quants were added. `pull`/`vendor` loop `hf download --include`
  over each entry.
- **`MODEL_FILE`** defaulted to `$(firstword $(MODEL_FILES))` and stayed the single file `serve` uses
  (`make serve MODEL_FILE=…` serves another vendored quant). The `--alias` is constant, so the client
  crushrc matches whichever quant is served.
- **Full precision is opt-in, off by default**: `FULL_MODEL_FILES` (empty) plus `FULL_MODEL_REPO`
  (defaulting to `MODEL_REPO`; set it when the full weights live in the base `…-30B` repo rather than
  `…-GGUF`). When set, `pull` also fetches them.
- **`check-repo`** lists the repo's real GGUF filenames (discovery for populating `MODEL_FILES`) instead
  of a single-file presence check, so the set is built from real files rather than guessed names.
- `HF_BIN`/`PYBIN` prefer the system `hf`/`python3` (the client image's dnf `python3-huggingface-hub`),
  else the venv, so this works on the dev Mac and inside the client image.

## Decisions

- **Full-precision weights (F16/BF16 GGUF, or the base repo's BF16 safetensors) are opt-in** (maintainer,
  2026-08-22). Not for size (airgap transfer size is a non-issue to the maintainer) but because most runs
  won't want that artifact.
- **Default download set: the single Q4_K_M GGUF.** Which ladder quants to fetch is chosen per run via
  `MODEL_FILES` after `make check-repo`, rather than fixing a multi-quant default.
- **No precision-to-`make serve` logic.** What each quant can serve is the operator's concern on their
  airgap hardware (NVIDIA/Linux, not the dev Mac); this task only makes the weights available.

## Verification

`make -n` validated the targets in-sandbox. The runtime step (`make check-repo`, choose filenames,
`make pull MODEL_FILES="…"` plus optional `FULL_MODEL_FILES=…`, confirm files land in `server/models/`)
needs the live Hugging Face repo and was left to the operator; its result was not recorded here.

## Related

- `server/Makefile` (`pull`, `vendor`, `serve`, `check-repo`).
- `tasks/reference/architecture.md`: the quant ladder (Q4_K_M ~16.8 GB, Q5_K_M ~20-21 GB, Q6_K
  ~24-25 GB, Q4_K_XL ~19.65 GB) and serve tuning.
- `vendor.sh`: the top-level one-command vendor, which picks up multi-quant via the server `vendor`.
