# Audit ALL vendored Go dependencies for network / phone-home (airgap hardening)

**Status:** complete
**Completed:** 2026-08-29
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

## What this did

Audited all ~213 vendored Go modules of Crush (pinned `CRUSH_TAG=v0.89.0`) for external network /
phone-home behavior, extending `tasks/disable-crush-telemetry.md` (which covered only Crush's own
code). Wrote the findings to `tasks/reference/dependency-network-audit.md`: all 213 modules triaged,
66 deep-audited, decisions D1–D12 named, each with a flag, default, patch file and rationale. The
patches and flags were implemented in `tasks/archive/2026/08/29/implement-egress-patch-flags.md`; the
runtime-verification question was split out to `tasks/archive/2026/09/22/decide-egress-verification.md`.

## Policy (William Emerison Six <billsix@gmail.com>, 2026-08-29)

- **Local/loopback traffic is the essential core, never a target.** Crush talking to the local model
  at `127.0.0.1:8080` (SSH tunnel + `--network=host`) is the point of the setup. Only external egress
  was in scope; every connection was first classified local vs external.
- **The axis is unsolicited phone-home vs useful user-initiated features**, not network vs no-network:
  - **KEEP + FLAG**: features a user would want online (web search). Listed first in the reference doc
    as "network functionality intentionally kept", since offline they only fail gracefully.
  - **REMOVE**: networky code this setup will not use even online (Google Cloud / GenAI SDKs; "I am
    never going to use those on an airgapped network").
  - **PATCH OUT**: telemetry, update checks, phone-home.
  - **DOCUMENT**: network-capable but never activated (exporter-less OpenTelemetry), no flag.
- **Borderline cases default to KEEP + FLAG**: a kept-but-unused feature costs only a graceful
  failure, while wrongly removing one loses functionality.
- **Standing principle: every decision is a flag with a default**, so nothing is irreversible.

## Decisions (confirmed by the maintainer 2026-08-29)

1. **Web search: kept by default** (`PATCH_OUT_WEB_SEARCH ?= 0`, patch present but off).
2. **Cloud/GenAI SDKs: removed by default** (`PATCH_OUT_CLOUD_SDKS ?= 1`, an import-dropping Crush patch).
3. **Dependency phone-home: patched out by default**, one patch + one `PATCH_OUT_<concern> ?= 1` flag
   per finding; provably inert deps documented only.
4. **Patch model revised**: vendor the complete, unpatched tree (`client/entrypoint/vendor/vendor-crush.sh`
   applies no patches; `go mod vendor` once, no `go mod tidy`), and apply ALL patches at build time in
   `client/entrypoint/03-build-crush.sh`, flag-guarded, in both the vendored and online paths. The
   existing patches got flags too: `crush-no-update-check` → `PATCH_OUT_UPDATE_CHECK ?= 1`,
   `crush-at-import` → `CRUSH_AT_IMPORT ?= 1`. This superseded the "vendored branch applies no patches"
   asymmetry in `tasks/archive/2026/08/29/extract-crush-build-to-script.md`.
5. **Follow-up borderline calls**: sourcegraph kept by default (`PATCH_OUT_SOURCEGRAPH ?= 0`, D2);
   `crush update-providers` patched out (`PATCH_OUT_UPDATE_PROVIDERS_CMD ?= 1`, D8);
   openrouter/vercel/hyper/copilot patched out by default, one flag + patch each (D9–D12), overriding
   the audit's initial document-only lean.

Rationale for the mechanics: Go compiles only what is imported, so a "removal" is a Crush patch that
drops an import; the module's source stays unused in `vendor/` and `go build -mod=vendor` accepts it
(it checks `vendor/modules.txt` against the untidied `go.mod`). Flag off restores it. An
import-dropping Crush patch was preferred over patching third-party source in `vendor/`. One patch
file per concern (`client/patches/<concern>.patch`), never a bundled mega-patch; a flag rather than
commenting-out because it is the repo's idiom, shows in `make help`, and toggles without a source edit.

## Method

Triaged every module in `vendor/modules.txt` into no-network vs network-capable (imports of `net`,
`net/http`, `grpc`, `crypto/tls`; host literals; known SDK families), then deep-audited the
network-capable subset: version, why present (direct or via which feature), source-cited behavior,
activation condition, disposition. Starting leads from a shallow scan (posthog-go gated by
`shouldEnableMetrics`; OpenTelemetry with no exporter; Google Cloud / GenAI; `segmentio/asm` and
`segmentio/encoding` as plain utility libs) were verified at source. The audit must be redone on every
`CRUSH_TAG` bump.

## Verification

Runtime egress verification was not part of this task. The design notes it handed to
`tasks/archive/2026/09/22/decide-egress-verification.md`: `--network=none` is wrong (under
`--network=host` it severs the local-model link); the right check is `strace -f -e trace=connect,sendto`
or `tcpdump` while exercising the flows, asserting no destination other than the local model, or an
nftables allow-only-local firewall. Either is a real-machine check (the ~22 GB image plus a live model).

## Related

- `tasks/disable-crush-telemetry.md` — the Crush-own-code audit this extended.
- `tasks/archive/2026/08/29/extract-crush-build-to-script.md` — the build/vendor machinery this revised.
- `tasks/verify-vendored-airgap-rebuild.md` — the airgap build the flag-selected patches feed.
