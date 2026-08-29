# Audit ALL vendored Go dependencies for network / phone-home (airgap hardening)

**Status:** in progress — go-ahead given 2026-08-29 (William Emerison Six <billsix@gmail.com>).
**Priority:** 4
**Difficulty:** 7
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

**Decisions confirmed 2026-08-29 (William Emerison Six <billsix@gmail.com>)** — every open question
was put to the maintainer explicitly, including the "settled" ones; all four answered:

1. **Web search: KEEP by default** — `PATCH_OUT_WEB_SEARCH ?= 0`, patch present but off.
2. **Cloud/GenAI SDKs: REMOVE by default** — `PATCH_OUT_CLOUD_SDKS ?= 1`, import-dropping Crush patch.
3. **Dep phone-home: PATCH OUT by default** — one patch + one `PATCH_OUT_<concern> ?= 1` flag per
   finding. Provably-inert deps (exporter-less OTel): DOCUMENT only, no flag (nothing to toggle).
4. **Patch model: full revision confirmed** — vendor the complete UNPATCHED tree; ALL patches
   (including the two existing ones) applied at build time in `03-build-crush.sh`, flag-guarded, both
   paths. `crush-no-update-check` gets `PATCH_OUT_UPDATE_CHECK ?= 1`; `crush-at-import` keeps
   `CRUSH_AT_IMPORT ?= 1`.

**Standing principle behind all four (maintainer, 2026-08-29): every decision is a flag with a
default — nothing is irreversible, so defaults are starting points, not commitments.** Borderline
cases default to KEEP + FLAG and are called out in the reference doc for later review.

**Verification: split out** — deferred to `tasks/decide-egress-verification.md` (decide *whether* a
runtime egress check is needed at all, after the audit's findings exist). The "Verification /
hardening idea" section below is the design discussion that task inherits; open question 3 is
thereby answered.

## BLUF

Audit all ~213 vendored Go dependencies (not just Crush's own code) for **external** network / phone-home
behavior, and neutralize it for the airgap build via a **flag-driven, one-patch-per-decision** system:
KEEP genuinely-useful online features (web search), PATCH-OUT unsolicited phone-home, REMOVE
out-of-design networky deps (cloud/GenAI SDKs) — never touching the essential local-model link
(`127.0.0.1:8080`). Deliverable: a verbose `tasks/reference/dependency-network-audit.md` with every
decision named. Done = that reference doc + the per-decision patches/flags wired into the vendor+build
flow.

## Context

Read these first:

- **`tasks/disable-crush-telemetry.md`** — the prior audit of **Crush's OWN code** (four vectors:
  PostHog `data.charm.land`, GitHub update-check `api.github.com`, `catwalk.charm.land` providers,
  `hyper.charm.land`), each with source `file:line` and the chosen fix. **This task EXTENDS that to the
  ~213 vendored dependencies** it did not cover.
- **`tasks/archive/2026/08/29/extract-crush-build-to-script.md`** — the current build + vendoring flow,
  the Go/vendor mechanics, and the patch invariants. **This task REVISES that design** (see "Patch
  system": vendor complete + patch at build time). Read it to know what you're changing *from*.
- **The machinery files (read them directly):**
  - `client/entrypoint/03-build-crush.sh` — the current Crush build (vendored vs clone dispatch).
  - `client/entrypoint/vendor/vendor-crush.sh` — the current vendoring (currently clone → **apply
    patches** → `go mod vendor`; this task stops it pre-patching).
  - `client/Dockerfile` — the build `RUN`, the `CRUSH_*` ARGs, `ENV GOBIN=/usr/local/bin`, the `COPY`s.
  - `client/Makefile` — `CRUSH_TAG`/`CRUSH_VENDORED`/`CRUSH_AT_IMPORT`/`VENDOR_TOOLS`, `VENDOR_DIR`,
    `CRUSH_VENDOR_FLAGS` (the `--volume …/vendor/crush:ro --build-arg CRUSH_VENDORED=1`), the
    `image`/`vendor` targets.
  - `client/patches/` — the existing `crush-no-update-check.patch` + `crush-at-import.patch`; the
    template + naming pattern for the new per-concern patch files.
  - `tasks/reference/architecture.md` — the two-halves (server on Mac / client container) overview +
    the vendoring/airgap design.
- **The dependency source to audit** = the **vendored tree on disk**: `client/vendor/crush` (Crush's own
  source) and `client/vendor/crush/vendor/` (all deps; `vendor/modules.txt` lists the ~213 modules).
  It is **gitignored** — produced by `make vendor` / `./vendor.sh`. If absent, regenerate it first. It is
  pinned to **`CRUSH_TAG` (currently `v0.89.0`)** in `client/Makefile`; the audit is against that tag —
  **re-audit on any bump.**
- **The whole project runs against a LOCAL model** (llama.cpp on the Mac, reached at `127.0.0.1:8080`
  via an SSH tunnel + `--network=host`). See the FOUNDATIONAL rule in "Why": local/loopback is
  essential, only external egress is in scope.

## Why

`disable-crush-telemetry.md` audited **Crush's own source** (the four charm.land/github vectors) but
**not** its **213 vendored Go modules**. Since this image is built and run on **airgapped** boxes, any
dependency that reaches the network is at best noise/latency (fails after a timeout) and at worst a
leak on a box with partial connectivity.

**FOUNDATIONAL — local/loopback is the ESSENTIAL core, never a target (Bill, 2026-08-29).** The whole
point of this setup is Crush talking to the **local model** at **`127.0.0.1:8080`** (the SSH-forwarded
port, reached via `--network=host`). Connections to **loopback / localhost / the configured local model
endpoint** are the intended, required traffic — **never flag, patch, or remove them.** The audit is
about **EXTERNAL / remote egress only**; every connection must first be classified **local vs external**,
and only external is in scope. (This also means the egress *verification* can't use `--network=none` —
it would kill the local-model link; see "Verification".)

**Beyond that, the axis is NOT "network vs no-network" — it's *unsolicited phone-home* vs
*user-initiated features that are legitimately useful online*.** Bill's policy (2026-08-29), in priority
order:

- **KEEP + FLAG — legitimate network functionality a user would want on a home/online network.**
  Example: Crush's **web search** tool. The user triggers it deliberately; on an airgapped box it just
  fails/degrades gracefully when they try it (they know they're offline), so **do NOT cripple it**. But
  it MUST be **flagged prominently at the TOP of the reference doc** — a "what network functionality we
  deliberately LEFT IN, and why" section — so the reader sees the intentional network surface first, and
  the airgap operator knows what will (harmlessly) reach for the network.
- **REMOVE — networky code for functionality this setup won't use, even online.** Patch it out so it
  isn't even in the vendored tree. Example: the Google Cloud / GenAI SDKs — Bill's explicit call
  (2026-08-29): "I am never going to use those on an airgapped network," and this project is
  local-model-first (Muse Glimmer, provider catalog suppressed), so the cloud-provider SDKs aren't a
  feature we'd use at home either → remove.
- **PATCH OUT — unsolicited phone-home / telemetry / update checks**, whether airgapped or not (never
  wanted). Keep any surrounding functionality; kill just the egress. (This is what
  `disable-crush-telemetry.md` did for Crush's own code; extend the same to any dep that does it.)
- **DOCUMENT — network-capable but never activated** (no exporter/endpoint, gated off): no code change,
  record the source-level reasoning.

**The judgment call per dep/feature: "would the user plausibly use this network feature on a home
network?"** Yes → keep + flag (web search). No, it's unsolicited → patch out (telemetry). No, it's a
feature outside this local-first design → remove (cloud SDKs). **Use discretion on the borderline
cases and flag them for Bill; when unsure, prefer KEEP + FLAG over removing something potentially
useful** — the airgap penalty for a kept-but-unused network feature is only a graceful failure, whereas
wrongly removing a useful online feature is real lost functionality.

The deliverable is a **verbose reference doc** (`tasks/reference/dependency-network-audit.md`) — a
standing, per-module record. This task tracks the *investigation*; the reference doc holds the
*findings* (they outlive the task).

**Keep this coherent with vendoring** — the whole point. See "Patch system" for the model: **vendoring
carries the COMPLETE, unpatched tree** (all deps present, so any decision is reversible on the airgap
box) and **the decisions are applied as patches at BUILD time** (in `03-build-crush.sh`, flag-guarded,
both paths) — NOT baked in at vendor time. And it must be **re-audited on every `CRUSH_TAG` bump** — the
dep set changes with the version.

## Scope & method

Source of truth = the **vendored tree at the pinned tag** (`client/vendor/crush` + its `vendor/`,
currently `CRUSH_TAG=v0.89.0`) — that's exactly what an airgap `make image CRUSH_VENDORED=1` builds.

Tiered, so 213 modules stays tractable:

1. **Triage all 213** (`vendor/modules.txt`) into *no-network* vs *network-capable*. Most are pure
   utility (encoding, `segmentio/asm`, `golang.org/x/sys` syscall wrappers, UI libs) with no net access.
   Cheap signals for the network-capable subset: imports of `net`, `net/http`, `google.golang.org/grpc`,
   `crypto/tls`; `http.Get/Post`/`http.NewRequest`/`grpc.Dial`; hardcoded `https://`/host literals;
   known SDK families (analytics: posthog/segment-analytics/amplitude/rudderstack/sentry; cloud:
   `cloud.google.com/*`, `aws-sdk-go`, `Azure/*`; observability: `go.opentelemetry.io/*`; auto-update).
2. **Deep-audit only the network-capable subset.** For each, in the reference doc, record:
   - module + version, and **why it's present** — a direct Crush dep, or transitive via which feature
     (e.g. OTel is pulled by the Google GenAI gRPC instrumentation);
   - **network behavior**, source-cited (`file:line`): what host/endpoint, what payload, transport;
   - **activation condition** — always on? only if a provider/env is configured? gated by a flag? (this
     decides "inert" vs "must act");
   - **disposition** per the policy above + the concrete patch/removal plan.
3. **Known starting points** (from the 2026-08-29 shallow scan — verify at source, don't trust the grep):
   - `posthog-go` — analytics SDK; already gated by Crush's `shouldEnableMetrics` (env disable). Confirm
     no *other* call path reaches it.
   - **OpenTelemetry** (`go.opentelemetry.io/otel` + otelgrpc/otelhttp contrib) — transitive
     instrumentation; exports nothing without an OTLP exporter/endpoint. Verify Crush never configures
     one; if it's only there for the Google SDK, removing that SDK likely drops it too.
   - **Google Cloud / GenAI** (`cloud.google.com/go/auth`, `googleapis/gax-go`, `genai`) — the headline
     "remove it" candidate: only active with a Gemini/Google provider, which the airgap setup never has.
   - `segmentio/asm`, `segmentio/encoding` — utility libs (SIMD/JSON), **not** analytics. Note as
     no-action so they're not mistaken for phone-home.

## Disposition mechanics (how removal/neutralization actually works with Go + vendoring)

**All of this happens at BUILD time from the complete vendored tree (see "vendor everything" in the
Patch system section) — NOT at vendor time.** `go mod vendor` runs ONCE on unpatched source; no
`go mod tidy` (it would drop deps we want kept in the tree for reversibility).

- **"Removing" an unused-but-networky dep = a *Crush source* patch that drops its import**, applied at
  build time (`git apply` in `03-build-crush.sh`, flag-guarded). Go compiles in everything **imported**;
  drop the import (e.g. remove the Gemini/Google provider registration + its imports) and the module
  isn't compiled into the binary — its source stays **unused in `vendor/`** (harmless; `go build
  -mod=vendor` ignores unimported vendored modules). Reversible: flag off → import back → compiled in.
- **Neutralizing a call in a *used* dep** = patch that dep's vendored source (`vendor/<module>/…`) at
  build time. `-mod=vendor` trusts `vendor/` (no re-hash), so it builds; re-verify per `CRUSH_TAG` bump.
  (This is the airgap-clean path. The online/non-vendored build patches the freshly-cloned tree the same
  way; it can't patch a *proxy-cached* module without a `go.mod replace`, but it isn't using one.)
- **Prefer an import-dropping *Crush* patch over a vendored-*dep*-source patch** where possible: it's one
  file touching Crush's own tree (not a third-party subtree), and it reads as "this feature is off,"
  which is easier to explain and revert.

## Patch system — one patch file + one named, defaulted, reversible flag per decision (Bill, 2026-08-29)

Every neutralizable concern is its **own unit**, so each can be explained, defaulted, and reverted
independently:

- **One patch file per concern** (`client/patches/<concern>.patch`) — granular, never a bundled
  mega-patch. Web search gets a patch too, even though it's kept by default.
- **One build-arg FLAG per patch, with a documented default** (chosen over commenting-out — it's the
  repo's idiom, toggles at `make image FLAG=…` with no source edit, shows in `make help`, and is
  cleanly reversible). The **default encodes the disposition**:
  - `1` = **patched out by default** → phone-home / telemetry / update-check, and out-of-design networky
    deps (cloud/GenAI SDKs).
  - `0` = **kept by default, patch present but OFF** → genuinely-useful online features (e.g.
    `PATCH_OUT_WEB_SEARCH ?= 0`). Flip to `1` to strip it for a hardened/airgap-only build.
- **Vendor the COMPLETE, UNPATCHED source + ALL deps; apply patches at BUILD time (Bill, 2026-08-29 —
  this REVISES the current model).** So the airgap box can build **any** flag configuration and revert
  any decision, from one complete tree:
  - **`entrypoint/vendor/vendor-crush.sh` applies NO patches** — just `git clone` (unpatched) +
    `go mod vendor` (the full dep set). The vendored tree is the complete airgap source-of-truth.
  - **ALL patches move to build time**, in `entrypoint/03-build-crush.sh`, flag-guarded, applied in
    **both** the vendored and non-vendored paths — including the existing `crush-no-update-check` /
    `crush-at-import` patches (which currently bake at vendor time). Each is
    `if [ "$PATCH_OUT_X" = "1" ]; then ( cd /tmp/crush && git apply /patches/<concern>.patch ); fi`.
    The Dockerfile/Makefile thread the flags through (ARG → passed explicitly to the script).
  - **Go mechanics that make this safe:** `go build -mod=vendor` is fine with an **unused** vendored
    module (it checks `vendor/modules.txt` vs `go.mod`, which we don't `tidy`, not vs actual imports) —
    so a removal patch that drops an import just leaves that dep's source sitting **unused** in
    `vendor/`, not compiled into the binary; flip the flag off and it's back. No `go mod tidy` at
    vendor time. (The existing patches only add stdlib imports / remove imports — never a new module
    dep — so the complete unpatched vendor tree covers every flag combo.)
  - **Consequence — the current "vendored branch applies no patches" asymmetry FLIPS.** Implementing
    this task rewrites `vendor-crush.sh` (stop pre-patching) and `03-build-crush.sh` (apply the
    flag-selected patches for the vendored path too). The extract-task's patch-asymmetry note is
    superseded here. Doesn't affect the current in-flight build (that's the old model).
- **Keep the two build paths' defaults in lockstep** so an online build and a vendored build with the
  same flags produce the same Crush.
- **Optional convenience** (only if the flag count gets unwieldy): a single meta/profile flag (e.g.
  `AIRGAP_HARDEN=1`) that flips the "kept" ones to patched-out — but the per-patch flags stay the source
  of truth. Don't let a profile hide individual decisions.

## Deliverable

- `tasks/reference/dependency-network-audit.md` — **verbose** (as long as needed). **Every decision is
  NAMED and carries its flag, default, patch file, and rationale** — so it can be explained to someone
  else and reverted later. Each decision entry (in sections 1 and 2 below) records:
  **decision name · disposition (KEEP / PATCH-OUT / REMOVE / INERT) · `PATCH_OUT_<X>` flag + default ·
  `client/patches/<concern>.patch` · what it contacts (source `file:line`) · rationale · offline behavior.**
  Structure:
  1. **TOP: "Network functionality intentionally KEPT (and why)."** The first thing a reader sees — the
     deliberate online features left in (web search, and any other user-initiated network use), each as a
     **named decision** (flag defaulting to `0` = kept, patch present-but-off), with why it's kept and how
     it degrades offline. This is the "what we left in and why" lead Bill asked for.
  2. **Removed / patched-out** — the phone-home and out-of-design networky deps, each a **named decision**
     (flag defaulting to `1` = patched out) with its patch file and what it neutralizes.
  3. **Triage table of all 213 modules** — no-network vs network-capable, one line each (so nothing is
     silently unexamined).
  4. **Deep entry per network-capable module** — behavior (`file:line`), activation condition,
     disposition, patch plan.
  5. **Flag index** — a table of every `PATCH_OUT_<X>` flag: default, patch file, one-line effect (the
     single place to see all the knobs), matching the flags wired into `03-build-crush.sh`.
  6. **Airgap posture summary.**
  Pinned to the audited `CRUSH_TAG`, with a re-audit-on-bump note.
- The concrete patches/removals become their own follow-on implementation task(s) once the analysis is
  in — this task is the analysis + the reference doc.

## Verification / hardening idea (propose, not required)

A standing **egress check** would make the audit *enforced*, not just documented — but it must **permit
the local model and block only external** egress (the local link is the point of the tool):

- **`--network=none` is WRONG here** — it gives the container an isolated loopback, so under this setup's
  `--network=host` it severs Crush's path to the host's `127.0.0.1:8080` (the local model). Crush
  couldn't work, so it would prove nothing.
- **Correct approach:** run Crush normally (talking to the local model) under **`strace -f -e
  trace=connect,sendto`** or a **`tcpdump`** on the bridge, exercise the flows (start, a chat, and each
  KEPT online feature like web search), and assert **no connection to any host other than the local
  model endpoint** — i.e. flag any **non-loopback / non-local-model** destination. That's the real
  "unexpected external egress" test, a superset of the two-host check in `disable-crush-telemetry.md`.
- **Or a firewall variant:** allow egress only to the local model endpoint (loopback / the forwarded
  port) and DROP the rest (`nftables`/`iptables`), then confirm Crush still serves and nothing errors on
  a blocked external attempt. Heavier, but genuinely enforced.
- Decide whether this becomes a `make` target or a manual real-machine check. Either way it is
  **real-machine** (the ~22 GB image + a live local model), not an in-sandbox check.

## Open questions

1. **The keep-vs-remove boundary** (mostly settled by the policy above): KEEP + FLAG genuinely-useful
   online features (**web search** — settled keep); REMOVE phone-home and out-of-design networky deps
   (**cloud/GenAI SDKs** — settled remove, Bill's call). The remaining discretion is the *borderline*
   features — the audit will **use discretion and flag each borderline one in the reference doc for Bill
   to confirm**, defaulting to KEEP + FLAG when unsure. (Provably-inert transitive deps like exporter-less
   OTel: document-but-leave, unless removing the feature that pulls them drops them for free.)
2. **Confirm the flag/patch shape** — one `client/patches/<concern>.patch` + one `PATCH_OUT_<X>` build-arg
   per decision, applied at **build time** in `03-build-crush.sh` (NOT `vendor-crush.sh`, which now just
   vendors the complete unpatched tree), flag-guarded, both build paths. (This is the recommended
   design in "Patch system"; confirm before implementing, since it rewrites both scripts.)
3. **Add the egress check** (`strace`/`tcpdump` for any **non-local** destination, or a firewall that
   permits only the local model endpoint — NOT `--network=none`, which would sever the model) as part of
   this task, or a separate follow-on? It's real-machine either way.

## Cross-links

- `tasks/disable-crush-telemetry.md` — the Crush-own-code audit this **extends to the dependencies**.
- `tasks/archive/2026/08/29/extract-crush-build-to-script.md` — the build/patch/vendor machinery this
  task REVISES (its "vendored branch applies no patches" asymmetry is superseded here — see "Patch system").
- `tasks/verify-vendored-airgap-rebuild.md` — the airgap build the flag-selected patches feed into.
- `entrypoint/03-build-crush.sh` — where ALL the flag-guarded patches get applied at build time (both
  paths); `entrypoint/vendor/vendor-crush.sh` — reworked to vendor the COMPLETE unpatched tree (no
  patching).
