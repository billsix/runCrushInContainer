# Context window — how big it is, why it feels small, and how to change it

**Status:** complete
**Started:** 2026-08-20 · **Completed:** 2026-08-20

Answered the maintainer's question ("is there anything in Crush to specify the context limit? Can a
curl command help?"), made the server/client window settings consistent and cross-referenced, and
kept the RAM-safe 32k default.

## What was done

- The core change (pinning Crush's `--context-window` to the server's window so Crush's compaction
  math lines up) had already been applied by the providers task: `client/entrypoint/crushrc` runs
  `model add … --context-window 32768`, matching `server/Makefile` `CTX=32768`.
- **`server/Makefile`**: added a KEEP IN SYNC note on `CTX` pointing at the crushrc
  `--context-window` (the crushrc already pointed back), plus the Metal wired-limit caveat for going
  bigger (`CTX=65536` roughly doubles KV RAM and may exceed the ~24-28 GB default wired limit; raise
  it with `sudo sysctl iogpu.wired_limit_mb`).

## Findings

The effective context is the **smaller** of two limits:

1. **The server's KV-cache window**: llama-server's `-c` (`server/Makefile` `CTX`, 32768). The hard
   cap.
2. **Crush's per-model `context_window`**: drives when Crush auto-summarizes. If it is smaller than
   the server's window, Crush compacts early, which reads as "the context feels small".

A curl reads the server side but cannot change it. Verified 2026-08-20:
`curl -s http://127.0.0.1:8080/v1/models` returned `meta.n_ctx: 32768` (current window) and
`n_ctx_train: 131072` (trained maximum, the ceiling for `-c`). `/props`
(`default_generation_settings.n_ctx`) shows the same.

How Crush uses `context_window` (verified in v0.89.0 source):

- For a runtime-discovered llamacpp provider, the enricher in `internal/discover/llamacpp.go` sets
  `context_window` from the server's `n_ctx` (falling back to `n_ctx_train`) if not already set.
- The auto-summarize trigger in `internal/agent/agent.go`: `context_window == 0` skips compaction;
  otherwise Crush summarizes when remaining tokens fall to 20% of the window (a flat 20k buffer above
  200k). At 32768 that is roughly 26k tokens used.
- `option auto-summarize false` in the crushrc turns compaction off (default on).

How to change it: `make serve CTX=65536` (up to 131072) raises the hard cap, at the cost of KV-cache
RAM on the 36 GB Mac (weights ~16.8 GB); keep `--parallel 1` so the whole window serves one client.
Set the matching `--context-window` in `client/entrypoint/crushrc` whenever `CTX` changes.

## Decisions

- **Kept `CTX` at 32k.** Bigger is RAM-risky on the 36 GB Mac and could not be validated from the
  sandbox; 64k is a one-flag override (plus the matching crushrc value and likely a
  `iogpu.wired_limit_mb` raise) once measured on the Mac.
- **Left `auto-summarize` on.** Disabling compaction trades graceful trimming for errors at the cap;
  that is the maintainer's call, not a default.
- **Not decided:** whether the "small" feeling was the 32k cap or early compaction. That needs a live
  session (degrading well before ~26k tokens means compaction; near 32k means the cap). The
  context-advisor script (`tasks/context-advisor-script.md`) is meant to print the live numbers.

## Related

- `tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md`: its crushrc pins the model with
  `--context-window 32768`; both tasks touch the same `model add` line.
- `tasks/archive/2026/08/21/verify-provider-suppression-airgapped.md`: the natural place to run the
  cap-vs-compaction check.
- `tasks/reference/architecture.md`: server tuning (`CTX`, `--parallel`, the KV-cache-restore note).
