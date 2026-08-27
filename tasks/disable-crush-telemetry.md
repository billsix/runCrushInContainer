# Disable Crush telemetry & phone-home in the client image

**Status:** in-progress
**Priority:** 3
**Difficulty:** 2
**Started:** 2026-08-27

## Goal

Crush `v0.89.0` (the pinned `CRUSH_TAG`) makes two unsolicited outbound calls: (1) **PostHog
usage telemetry** to `https://data.charm.land`, and (2) a **GitHub update check** to
`https://api.github.com/repos/charmbracelet/crush/releases/latest` on startup. Turn both off at
the image/config level so the throwaway client never phones home — matching the repo's
privacy-conscious, airgap-oriented posture. The telemetry half has built-in opt-outs (easy); the
update check has none and needs a source patch or an accepted-and-documented exception.

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

### 3. Other charm.land hosts (context — not in scope unless we decide otherwise)
- `catwalk.charm.land` — the embedded provider catalog. **Already suppressed** in this repo's baked
  `crushrc` via `option default-providers false` (see `architecture.md` "Permissions/Provider").
  Worth a quick confirm that suppression also skips the catwalk *fetch*, not just the picker.
- `hyper.charm.land` — Charm's hosted "Hyper" provider/OAuth. **Not used** in this setup (local
  llamacpp provider only); reachable only if someone configures it. Env override `HYPER_URL`.

## Plan

- [ ] **Telemetry (do first — cheap, high value):** add `ENV CRUSH_DISABLE_METRICS=1` (and
      `DO_NOT_TRACK=1` belt-and-suspenders) to `client/Dockerfile` near the other `ENV`/`ARG`
      lines (~L55-58). Env is launch-independent — covers `crush`, `crush run`, `crush stats`, and
      survives a mounted-config override, unlike a crushrc-only switch.
- [ ] **Telemetry (defense-in-depth + visibility):** also add `option metrics false` to the baked
      `client/entrypoint/crushrc`, with a comment, so the intent is discoverable in the config the
      user actually reads. (Decide: env-only, crushrc-only, or both — see Q1.)
- [ ] **Update check (pending Q2):** if disabling, add `client/patches/crush-no-update-check.patch`
      that no-ops `checkForUpdates` (or short-circuits `update.Check`), applied at image build
      alongside the `@`-import patch; wire it into both the online (`go install`/source) and
      vendored (`CRUSH_VENDORED=1`) build paths in the Dockerfile. Re-verify on every `CRUSH_TAG`
      bump (same caveat as the `@`-import patch).
- [ ] **Verify:** rebuild the client image; confirm `crush` starts with no outbound to
      `data.charm.land` or `api.github.com` (e.g. run under nested podman with egress watched, or
      grep the debug log for the PostHog/update slog lines). Confirm the model still works.
- [ ] Update `tasks/reference/architecture.md` (a "Telemetry / phone-home" note) and, if the
      update-check patch lands, `crush-capabilities.md` + the `CLAUDE.md` patch list.

## Notes / decisions

- Cleanest telemetry home is the **Dockerfile `ENV`**, not just crushrc: it disables metrics
  regardless of how Crush is invoked or whether the config is overridden, and it needs no source
  patch. The crushrc `option metrics false` is additive (documents intent where the user looks).
- The update check is the only phone-home with **no built-in off switch** — it's the one that
  actually requires touching Crush's source (or accepting it).

## Open questions

1. **Telemetry disable mechanism** — env in Dockerfile, crushrc `option metrics false`, or both?
   Recommend **both** (env is the robust guarantee; crushrc makes the intent visible in the config
   the user edits). Trivial either way.
2. **The GitHub update check** — disable it via a source patch (fits the existing
   `client/patches/` + build-flag machinery, but adds a patch to re-verify on each `CRUSH_TAG`
   bump), or leave it and document it as an accepted low-sensitivity exception (no identifying
   payload; just times out offline)? Recommend **patch it** — the repo already patches Crush and is
   explicitly airgap-oriented, so "no unsolicited egress at all" is the consistent stance.
3. **Scope** — keep this task to telemetry + update check only, or also add a one-line confirmation
   that `catwalk.charm.land` is not fetched under `default-providers false`? Recommend a **quick
   confirm** (item in Findings §3), no separate work.
