# Dependency network audit — every vendored Go module, classified for airgap egress

**Status:** IN PROGRESS — skeleton + phase-1 triage done; phase-2 deep audit underway
(2026-08-29). Do not treat unfinished sections as findings.
**Audited version:** Crush **v0.89.0** (commit `ba531a409ab68f91144c80eafae8b952daa35a0d`), the
`CRUSH_TAG` pin in `client/Makefile` — 213 vendored modules per `vendor/modules.txt`.
**Re-audit on any `CRUSH_TAG` bump.** Re-sync check: compare
`git -C client/vendor/crush rev-parse HEAD` against the SHA above; if they differ, this doc is stale.
**Produced by:** `tasks/audit-dependency-network-egress.md` (the investigation task — method,
policy, and decision history live there). Regenerate the phase-1 table with
`python3 tasks/adhoc/audit-dependency-network-egress/triage_modules.py` from the repo root.

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
**Pending phase 2.** Each entry will carry: decision name · `PATCH_OUT_<X>` flag (default `0` =
kept) · patch file · endpoints (`file:line`) · why kept · offline behavior.

## 2. Removed / patched out by default

**Pending phase 2.** Each entry: decision name · flag (default `1` = patched out) · patch file ·
what it neutralizes (`file:line`) · rationale.

Settled by the maintainer 2026-08-29 (details pending the deep audit):

- **Cloud/GenAI SDK family** (`cloud.google.com/*`, `google.golang.org/genai`, likely the AWS/Azure
  SDK families — same class, to be confirmed) — REMOVE by default via import-dropping Crush
  patch(es); out-of-design for a local-model-first setup.
- **Unsolicited phone-home in any dep** — PATCH OUT by default, one patch + one flag per concern.
- **Web search** (if present in v0.89.0 — being verified) — KEEP by default
  (`PATCH_OUT_WEB_SEARCH ?= 0`).

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

**Pending phase 2** (per-module: why present / import chain · behavior `file:line` · activation
condition · disposition · patch plan).

## 5. Flag index

**Pending** — one row per `PATCH_OUT_<X>` build-arg: default, patch file, one-line effect. Must
match what `client/entrypoint/03-build-crush.sh` actually wires.

## 6. Airgap posture summary

**Pending phase 2.**

## Cross-links

- `tasks/audit-dependency-network-egress.md` — the investigation task (policy, decisions, method).
- `tasks/disable-crush-telemetry.md` — the prior audit of Crush's own code (the four charm.land /
  github.com vectors).
- `tasks/decide-egress-verification.md` — whether to add a runtime egress check enforcing this audit.
- `tasks/adhoc/audit-dependency-network-egress/triage_modules.py` — the phase-1 scanner.
