# Decide whether the dependency-egress audit needs an enforced verification check

**Status:** proposed — decide after the audit lands (William Emerison Six <billsix@gmail.com>, 2026-08-29: "no verification needed for now … a follow up task, to decide if we even need to")
**Priority:** 6
**Difficulty:** 3
**Started:** 2026-08-29

## BLUF

Decide whether the dependency network audit (`tasks/audit-dependency-network-egress.md`) should be
*enforced* by a runtime egress check — and if yes, design and run it. "Done" = a recorded yes/no
decision from the maintainer; if yes, additionally a working check (strace/tcpdump trace or a
firewall rule set) that asserts Crush contacts **no host other than the local model endpoint**,
run on the real machine.

## Context

Read first:

- `tasks/audit-dependency-network-egress.md` — the audit this would verify. Its
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
- Either way it is **real-machine** (the ~22 GB client image + a live local model on the Mac) — not
  an in-sandbox check.
- The alternative to a runtime check is relying on the audit's source-level findings alone (every
  network-capable dep documented `file:line`, phone-home patched out by default) — a legitimate
  outcome; that is exactly the "do we even need it" question this task exists to answer.

## Goal

Answer, with the maintainer: is the source-level audit + default-on patches sufficient, or do we
want a runtime egress check as a standing gate? If wanted: pick observe-vs-enforce, decide
`make`-target vs documented manual procedure, and run it once on the real machine.

## Plan

- [ ] Wait for the audit reference doc (`tasks/reference/dependency-network-audit.md`) to exist —
      the decision needs its findings (how much network-capable surface actually remains).
- [ ] Put the yes/no to the maintainer with the audit's numbers in hand.
- [ ] If yes: pick mechanism (observe vs enforce), write the procedure/target, run on real machine.

## Notes / decisions

## Open questions

1. Is a runtime check needed at all, or is the source-level audit sufficient? (Deferred until the
   audit's findings exist — that's this task's whole point.)
