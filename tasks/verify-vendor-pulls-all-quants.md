# Verify vendor's quant coverage — and that "pull all" really pulls every Glimmer model at every quant

**Status:** proposed — **deferred** until the airgap target hardware (and thus the quant) is chosen.
Real-machine/network check (talks to Hugging Face). The model-universe research (open question 1) is
**done** and lives in `tasks/reference/glimmer-models-and-airgap-quant-selection.md` — which also
reframes this task toward *airgap-optimal single-quant selection* rather than "pull everything."
**Priority:** 4
**Difficulty:** 3
**Created:** 2026-08-25 (William Emerison Six <billsix@gmail.com>)

## Goal

Three things, in order:

1. **Confirm what the vendor path pulls by default** (which quant level(s)).
2. **Enumerate what is actually available** on Hugging Face (every quant, and whether there is more than
   one Glimmer model repo).
3. **Make the "pull all" switch genuinely pull all** — verify that `FULL=1 ./vendor.sh` (which presets
   `MODEL_FILES=*.gguf` + `FULL_MODEL_FILES=*.safetensors`) fetches **every Glimmer model at every quant
   level**, and fix it if it doesn't.

## Current state (measured 2026-08-25, from the source)

- **Default = a single Q4_K_M file.** `server/Makefile`: `MODEL_REPO ?= meta-models/Muse-Glimmer-30B-GGUF`,
  `MODEL_FILES ?= Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` (an exact filename, not a glob). `MODEL_FILE`
  (what to *serve*) is `$(firstword $(MODEL_FILES))`.
- **`pull`** loops `MODEL_FILES`, running `hf download $(MODEL_REPO) --include "$$f" --local-dir …` per
  entry, then the same for `FULL_MODEL_FILES` from `FULL_MODEL_REPO` (default `= MODEL_REPO`; empty
  `FULL_MODEL_FILES` by default).
- **"Pull all" is `FULL=1`** in `vendor.sh:38-42`: it sets `MODEL_FILES=*.gguf`,
  `FULL_MODEL_FILES=*.safetensors`, `FULL_MODEL_REPO=meta-models/Muse-Glimmer-30B` (the base, non-GGUF
  repo). Each entry is passed to `hf download --include`, so these are globs.
- **`make -C server check-repo`** lists MODEL_REPO's GGUF filenames (via `HfApi().model_info`) — the
  discovery tool for what quants exist.

## Plan / verification steps

1. **Baseline the default.** From a clean `server/models/`, note that a plain `make pull` / `./vendor.sh`
   fetches exactly the one Q4_K_M file above — nothing else.
2. **Enumerate availability.** Run `make -C server check-repo` and record **every** GGUF the repo holds
   and their quant levels (Q4_K_M, Q5_K_M, Q6_K, Q8_0, F16, …). This is the ground-truth "all quants" set.
3. **Resolve "all Glimmer models" (the plural).** Determine whether there is **one** GGUF repo or
   **several** — e.g. other sizes, a base vs instruct variant, or a separate mmproj repo — under the
   `meta-models/…Glimmer…` namespace on HF. `MODEL_REPO`/`FULL_MODEL_REPO` today name exactly **two**
   repos (`…-30B-GGUF` for quants, `…-30B` for full weights); if the family is larger, `FULL=1` cannot
   reach the others (it only globs those two). **This is the crux of the request** — see open question 1.
4. **Prove the glob covers every quant.** With `FULL=1`, `--include "*.gguf"` should match **every** file
   `check-repo` listed. Diff the glob's actual matches against the step-2 list. **Caveat, check here:**
   a large quant may be a **sharded GGUF** (`…-00001-of-0000N.gguf`) — `*.gguf` matches all parts, but
   confirm none are missed and that all shards of a set land together (a partial set is unusable). Also
   confirm the harmless mmproj/dflash `*.gguf` extras (noted in README) don't crowd out or shadow a real
   quant.
5. **Check the full-precision path.** `FULL_MODEL_FILES=*.safetensors` from `FULL_MODEL_REPO` grabs the
   weight shards. **Caveat:** `*.safetensors` alone omits `config.json` / tokenizer / `*.json` index —
   so the vendored full weights are **not runnable as-is**. Decide whether that's intended (weights only,
   for re-quantizing) or whether "pull all" should include the config/tokenizer too (open question 2).
6. **Fix any gap** surfaced by 3–5: e.g. broaden the repo set, widen/repair the include globs, or add a
   post-pull assertion that the number of GGUFs fetched equals `check-repo`'s count (so a silently-missed
   quant fails loudly instead of passing).

## Where this runs

Needs **network to Hugging Face** (`check-repo` and the actual pulls) and is size-heavy (a full pull is
tens of GB), so it's a real-machine check, not a sandbox one. `check-repo` and the *dry* glob-vs-list
diff (steps 2–4) are cheap and network-only; steps 1/5's full download is the expensive part — a `--dry`
listing or fetching one representative file per quant may suffice to prove coverage without pulling
everything.

## Open questions

1. **Is "all of the Glimmer models" one repo's quant ladder, or multiple repos?** If several (other
   sizes / a base+instruct split / a distinct mmproj repo), `FULL=1` as written misses them — it only
   globs `MODEL_REPO` (GGUF) + `FULL_MODEL_REPO` (safetensors). **Recommend** first running `check-repo`
   and browsing the `meta-models` HF namespace to settle the model universe, *then* deciding whether
   `FULL=1` needs to iterate a **list** of repos rather than two fixed ones.
2. **Should `FULL=1`'s full-precision pull be *runnable* (add `config.json` + tokenizer + index), or
   weights-only?** `*.safetensors` alone isn't loadable. **Recommend** weights-plus-metadata (include the
   repo's `*.json` / tokenizer files) so a vendored full model is actually usable offline — unless the
   intent is strictly re-quantization inputs.

## Cross-links

- `server/Makefile` — `MODEL_REPO` / `MODEL_FILES` / `FULL_MODEL_FILES` / `FULL_MODEL_REPO`, the `pull`
  loop, and `check-repo`.
- `vendor.sh:38-42` — the `FULL=1` preset block (the "pull all" switch).
- `tasks/archive/2026/08/22/vendor-multiple-glimmer-quants.md` — the multi-quant vendoring this verifies.
- `tasks/reference/architecture.md` — the quant ladder + offline source-vendoring workflow.
