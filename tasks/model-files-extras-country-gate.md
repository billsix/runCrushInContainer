# Close the country-gate hole in the opt-in `MODEL_FILES` extras download

**Status:** proposed — needs go-ahead. Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>) — a
gap surfaced while verifying the `MODEL_COUNTRIES` country gate (implemented in the archived
`tasks/archive/2026/09/20/country-gated-model-selection.md`).
**Priority:** 6
**Difficulty:** 2 (a small `server/Makefile` change; the tricky part is deciding the desired behaviour)

## BLUF

`MODEL_COUNTRIES` (the country allowlist, default `US`) gates which models get pulled/served/offered — but
there is **one path it doesn't cover**: the opt-in **`MODEL_FILES`** extra-download loop. That loop pulls
*additional* files (extra quants, a vision `mmproj`, etc.) from the **selected `MODEL=`'s** repo, which
defaults to `glimmer` (a US model) — it does **not** consult the country allowlist. So a command like
`make pull MODEL_COUNTRIES=China MODEL_FILES="*.gguf"` would still fetch a **US** model's extra files
despite a China-only filter, quietly bypassing the gate. "Done" = the extras path respects
`MODEL_COUNTRIES` (or explicitly, loudly requires an override to bypass it).

## Background (so this is understandable cold)

The country gate works like this: `server/Makefile` tags each model with `MODEL_COUNTRY_<m>` (US/FR/CN);
`MODEL_COUNTRIES` (default `US`) is an allowlist; `ACTIVE_MODELS` is the models whose country is allowed;
`make pull` walks `ACTIVE_MODELS` and downloads each model's **main** GGUF. That part is correct — a China
filter pulls only the Chinese model.

Separately, `make pull` supports **`MODEL_FILES`** — an *opt-in* way to grab **extra** files from **one**
model's repo (empty by default). It exists so you can pull a whole quant ladder or a model's vision
projector, e.g. `make pull MODEL_FILES="*.gguf"` (every quant of the selected model) or
`make pull MODEL=gemma MODEL_FILES="*mmproj*"`. Crucially it downloads from `MODEL_REPO` =
`MODEL_REPO_$(MODEL)`, and **`MODEL` defaults to `glimmer`** — so `MODEL_FILES` is scoped to the single
selected model, **independent of `ACTIVE_MODELS`/`MODEL_COUNTRIES`**.

**The hole:** that extras loop never checks the country allowlist. If the selected `MODEL=` is a country the
filter *excludes*, its extra files are still fetched. It only bites when someone uses the opt-in
`MODEL_FILES` (or `FULL_MODEL_FILES`, below) together with a restrictive `MODEL_COUNTRIES` — the default
(empty `MODEL_FILES`) is unaffected — but for a **provenance/governance** feature, a silent bypass is worth
closing. (Also check **`FULL_MODEL_FILES`/`FULL_MODEL_REPO`**, the opt-in full-precision-weights download —
`FULL_MODEL_REPO` also defaults to glimmer's repo, so it has the same shape of gap.)

## Options (decide the desired behaviour)
- **(A) Refuse when the selected model isn't active.** If `MODEL_FILES`/`FULL_MODEL_FILES` is non-empty and
  the selected `MODEL=` is **not** in `ACTIVE_MODELS`, error out with a clear message
  ("MODEL=qwen is excluded by MODEL_COUNTRIES=US; refusing to pull its extras — widen MODEL_COUNTRIES or
  change MODEL"). Simplest; keeps the gate airtight. **Recommended.**
- **(B) Gate the extras by country too.** Only run the extras loop when the selected model is active
  (silently skip otherwise). Quieter but can surprise ("why didn't my extras download?").
- **(C) Explicit override to bypass.** Keep today's behaviour only when the user passes an explicit
  `ALLOW_COUNTRY_BYPASS=1` (or sets `MODEL_COUNTRIES=ALL`); otherwise refuse per (A). Most flexible.

**Recommendation: (A)** — a country gate for a governance feature should fail closed; the operator can widen
`MODEL_COUNTRIES` or pick an allowed `MODEL=` when they really want the extras.

## Plan (if A)
1. In `server/Makefile`, where `MODEL_FILES`/`FULL_MODEL_FILES` are consumed, add a guard: if either is
   non-empty AND `$(filter $(MODEL),$(ACTIVE_MODELS))` is empty, `$(error …)` with the message above.
2. Do the same for the `FULL_MODEL_*` path.
3. Verify with `make -n`: `make pull MODEL=qwen MODEL_FILES="*.gguf" MODEL_COUNTRIES=US` errors; the same
   with `MODEL_COUNTRIES=US,CN` (or `ALL`) succeeds; the default (empty `MODEL_FILES`) is unchanged.

## Related
- The gate it patches: `tasks/archive/2026/09/20/country-gated-model-selection.md`, and the durable design in
  `tasks/reference/model-registry-country-gate-and-checksums.md` ("Known gap").
- Mechanism: `server/Makefile` (`MODEL_FILES`, `FULL_MODEL_FILES`, `FULL_MODEL_REPO`, `ACTIVE_MODELS`).
