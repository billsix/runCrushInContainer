# The model system: registry, country/OSI gate, checksums, and client autodiscovery

Durable reference for how runCrush chooses, gates, vendors, verifies, and offers its local models. States
what is TRUE now (not a work log). Read before touching `server/Makefile`'s model rows,
`server/tools/checksum.py`, `server/models.CHECKSUMS`, or `client/entrypoint/crushrc`. Landed 2026-09-20
(archived tasks `tasks/archive/2026/09/20/country-gated-model-selection.md` + `.../vendor-models-with-checksum-verification.md`).

## The registry (`server/Makefile`)

Models are a table keyed by `MODEL=`; each row has `MODEL_REPO_<m>` (HF repo), `MODEL_FILE_<m>` (exact GGUF
filename — an `hf download --include` pattern), `MODEL_ALIAS_<m>` (what llama-server reports at
`/v1/models`, and the crushrc provider id), `MODEL_PORT_<m>` (fixed), and **`MODEL_COUNTRY_<m>`** (ISO-3166
alpha-2). The set as of 2026-09-20 — **all Apache-2.0 weights** (see the OSI policy below):

| MODEL= | HF repo | country | port | weights license |
|---|---|---|---|---|
| glimmer (default) | meta-models/Muse-Glimmer-30B-GGUF | US | 8080 | Apache-2.0 (Meta) |
| gemma | google/gemma-4-26B-A4B-it-qat-q4_0-gguf | US | 8081 | Apache-2.0 (Gemma 4 only; 1–3 are NOT OSI) |
| granite | ibm-granite/granite-34b-code-instruct-8k-GGUF | US | 8082 | Apache-2.0 (IBM) |
| devstral | mistralai/Devstral-Small-2507_gguf | FR | 8083 | Apache-2.0 (Mistral) |
| qwen | unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF | CN | 8084 | Apache-2.0 (Qwen upstream + unsloth GGUF) |

Ports are sequential and **fixed** (US first, then FR, then CN); keep the port/alias tables in
`server/Makefile`, `client/entrypoint/crushrc`, and `client/entrypoint/shell.sh` in sync (their comments
say so). Each GGUF is ~Q4 and fits the 36 GB Mac **one at a time** (not concurrently). DeepSeek-Coder is
deliberately absent — see the OSI policy.

## The OSI-only policy (a hard selection rule)

Only **OSI-approved-licence weights** (Apache-2.0 / MIT) are ever added. This is enforced at *selection*
time, so the registry is OSI-by-construction — there is **no runtime license flag**; country is the only
runtime axis. **The lesson that makes this non-trivial: a repo's license ≠ its weights' license.** DeepSeek-
Coder's *repo* is MIT but its *weights* ship under a restrictive DeepSeek Model License (use restrictions),
so it fails the bar and is excluded; Meta's Llama-Community-License models are likewise out. When adding a
model, **verify the weights (model-card) license specifically**, not the repo or the org's flagship.

## The country gate — `MODEL_COUNTRIES`

`MODEL_COUNTRIES` is a comma-list country allowlist, **default `US`**. It normalizes friendly aliases
(`USA`→`US`, `France`→`FR`, `China`→`CN`) to ISO alpha-2, and `ALL` disables the filter. It derives
`ACTIVE_MODELS` = the models whose `MODEL_COUNTRY_<m>` is in the allowlist, and **gates pull, vendor, serve,
and offer together**: `pull`/`vendor`/`checksums` walk `ACTIVE_MODELS`; `serve`/`serve-mlx` refuse a `MODEL=`
outside it (exit nonzero with a clear message). Examples: unset/`US` → glimmer+gemma+granite; `US,FR` → +
devstral; `ALL` → all five; `China` → qwen only. The default `US` is the safe baseline; the strongest
*agentic* coders are non-US (Qwen/Devstral), so peak coding uses `US,FR` or `ALL`.

> **Known gap (see the follow-up task):** the opt-in `MODEL_FILES` extras-download loop uses the selected
> `MODEL=` (glimmer by default), **not** `ACTIVE_MODELS`, so it is NOT country-gated — a country filter can
> be bypassed for *extra* files. The default path (empty `MODEL_FILES`) is unaffected.

## Checksum integrity (`server/tools/checksum.py` + `server/models.CHECKSUMS`)

Every vendored GGUF is pinned with **three hashes — MD5 + SHA-256 + BLAKE2b** (Gentoo-Manifest style, in the
tracked `server/models.CHECKSUMS`; SHA-256/BLAKE2b are the strong pair, MD5 a legacy extra). `checksum.py` is
stdlib-only (so the serve gate needs no venv), computes all three (+ size) in one read pass, and a file
passes only if **all** match. Verification runs at **two gates**: `make pull` verifies after each download
(fail + quarantine to `<file>.corrupt` on mismatch), and `make serve` re-verifies the selected model's
file(s) **before launching llama-server** and refuses to start on mismatch — so a file corrupted/swapped
after vendoring is never served. `make checksums-refresh` regenerates the manifest for the active files as a
reviewable diff (a silently-changed upstream file shows up as a checksum change). Since the Mac fetches the
same HF bytes, a manifest generated anywhere is valid there.

## Client autodiscovery (`client/entrypoint/crushrc`)

The crushrc no longer hardcodes two providers: a `try_model port alias …` helper **probes each model port's
`/v1/models`** and registers a provider only for the ones answering, then preselects the first live one
(falling back to pinning glimmer if none answer, so Crush never hits onboarding). Country gating reaches the
client **by liveness** — the server only serves allowed models, so only their ports answer, so only they are
offered. (The vendored Go `internal/discover/llamacpp.go` enricher was left untouched; the crushrc probe is
the delivering mechanism. Touching the Go needs a full Crush rebuild.)

## Adding a model (checklist)
1. Confirm the **weights** license is OSI-approved (Apache-2.0/MIT) — check the model card, not just the repo.
2. Find the HF GGUF repo + exact filename (`make check-repo`); pick a ~Q4 quant that fits 36 GB.
3. Add the `MODEL_*_<m>` row incl. `MODEL_COUNTRY_<m>`; give it the next port; add to `MODELS`.
4. Sync `crushrc` (a `try_model` line) + `shell.sh` (the localhost-only socket bridge port list).
5. `make pull` (with a country filter that includes it) → `make checksums-refresh` → commit `models.CHECKSUMS`.
