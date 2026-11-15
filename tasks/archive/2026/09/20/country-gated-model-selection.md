# Add coding-agent models with a country-of-origin allowlist (default USA)

**Status:** complete
**Completed:** 2026-09-20
Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>).

Researched and chose three more open-weight coding-agent models for the Mac Studio (36 GB unified
memory), recorded each model's country of origin, and added a `MODEL_COUNTRIES` allowlist (default
`US`) that gates which models are pulled, served and offered. Implemented and sandbox-verified; the
real `make serve` runs on the Mac (Metal) as the operator's normal path. The durable design is
**`tasks/reference/model-registry-country-gate-and-checksums.md`** (read that, not this).

## What was built

- A 5-model registry in `server/Makefile`: glimmer, gemma, granite (US), devstral (FR), qwen (CN), on
  ports 8080–8084, **all Apache-2.0 weights**.
- `MODEL_COUNTRIES` (default `US`; aliases; `ALL`) gating pull/serve/offer together. Verified via
  `make -n`: US→3 models, US,FR→4, ALL→5, China→qwen.
- Client autodiscovery in `crushrc` (probes each port, offers the live ones), and the 5-port
  localhost-only bridge in `client/entrypoint/shell.sh`.
- All 5 HF repos resolved and downloaded (~80 GB), with multi-hash checksums generated.
- Left the vendored Go enricher `client/vendor/crush/internal/discover/llamacpp.go` untouched: the
  crushrc liveness probe delivers autodiscovery, and changing the Go needs a full Crush rebuild that
  could not be verified in-sandbox.
- Known gap: the opt-in `MODEL_FILES` extras path is not country-gated; follow-up
  `tasks/model-files-extras-country-gate.md`.

## Model selection (2026-09-20)

Criteria: fits 36 GB at Q4/Q5 with KV-cache headroom (≈24–32B, or a ~30B MoE); strong at *agentic*
coding; OSI-licensed open weights; servable by llama.cpp as GGUF. Licences were verified per model
online, not by org.

| Model | Org / Country | Weights licence | Decision |
|---|---|---|---|
| Muse Glimmer (~30B) | Meta / US | Apache-2.0 | kept (existing) |
| Gemma 4 (26B-A4B) | Google / US | Apache-2.0 | kept (existing; Gemma 1–3 were not OSI) |
| Devstral Small 2 (~24B) | Mistral / FR | Apache-2.0 | added; agentic coder |
| Qwen3-Coder (~30B-A3B MoE) | Alibaba / CN | Apache-2.0 | added; 480B flagship does not fit |
| IBM Granite Code (~34B) | IBM / US | Apache-2.0 | added; strengthens the US default |
| DeepSeek-Coder | DeepSeek / CN | DeepSeek Model License (repo MIT) | **excluded**: weights not OSI |

Other candidates considered and not added: Codestral, GLM/Kimi code models, CodeGemma, Code Llama,
Phi. Caveat recorded at selection: the strongest dedicated agentic coders are non-US, so the `US`
default is the safe baseline and peak coding wants `US,FR` or `ALL`.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-09-20)
1. **"Country" = org HQ of the releasing entity** (Mistral→France, Alibaba/DeepSeek/Zhipu/Moonshot→China,
   Meta/Google/IBM/Microsoft→USA). Simple and verifiable; note multinational edge cases (StarCoder consortium).
2. **ISO-3166 alpha-2 internally, with friendly aliases** (`USA`→`US`, `France`→`FR`, `China`→`CN`).
3. **`MODEL_COUNTRIES` gates serve + vendor + offer TOGETHER** (one flag, all three surfaces), **default US**.
4. **One port per model**, and **Crush autodiscovers the active ports and offers them** in its model
   dialog, building on the crushrc's load-time probe of the local endpoints
   (`tasks/archive/2026/09/22/crushrc-startup-failure-and-model-preselect.md`) rather than hardcoding
   two providers. Superseded the earlier "pin exactly two providers" crushrc.
5. **OSI-approved licenses ONLY — hard requirement.** Every model in the set/registry must be OSI-approved
   (Apache-2.0 or MIT *weights*); a model whose *weights* carry use restrictions (e.g. DeepSeek-Coder,
   Llama-license models) is excluded at **selection** time. Because the registry is OSI-by-construction, no
   runtime *license* flag is needed — OSI is enforced when a model is added, not gated at runtime. Country
   stays the runtime axis (`MODEL_COUNTRIES`). Verify the *weights* license per model (repo ≠ weights, as
   DeepSeek showed).

The maintainer approved the model shortlist before Phase 3 (the flag) was implemented.

## Related
- `server/Makefile`, `client/entrypoint/crushrc`, `README.md` "The models"; vendoring: `vendor.sh`,
  `tasks/archive/2026/08/22/vendor-multiple-glimmer-quants.md`.
- Sources consulted (2026 landscape): Modal "Best Open Source Code LLMs for Tool-Calling AI Agents in
  2026", Mistral Devstral Small 2, Qwen3-Coder, Apple-silicon GGUF memory-sizing guides.
