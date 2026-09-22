# Add coding-agent models with a country-of-origin allowlist (default USA)

**Status:** DONE — implemented + sandbox-verified 2026-09-20 (the real `make serve` runs on the Mac —
Metal — as the operator's normal path). Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>). Archived.

## Implemented (2026-09-20)

5-model registry in `server/Makefile` (glimmer/gemma/granite = US, devstral = FR, qwen = CN; ports
8080–8084; **all Apache-2.0 weights**), the `MODEL_COUNTRIES` allowlist (default `US`, aliases, `ALL`;
gates pull/serve/offer together — verified via `make -n`: US→3, US,FR→4, ALL→5, China→qwen), client
autodiscovery in `crushrc` (probes each port, offers the live ones), and the 5-port localhost-only bridge in
`shell.sh`. All 5 HF repos resolved + downloaded (~80 GB) + multi-hash checksums generated. Durable design
is now in **`tasks/reference/model-registry-country-gate-and-checksums.md`** (read that, not this).
- **Client autodiscovery note (logged before archival, per the maintainer):** the vendored Go
  `client/vendor/crush/internal/discover/llamacpp.go` enricher was **left untouched** — the crushrc
  liveness probe is the delivering mechanism; touching the Go needs a full Crush rebuild that can't be
  verified in-sandbox. Revisit only if the Go enricher is wanted too.
- **Known gap → follow-up:** the opt-in `MODEL_FILES` extras path isn't country-gated —
  `tasks/model-files-extras-country-gate.md`.
Research-heavy first half — a good **Fable** candidate for the research/decide phases.
**Priority:** 5
**Difficulty:** 6 (Phase 3 touches the server model registry, `vendor.sh`, and the client crushrc)

## BLUF

Three phases. **(1) Research + decide** which additional open-weight **coding-agent** models to add that
run well on the maintainer's **Mac Studio, 36 GB unified memory** (the user has heard good things about
Qwen — likely Qwen3-Coder / Qwen3.x ~30B — and asks whether Mistral has one; it does: Devstral / Codestral).
**(2) Record each model's country of origin.** **(3) Implement a country allowlist flag** —
`MODEL_COUNTRIES` — that gates which models are **served, vendored, and offered**: a list of allowed
countries, **default `USA`** if unset, overridable with a country list (e.g. `USA,France`) or `ALL` (every
country). "Done" = a decided model set, a model→country registry, and a working `MODEL_COUNTRIES` filter
whose default (USA) serves/vendors only US-origin models.

## Context (cold-start)

- **Current models:** two, both US-origin — **Muse Glimmer** (Meta) on `127.0.0.1:8080` and **Gemma 4**
  (Google) on `:8081`, served by llama.cpp on the Mac (`server/Makefile`, `make serve MODEL=glimmer|gemma`),
  reached from the client container over the SSH tunnel. **Ports are currently fixed** (8080/8081) and the
  client crushrc pins exactly those two providers.
- **Vendoring:** model weights (GGUF quants) are vendored/pinned (see the archived
  `tasks/archive/2026/08/22/vendor-multiple-glimmer-quants.md` and `vendor.sh`) so a build/run is offline
  and reproducible. Adding a model means adding its vendored quant + a server port/provider + a client
  provider — the country allowlist must gate all three.
- **The 36 GB budget:** leave headroom for macOS + the KV cache, so realistically a **Q4_K_M / Q5_K_M**
  quant of a **~24–32B** model (a Q4 27–30B is ~18–20 GB; 32B is tight at long context; a 30B **MoE** like
  Qwen3-Coder-30B-A3B is fast and fits well). Long coding-agent contexts eat KV cache — size for that.

## Phase 1 — research + decide the models

**Criteria:** (a) fits 36 GB at Q4/Q5 with KV headroom; (b) strong at **agentic** coding (tool-calling,
SWE-bench Verified — not just autocomplete); (c) open weights with a usable license; (d) GGUF /
llama.cpp-servable. **Seed candidates to verify + choose from** (versions move fast — reconfirm current
releases at execution):

| Model (candidate) | Org | Country | Fit @36 GB | Notes |
|---|---|---|---|---|
| **Devstral Small 2** (~24B) | Mistral AI | **France** | Q4/Q5 ✓ | Purpose-built **agentic** coder (OpenHands/SWE-bench), Apache-2.0 — a top pick |
| **Codestral** (~22B) | Mistral AI | **France** | ✓ | Code-specialized; check license (Mistral non-production vs Apache) |
| **Qwen3-Coder** (~30B-A3B MoE) / **Qwen3.x ~27–32B** | Alibaba | **China** | ✓ (MoE fast) | Strong agentic coder; the 480B flagship does NOT fit — use the ~30B variant |
| **DeepSeek-Coder(-V2/V3) Lite** (~16B MoE) | DeepSeek | **China** | ✓ | Strong coder; use a Lite/small variant (flagship too big) |
| **GLM (code)** / **Kimi (code)** | Zhipu / Moonshot | **China** | verify | Newer 2026 open coders; check a sub-32B variant exists |
| **IBM Granite Code** (~20–34B) | IBM | **USA** | ✓ | US-origin coder (relevant to the default allowlist) |
| **CodeGemma** / **Gemma** (code) | Google | **USA** | ✓ | US; Gemma already present |
| **Code Llama / Llama 3.x** | Meta | **USA** | ✓ | US; Muse Glimmer (Meta) already present |
| **Phi (code)** | Microsoft | **USA** | ✓ | US; smaller |

**Deliverable of Phase 1:** a chosen shortlist (e.g. Devstral for France, a Qwen3-Coder ~30B for China, one
US coder beyond the current two) with the exact model id, quant, approx memory, license, and a one-line
"why". Note that with `MODEL_COUNTRIES=USA` default, at least one strong **US** coder should be in the set so
the default is useful, not just the two current models.

### Approved model set (2026-09-20) — one item pending (Muse Glimmer)

**License gate:** the maintainer requires **OSI-approved** licenses. Verified online 2026-09-20 (per-model,
not by org — that mistake had me wrongly flag Glimmer):

| Model | Org / Country | License | OSI (weights) | Fit @36 GB |
|---|---|---|---|---|
| **Muse Glimmer** (~30B) | Meta / 🇺🇸 US | Apache-2.0 | ✅ | existing; keep — Meta's open agentic model (Aug 2026) |
| **Gemma 4** (26B-A4B) | Google / 🇺🇸 US | Apache-2.0 | ✅ | existing; keep (Gemma 1–3 were NOT OSI; 4 is) |
| **Devstral Small 2** (~24B) | Mistral / 🇫🇷 FR | Apache-2.0 | ✅ | Q4/Q5 — agentic coder, top France pick |
| **Qwen3-Coder** (~30B-A3B MoE) | Alibaba / 🇨🇳 CN | Apache-2.0 | ✅ | Q4 (MoE fast) — top China pick |
| **IBM Granite Code** (~34B) | IBM / 🇺🇸 US | Apache-2.0 | ✅ | US coder to strengthen the default |
| ~~DeepSeek-Coder~~ (DROPPED) | DeepSeek / 🇨🇳 CN | repo MIT, **weights = DeepSeek Model License** | ❌ NO | **EXCLUDED** — weights not OSI (use restrictions, like Llama) |

**FINAL SET (decided 2026-09-20 — OSI-approved licenses ONLY; that is a hard requirement):**
- **Keep:** **Muse Glimmer** (US, Apache-2.0) + **Gemma 4** (US, Apache-2.0) — the US default is fully OSI.
- **Add:** **Devstral Small 2** (🇫🇷 FR, Apache-2.0), **Qwen3-Coder** (🇨🇳 CN, Apache-2.0),
  **IBM Granite Code** (🇺🇸 US, Apache-2.0).
- **DROPPED: DeepSeek-Coder** — its *weights* ship under a restrictive DeepSeek Model License (repo is MIT,
  weights are not), so it fails the OSI-only bar. Not added. Qwen3-Coder already covers China with a clean
  Apache-2.0 license, so China is still represented.
- **Coding caveat:** the strongest dedicated agentic coders are non-US (Qwen/Devstral); US OSI coders
  (Granite, CodeGemma, gpt-oss) trail for agentic work — so a `USA`-only default is the safe baseline, and
  peak coding wants `USA,France` (adds Devstral) or `ALL`.
- Pin the exact GGUF id + quant per model at vendoring time (versions move fast; reconfirm current releases).

## Phase 2 — country of origin

Produce a verified **model → org → country** table (seeded above). "Country" needs a definition (open
question 1) — proposed: the **headquarters country of the org that trained/released the weights** (Mistral →
France, Alibaba/DeepSeek/Zhipu/Moonshot → China, Meta/Google/IBM/Microsoft → USA, Mistral → France). Record
it as a per-model field in the registry so Phase 3 can filter on it.

## Phase 3 — the `MODEL_COUNTRIES` allowlist flag

A flag that selects the **set of models used AND vendored** by country:

- **`MODEL_COUNTRIES`** — a comma-separated allowlist of countries. **Default `USA`** when unset. Special
  value **`ALL`** = every country (no filter). Example overrides: `MODEL_COUNTRIES="USA,France"` (adds
  Mistral), `MODEL_COUNTRIES=ALL`.
- **A model registry** (one source of truth — likely in `server/` and shared/derived by the client) where
  each model carries `country`, its GGUF id/quant, and its port. The flag filters this registry.
- **Gate all three surfaces** (decide together vs independent — open question 3):
  - **Serve** (`server/Makefile` / `make serve`): only offer/serve models whose country ∈ allowlist.
  - **Vendor** (`vendor.sh` / the vendoring step): only download/pin the allowed countries' weights — don't
    fetch (or ship) a disallowed country's model.
  - **Offer** (the client **crushrc** provider generation): only configure providers for allowed models, so
    Crush's model dialog shows only those.
- **Default behavior:** unset ⇒ `USA` ⇒ only US-origin models (Muse Glimmer, Gemma, + any US coder added)
  are served/vendored/offered. This is the "safe default; opt into other countries explicitly" posture.
- **Ports:** more than two models needs more than the fixed 8080/8081 (or a served-one-at-a-time selection);
  resolve as part of this (open question 4).

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-09-20)
1. **"Country" = org HQ of the releasing entity** (Mistral→France, Alibaba/DeepSeek/Zhipu/Moonshot→China,
   Meta/Google/IBM/Microsoft→USA). Simple and verifiable; note multinational edge cases (StarCoder consortium).
2. **ISO-3166 alpha-2 internally, with friendly aliases** (`USA`→`US`, `France`→`FR`, `China`→`CN`).
3. **`MODEL_COUNTRIES` gates serve + vendor + offer TOGETHER** (one flag, all three surfaces), **default US**.
4. **One port per model**, and **Crush autodiscovers the active ports and offers them** in its model dialog.
   Build on the EXISTING mechanism (confirmed 2026-09-20): the vendored Crush has an `internal/discover/`
   package (`client/vendor/crush/internal/discover/llamacpp.go`, `omlx.go`) plus the crushrc's load-time
   probe of the local endpoints (`00-install-minimal.sh`, `tasks/archive/2026/09/22/crushrc-startup-failure-and-model-preselect.md`).
   Extend that from the fixed 8080/8081 pair to a **port-per-model range** (each allowed model gets a port;
   discovery enumerates whichever are live) rather than hardcoding two providers.
5. **OSI-approved licenses ONLY — hard requirement.** Every model in the set/registry must be OSI-approved
   (Apache-2.0 or MIT *weights*); a model whose *weights* carry use restrictions (e.g. DeepSeek-Coder,
   Llama-license models) is excluded at **selection** time. Because the registry is OSI-by-construction, no
   runtime *license* flag is needed — OSI is enforced when a model is added, not gated at runtime. Country
   stays the runtime axis (`MODEL_COUNTRIES`). Verify the *weights* license per model (repo ≠ weights, as
   DeepSeek showed).

**Gate before implementing (maintainer, 2026-09-20):** the maintainer wants the **model shortlist approved
first** — see "Recommended model set" below; implementation of Phase 3 proceeds only after sign-off on the set.

## Related
- Current model setup: `server/Makefile` (ports/serve), the client crushrc (baked provider pinning), and
  `README.md` "The models". Vendoring: `vendor.sh`,
  `tasks/archive/2026/08/22/vendor-multiple-glimmer-quants.md`.
- Sources (2026 landscape, verify at execution): Modal "Best Open Source Code LLMs for Tool-Calling AI
  Agents in 2026", Mistral **Devstral Small 2** (Apache-2.0, ~24B, 32 GB-Mac-capable), Qwen3-Coder,
  Apple-silicon GGUF/quant memory-sizing guides.
