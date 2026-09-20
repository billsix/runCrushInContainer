# Localhost-only network mode for the Crush client container (opt-in egress lockdown)

**Status:** DONE (implemented) 2026-09-20 — the `LOCALHOST_ONLY` toggle landed and passed in-sandbox static
checks; the end-to-end behaviour (model reachable + all other egress blocked) is the maintainer's local
test, tracked separately in `tasks/verify-localhost-only-network-mode.md`. Filed 2026-09-20
(William Emerison Six <billsix@gmail.com>), applying **Option H** of the `whitelistnetwork` sandbox writeup
(sibling repo, `tasks/whitelist-only-network-sandbox.md`). Archived.

## Implementation (2026-09-20) — awaiting local testing

Landed as an additive `LOCALHOST_ONLY` toggle (default off; the default `make shell` path is unchanged —
verified via `make -n`):
- **`client/Makefile`:** `LOCALHOST_ONLY ?= 0` + `MUSE_SOCK_DIR ?= $(HOME)/.cache/runcrush-muse-sockets`.
  When `=1`: `NET_FLAGS := --network=none`, `mkdir -p` the socket dir, and add
  `-v $(MUSE_SOCK_DIR):/run/muse:Z` to the shared `SHELL_RUN_FLAGS` (so `shell` AND `shell-exec` get it);
  also passes `-e LOCALHOST_ONLY` + `-e MUSE_SOCK_DIR` in.
- **`client/entrypoint/shell.sh`:** when `LOCALHOST_ONLY=1`, starts a `socat` bridge per port
  (`TCP-LISTEN:PORT,bind=127.0.0.1,reuseaddr,fork` → `UNIX-CONNECT:/run/muse/PORT.sock`) for any socket
  present, so Crush's unchanged `127.0.0.1:8080/8081` probe still reaches the model; the launch banner is
  mode-aware (shows the unix-socket SSH forward in localhost-only mode, the TCP form otherwise).
- **`README.md`:** the shown `make shell` example is `LOCALHOST_ONLY=1` (recommended, "no internet"); a
  "Network modes" section documents both — localhost-only (`--network=none` + the unix-socket SSH forward)
  and full-internet (`--network=host`, the bare default) — with the matching host SSH command for each.
- **Verified in-sandbox:** `make -n shell` → `--network=host`, no socket mount; `make -n shell
  LOCALHOST_ONLY=1` → `--network=none` + the `/run/muse` mount; `shell.sh` parses. The end-to-end model
  reachability + egress-blocked check is the maintainer's local test (needs the Mac + SSH).
**Priority:** 5
**Difficulty:** 4 (mechanism is straightforward — the moving part is the SSH-forward → socket → socat bridge)

## BLUF

Add an **opt-in "localhost-only" network mode** to the Crush client container so it can reach **only the
local model endpoint** (the SSH-forwarded `127.0.0.1:8080`/`8081`) and **nothing else** — no internet, no
other host. Today the client runs `--network=host` (`client/Makefile:138`, `NET_FLAGS ?= --network=host`),
which lets `127.0.0.1:8080` reach the host's SSH-forwarded LLM **but also gives the container the host's
entire network**. This task locks that down as a toggle. **The default stays network-on** (`--network=host`
as now); localhost-only is opt-in. The **README's shown example is the localhost-only mode**; with the
toggle unset the bare default stays network-on (Decision 1), and both modes are documented explicitly. The
maintainer does the local testing (SSH tunnel + Crush generating against the model under lockdown).

## Context (cold-start)

- **Current wiring:** the Mac serves llama.cpp on `127.0.0.1:8080` (Muse Glimmer) / `:8081` (Gemma); the
  **Linux host** runs `ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 you@mac-studio`
  (`client/entrypoint/shell.sh:20`); the **container** runs `--network=host` so its `127.0.0.1:8080` is the
  host's forwarded port. Crush's baked crushrc probes `127.0.0.1:8080/8081` at load. Ports are fixed
  (8080/8081).
- **The idea (Option H, from the whitelistnetwork writeup):** the *strongest and simplest* lockdown is
  **`--network=none` + a unix-socket-forwarded tunnel + a `socat` bridge** — the container gets ONLY its own
  loopback, and the model is reached through a bind-mounted unix socket, so there is literally **no external
  egress path** and no firewall to tamper with. **`socat` is already installed** in the client image
  (`client/entrypoint/01-install-base.sh:384`), so the bridge is ready to use.
- **This complements** `tasks/decide-egress-verification.md` (whether to *verify* egress) — a localhost-only
  mode is a concrete *enforcement* that, when on, makes the audit concern moot for that run. The egress
  surface is already enumerated in `tasks/reference/dependency-network-audit.md` (D1–D12) — **that audit is
  the correctness gate**: under `--network=none` Crush must need *nothing* but the model (see the
  correctness open question; telemetry is handled by `tasks/disable-crush-telemetry.md`).

## Mechanism (as built)

A `LOCALHOST_ONLY=1` toggle on the client `make` that flips three things:

1. **`NET_FLAGS = --network=none`** (instead of `--network=host`) — the container gets only loopback.
2. **Mount the forwarded socket(s)** into the container (via the existing `EXTRA_MOUNTS` hook or a dedicated
   var), e.g. host `/run/muse/8080.sock`, `/run/muse/8081.sock` → same paths in the container.
3. **A `socat` bridge in the container** (an entrypoint step, only when the mode is on) so Crush's unchanged
   `http://127.0.0.1:8080` still works:
   `socat TCP-LISTEN:8080,bind=127.0.0.1,reuseaddr,fork UNIX-CONNECT:/run/muse/8080.sock &` (+ 8081).

The **host side** must forward to unix sockets rather than TCP for this — either directly with SSH
(`ssh -N -L /run/muse/8080.sock:127.0.0.1:8080 -L /run/muse/8081.sock:127.0.0.1:8081 you@mac-studio`) or a
host-side `socat` that re-exposes the existing TCP forward as a socket. Net result: container reaches ONLY
its loopback + the two mounted sockets → the model, and nothing else. (Alternative, if a TCP path is
preferred: a private podman network allowing only `host.containers.internal` at the two ports, default-deny
the rest — heavier and less airtight than `--network=none`; the writeup rejects `--network=host` for this
since it exposes everything.)

## Plan (as executed)
1. **Client `make` toggle:** add `LOCALHOST_ONLY` (default off) that sets `NET_FLAGS=--network=none`, adds
   the socket mount, and signals the entrypoint to start the socat bridge. Keep `NET_FLAGS ?= --network=host`
   as the default. Thread through both `shell` and `shell-exec` (share their run-flag block so they can't
   drift).
2. **Entrypoint bridge:** a small guarded step (runs only under the toggle) that starts the socat
   TCP→unix-socket bridges for 8080/8081 before Crush loads (crushrc probes them at load).
3. **Host-forward doc/helper:** document (and optionally add a helper) for the unix-socket SSH forward the
   mode requires; update the `shell.sh` hint banner to show both the default TCP and the socket form.
4. **README:** feature localhost-only as the **shown example** (Decision 1), with the bare default staying
   network-on. Document BOTH modes adjacently and explicitly, in the maintainer's phrasing — e.g.
   "If running with **no internet access**, use `make … LOCALHOST_ONLY=1` (+ the unix-socket SSH forward)";
   next line "If you want the **full internet**, use `make …` (the default)". Include the matching
   host-side SSH-forward command for each mode (unix-socket form for localhost-only, TCP form for full).
5. **Correctness check (before shipping):** confirm from `dependency-network-audit.md` that Crush needs no
   runtime network beyond the model (telemetry off, no runtime fetches) — else `--network=none` will break
   it, and the mode must either allow those specific endpoints (then it's not "localhost only") or depend on
   those being disabled.
6. **Local testing (maintainer):** with the socket SSH forward up, run the client under `LOCALHOST_ONLY=1`
   and confirm (a) Crush reaches the model and generates, and (b) the container **cannot** reach any other
   host (e.g. `curl https://example.com` fails). Then confirm the default (no toggle) still works as today.

## Decisions (William Emerison Six <billsix@gmail.com>, 2026-09-20)
1. **README shows localhost-only as the example; unset = network-on.** The primary documented invocation
   enables `LOCALHOST_ONLY=1`; with the toggle unset the bare default stays `--network=host` (full internet).
   Both modes are documented explicitly and adjacently ("no internet access → X" / "full internet → Y",
   see Plan step 4).
2. **Socket approach confirmed.** `--network=none` + unix-socket SSH forward + `socat` bridge. Changing the
   host-side SSH command between the two modes (unix-socket for localhost-only, TCP for full internet) is
   fine — document both forms.
3. **Correctness accepted.** Proceed on the basis that Crush needs nothing but the model at runtime
   (telemetry disabled). Still sanity-check against `dependency-network-audit.md` during implementation, but
   it is not a blocker.

## Related
- Source idea: the `whitelistnetwork` sandbox repo, `tasks/whitelist-only-network-sandbox.md` **Option H**
  (loopback-only via `--network=none` + SSH-forward-to-unix-socket).
- `tasks/decide-egress-verification.md` (verify egress — complementary), `tasks/reference/dependency-network-audit.md`
  (the egress surface, D1–D12), `tasks/disable-crush-telemetry.md`.
- Toggle point: `client/Makefile:138` (`NET_FLAGS`), `EXTRA_MOUNTS`, `client/entrypoint/shell.sh` (the SSH
  hint), `socat` already in `client/entrypoint/01-install-base.sh`.
