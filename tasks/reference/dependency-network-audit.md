# Dependency network audit — every vendored Go module, classified for airgap egress

**Status:** analysis complete AND **implemented** (2026-08-29) — all 213 modules triaged, all 66
flagged modules deep-audited at source; all decisions D1–D12 confirmed by the maintainer (William
Emerison Six <billsix@gmail.com>, 2026-08-29), defaults as in the flag index (§5). The patches
exist in `client/patches/`, wired through `client/entrypoint/03-build-crush.sh` /
`client/Dockerfile` / `client/Makefile` (work record: `tasks/archive/2026/08/29/implement-egress-patch-flags.md`).
Where an entry below describes patch *mechanics*, the implemented shape is authoritative — see the
"implemented as" notes; the audit's `file:line` findings themselves are unchanged.
**Audited version:** Crush **v0.89.0** (commit `ba531a409ab68f91144c80eafae8b952daa35a0d`), the
`CRUSH_TAG` pin in `client/Makefile` — 213 vendored modules per `vendor/modules.txt`.
**Re-audit on any `CRUSH_TAG` bump.** Re-sync check: compare
`git -C client/vendor/crush rev-parse HEAD` against the SHA above; if they differ, this doc is stale.
**Produced by:** `tasks/archive/2026/08/29/audit-dependency-network-egress.md` (the investigation task — method,
policy, and decision history live there). Regenerate the phase-1 table with
`python3 tools/triage_dependency_egress.py` from the repo root.

**FOUNDATIONAL:** this deployment's only intended traffic is Crush → the **local model at
`127.0.0.1:8080`** (llama.cpp behind an SSH tunnel, `--network=host`). Loopback/local-model traffic
is the essential core — never a finding, never patched. Everything below concerns **external**
egress only.

**Every decision below is a flag with a default — nothing is irreversible** (maintainer decision,
2026-08-29). Defaults encode the disposition (`1` = patched out by default, `0` = kept by default);
any build can flip any of them (`make image PATCH_OUT_<X>=…`). The vendored tree stays complete and
unpatched, so the airgap box can build every combination.

## 1. Network functionality intentionally KEPT (and why)

_The deliberate online surface — what will (harmlessly) reach for the network, and why it stays._

- **D1 — Web tools · KEEP · `PATCH_OUT_WEB_TOOLS ?= 0` · `client/patches/no-web-tools.patch`.**
  The task doc's "web search" turned out to be a **family of five** default-enabled tools:
  `web_search` (DuckDuckGo Lite, `internal/agent/tools/search.go:68`), `web_fetch` +
  `fetch` + `download` (arbitrary URL GET, scheme-guarded), and `agentic_fetch` (sub-agent
  wrapping search+fetch, `internal/agent/agentic_fetch_tool.go:165-172`). Kept because they are
  user/model-initiated features genuinely useful on an online network; offline they fail with an
  ordinary network error, harmlessly. Implemented as: the patch (when flipped to `1`) removes the
  tool *registrations* (`coordinator.go` buildTools + the `allToolNames()` entries) — the tool
  files stay compiled because the UI layer switches on their name constants, so
  `html-to-markdown`/`goquery` remain in the binary (they are NO-EGRESS libs, §4.5; the egress
  belongs to the tools). No-patch alternative: the crushrc `deny` verb
  (`options.disabled_tools`) filters the tool list without a rebuild.
- **D2 — Sourcegraph tool · KEEP · `PATCH_OUT_SOURCEGRAPH ?= 0` ·
  `client/patches/no-sourcegraph.patch`.** Public-code search against the hardcoded
  `https://sourcegraph.com/.api/graphql` (`internal/agent/tools/sourcegraph.go:113`). Its own
  flag (separate third party, separate endpoint) but same character as D1: user-initiated,
  degrades gracefully. Default confirmed **keep** by the maintainer (2026-08-29).
- **MCP — KEEP, no patch needed (documented).** All egress targets operator-configured URLs
  only; stdio transport is a local subprocess; empty MCP config ⇒ zero connections (§4.3). Not a
  decision flag — there is no unsolicited egress to toggle.
- **The local-model link — FOUNDATIONAL, untouchable.** `openai-go/v3` +
  `fantasy/providers/{openai,openaicompat}` + the llamacpp discover/enricher path (§4.4). Every
  patch must leave this chain intact; `api.openai.com` is proven unreachable on it.

## 2. Removed / patched out by default

- **D3 — Update check · PATCH OUT · `PATCH_OUT_UPDATE_CHECK ?= 1` ·
  `client/patches/crush-no-update-check.patch` (existing, gains its flag).** Startup GET to
  `api.github.com` (`internal/update/update.go:15,94`, launched `internal/app/app.go:139`).
  Unsolicited; never wanted.
- **D4 — Telemetry hard-off · PATCH OUT · `PATCH_OUT_TELEMETRY ?= 1` ·
  `client/patches/no-telemetry.patch` (new).** Forces `shouldEnableMetrics`
  (`internal/cmd/root.go:966-978`) to `false` at build time, making the PostHog path
  (`data.charm.land/batch/`, §4.3) unreachable regardless of env/config. Complements — does not
  replace — the existing `CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1` env and `option metrics false`.
  The gate is proven total (§4.3), so this one patch covers every emitter.
- **D5 — Google/Vertex providers · REMOVE · `PATCH_OUT_GOOGLE_PROVIDER ?= 1` ·
  `client/patches/no-google-provider.patch`.** Implemented as a **vendored-fantasy-only** patch
  (Crush untouched — cleaner than the §4.1 Crush-side cut lists, because the SDK imports live in
  fantasy): (a) `providers/google` is gutted to a stub (`google_removed.go` keeps the exported
  surface — Name, Option, With*, New→error, GetReasoningMetadata — and `provider_options.go`,
  which has no genai dependency, is kept), so Crush and the openrouter/vercel hooks compile
  unchanged; (b) `providers/anthropic` loses its Vertex branch (imports replaced by marker
  comments, block replaced by an erroring guard). Drops from the binary:
  `google.golang.org/genai`, `cloud.google.com/go/{auth,civil,compute/metadata}`,
  `google.golang.org/api`, `grpc`, `s2a-go`, `gax-go`, `x/oauth2/google` subpackages — and orphans
  the OTel tree, `gorilla/websocket`, `httpsnoop`. Out-of-design (maintainer, 2026-08-29); also
  eliminates the GCE metadata-probe risk class entirely.
- **D6 — Bedrock/AWS · REMOVE · `PATCH_OUT_BEDROCK_AWS ?= 1` ·
  `client/patches/no-bedrock-aws.patch`.** Implemented as a **vendored-fantasy-only** patch: strip
  the `useBedrock` branch of `providers/anthropic` (erroring guard), delete
  `providers/anthropic/bedrock.go`, and replace the two AWS imports with marker comments. Crush is
  untouched — its `providers/bedrock` wrapper and `aws_sso_refresh.go` (local `exec`, no network)
  compile but end at the guard. Drops all 9 `aws-sdk-go-v2` modules + `smithy-go`, and the IMDS
  (`169.254.169.254`) risk class. Same out-of-design rationale as D5.
- **D7 — Azure · REMOVE · `PATCH_OUT_AZURE ?= 1` · `client/patches/no-azure.patch`.** Implemented
  as a stub of vendored `fantasy/providers/azure` (New→error, the `openai-go/v3/azure` import
  dropped; option surface kept), rather than the §4.2 Crush-side cut — zero Crush edits. Drops
  `azcore` + `sdk/internal` (+ `openai-go/v3/azure`).
- **D8 — `crush update-providers` · PATCH OUT · `PATCH_OUT_UPDATE_PROVIDERS_CMD ?= 1` ·
  `client/patches/no-update-providers-cmd.patch`.** The one catwalk path the
  `default-providers false` gate does not cover (`internal/config/provider.go:60,67`, via
  `internal/cmd/update_providers.go`). Technically user-initiated, but the provider catalog is
  suppressed by design in this local-first setup, so the command has nothing useful to fetch.
  Default confirmed **patch out** by the maintainer (2026-08-29).
- **D9 — OpenRouter provider · REMOVE · `PATCH_OUT_OPENROUTER ?= 1` ·
  `client/patches/no-openrouter.patch`.** Cloud LLM gateway (`https://openrouter.ai/api/v1`,
  forced — `fantasy/providers/openrouter/openrouter.go:20,33`). Implemented as an erroring guard
  at the top of vendored `fantasy/providers/openrouter` `New()` — no SDK weight is involved, so a
  minimal reversible guard beats an import cut; a configured openrouter-typed provider fails with
  an explicit error. (The package stays compiled; its egress needs `New()`.)
- **D10 — Vercel provider · REMOVE · `PATCH_OUT_VERCEL ?= 1` ·
  `client/patches/no-vercel.patch`.** Cloud gateway (`https://ai-gateway.vercel.sh/v1`, forced —
  `fantasy/providers/vercel/vercel.go:19,32`). Same shape as D9: erroring guard in vendored
  `fantasy/providers/vercel` `New()`.
- **D11 — Hyper provider · REMOVE · `PATCH_OUT_HYPER ?= 1` · `client/patches/no-hyper.patch`.**
  Charm's hosted provider (`https://hyper.charm.land`). Implemented as **guards at every egress
  chokepoint** rather than package deletion (the hyper wiring spans config/UI/login across many
  files — the audit's delete-the-packages cut list was incomplete): the device-flow OAuth
  (`internal/oauth/hyper/device.go`: InitiateDeviceAuth, pollOnce, ExchangeToken,
  IntrospectToken), the catalog fetch (`internal/config/hyper.go` doGet), the credits fetch
  (`internal/agent/hyper/provider.go` FetchCredits), and the LLM proxy path + `x-crush-id` header
  (`coordinator.go` hyper case; the now-unused `internal/event` import goes with it). Was already
  dormant via `default-providers false`; now no request to hyper.charm.land can be built.
- **D12 — Copilot OAuth/provider · REMOVE · `PATCH_OUT_COPILOT ?= 1` ·
  `client/patches/no-copilot.patch`.** GitHub device-flow OAuth
  (`internal/oauth/copilot/oauth.go:20-22` — `github.com/login/*`,
  `api.github.com/copilot_internal/v2/token`). Implemented as guards on the three request
  builders (RequestDeviceCode, tryGetToken, getCopilotToken) — which also disables the Copilot
  provider's token-refresh client. Was reachable only via explicit `crush auth`.

(D9–D12 confirmed patch-out-by-default by the maintainer, 2026-08-29 — overriding the audit's
initial document-only lean: out-of-design for the local-first setup, same class as D5–D7.)

**Considered and NOT patched (documented instead):** OTel (cannot export — no exporter vendored,
§4.3); `x/oauth2` (needed by MCP OAuth); catwalk module (types are load-bearing; its network
surface is already dead); the anthropic direct provider (inert without config; removing it
entirely would additionally drop `anthropic-sdk-go` + `standard-webhooks` — available as a future
cut if wanted).

## 3. Phase-1 triage of all 213 modules

Mechanical scan (see the script header for signal definitions). Tiers: **NETWORK** = client-side
call sites, wire-protocol imports, or endpoint string literals — gets a phase-2 deep entry;
**imports-only** = net-adjacent imports, no call sites (often just status codes/types);
**url-strings-only** = URL literals in strings, no network code; **no-network** = none of the
above. The tier is a *lead, not a verdict* — phase 2 confirms or refutes each flagged row at
source level.

Counts: **NETWORK: 46 · imports-only: 13 · url-strings-only: 7 · no-network: 147**.

### Flagged modules (phase-2 work-list)

| module | version | tier |
|---|---|---|
| charm.land/catwalk | v0.51.18 | NETWORK |
| charm.land/fantasy | v0.41.0 | NETWORK |
| cloud.google.com/go | v0.123.0 | NETWORK |
| cloud.google.com/go/auth | v0.22.0 | NETWORK |
| cloud.google.com/go/compute/metadata | v0.9.0 | NETWORK |
| github.com/Azure/azure-sdk-for-go/sdk/azcore | v1.22.0 | NETWORK |
| github.com/JohannesKaufmann/html-to-markdown | v1.6.0 | NETWORK |
| github.com/PuerkitoBio/goquery | v1.12.0 | NETWORK |
| github.com/andybalholm/brotli | v1.2.2 | NETWORK |
| github.com/anthropics/anthropic-sdk-go | v1.63.0 | NETWORK |
| github.com/aws/aws-sdk-go-v2 | v1.43.4 | NETWORK |
| github.com/aws/aws-sdk-go-v2/config | v1.32.35 | NETWORK |
| github.com/aws/aws-sdk-go-v2/feature/ec2/imds | v1.18.35 | NETWORK |
| github.com/aws/aws-sdk-go-v2/internal/v4a | v1.4.36 | NETWORK |
| github.com/aws/aws-sdk-go-v2/service/signin | v1.5.4 | NETWORK |
| github.com/aws/aws-sdk-go-v2/service/sso | v1.33.4 | NETWORK |
| github.com/aws/aws-sdk-go-v2/service/ssooidc | v1.38.4 | NETWORK |
| github.com/aws/aws-sdk-go-v2/service/sts | v1.45.4 | NETWORK |
| github.com/aws/smithy-go | v1.27.6 | NETWORK |
| github.com/felixge/httpsnoop | v1.1.0 | NETWORK |
| github.com/go-openapi/spec | v0.20.6 | NETWORK |
| github.com/go-openapi/swag | v0.19.15 | NETWORK |
| github.com/godbus/dbus/v5 | v5.2.2 | NETWORK |
| github.com/google/s2a-go | v0.1.9 | NETWORK |
| github.com/googleapis/gax-go/v2 | v2.23.0 | NETWORK |
| github.com/gorilla/websocket | v1.5.3 | NETWORK |
| github.com/invopop/jsonschema | v0.14.0 | NETWORK |
| github.com/kaptinlin/jsonschema | v0.9.8 | NETWORK |
| github.com/modelcontextprotocol/go-sdk | v1.7.0 | NETWORK |
| github.com/openai/openai-go/v3 | v3.50.0 | NETWORK |
| github.com/posthog/posthog-go | v1.23.0 | NETWORK |
| github.com/rivo/uniseg | v0.4.7 | NETWORK |
| github.com/standard-webhooks/standard-webhooks/libraries | v0.0.1 | NETWORK |
| github.com/stretchr/testify | v1.11.1 | NETWORK |
| go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc | v0.69.0 | NETWORK |
| go.opentelemetry.io/otel | v1.44.0 | NETWORK |
| golang.design/x/clipboard | v0.8.0 | NETWORK |
| golang.org/x/mobile | v0.0.0-20250606033058-a2a15c67f36f | NETWORK |
| golang.org/x/net | v0.57.0 | NETWORK |
| golang.org/x/oauth2 | v0.36.0 | NETWORK |
| golang.org/x/sys | v0.47.0 | NETWORK |
| golang.org/x/tools | v0.48.0 | NETWORK |
| google.golang.org/api | v0.291.0 | NETWORK |
| google.golang.org/genai | v1.67.0 | NETWORK |
| google.golang.org/grpc | v1.83.0 | NETWORK |
| gopkg.in/dnaeon/go-vcr.v4 | v4.0.6-0.20251110073552-01de4eb40290 | NETWORK |
| charm.land/x/vcr | v0.1.1 | imports-only |
| github.com/Azure/azure-sdk-for-go/sdk/internal | v1.12.0 | imports-only |
| github.com/Microsoft/go-winio | v0.6.2 | imports-only |
| github.com/aws/aws-sdk-go-v2/credentials | v1.19.34 | imports-only |
| github.com/charmbracelet/x/etag | v0.2.0 | imports-only |
| github.com/go-viper/mapstructure/v2 | v2.5.0 | imports-only |
| github.com/google/uuid | v1.6.0 | imports-only |
| github.com/mailru/easyjson | v0.7.7 | imports-only |
| github.com/mitchellh/mapstructure | v1.5.0 | imports-only |
| github.com/spf13/pflag | v1.0.9 | imports-only |
| github.com/swaggo/http-swagger/v2 | v2.0.2 | imports-only |
| github.com/swaggo/swag | v1.16.6 | imports-only |
| go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp | v0.69.0 | imports-only |
| github.com/google/jsonschema-go | v0.4.3 | url-strings-only |
| github.com/microcosm-cc/bluemonday | v1.0.27 | url-strings-only |
| github.com/pressly/goose/v3 | v3.27.3 | url-strings-only |
| github.com/yuin/goldmark-emoji | v1.0.5 | url-strings-only |
| google.golang.org/protobuf | v1.36.11 | url-strings-only |
| modernc.org/sqlite | v1.56.0 | url-strings-only |
| mvdan.cc/sh/v3 | v3.13.1 | url-strings-only |

### The 147 no-network modules

Not listed row-by-row here (regenerate the full 213-row table with the triage script for the
complete listing); the count and the script are the record that nothing went unexamined. Spot-check
membership of any module: run the script and grep its output.

## 4. Deep entries — network-capable modules

Per-module: why present / import chain · behavior (`file:line`, paths relative to
`client/vendor/crush`) · activation condition · disposition. Findings produced by parallel
source-readers and independently spot-verified before entry (import chains, endpoint constants,
gate conditions re-checked by grep/read at the cited lines). Dispositions here are the audit's
recommendation; the *named decisions* with flags land in sections 1–2.

**A cross-cutting mechanical fact that shapes every patch:** Crush's own code imports **no provider
SDK directly** (sole exception: one `openai-go/v3/option` symbol at
`internal/agent/coordinator.go:53`). Every SDK arrives transitively through `charm.land/fantasy`'s
provider subpackages, imported at `coordinator.go:45-52`, `internal/agent/agent.go:31-36`, and
`internal/message/content.go:13-15`. Because Go compiles what a *package graph* imports, dropping an
SDK from the binary requires cutting its import inside **vendored fantasy**, not just Crush — a
Crush-only patch removes the feature but not the compiled code. Azure is the one exception (a clean
single-line Crush cut).

### 4.1 Google family (Root A: Gemini; Root B: Anthropic-Vertex)

Two independent roots, both inside vendored fantasy — Crush's own code imports zero Google packages:

- **Root A:** `fantasy/providers/google/google.go:22` → `google.golang.org/genai` →
  `cloud.google.com/go/auth`, `/civil`, `/compute/metadata`, `s2a-go`, `gax-go`. Also re-imported by
  `fantasy/providers/openrouter/language_model_hooks.go:12` and
  `fantasy/providers/vercel/language_model_hooks.go:12` (verified).
- **Root B:** `fantasy/providers/anthropic/anthropic.go:24,26` → `anthropic-sdk-go/vertex` →
  `google.golang.org/api`, `x/oauth2/google`, `oauth2adapt`, `grpc`, `s2a-go`, `compute/metadata`.

| module | behavior | activation | disposition |
|---|---|---|---|
| `google.golang.org/genai` v1.67.0 | HTTP + WebSocket (Gemini Live, `live.go:123`); hosts `aiplatform.googleapis.com`, `generativelanguage.googleapis.com` (`client.go:321-336`) | only via `genai.NewClient` from a configured google/google-vertex provider; explicit base URL beats defaults; ADC skipped when a custom base URL is set (`client.go:506-507`) | REMOVE (with family) |
| `cloud.google.com/go/auth` v0.22.0 | OAuth/ADC endpoints (`credentials/detect.go:40-47`: `accounts.google.com`, `oauth2.mtls.googleapis.com`); async token-refresh goroutine `auth.go:381` — fires only after a credential exists | call-time only; ADC search order `detect.go:122-129` (env var → gcloud file → GCE probe) | REMOVE (with family) |
| `cloud.google.com/go/compute/metadata` v0.9.0 | **the ambient-probe module**: `OnGCE()` fires two parallel goroutines — HTTP to `169.254.169.254` (`metadata.go:431`) + DNS `metadata.google.internal.` (`metadata.go:445`), 2s timeout — with **no credentials needed** | call-time only, four call sites, all behind a configured Vertex provider (e.g. `fantasy/providers/anthropic/anthropic.go:266` requires vertexProject AND vertexLocation — verified). Never at init(). `GCE_METADATA_HOST` env short-circuits with zero traffic (`metadata.go:458`) | REMOVE (with family); highest-risk module if misconfigured |
| `cloud.google.com/go` (only `/civil` vendored) | none — pure date types | n/a | inert; drops with genai |
| `cloud.google.com/go/auth/oauth2adapt` | none of its own (adapter) | n/a | drops with Root B |
| `googleapis/gax-go/v2` v2.23.0 | none — retry/backoff/headers; the OTel schema URL string is a namespace, never fetched (`telemetry.go:136`) | no egress under any config | inert; drops with family |
| `google/s2a-go` v0.1.9 | gRPC to an S2A handshaker at an address obtained *from the metadata server* — no hardcoded host | double-gated: `EXPERIMENTAL_GOOGLE_API_USE_S2A` env + conditions Crush never satisfies (`auth/internal/transport/s2a.go:111-133`) | unreachable; drops with family |
| `google.golang.org/api` v0.291.0 | HTTP + gRPC transports; DirectPath/ALTS branches gated on `OnGCE()` | Root B only — the **Anthropic** provider's Vertex backend drags this in, not any Google provider | REMOVE (with Root B cut) |
| `google.golang.org/grpc` v1.83.0 | generic transport; one hardcoded host: ALTS `metadata.google.internal.:8080` (`credentials/alts/alts.go:46`), only via the `OnGCE()`-gated DirectPath branch. The `google-c2p` xDS resolver is **not vendored** (verified: no xds/rls in `modules.txt`) | no gRPC channel dialed in any compiled Crush path (genai = HTTP/WS; anthropic-vertex = HTTP) | inert; drops with Root B |
| `golang.org/x/oauth2` v0.36.0 | base package: no hardcoded hosts, URLs from caller config; `/google` subpackage: `accounts.google.com`, `oauth2.googleapis.com` (`google.go:26-36`) + metadata reach (`default.go:253`) | no init(), no background goroutines, lazy refresh only | **KEEP the module** — Crush's MCP OAuth needs the base package (`internal/oauth/mcp/handler.go:23`, `internal/agent/tools/mcp/init.go:29`); only the `/google` subpackages go dead with the family |

**Init audit (family-wide):** every `func init()` enumerated — all are closure/socket-option/
protobuf-descriptor setup; **zero network I/O, zero goroutines at init**. Nothing here can egress
before provider construction.

**Cut set (both cuts required to drop `compute/metadata`):**
- **Cut A** (kills genai + cloud.google.com/go/{auth,civil}): remove `fantasy/providers/google` —
  five import sites: `coordinator.go:48`, `agent.go:33`, `message/content.go:14`, plus vendored
  `fantasy/providers/{openrouter,vercel}/language_model_hooks.go:12`.
- **Cut B** (kills google.golang.org/api, x/oauth2/google, oauth2adapt, grpc, s2a-go, gax-go):
  remove the Vertex branch of vendored `fantasy/providers/anthropic` — imports `anthropic.go:24,26`
  + block `anthropic.go:266-287`. Fantasy-side patch only; no Crush-side equivalent exists short of
  dropping the whole Anthropic provider.

### 4.2 AWS + Azure families

**Headline: no AWS or Azure egress can fire without an explicitly configured AND selected
Bedrock/Azure provider.** No init()-time probes, no background goroutines (verified: the only
inits precompute curves/RNG/clocks/transport structs).

- **Why present (AWS):** `fantasy/providers/anthropic/anthropic.go:21-22` unconditionally imports
  `anthropic-sdk-go/bedrock` + `aws-sdk-go-v2/config` (verified) — so the plain Anthropic provider
  drags in all 9 AWS modules + `smithy-go` even when Bedrock is never used. Crush itself never
  imports the AWS SDK; its Bedrock-eligibility check is env-var reads only
  (`internal/config/load.go:1057-1077`, no network).
- **The IMDS question:** the `169.254.169.254` / `[fd00:ec2::254]` probe
  (`feature/ec2/imds/api_client.go:59-60`) is three gates deep: (1) Crush never calls
  `LoadDefaultConfig`; (2) the only call site is behind `if a.options.useBedrock`
  (`fantasy/providers/anthropic/anthropic.go:288-295`, verified); (3) even then the IMDS hit is
  lazy — fires on first credential `Retrieve()`, i.e. when the first Bedrock request is signed.
  Timeouts tightly bounded (250ms dial / 500ms header / ≤1s backoff). `AWS_EC2_METADATA_DISABLED=true`
  hard-disables it (`api_client.go:54,84-88`).
- **sts/sso/ssooidc/signin:** pulled solely by `config`'s credential chain; each fires only for a
  profile with the matching keys (`config/resolve_credentials.go:163-205`); regional endpoint
  templates at each service's `internal/endpoints/endpoints.go:136`. `internal/v4a` is pure crypto.
- **`smithy-go`:** no endpoints, no dialing — protocol/middleware runtime. Inert.
- **Azure (`azcore` + `sdk/internal`):** single clean chain —
  `coordinator.go:46` (verified sole importer) → `fantasy/providers/azure/azure.go:11` →
  `openai-go/v3/azure`. The `login.microsoftonline.com` constants (`azcore/cloud/cloud.go:13-17`)
  are **never dereferenced**: they need a `TokenCredential` from `azidentity`, which is **not
  vendored at all**; Crush uses API-key auth exclusively (`fantasy/providers/azure/azure.go:55`).
  azcore's one init() builds an http.Transport, opens no connection. Dead weight — compiled in,
  zero reachable egress.
- **Cut set:** Azure = one Crush import (`coordinator.go:46` + its uses at `:414`, `:1006-1027`,
  `:1134-1135`) drops `azcore` + `sdk/internal` entirely. AWS = requires a **fantasy vendor patch**
  (strip `anthropic.go:288-306` + `providers/anthropic/bedrock.go` + the two imports); that single
  patch removes all 9 AWS modules + smithy-go. Bedrock's Crush-side wiring additionally spans
  `coordinator.go:47,1029-1056,1136-1137`, `agent.go:32,1488-1490`, and the whole
  `internal/agent/aws_sso_refresh.go` (shells out to the `aws` CLI on expired-credential errors).

### 4.3 Telemetry + protocol family

- **`posthog/posthog-go` v1.23.0 — the only real unsolicited egress in the dep tree.**
  Sole imports: `internal/event/{event,logger}.go` (+test). Crush overrides the SDK default to
  `https://data.charm.land` with a hardcoded key (`internal/event/event.go:17-18`, verified);
  wire call is `POST {endpoint}/batch/` (`posthog.go:1581`). The batching goroutine starts at
  client construction (`posthog.go:305`) but its 5s ticker no-ops on an empty queue
  (`posthog.go:1711`). **No feature-flag polling:** the `/flags` poller is constructed only when a
  secret key is set (`posthog.go:286-288`, verified) — Crush sets none. Gate coverage is total:
  `shouldEnableMetrics` (`internal/cmd/root.go:966-978`) guards all four `event.Init()` sites, and
  `Init` is the only assignment of the package client; every emitter early-returns on `client ==
  nil` (`event.go:72,85,100,123`). Disposition: PATCH OUT by default (extends the existing
  env/config disable with a build-time patch).
- **OpenTelemetry (`otel` v1.44.0, `otelgrpc`, `otelhttp`, `auto/sdk`) — INERT, confirmed.**
  Zero Crush imports; pulled only by the Google transports. **No exporter or SDK is vendored**
  (verified: `vendor/go.opentelemetry.io/` holds only `auto`, `contrib`, `otel` — no `otel/sdk`,
  no `exporters/*`), and nothing in the whole tree calls `otel.SetTracerProvider` — the global
  provider stays a no-op forever. Cannot export. DOCUMENT only; orphaned entirely by the Google cuts.
- **`modelcontextprotocol/go-sdk` v1.7.0 — KEEP.** Direct dep; transports stdio (local subprocess,
  zero network), http, sse (`internal/agent/tools/mcp/init.go:998-1155`); every URL is
  operator-supplied — **no hardcoded hosts anywhere in the SDK** (grep-verified by the reader).
  Empty MCP config ⇒ zero connections (`init.go:299-300`). OAuth only on 401/403 from a configured
  server; redirect listener is loopback.
- **`gorilla/websocket` v1.5.3** — sole importer in the entire tree: `genai/live.go` (verified),
  the Gemini Live API. No Crush/fantasy code reaches it. Dead code; orphaned by Cut A.
- **`golang.org/x/net` v0.57.0** — HTTP/2 plumbing + HTML parsing; no egress of its own. One
  inbound nuance: `x/net/trace`'s init registers `/debug/requests` on `http.DefaultServeMux`
  (`trace.go:120-132`) — unexposed (Crush's server builds its own handler); `-tags grpcnotrace`
  would drop it as belt-and-braces. KEEP.
- **`standard-webhooks/libraries`** — pure HMAC verification; only importer is
  `anthropic-sdk-go/betawebhook.go`, which nothing reaches. No network I/O at all. Inert.
- **`felixge/httpsnoop`** — only importer is `otelhttp/handler.go` (server side), which has zero
  call sites. Inert.
- **`go-vcr.v4` + `charm.land/x/vcr`** — test-only; `NewRecorder(t *testing.T, …)` (verified,
  `recorder.go:38`) is structurally uncallable from production code, so neither is linked into the
  shipped binary. (Present in `vendor/` because `go mod vendor` includes test deps of the main
  module's own packages.) Caveat for CI: running the agent tests airgapped with a missing cassette
  would attempt a real provider call.

### 4.4 LLM-provider core (openai-go, anthropic-sdk-go, fantasy, catwalk)

- **`openai-go/v3` v3.50.0 — ESSENTIAL, never patch.** This is the local-model transport:
  crushrc `--type llamacpp` → `coordinator.go:1154-1158` default branch →
  `buildOpenaiCompatProvider` → `fantasy/providers/openaicompat/openaicompat.go:56` →
  `fantasy/providers/openai/openai.go:166-189` (`option.WithBaseURL` at `:174`) →
  `openai.NewClient`. **Base-URL override proof (verified):** caller options are appended after
  defaults and win (`client.go:105-111`), and the hardcoded `api.openai.com` is only a
  *DefaultBaseURL* promoted when no explicit BaseURL was set
  (`internal/requestconfig/requestconfig.go:525-526`); fantasy always sets one
  (`providers/openai/openai.go:55` `cmp.Or(baseURL, DefaultURL)` — verified). So
  `api.openai.com` is unreachable on the llamacpp path. The SDK's `auth` package (Azure/GCP IMDS,
  `auth.openai.com` workload identity) is reachable only via `option.WithWorkloadIdentity`, which
  nothing calls. Caveat: `DefaultClientOptions` reads `OPENAI_BASE_URL` / `OPENAI_API_KEY` /
  `OPENAI_CUSTOM_HEADERS` etc. (`client.go:66-95`) — fantasy's explicit base URL still wins, but
  scrubbing `OPENAI_*` from the container env is cheap defense in depth.
- **`anthropic-sdk-go` v1.63.0** — not imported by Crush; sole importers are
  `fantasy/providers/{anthropic,bedrock}`. Endpoints: `api.anthropic.com` (default,
  `option/requestoption.go:601`), Bedrock (`bedrock/bedrock.go:237`), Vertex
  (`vertex/vertex.go:88,94`). Constructed at exactly one site —
  `fantasy/providers/anthropic/anthropic.go:311` (verified) — inside `LanguageModel()`, i.e. only
  when an anthropic/bedrock-typed provider is *selected*. Its five-step env credential chain
  (`ANTHROPIC_*`, federation token exchange) is dead here, and fantasy passes an explicit API key,
  which suppresses the profile/federation paths.
- **`charm.land/fantasy` v0.41.0** — the provider abstraction; all 8 provider subpackages
  vendored and imported by `coordinator.go:45-52`. Per-provider endpoint constants (verified):
  openrouter `https://openrouter.ai/api/v1` (`openrouter.go:20`), vercel
  `https://ai-gateway.vercel.sh/v1` (`vercel.go:19`), azure
  `https://{resource}.openai.azure.com/openai/v1` (`azure.go:75`), anthropic
  `https://api.anthropic.com` (`anthropic.go:118`), openai `https://api.openai.com/v1`
  (`openai.go:19`, always overridden here). The triage's `charm.land` hit is only a User-Agent
  string (`internal/httpheaders/httpheaders.go:12`) — fantasy contacts no Charm host. Its
  `init()`s register JSON unmarshalers only (pure `sync.Map`, no network). **Nothing fires without
  an explicitly configured provider of that type.** Separability: each provider is its own package;
  the anthropic package is NOT internally separable (direct + vertex + bedrock backends in one
  file) — hence the family cuts in §4.1/§4.2.
- **`charm.land/catwalk` v0.51.18** — imported by ~40 Crush files but almost entirely as a
  type/constant vocabulary. The module contains **exactly one HTTP call site**
  (`pkg/catwalk/client.go:47-79`, `GET {baseURL}/v2/providers`); its own default URL is
  `http://localhost:8080` (`client.go:15` — verified). The `catwalk.charm.land` host lives in
  **Crush's** code (`internal/config/load.go:37` — verified), consumed at
  `provider.go:60,189,200`. Startup fetch is dead under `option default-providers false`
  (`provider.go:186-188` returns before the client is constructed); the one ungated path is the
  manual `crush update-providers` command (`provider.go:60,67`). `pkg/embedded` is `//go:embed`
  JSON — the offline fallback; keep it.

### 4.5 Long tail (triage-flagged utility modules)

All 30 remaining flagged modules verified **NO-EGRESS** at source. Highlights (full verdicts with
`file:line` in the phase-2 reader outputs; representative evidence):

- **False positives of note:** `rivo/uniseg` (the "NETWORK" token is emoji table data —
  "THREE NETWORKED COMPUTERS"; its net/http hits are `//go:build generate` files);
  `nfnt/resize` (the "net" match is the *mitchellnetravali* filter name); `testify`
  (test-only, zero non-test importers, vendored because `go mod vendor` includes the main
  module's test deps).
- **Local-IPC, not egress:** `godbus/dbus` (unix-socket session bus for desktop notifications;
  its TCP transport is selected only by a `DBUS_SESSION_BUS_ADDRESS` scheme),
  `golang.design/x/clipboard` (X11/Wayland unix sockets), `Microsoft/go-winio` (named pipes),
  `atotto/clipboard` (shells out to `xsel`/`wl-copy`/`pbcopy`).
- **Egress attribution:** `html-to-markdown` and `goquery` are the *post-processing* stage of the
  fetch tools — Crush uses only their in-memory converters (`ConvertString`,
  `NewDocumentFromReader`); each lib's own URL-fetching entry point (`ConvertURL`,
  deprecated `NewDocument(url)`) has zero callers. The egress belongs to the tools (§4.6), not
  these libs — disabling the libs would not disable the fetch.
- **Dead codegen halves:** `go-openapi/{spec,swag}` (remote `$ref` loader exists but only the
  never-invoked `swag init` parser half reaches it), `swaggo/*` (runtime registers an embedded
  swagger.json served over Crush's **unix-socket** listener; UI assets embedded, no CDN).
- **⚠ LOUD FLAG — `kaptinlin/jsonschema` v0.9.8: dormant HTTP `$ref` fetcher, one API call from
  live.** `NewCompiler()` unconditionally registers http/https loaders
  (`compiler.go:397-425` — verified); any schema with an absolute `"$ref": "https://…"` is fetched
  at compile time, no allowlist. Unreachable today **only** because Crush never calls fantasy's
  `GenerateObject`/`StreamObject` (grep of `internal/` for `fantasy/object|fantasy/schema` is
  empty — verified). If a future Crush adopts structured output, a provider- or model-controlled
  schema becomes an SSRF primitive. **Re-check this on every `CRUSH_TAG` bump.**
- **⚠ Build-tag-conditional — `golang.org/x/mobile`:** contains a real downloader
  (`gl/dll_windows.go:22-25`, `http.Get` of `dl.google.com/go/mobile/angle-…` — verified) but the
  only importer chain starts at an `//go:build android` file and Crush's clipboard excludes
  android (`internal/clipboard/clipboard_supported.go:1` — verified). Not compiled; would activate
  only if an android/shiny target were ever added.
- **`google/jsonschema-go`** (used by the MCP SDK for tool schemas) has **no net/http at all** —
  MCP-supplied schemas cannot trigger a fetch. Contrast with kaptinlin above.

### 4.6 Crush's own code — feature → egress map (context for the patches)

From the feature-map reader (verified on key lines). Crush's own external-endpoint surface:

- **Six default-enabled network tools** (all in `allToolNames()`,
  `internal/config/config.go:787-818`): `web_search` (DuckDuckGo Lite,
  `tools/search.go:68` — verified), `web_fetch` (arbitrary URL), `agentic_fetch` (spawns a
  sub-agent holding web_search/web_fetch/sourcegraph, `agentic_fetch_tool.go:165-172`), `fetch` +
  `download` (arbitrary URL GET, scheme-guarded), `sourcegraph` (hardcoded
  `https://sourcegraph.com/.api/graphql`, `tools/sourcegraph.go:113` — verified). A no-patch off
  switch exists (`options.disabled_tools` via the crushrc `deny` verb) but only filters the tool
  list — the code stays linked.
- **Telemetry/update/catalog** — as previously audited in `tasks/disable-crush-telemetry.md`;
  re-verified against this checkout with two additions: (1) the `customProvidersOnly` gate also
  suppresses the **hyper** catalog fetch (`internal/config/provider.go:206-208`) — stronger than
  documented; (2) **one ungated catwalk path remains**: `crush update-providers`
  (`provider.go:60`, explicit user command) can still reach `catwalk.charm.land`. Minor line drift
  in the old doc: `provider.go:175,186-188` (was 176,184-185), `app.go:798` (was 797).
- **Copilot + Hyper OAuth flows** (`internal/oauth/{copilot,hyper}/`) — github.com/hyper.charm.land
  device flows; reachable only via explicit `crush auth` / a hyper provider. Dormant here.
- **The local-model path (must survive all patches):** crushrc `--type llamacpp` →
  `internal/shellconfig` → `internal/config` → `internal/discover/llamacpp.go` enricher →
  `coordinator.go:1156-1162` `default:` branch (verified) → `buildOpenaiCompatProvider`
  (`coordinator.go:969-1004`) → `fantasy/providers/openaicompat` → `openai-go/v3` → the socket.
  Files that must stay untouched: `internal/shellconfig/*`, `internal/config/*`,
  `internal/discover/*`, `coordinator.go` openaicompat path, `internal/log/http.go`,
  `internal/message/content.go`. Note `fantasy/providers/openai` also cannot be dropped
  (`message/content.go` persists its reasoning-metadata type), and the shared options case
  `coordinator.go:414` (`case openai.Name, azure.Name:`) must be edited, not deleted, by the Azure
  patch.

## 5. Flag index

One row per decision flag — implemented and wired (2026-08-29) through
`client/entrypoint/03-build-crush.sh` (flag-guarded `git apply --unidiff-zero`, both build modes),
`client/Dockerfile` (ARGs, semantic defaults), and `client/Makefile` (`?=` defaults +
`--build-arg` threading). Keep this table matching that wiring:

| flag | default | patch file | effect when `1` |
|---|---|---|---|
| `PATCH_OUT_WEB_TOOLS` | `0` (kept) | `no-web-tools.patch` | strips web_search/web_fetch/agentic_fetch/fetch/download tools |
| `PATCH_OUT_SOURCEGRAPH` | `0` (kept) | `no-sourcegraph.patch` | strips the sourcegraph.com code-search tool |
| `PATCH_OUT_UPDATE_CHECK` | `1` (out) | `crush-no-update-check.patch` | no startup api.github.com release check |
| `PATCH_OUT_TELEMETRY` | `1` (out) | `no-telemetry.patch` | PostHog/data.charm.land unreachable at build level |
| `PATCH_OUT_GOOGLE_PROVIDER` | `1` (out) | `no-google-provider.patch` | Google/Vertex providers gone; genai/gcloud/grpc/otel families uncompiled |
| `PATCH_OUT_BEDROCK_AWS` | `1` (out) | `no-bedrock-aws.patch` | Bedrock gone; all AWS SDK modules uncompiled |
| `PATCH_OUT_AZURE` | `1` (out) | `no-azure.patch` | Azure provider gone; azcore uncompiled |
| `PATCH_OUT_UPDATE_PROVIDERS_CMD` | `1` (out) | `no-update-providers-cmd.patch` | removes the ungated catwalk fetch command |
| `PATCH_OUT_OPENROUTER` | `1` (out) | `no-openrouter.patch` | openrouter.ai provider gone |
| `PATCH_OUT_VERCEL` | `1` (out) | `no-vercel.patch` | Vercel AI-gateway provider gone |
| `PATCH_OUT_HYPER` | `1` (out) | `no-hyper.patch` | hyper.charm.land provider, OAuth, and x-crush-id header gone |
| `PATCH_OUT_COPILOT` | `1` (out) | `no-copilot.patch` | GitHub Copilot device-flow OAuth + provider case gone |
| `CRUSH_AT_IMPORT` | `1` (applied) | `crush-at-import.patch` | (existing feature patch, unchanged semantics) |

Patches sharing files must remain **independently applicable AND reversible in any flag
combination** — proven by `tools/sweep_egress_patch_combos.sh`
(42 combinations, byte-identical restore). Authoring invariants for any future patch: use
zero-context hunks where patches share a file, and **never bare-delete a line — replace it with a
unique marker comment** so the hunk is anchored in BOTH directions (a bare deletion's reverse is
an unanchored insertion, which mis-placed re-added import lines until fixed on 2026-08-29). Apply
with `git apply --unidiff-zero`, in the canonical order listed in `03-build-crush.sh`.

## 6. Airgap posture summary

At the audited tag, with the recommended defaults applied and the standing config
(`option default-providers false`, `CRUSH_DISABLE_METRICS=1`, `DO_NOT_TRACK=1`, providers pointed
at `127.0.0.1:8080`):

- **Unsolicited egress: zero.** The only unsolicited path in the entire 213-module tree —
  PostHog → `data.charm.land/batch/` — is triple-killed (env, config, D4 patch); the update check
  is patched out (D3). Nothing else in any dependency fires without explicit configuration or an
  explicit user/model action: **no init()-time network, no init()-time goroutines anywhere in the
  audited families** (enumerated in §4.1–4.3).
- **Remaining intentional surface:** the five web tools (D1) + sourcegraph (D2) — user/model-
  initiated, fail gracefully offline — and any MCP server the operator explicitly configures.
- **Compiled-out by default:** the Google, AWS, and Azure SDK families (D5–D7) — removing every
  ambient-probe risk class (GCE metadata `169.254.169.254`/DNS, AWS IMDS, ALTS/S2A) from the
  binary rather than merely gating it — plus the OpenRouter/Vercel/Hyper/Copilot provider wirings
  and OAuth flows (D9–D12).
- **Local-model link:** unaffected by every flag combination — the llamacpp → openaicompat →
  openai-go chain is documented in §4.4 with its base-URL override proof.
- **Watch items on every `CRUSH_TAG` bump:** the kaptinlin/jsonschema dormant `$ref` fetcher
  (§4.5) — becomes live if Crush adopts fantasy's structured-output API; the x/mobile downloader
  (build-tag-gated); and re-run the whole triage (`tools/triage_dependency_egress.py`).
- **Defense-in-depth env for the image (optional, cheap):** keep `OPENAI_*`, `ANTHROPIC_*`,
  `GOOGLE_*`, `AWS_*` out of the container environment; `AWS_EC2_METADATA_DISABLED=true` if D6 is
  ever flipped off.

## Cross-links

- `tasks/archive/2026/08/29/audit-dependency-network-egress.md` — the investigation task (policy, decisions, method).
- `tasks/disable-crush-telemetry.md` — the prior audit of Crush's own code (the four charm.land /
  github.com vectors).
- `tasks/decide-egress-verification.md` — whether to add a runtime egress check enforcing this audit.
- `tools/triage_dependency_egress.py` — the phase-1 scanner.
