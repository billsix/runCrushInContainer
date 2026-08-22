# Vendor multiple Glimmer model quants (not just one)

**Status:** complete — implemented in `server/Makefile` (validated with `make -n`) and documented in
`README.md` ("Download several quants (or the full weights)"). The runtime step (`make check-repo` →
set `MODEL_FILES` → `make pull`) needs the live HF repo, which is the operator's to run.
**Completed:** 2026-08-22
**Priority:** 5
**Difficulty:** 4
**Started:** 2026-08-22 · **Implemented:** 2026-08-22

## Implementation (2026-08-22)

- **`MODEL_FILES`** (space-separated download set; entries are exact names or `hf --include` globs like
  `*Q5_K_M*.gguf`) replaces the single `MODEL_FILE` for downloading. Defaults to the one Q4_K_M GGUF →
  **no behavior change** unless you add quants. `pull`/`vendor` loop `hf download --include` over each.
- **`MODEL_FILE`** now defaults to `$(firstword $(MODEL_FILES))` and is the single file `serve` uses —
  override to serve a different vendored quant (`make serve MODEL_FILE=…`). The `--alias` is constant, so
  the client crushrc still matches whichever quant is served.
- **Full-precision → opt-in, OFF by default:** `FULL_MODEL_FILES` (empty by default) + `FULL_MODEL_REPO`
  (defaults to `MODEL_REPO`, set it when the full weights live in the base `…-30B` repo, not `…-GGUF`).
  When set, `pull` also fetches those. Archival/conversion artifacts — serving them is the operator's call.
- **`check-repo`** now **lists the repo's real GGUF filenames** (discovery for populating `MODEL_FILES`)
  instead of a single-file presence check — honoring "enumerate real files, don't guess."
- `HF_BIN`/`PYBIN` prefer the system `hf`/`python3` (client image / dnf `python3-huggingface-hub`), else
  the venv — so this works both on the dev Mac (venv) and inside the client image.

Runtime verification (operator, needs network + the real repo): `make check-repo` → pick filenames →
`make pull MODEL_FILES="…"` (+ optional `FULL_MODEL_FILES=…`) → confirm the files land in `server/models/`.

## Goal

Let vendoring download **several Muse Glimmer weights at different precisions**, not just the single
`MODEL_FILE`, so an airgap box can carry a ladder and the operator can pick per hardware / quality
trade-off without re-downloading online:

- **Quant ladder:** Q4_K_M, Q5_K_M, Q6_K, Q4_K_XL (and Q8_0 if wanted).
- **Full / unquantized (maintainer, 2026-08-22) — OPT-IN:** optionally the full-precision model too — an
  **F16/BF16 GGUF** if the GGUF repo publishes one, and/or the **original BF16 safetensors** from the base
  model repo (what the GGUFs are quantized from). Kept behind an opt-in flag/target (off by default), not
  because of size (the airgap transfer size is a non-issue per the maintainer) but because it's a distinct
  artifact most runs won't want. What each quant/precision can actually *serve* is the operator's concern
  on their airgap hardware (NVIDIA/Linux, not the dev Mac) — this task just makes the weights available;
  don't wire precision-to-`make serve` logic here.
- **Verify what actually exists on HF first** — the repo path/filenames are already marked "verify before
  relying" (`server/Makefile`), and the full weights may live in a *separate* repo from the GGUFs
  (`…-GGUF` vs the base `…` repo). Enumerate real files (e.g. `hf`/HF API) before hardcoding a set.

## Why

The quant ladder is already documented (`tasks/reference/architecture.md` — Q4_K_M default ~16.8 GB,
Q5_K_M ~20–21 GB, Q6_K ~24–25 GB, Q4_K_XL ~19.65 GB). Today `server/Makefile` pulls exactly one
(`MODEL_FILE`) into `server/models`, and `make serve` serves that one. For airgap especially, fetching a
range once (online) means you can trade quality vs RAM later with no network.

## Sketch (to design on go-ahead)

- `server/Makefile`: turn `MODEL_FILE` into a **list** (e.g. `MODEL_FILES ?= <q4> <q5> …`), and have
  `pull` (and `vendor`) loop `hf download --include` over each into `server/models/`. Keep a default
  single-quant for the simple case.
- `make serve` (dev Mac only): selecting which quant to serve is a maintainer-dev-box concern; the
  airgap serve is the operator's own (their NVIDIA/Linux hardware). Don't over-engineer serve here.
- Consider `check-repo` verifying each requested quant resolves on HF before a multi-download.

## Open questions

1. Which quants make the default vendor set (all of the ladder, or a chosen subset)? — decide at design
   time. (Transfer size is not a constraint — the maintainer doesn't care about airgap archive size.)
2. Full-precision model → **decided: opt-in, off by default** (a separate flag/target), not because of
   size but because most runs won't want it. Still: verify the actual HF artifact/repo before wiring it.

## Cross-links

- `server/Makefile` (`MODEL_REPO`/`MODEL_FILE`/`pull`/`vendor`/`serve`).
- `tasks/reference/architecture.md` — the quant ladder + serve tuning.
- `vendor.sh` — the top-level one-command vendor (would pick up multi-quant via the server `vendor`).
