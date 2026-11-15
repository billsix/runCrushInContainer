# Localhost-only network mode for the Crush client container (opt-in egress lockdown)

**Status:** complete
**Completed:** 2026-09-20
Filed 2026-09-20 (William Emerison Six <billsix@gmail.com>), applying **Option H** of the
`whitelistnetwork` sandbox writeup (sibling repo, `tasks/whitelist-only-network-sandbox.md`).

Added an opt-in `LOCALHOST_ONLY=1` toggle so the client container can reach only the SSH-forwarded
local model and nothing else. The default client run (`--network=host`, which gives the container
the host's whole network) was left unchanged. In-sandbox static checks passed; the end-to-end test
was tracked in `tasks/archive/2026/09/22/verify-localhost-only-network-mode.md`, later superseded
(2026-09-22) by `tasks/archive/2026/09/22/runcrush-launcher-scripts.md`. The current description of
both modes is `tasks/reference/client-network-modes-and-launchers.md`.

## Mechanism

`--network=none` (the container gets only its own loopback) + a host SSH forward to **unix sockets**
+ an in-container `socat` bridge, so Crush's unchanged `127.0.0.1:<port>` probe reaches the model
through a bind-mounted socket. There is no external egress path and no firewall to tamper with. A
private podman network allowing only `host.containers.internal` was the heavier, less airtight
alternative and was not used. `socat` was already in `client/entrypoint/01-install-base.sh`.

## What was built

- **`client/Makefile`:** `LOCALHOST_ONLY ?= 0` and `MUSE_SOCK_DIR ?= $(HOME)/.cache/runcrush-muse-sockets`.
  When `=1`: `NET_FLAGS := --network=none`, `mkdir -p` the socket dir, and add
  `-v $(MUSE_SOCK_DIR):/run/muse:Z` to the shared `SHELL_RUN_FLAGS` (so `shell` and `shell-exec` both
  get it); also pass `-e LOCALHOST_ONLY` and `-e MUSE_SOCK_DIR`.
- **`client/entrypoint/shell.sh`:** under `LOCALHOST_ONLY=1`, starts a `socat` bridge per port
  (`TCP-LISTEN:PORT,bind=127.0.0.1,reuseaddr,fork` → `UNIX-CONNECT:/run/muse/PORT.sock`) for each
  socket present, before Crush loads; the launch banner shows the unix-socket SSH forward in this
  mode and the TCP form otherwise. (Built for ports 8080/8081; the five-port version came with
  `tasks/archive/2026/09/20/country-gated-model-selection.md`.)
- **`README.md`:** the shown `make shell` example is `LOCALHOST_ONLY=1` ("no internet"); a "Network
  modes" section documents both modes with the matching host SSH command for each.
- No separate host-forward helper script was added in this task; the SSH command is documented.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-09-20)
1. **README shows localhost-only as the example; unset = network-on.** The primary documented invocation
   enables `LOCALHOST_ONLY=1`; with the toggle unset the bare default stays `--network=host` (full internet).
   Both modes are documented explicitly and adjacently ("no internet access → X" / "full internet → Y").
2. **Socket approach confirmed.** `--network=none` + unix-socket SSH forward + `socat` bridge. Changing the
   host-side SSH command between the two modes (unix-socket for localhost-only, TCP for full internet) is
   fine — document both forms.
3. **Correctness accepted.** Proceed on the basis that Crush needs nothing but the model at runtime
   (telemetry disabled). Still sanity-check against `dependency-network-audit.md` during implementation, but
   it is not a blocker.

## Verification (in-sandbox)

`make -n shell` → `--network=host`, no socket mount; `make -n shell LOCALHOST_ONLY=1` →
`--network=none` + the `/run/muse` mount; `shell.sh` parsed. Model reachability and blocked egress
needed the Mac + SSH, so they were left to the maintainer's local test (see the verify task above).

## Related
- `tasks/archive/2026/09/22/decide-egress-verification.md` (verifying egress, complementary),
  `tasks/reference/dependency-network-audit.md` (the egress surface, D1–D12),
  `tasks/disable-crush-telemetry.md`.
