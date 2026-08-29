# Disable Crush telemetry & phone-home in the client image

**Status:** blocked
**Priority:** 6
**Difficulty:** 2
**Started:** 2026-08-27
**Blocked on:** a real-machine client-image rebuild + runtime egress check — only the maintainer can
run it on the target host (the image is ~22 GB; not done in-sandbox). Implementation is complete and
staged; this is the last gate before archive.
**Recheck:** on the host, `make -C client image` (green build proves the restructured RUN + both
patches apply), then start Crush with egress watched (e.g. `strace -f -e trace=network` or a tcpdump
on the bridge) and confirm **no** connection to `data.charm.land` or `api.github.com` and that the
model still answers. Cleared = build green + zero egress to those two hosts. (Folds into
`verify-auto-allow-file-tools.md`, which also needs a rebuild.)

## Goal

Crush `v0.89.0` (the pinned `CRUSH_TAG`) makes two unsolicited outbound calls: (1) **PostHog
usage telemetry** to `https://data.charm.land`, and (2) a **GitHub update check** to
`https://api.github.com/repos/charmbracelet/crush/releases/latest` on startup. Turn both off at
the image/config level so the throwaway client never phones home — matching the repo's
privacy-conscious, airgap-oriented posture. The telemetry half has built-in opt-outs (easy); the
update check has none and needs a source patch or an accepted-and-documented exception.

**Scope note:** this task audits **Crush's OWN code** only. A full audit of the **~213 vendored Go
dependencies** for their own network/phone-home behavior (and a per-decision, flag-driven patch system
for the airgap build) is tracked separately in **`audit-dependency-network-egress.md`**, which extends
this work.

## Findings (source-verified against v0.89.0, commit `ba531a4`, 2026-08-27)

### 1. PostHog usage telemetry → `https://data.charm.land`
- Dependency: `github.com/posthog/posthog-go v1.23.0` (`go.mod:54`).
- Implementation: `internal/event/event.go` — endpoint `data.charm.land`, hardcoded project key
  `phc_4zt4…`. Sends a machine ID + metadata props (GOOS/GOARCH/TERM/SHELL/Version/GoVersion,
  interactive-vs-not, session-continue flags), plus `Error()` exception events. **Prompts/responses
  are NOT collected** (per upstream README) — usage metadata only.
- **Gating is clean and total.** All four `event.Init()` call sites
  (`internal/cmd/root.go:396`, `root.go:492`, `session.go:119`, `stats.go:167`) are wrapped in
  `if shouldEnableMetrics(cfg)`. When it returns false, `client` stays nil and every
  `send`/`Error`/`Alias`/`Flush` short-circuits on `client == nil`. Disabling is comprehensive.
- **Three independent opt-outs** (`shouldEnableMetrics`, `root.go:966`), any one suffices:
  - env `CRUSH_DISABLE_METRICS=1`
  - env `DO_NOT_TRACK=1` (the cross-tool https://donottrack.sh convention)
  - config `option metrics false` in crushrc → `options.disable_metrics = true`
    (`internal/shellconfig/options.go:188`, inverted key).

### 2. GitHub update check → `api.github.com/.../releases/latest`
- `internal/app/app.go:139` fires `go app.checkForUpdates(ctx)` unconditionally at App startup;
  body at `app.go:797` calls `update.Check` → GET `githubApiUrl`
  (`internal/update/update.go:15`), 30s timeout, `User-Agent: crush/1.0`.
- **No env var, no config flag gates it.** The request carries no identifying payload beyond IP +
  UA, but it is still an unsolicited outbound call on every launch. On an airgapped box it just
  fails after the 30s timeout in a background goroutine (non-blocking, but noisy in logs).
- To disable requires either a **source patch** (no-op `checkForUpdates`) — which fits the existing
  patch machinery (`client/patches/crush-at-import.patch`, gated by `CRUSH_AT_IMPORT`) — or leaving
  it and documenting it as an accepted low-sensitivity exception.

### 3. Other charm.land hosts (context — confirmed, no action needed)
- `catwalk.charm.land` — the embedded provider catalog. **Already suppressed** in this repo's baked
  `crushrc` via `option default-providers false`. **Confirmed source-side (2026-08-27):** the catwalk
  fetch goroutine in `Providers()` starts with `if customProvidersOnly { return }` where
  `customProvidersOnly := cfg.Options.DisableDefaultProviders` (`internal/config/provider.go:176,184-185`).
  So the flag **skips the HTTP fetch entirely**, not just the picker — `catwalk.charm.land` is never
  contacted. No work needed.
- `hyper.charm.land` — Charm's hosted "Hyper" provider/OAuth. **Not used** in this setup (local
  llamacpp provider only); the Hyper token refresher only fires if a Hyper provider is configured.
  Env override `HYPER_URL`. No work needed.

## Plan (approach decided 2026-08-27 — see Decisions) — IMPLEMENTED 2026-08-27

- [x] **Telemetry — Dockerfile env:** `ENV CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1` added to
      `client/Dockerfile` (above the `GOBIN` ENV), with a comment.
- [x] **Telemetry — crushrc visibility:** `option metrics false` added to `client/entrypoint/crushrc`
      (new "Privacy: no telemetry" block), with a comment cross-referencing the env + the patch.
- [x] **Update check — patch it out (always applied):** created
      `client/patches/crush-no-update-check.patch` — removes the `go app.checkForUpdates(ctx)` launch
      in `internal/app/app.go` (`checkForUpdates`/`update.Check` left defined but uncalled; an unused
      method is legal Go, so it's a one-site patch). Wired into **both** build paths:
      - **Dockerfile RUN restructured** — the non-vendored branch now ALWAYS `git clone`s + `git
        apply`s `crush-no-update-check.patch`, then applies `crush-at-import.patch` only if
        `CRUSH_AT_IMPORT=1`, then `go install .`. Consequence (intended): the old plain
        `go install …@tag` else-branch is gone — a patch needs a source tree, so every non-vendored
        build is now a source build. `CRUSH_AT_IMPORT=0` now means "source build without the
        @-import patch" (update-check patch still applied), not "stock upstream". Dockerfile comment
        updated to say so.
      - **`vendor-crush.sh`** — applies `crush-no-update-check.patch` unconditionally (new
        `UPDATE_PATCH_FILE`, default `/patches/crush-no-update-check.patch`) before the conditional
        `@`-import patch, so the offline `CRUSH_VENDORED=1` tree carries it. `make vendor` needs no
        change (runs inside the image where `/patches/` is baked; passes `CRUSH_TAG`/`CRUSH_AT_IMPORT`).
      - Re-verify both patches apply on every `CRUSH_TAG` bump (same caveat as `@`-import).
- [~] **Verify:** DONE cheaply — patch applies cleanly to pristine v0.89.0 (`git apply --check`),
      the patched `internal/app` package compiles (`go build ./internal/app/` → exit 0), gofmt-clean,
      and `bash -n vendor-crush.sh` passes. PENDING (real machine): a full client-image rebuild +
      confirm `crush` starts with no egress to `data.charm.land` / `api.github.com` and the model
      still works. Folds naturally into `verify-auto-allow-file-tools.md` (needs a rebuild anyway) and
      `verify-vendored-airgap-rebuild.md` (exercises the vendored patch path). Not attempted here:
      the client image is ~22 GB and nested three-deep — real-machine territory per this repo's
      workflow.
- [ ] Update `tasks/reference/architecture.md` (a "Telemetry / phone-home" note) and
      `crush-capabilities.md` + the `CLAUDE.md` patch list (for the new update-check patch). *(Do at
      session-end doc sweep or when the rebuild verification lands.)*

## Notes / decisions

Decisions confirmed by William Emerison Six <billsix@gmail.com>, 2026-08-27:

1. **Telemetry — do BOTH.** Dockerfile `ENV CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1` (the robust,
   launch-independent guarantee that survives a config override) **and** `option metrics false` in
   the baked crushrc (documents intent where the user actually looks). Cheap either way.
2. **Update check — PATCH IT OUT.** Consistent with the repo's airgap orientation and the fact it
   already patches Crush (`client/patches/`): the stance is "no unsolicited egress at all", not
   "low-sensitivity, leave it". New patch applied at build alongside the `@`-import patch, in both
   the online and vendored build paths — **always applied, no build flag** (a runCrush client never
   wants the update check; unlike `@`-import, there's no fork case for a toggle).
3. **catwalk scope — quick confirm done, no work needed.** Source-verified that
   `option default-providers false` skips the catwalk *fetch* (not just the picker) — see
   Findings §3. `hyper.charm.land` is likewise never contacted in this local-only setup.

Design rationale that stands regardless: the Dockerfile `ENV` is the cleanest telemetry home
because it disables metrics no matter how Crush is invoked or whether the config is overridden, with
no source patch. The update check is the only phone-home with **no built-in off switch**, so it's
the one that genuinely requires touching Crush's source.

## Open questions

None — approach fully decided (see Notes / decisions). The update-check patch is **always applied,
no build flag** (confirmed 2026-08-27). Ready to implement on go-ahead.
