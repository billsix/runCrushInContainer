# Decide whether the dependency-egress audit needs an enforced verification check

**Status:** proposed — **askable now**: the audit landed and was implemented 2026-08-29
(`tasks/reference/dependency-network-audit.md` — findings, D1–D12, flag index), so the decision has
its numbers. Deferred originally by the maintainer (William Emerison Six <billsix@gmail.com>,
2026-08-29: "no verification needed for now … a follow up task, to decide if we even need to").
Note: `tasks/minimal-client-image.md` (proposed) would bake strace+tcpdump into a sandbox-buildable
minimal image — exactly the environment a runtime egress check would run in; if a check is wanted,
consider sequencing after that task.
**Priority:** 6
**Difficulty:** 3
**Started:** 2026-08-29

## BLUF

Decide whether the dependency network audit (`tasks/archive/2026/08/29/audit-dependency-network-egress.md`) should be
*enforced* by a runtime egress check — and if yes, design and run it. "Done" = a recorded yes/no
decision from the maintainer; if yes, additionally a working check (strace/tcpdump trace or a
firewall rule set) that asserts Crush contacts **no host other than the local model endpoint**,
run on the real machine.

## Context

Read first:

- `tasks/archive/2026/08/29/audit-dependency-network-egress.md` — the audit this would verify. Its
  "Verification / hardening idea" section holds the full design discussion; this task was split out
  of it on 2026-08-29 (the maintainer deferred verification: decide *whether* before building *what*).
- `tasks/disable-crush-telemetry.md` — the prior two-host egress check idea this would supersede/extend.
- `tasks/reference/architecture.md` — the local-model topology (`127.0.0.1:8080` over an SSH tunnel,
  `--network=host`).

Decisions already made, with rationale:

- **`--network=none` is the WRONG mechanism** — under `--network=host` it severs the container's path
  to the host's `127.0.0.1:8080`, killing the essential local-model link, so it proves nothing.
- The candidate mechanisms, if we do build a check (from the audit task):
  1. **Observe:** run Crush normally under `strace -f -e trace=connect,sendto` (or `tcpdump`),
     exercise startup + a chat + each KEPT online feature, assert every destination is
     loopback/the local model.
  2. **Enforce:** an `nftables`/`iptables` rule set allowing only the local model endpoint, DROP the
     rest; confirm Crush still works and blocked attempts fail gracefully.
- Originally judged **real-machine only** (the ~22 GB client image + a live local model). Partly
  superseded 2026-08-29: if `tasks/minimal-client-image.md` lands (a sandbox-buildable minimal
  image with strace+tcpdump baked in), the observe-mode check can run **in-sandbox** against a
  stub OpenAI endpoint on loopback; only a check against the real Mac-served model stays
  real-machine.
- The alternative to a runtime check is relying on the audit's source-level findings alone (every
  network-capable dep documented `file:line`, phone-home patched out by default) — a legitimate
  outcome; that is exactly the "do we even need it" question this task exists to answer.

## Goal

Answer, with the maintainer: is the source-level audit + default-on patches sufficient, or do we
want a runtime egress check as a standing gate? If wanted: pick observe-vs-enforce, decide
`make`-target vs documented manual procedure, and run it once on the real machine.

## Plan

- [x] Wait for the audit reference doc (`tasks/reference/dependency-network-audit.md`) — landed
      and implemented 2026-08-29. The numbers: zero unsolicited egress with default flags; the
      remaining intentional surface is the web tools (D1), sourcegraph (D2), and operator-
      configured MCP servers.
- [ ] Put the yes/no to the maintainer with the audit's numbers in hand.
- [ ] If yes: pick mechanism (observe vs enforce) and environment (in-sandbox minimal image with a
      stub endpoint, vs real machine against the live model), write the procedure/target, run it.

## Notes / decisions

## Open questions

1. Is a runtime check needed at all, or is the source-level audit sufficient? (Deferred until the
   audit's findings exist — that's this task's whole point.)
