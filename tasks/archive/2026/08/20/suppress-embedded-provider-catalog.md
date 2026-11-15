# Make Crush offer ONLY the local model — suppress the embedded provider catalog

**Status:** complete
**Started:** 2026-08-20 · **Completed:** 2026-08-20

Fixed the client so Crush offers only the local model: the crushrc now disables Crush's embedded
provider catalog and pins the model explicitly, and the server reports a stable alias ID. Verified at
config level (`crush models` went from 1532 entries to 1). The durable mechanism is in
`tasks/reference/crush-capabilities.md` ("Provider & model selection"); the airgapped real-world check
was tracked in `tasks/archive/2026/08/21/verify-provider-suppression-airgapped.md`.

> **Superseded (2026-09-20):** the single pinned `muse-glimmer` provider and the one `MODEL_ALIAS`
> variable were replaced by the five-port model table (per-row `MODEL_ALIAS_<m>`) and probe-based
> provider registration in the crushrc. See
> `tasks/reference/model-registry-country-gate-and-checksums.md` and
> `tasks/reference/crush-capabilities.md` § "Which model is active at startup".
> `option default-providers false` still applies.

## Symptom (maintainer, on a separate airgapped machine, 2026-08-20)

With no `crush.json` in the launch directory, Crush showed a picker of ~15-20 unwanted models; with a
`crush.json` present it "finds the models and only loads those." The client bakes a `crushrc` (no
`crush.json`), so it would show the same catalog.

## Root cause (verified in Crush v0.89.0 source)

The extra models are Crush's **embedded Catwalk provider catalog**, merged in by default and loaded
from `embedded.GetAll()` when offline (`internal/config/catwalk.go`). The off-switch is
`disable_default_providers` (`internal/config/config.go`), spelled **`option default-providers false`**
in crushrc (inverted; `internal/shellconfig/options.go`) and `"disable_default_providers": true` in
`crush.json`. The picker reads `config.Providers(cfg)`, which short-circuits to custom providers only
when that option is on (`internal/config/provider.go`).

Why a `crush.json` made the list go away (not an rc-vs-json difference), two possible mechanisms:

1. It set `disable_default_providers: true`, so the catalog never appears.
2. It fully specified a provider with an explicit `models` list, so `IsConfigured()` was true and
   Crush skipped the onboarding catalog picker (`internal/ui/model/ui.go`). The old crushrc's provider
   had no models and relied on live discovery (`GET /v1/models`, 3-second timeout,
   `internal/config/load.go`); airgapped, discovery failed, the provider was **deleted** ("Skipping
   custom provider because the provider has no models"), and onboarding showed the catalog.

The decisive variable is whether the provider has a models list without needing live discovery.
Secondary finding: discovery-dependent config is fragile even when online, since launching Crush
before the tunnel and llama-server are reachable (or a slow first connect over 3 s) drops the
provider. `model add <provider>/<model-id>` (`internal/shellconfig/model.go`) removes that dependency.

Which mechanism the airgapped box actually hit was never confirmed (it would need that box's
`crush.json`); the fix covers both.

## Live server probe (2026-08-20)

The maintainer ran `curl -s http://127.0.0.1:8080/v1/models` on the host (the sandbox cannot reach
the host's loopback tunnel). The served ID was the raw `-m` path,
`./models/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` (no `--alias` set), with `n_ctx` 32768, ~27.9B
params, Q4_K_M, `owned_by: llamacpp`.

## Decisions

- **Pinned a stable alias instead of the raw path ID.** The path changes with every quant/file swap and
  contains `/` and `.`, awkward in `model add <provider>/<id>`. With `--alias`, swapping the GGUF never
  touches the client config.
- **Applied both fixes** (catalog suppression and an explicit model) so the result holds regardless of
  which mechanism was in play. Explicit specification is more verbose than auto-discovery but
  deterministic and offline-safe.

## What was done

- **`client/entrypoint/crushrc`**: added `option default-providers false`, an `--api-key`, an explicit
  `model add muse-glimmer/muse-glimmer --context-window 32768`, and `model large|small` selections.
- **`server/Makefile`**: added `MODEL_ALIAS ?= muse-glimmer` and `--alias $(MODEL_ALIAS)` on `serve`,
  so `/v1/models` reports `muse-glimmer`.

## Verification

Before/after with `crush v0.89.0`, an isolated config, and the endpoint deliberately unreachable:
`crush models` listed **1532** models with the old crushrc and **exactly one**
(`muse-glimmer/muse-glimmer`) with the new one, exiting 0 without contacting the endpoint.

Left to the maintainer at the time: rebuild the client image (`cd client && make image`, since the
crushrc is `COPY`d at build), restart `make serve` to pick up the alias (functionally optional, since
llama-server serves its one loaded model regardless of the request's model field), and a live session
check with no picker. The live check was not doable from the sandbox and was handed to the airgapped
verification task.

## Related

- `client/entrypoint/crushrc`; the old "auto-discovers the served model" claim was in
  `tasks/reference/architecture.md` (client section).
- `tasks/reference/crush-capabilities.md`.
- `tasks/archive/2026/08/20/context-window-sizing.md`: touches the same `model add` line.
