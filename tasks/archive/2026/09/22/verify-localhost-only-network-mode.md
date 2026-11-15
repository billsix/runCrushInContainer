# Verify the localhost-only network mode works end-to-end (maintainer local test)

**Status:** superseded — folded into `tasks/archive/2026/09/22/runcrush-launcher-scripts.md`, which
carried this end-to-end test and replaced the manual forward/launch steps with the launcher script.
Archived unrun.
**Completed:** 2026-09-22

## What this was

Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>) as the hands-on follow-up to
`tasks/archive/2026/09/20/localhost-only-network-mode.md`. The `LOCALHOST_ONLY=1` mode had passed
in-sandbox static checks (`make -n` showed `--network=none` + the socket mount; `shell.sh` parsed), but
its end-to-end behaviour needed the Mac serving a model and a real unix-socket SSH forward, so it could
not run in the sandbox. The test was to confirm (a) Crush reaches the model under `--network=none`, and
(b) the container reaches nothing else.

## The test as written (carried forward into the launcher task)

1. **Mac:** `cd server && make serve` (Muse Glimmer on `127.0.0.1:8080`) and/or
   `make serve MODEL=gemma` (`:8081`).
2. **Linux host:** the **unix-socket** SSH forward (not the TCP one), up before launch:
   ```sh
   ssh -N -L ~/.cache/runcrush-muse-sockets/8080.sock:127.0.0.1:8080 \
           -L ~/.cache/runcrush-muse-sockets/8081.sock:127.0.0.1:8081 you@mac-studio.local
   ```
3. **Launch:** `cd client && make shell LOCALHOST_ONLY=1`.
4. **Model reachable:** `curl -s http://127.0.0.1:8080/v1/models` returns the model; `crush` generates.
5. **Egress blocked:** `curl -m5 https://example.com`, `curl -m5 https://1.1.1.1`, and
   `getent hosts github.com` / `curl -m5 https://github.com` all fail.
6. **Default unchanged:** `make shell` with the ordinary TCP forward reaches the model and the internet.

Pass = step 4 works, every step-5 probe fails, step 6 unchanged. Failure modes noted: the socket forward
not up before launch, the socat bridge not started (check `/run/muse/*.sock` inside), or Crush needing
another host at runtime (cross-check `tasks/reference/dependency-network-audit.md`).

## Related
- Implementation: `tasks/archive/2026/09/20/localhost-only-network-mode.md`.
- Superseding task: `tasks/archive/2026/09/22/runcrush-launcher-scripts.md`.
- Source idea: the `whitelistnetwork` sandbox repo, `tasks/whitelist-only-network-sandbox.md` (Option H).
- Egress surface: `tasks/reference/dependency-network-audit.md`; the audit-verification decision:
  `tasks/archive/2026/09/22/decide-egress-verification.md` (a passing localhost-only run is enforced
  egress isolation).
