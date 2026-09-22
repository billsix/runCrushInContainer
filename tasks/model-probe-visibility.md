# Make the model-port probe visible before `crush` starts (banner + probe log)

**Status:** proposed — needs go-ahead. Filed 2026-09-22 (William Emerison Six <billsix@gmail.com>) as the
follow-on to the archived `tasks/archive/2026/09/22/crushrc-startup-failure-and-model-preselect.md`.
**Priority:** 5
**Difficulty:** 2

## BLUF

When the crushrc's five-port probe finds nothing live it silently pins Muse Glimmer, and the user learns
that only when the first message fails with "connection refused" on 8080 — which is exactly what
happened on 2026-09-22 with Gemma served (a rebuilt image then found Gemma; the cause of the one bad
run was never pinned down). Make the verdict visible *before* `crush` starts: `shell.sh` runs the same
five `curl` probes and prints "live: gemma-4 (8081)" or a loud "no model port answers — is `make serve`
done loading? (`make probe MODEL=<m>` on the Mac)"; and the crushrc logs each port's curl exit code +
HTTP status to `/tmp/crushrc-probe.log`. "Done" = both landed, the banner shows the right model on the
real machine, and a deliberately-too-early start shows the warning instead of a silent fallback.

## Context (cold-start)

- The probe: `client/entrypoint/crushrc` `try_model` (five `curl -sf -m 2 http://127.0.0.1:808x/v1/models`
  calls; the `[ -z "$first_live" ]` fallback pins Glimmer). Proven correct in-sandbox 2026-09-22 (vendored
  Crush, stub on 8081 → only `gemma-4` registered, 8081 dialed) — see the archived task above.
- Where the banner goes: `client/entrypoint/shell.sh` already prints a mode-aware hint before `exec
  bash "$@"`, guarded on `[ "$#" -eq 0 ]` (interactive only), and is **bind-mounted**, so a change is
  live without `make image`. The crushrc is **baked** (`client/Dockerfile:149`), so its change needs a
  rebuild — which is also why "stale image" was a credible cause of the bad run.
- Why a probe can legitimately fail while the model is "up": llama-server answers `/v1/models` with
  HTTP 503 "Loading model" until the weights are loaded; `curl -f` treats that as failure. A second
  lead was proxy env leaking in (podman forwards host `http_proxy`/`https_proxy` by default). Logging
  the HTTP status distinguishes them.
- Under `LOCALHOST_ONLY=1` the probes go through `shell.sh`'s socat bridge, which is started earlier
  in the same script — the banner must run after that loop.

## Plan

- [ ] `shell.sh`: after the socat loop and inside the interactive guard, probe the five ports (same
  `curl -sf -m 2`), print the live list with aliases, or the warning with the `make probe` hint.
- [ ] `crushrc`: in `try_model`, append `port curl-exit http-status` per probe to `/tmp/crushrc-probe.log`
  (`curl -s -o /dev/null -w '%{http_code}'`), and on the fallback branch write one `FALLBACK glimmer`
  line. Stderr is swallowed by the TUI, so a file is the channel.
- [ ] In-sandbox proof: `shell.sh` with a stub on 8081 → banner says gemma-4; with none → warning;
  crushrc through the vendored Crush → log has five lines and the right verdict.
- [ ] Real machine: start `crush` too early on purpose (right after `make serve MODEL=gemma`) and
  confirm the warning; wait for `make probe` to answer and confirm the banner names Gemma.
- [ ] Docs: `tasks/reference/crush-capabilities.md` § "Which model is active at startup" (the probe log),
  README "Network modes" one line, then archive.

## Checks to do (maintainer, recorded 2026-09-22 at session end)

- [ ] **Go/no-go on this task.** Recommendation: go — the `shell.sh` half is live with no rebuild; the
      crushrc half rides the next `make image`.
- [ ] **For the record of the archived preselect task:** after the 2026-09-22 rebuild that found Gemma,
      did `ctrl+l` list Gemma — and only the served model(s)? Write the answer into
      `tasks/archive/2026/09/22/crushrc-startup-failure-and-model-preselect.md` ("Record when done"
      line: `ctrl+l` listing not separately reported). "Don't know" is acceptable; the banner this task
      adds makes it observable next time.

## Notes / decisions

## Open questions

1. Implement now, or leave proposed? (Recommendation: now — `shell.sh` half is a no-rebuild change;
   the crushrc half rides the next image rebuild.) Tracked as the first check above.
