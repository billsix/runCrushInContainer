# Rewrote the two-model text to the five-port autodiscovery design

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §1.1, §1.6 F7

## What this did

The code serves five models on fixed ports (8080 glimmer, 8081 gemma, 8082 granite, 8083 devstral,
8084 qwen; `server/Makefile`), the launchers forward all five (`client/runCrush-common.sh`), and the
crushrc registers a provider for each port that answers and preselects the first. Docs still
described two models on 8080/8081. Rewritten:

- `CLAUDE.md`: the `MODEL=` list, the one-tunnel-forwards-all-five line, and probe-based
  preselection.
- `README.md`: the hand-run tunnel commands (TCP and the unix-socket form) forward all five ports;
  the verify step, the "Network modes" text, the fixed-ports note; `vendor.sh`'s default (one GGUF per
  active model, ~53 GB for the default US set); "12 slash commands".
- `tasks/reference/architecture.md` (diagram and the provider paragraph), `FORKING.md`,
  `tasks/reference/new-hardware-bringup.md`, `tasks/reference/crush-capabilities.md`, `vendor.sh`'s
  and `client/Makefile`'s comments, `client/entrypoint/00-install-minimal.sh`'s curl note.
- Left as written: `tasks/reference/gemma-4-alongside-glimmer.md`, a dated decision record of the
  two-model step.

## Verification

`git grep` outside the archive and review records for "8080/8081", "both model ports", "probes
both", "exactly two", "two serving ports" and `glimmer|gemma)` finds only the crushrc comment that
names the old scheme it replaced.
