# Verify the localhost-only network mode works end-to-end (maintainer local test)

**Status:** proposed — **maintainer hands-on test**, deferred (needs the Mac serving a model + a real SSH
forward; can't run in the sandbox). Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>) as the
verification follow-up to the now-implemented
[localhost-only-network-mode](archive/2026/09/20/localhost-only-network-mode.md).
**Priority:** 4
**Difficulty:** 2 (just running it — no code, unless the test finds a bug)

## BLUF

The `LOCALHOST_ONLY=1` mode is implemented and passed in-sandbox static checks (`make -n` shows
`--network=none` + the socket mount; `shell.sh` parses), but the **end-to-end behaviour was not verified**
because it needs the Mac serving a model and a real unix-socket SSH forward. This task is the maintainer's
hands-on confirmation that: **(a) Crush reaches the model** under `--network=none`, and **(b) the container
can reach nothing else** (no internet, no other host). "Done" = both confirmed on the real machine (and any
bug found is fixed).

## Test steps

1. **Mac:** serve a model — `cd server && make serve` (Muse Glimmer on `127.0.0.1:8080`) and/or
   `make serve MODEL=gemma` (`:8081`).
2. **Linux host:** set up the **unix-socket** SSH forward (NOT the TCP one) — the sockets must exist before
   launching:
   ```sh
   ssh -N -L ~/.cache/runcrush-muse-sockets/8080.sock:127.0.0.1:8080 \
           -L ~/.cache/runcrush-muse-sockets/8081.sock:127.0.0.1:8081 you@mac-studio.local
   ```
3. **Launch locked-down:** `cd client && make shell LOCALHOST_ONLY=1`.
4. **(a) Model reachable:** inside, `curl -s http://127.0.0.1:8080/v1/models` returns the model, and
   `crush` starts + generates against it.
5. **(b) Egress blocked** — all of these must FAIL inside the container:
   - `curl -m5 https://example.com` (external host),
   - `curl -m5 https://1.1.1.1` (raw IP — proves it's not just DNS),
   - `getent hosts github.com` / `curl -m5 https://github.com` (DNS + a real dependency host).
6. **Default still works:** `make shell` (no toggle) with the ordinary TCP forward (`ssh -N -L 8080:… -L
   8081:…`) reaches the model AND the internet, unchanged.

## Pass / fail
- **Pass:** step 4 works, every probe in step 5 fails (no egress), step 6 unchanged.
- **Fail modes to watch:** model unreachable → the socket forward wasn't up before launch, or the socat
  bridge didn't start (check `/run/muse/*.sock` exist inside); OR Crush needs some *other* host at runtime
  (then `--network=none` breaks a feature — cross-check `tasks/reference/dependency-network-audit.md` and
  decide whether to allow that specific endpoint, i.e. it's not purely "localhost only").

## Related
- Implementation (archived): `tasks/archive/2026/09/20/localhost-only-network-mode.md`.
- Source idea: the `whitelistnetwork` sandbox, `tasks/whitelist-only-network-sandbox.md` (Option H).
- Egress surface: `tasks/reference/dependency-network-audit.md`; the audit-verification decision:
  `tasks/decide-egress-verification.md` (this test partly answers it — a passing localhost-only run *is*
  enforced egress isolation).
