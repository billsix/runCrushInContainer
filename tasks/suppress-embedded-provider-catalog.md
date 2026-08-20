# Make Crush offer ONLY the local model — suppress the embedded provider catalog

**Status:** researched — root cause found, served model ID captured, exact fix written below;
**needs go-ahead to apply** to `client/entrypoint/crushrc` (nothing applied yet)
**Priority:** 3
**Difficulty:** 3
**Started:** 2026-08-20

## Symptom (maintainer, on a separate airgapped machine, 2026-08-20)

Running Crush with **no `crush.json` in the launch directory** shows a picker of ~15–20 models
(models the maintainer does NOT want offered). With a `crush.json` present at the launch dir, Crush
"finds the models and only loads those." Goal: **only the local model should ever be offered** — the
15–20 must not appear. This affects runCrushInContainer directly: the client bakes a `crushrc` (no
`crush.json`), so it would show the same catalog.

## Root cause (verified in Crush v0.89.0 source)

The ~15–20 models are Crush's **embedded Catwalk provider catalog** — the built-in list of known
providers/models (OpenAI, Anthropic, Google, …) that Crush **merges in by default** and falls back to
when offline. `internal/config/catwalk.go:45-47`: when not auto-updating (airgapped/offline), Crush
loads `embedded.GetAll()` — the full built-in catalog. These are merged with any user-configured
providers and offered in the model picker.

**The documented off-switch is `disable_default_providers`** (`internal/config/config.go:329`):

> *"Ignore all default/embedded providers. When enabled, providers must be fully specified in the
> config file with base_url, models, and api_key — no merging with defaults occurs."*

- **crushrc spelling** (`internal/shellconfig/options.go:191`): the option is `default-providers`,
  **inverted**, mapping to JSON `disable_default_providers`. So **`option default-providers false`**
  in crushrc = "do NOT include built-in providers" = `disable_default_providers: true`. (Docs
  `docs/config/README.md:479`: "default-providers — include built-in providers".)
- **crush.json spelling:** `"disable_default_providers": true`.

### Why a `crush.json` makes the list go away (precise mechanism — NOT an rc-vs-json thing)

The model list is built from `config.Providers(cfg)` (dialog `internal/ui/dialog/models.go:359`),
which returns the **built-in Catwalk catalog** (the 15–20) UNLESS `disable_default_providers` is set —
`internal/config/provider.go:175,186` short-circuits to custom-providers-only when the option is on.
There are two ways a `crush.json` changes the outcome; the second is the likely one on the airgapped
box:

1. **The `crush.json` sets `disable_default_providers: true`** → `config.Providers()` returns only the
   custom provider; the catalog never appears. Direct.
2. **The `crush.json` fully specifies a working provider (base_url + an explicit `models` list)** →
   Crush has an enabled provider, so `IsConfigured()` is true and it does NOT fall into the onboarding
   catalog picker (`internal/ui/model/ui.go:491`: `if !IsConfigured() → uiOnboarding`; `IsConfigured`
   = ≥1 enabled provider, `config.go:720`). **The reason the `crushrc` did NOT achieve this offline:**
   its provider has no `models`, so it relies on live discovery (`GET /v1/models`, 3-second timeout);
   airgapped that discovery fails → the provider is **deleted** (`load.go:471`) → `!IsConfigured()` →
   onboarding shows the catalog. The `crush.json` listed models explicitly, so the provider survived.

So the decisive variable is **whether the provider ends up with a models list without needing live
discovery** — not the file format. "finds the models and only loads those" points at mechanism #2
(startup/onboarding). To be 100% certain which was in play, inspect the actual airgapped `crush.json`:
does it carry `disable_default_providers`, an explicit `models` array, or a selected model?

### Secondary finding — with defaults disabled, the local provider must carry EXPLICIT models

With `disable_default_providers: true`, "providers must be fully specified … with base_url, models,
and api_key." Our baked crushrc declares the provider with **no models**, relying on **load-time
auto-discovery** (`internal/config/load.go:382-475`): for a custom provider with no models Crush hits
the endpoint (`/v1/models`) with a **3-second timeout** (`load.go:394`); **if discovery fails or
returns nothing, the provider is deleted** (`load.go:471-472`, `:479-480` — "Skipping custom provider
because the provider has no models"). So a crushrc that depends on discovery is fragile: launch Crush
before the SSH tunnel + llama-server are reachable (or the lazy forward's first connect exceeds 3s)
and the provider vanishes entirely. `crushrc` can declare models explicitly with **`model add
<provider>/<model-id>`** (`internal/shellconfig/model.go:80-108`), which removes the discovery
dependency and is airgapped-robust.

## Live server probe — the served model ID (2026-08-20)

To pin the model in `crushrc` (mechanism #2) we need the exact ID the server reports. The maintainer
ran this **on the host** (where the SSH tunnel terminates — the sandbox this agent runs in is on a
bridged network and cannot reach the host's loopback tunnel):

```sh
curl -s http://127.0.0.1:8080/v1/models
```

Response (trimmed to the relevant fields):

```json
{"object":"list","data":[{"id":"./models/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf",
  "aliases":["./models/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"],"owned_by":"llamacpp",
  "meta":{"n_ctx":32768,"n_params":27854794240,"size":16743567360,"ftype":"Q4_K - Medium"}}]}
```

**What this tells us / what to do with it:**
- The served model **ID is `./models/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf`** — llama-server reports
  the raw `-m` path because no `--alias` is set. It also confirms the server is healthy: Q4_K_M, 32768
  ctx, ~27.9B params, `owned_by: llamacpp` (matches `server/Makefile` defaults).
- That path-shaped ID is **fragile for a template**: it changes the moment `MODEL_FILE` (quant/file)
  changes, and it contains `/` and `.` which are awkward in `model add <provider>/<id>`.
- **Recommendation — pin a stable alias instead of the path.** Add `--alias muse-glimmer` to the
  server's `make serve` (a `MODEL_ALIAS` var in `server/Makefile`) so `/v1/models` reports the constant
  ID `muse-glimmer`, and pin the client `crushrc` to that. Then swapping quant/file never touches the
  client config. This is the one place the **server** is relevant to this task: it owns the ID string
  the client must match. Fallback if the server can't be changed: pin the raw path ID verbatim in
  `crushrc` (works, but re-edit on any model swap).

## Fix (proposed — NOT applied; for the baked `client/entrypoint/crushrc`, plus one server line)

Both parts matter; they close the two different paths above. **Concrete config, using the alias
recommendation:**

Server side — `server/Makefile` (one variable + one flag) so the ID is a stable constant:

```make
MODEL_ALIAS ?= muse-glimmer
# in the serve target, add:  --alias $(MODEL_ALIAS)
```

Client side — append to `client/entrypoint/crushrc` (keep it in sync with `MODEL_ALIAS`):

```sh
option default-providers false        # suppress the ~15-20 built-in catalog (mechanism #1)

provider add muse-glimmer \
  --name "Muse Glimmer (local llama.cpp)" \
  --type llamacpp \
  --base-url "http://127.0.0.1:8080" \
  --api-key "local-no-key-needed"

model add muse-glimmer/muse-glimmer --name "Muse Glimmer 30B" --context-window 32768
model large muse-glimmer/muse-glimmer   # `model large|small` are the real select subcommands
model small muse-glimmer/muse-glimmer   # (verified internal/shellconfig/model.go:41-47)
```

Both parts, restated:

1. **Give the provider an EXPLICIT models list — the load-bearing fix (mechanism #2).**
   `model add muse-glimmer/<served-model-id>` (`internal/shellconfig/model.go:80-108`) so the provider
   is fully specified and **never depends on live discovery** — it survives even when the tunnel/server
   isn't reachable at launch, so Crush stays `IsConfigured()` and never falls into the onboarding
   catalog. Optionally also `model select large|small muse-glimmer/<id>` (`model.go:180-190`) so the
   model is preselected and no picker appears at all.
2. **`option default-providers false` — belt-and-suspenders (mechanism #1).** Sets
   `disable_default_providers: true`, so `config.Providers()` returns only our provider and the 15–20
   can't appear even if someone opens the model picker manually. (Note: with defaults disabled, the
   provider MUST be fully specified — which #1 already does.)

Trade-off vs. the current crushrc: today's config leans on auto-discovery ("no model to name"),
convenient when the endpoint is up but exactly what produces the fragility here. Explicit
specification is more verbose but deterministic and offline-safe.

## Open questions

1. **Served model ID — RESOLVED (2026-08-20):** `./models/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf`
   (from the live probe above). Recommend pinning a stable `--alias muse-glimmer` on the server rather
   than this path. Decision needed: **alias (recommended) vs raw-path pin** — see the probe section.
2. **Mechanism (#1 catalog-merge vs #2 provider-dropped-into-onboarding) — covered either way.** The
   proposed fix applies BOTH `option default-providers false` and an explicit pinned model, so it
   holds regardless of which path the airgapped box hit. Confirming which was in play needs the actual
   airgapped `crush.json` (does it set `disable_default_providers`, or list models?) — nice-to-have,
   not blocking.
3. **Go-ahead to APPLY the fix?** Nothing is applied yet (I reverted my earlier edits). This is the
   decision that unblocks implementation: apply the `crushrc` block (and the one `server/Makefile`
   alias line), then rebuild the client image and confirm on a live session. Recommend yes.

## Relevance / cross-links

- The baked config is `client/entrypoint/crushrc`; the "auto-discovers the served model" claim is in
  `tasks/reference/architecture.md` (client section) — that claim is the source of the fragility in
  the secondary finding and should be updated when this lands.
- Capability facts: `tasks/reference/crush-capabilities.md`.
