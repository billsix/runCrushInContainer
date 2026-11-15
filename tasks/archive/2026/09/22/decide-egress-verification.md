# Decide whether the dependency-egress audit needs an enforced verification check

**Status:** complete
**Completed:** 2026-09-22
Started 2026-08-29.

Decided whether the dependency network audit (`tasks/archive/2026/08/29/audit-dependency-network-egress.md`,
durable findings in `tasks/reference/dependency-network-audit.md`) should be enforced by a standing
runtime egress check. Answer: **no; enforcement exists by construction** in the no-internet mode. The
maintainer had deferred the question when the audit landed (William Emerison Six <billsix@gmail.com>,
2026-08-29: "no verification needed for now … a follow up task, to decide if we even need to").

## Inputs to the decision

- The audit's numbers: zero unsolicited egress with default flags; the remaining intentional surface
  is the web tools (D1), sourcegraph (D2), and operator-configured MCP servers.
- Candidate mechanisms had been an observe mode (`strace -f -e trace=connect,sendto` or `tcpdump`
  over startup, a chat and each kept online feature) and an enforce mode (an `nftables` rule set
  allowing only the model endpoint).
- An in-sandbox check had once been practical on the minimal client image, which was removed
  2026-09-12 (`tasks/reference/nested-podman-vs-image-content.md`); the full image could not build in
  the then nested RAM store.
- Earlier reasoning that `--network=none` was the wrong mechanism (it would sever the TCP path to the
  model) was superseded 2026-09-20: with the model forwarded to a bind-mounted unix socket and a
  `socat` bridge inside (`LOCALHOST_ONLY=1`), `--network=none` keeps the model link
  (`tasks/reference/client-network-modes-and-launchers.md`).

## Decision (2026-09-22, William Emerison Six <billsix@gmail.com>)

**No standing runtime egress check.** The question had a third answer once the localhost-only mode
landed (2026-09-20) and its one-command launcher made it the recommended way in (2026-09-22):

- **No-internet mode (`runCrushNoInternet.sh` / `make shell LOCALHOST_ONLY=1`) is enforcement by
  construction.** The container runs `--network=none` and reaches the model only through a
  bind-mounted unix socket — a file, not a network path — so there is no egress to observe or to
  firewall. The maintainer's real-machine probe set (`curl https://1.1.1.1`, `getent hosts
  github.com` failing inside; `tasks/archive/2026/09/22/runcrush-launcher-scripts.md` step 5) is the one-time proof.
- **With-internet mode (`runCrushWithInternet.sh` / bare `make shell`, `--network=host`) relies on
  the source-level audit + the default-on build patches** (`tasks/reference/dependency-network-audit.md`,
  `PATCH_OUT_*`). The one observed check the maintainer still wants for *that* mode — zero traffic to
  `data.charm.land` / `api.github.com` — stays tracked in `tasks/disable-crush-telemetry.md`
  (re-scoped 2026-09-22); it is a targeted watch, not the standing gate this task asked about.

The enforcement itself is exercised in `tasks/archive/2026/09/22/verify-localhost-only-network-mode.md`
and the launcher task; this doc records only the decision.
