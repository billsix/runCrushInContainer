# Context window — how big it is, why it feels small, and how to change it

**Status:** researched — findings + how-to below; needs go-ahead on any config change (nothing applied)
**Priority:** 4
**Difficulty:** 2
**Started:** 2026-08-20

## The question (maintainer, 2026-08-20)

"Is there anything in Crush to specify the context limit? The context feels small and I don't know
how to change it. Can a curl command help?"

## Short answer

There are **two separate limits**, and the effective context is the **smaller** of them:

1. **The server's KV-cache window** — llama-server's `-c` flag (our `server/Makefile` `CTX`, currently
   **32768**). This is the *hard* cap: the model physically cannot attend beyond it.
2. **Crush's per-model `context_window`** — a number in Crush's model config that drives **when Crush
   auto-summarizes** (compacts) the conversation. If this is smaller than the server's window, Crush
   starts throwing away / summarizing history early — which is exactly what "the context feels small"
   looks like even though the server could hold more.

**A curl helps you READ the server side** (not change it): you already ran it, and it answered the
question — see below. Changing the limit is done in the `Makefile` (server) and `crushrc` (client),
not via curl.

## What the curl already told us (verified 2026-08-20)

`curl -s http://127.0.0.1:8080/v1/models` returned, in `meta`:

- **`n_ctx: 32768`** — the server's *current* context window (what `-c`/`CTX` is set to).
- **`n_ctx_train: 131072`** — the model's *trained maximum*. This is the ceiling you can raise `-c`
  to (RAM permitting); going above it degrades quality.

So the server is currently at 32k out of a possible 131k. (llama-server also exposes `/props`, whose
`default_generation_settings.n_ctx` shows the same number — either curl works as the read.)

## How Crush uses `context_window` (verified in v0.89.0 source)

- For a **llamacpp** provider discovered at runtime, Crush's enricher **reads the server's `n_ctx`**
  and sets the model's `context_window` to it (`internal/discover/llamacpp.go:38-75`, prefers `n_ctx`,
  falls back to `n_ctx_train`) — but only if it isn't already set.
- Auto-summarize trigger (`internal/agent/agent.go:1038-1053`): let `cw = context_window`.
  - **`cw == 0` (unknown) → auto-summarize is SKIPPED** (Crush won't compact — it deliberately avoids
    truncating local models whose window it doesn't know).
  - Otherwise Crush summarizes when `remaining <= threshold`, where `threshold = 20% of cw` (or a flat
    20k buffer if `cw > 200k`). So at `cw = 32768` it compacts at roughly **26k tokens used**.
- **`option auto-summarize`** (crushrc; `disable_auto_summarize`, default ON — `config.go:321`,
  `options.go:189`): `option auto-summarize false` turns compaction OFF entirely.

**So "feels small" has two plausible causes:**
- **(a) The server cap (32k) is genuinely the limit** — raise it (below).
- **(b) Crush is compacting at ~80% of its `context_window`** — either its window is set low, or 32k
  simply isn't much for a long coding session, and auto-summarize is trimming history. Setting the
  window correctly and/or tuning auto-summarize addresses this.

## How to change it

### Raise the server's real window (the hard cap)

`server/Makefile` already parameterizes it: **`make serve CTX=65536`** (or higher, up to `131072`).
This is the only place that actually enlarges what the model can attend to.

- **Cost: KV-cache RAM grows with context.** On the 36 GB Mac with Q4 weights (~16.8 GB), 32k is
  comfortable; doubling to 64k roughly doubles the KV-cache RAM, and 131k is likely too much to fit
  alongside weights + OS — measure before committing (watch for slowdowns / the "failed to restore kv
  cache" log noted in `tasks/reference/architecture.md`). Keep `--parallel 1` (already the default) so
  the whole window serves the one client rather than being divided across slots.

### Tell Crush the window (so it compacts at the right point, not early)

In `client/entrypoint/crushrc`, pin it explicitly on the model:

```sh
model add muse-glimmer/<id> --context-window 32768   # match the server's -c / CTX
```

(Keep this number in sync with `CTX`.) If instead you rely on runtime discovery, the llamacpp enricher
sets `context_window` from the server's `n_ctx` automatically — but pinning is deterministic and
offline-safe, and it ties into `tasks/suppress-embedded-provider-catalog.md`, whose proposed crushrc
already includes `--context-window 32768`.

### If Crush is summarizing too aggressively

`option auto-summarize false` in `crushrc` disables compaction — Crush then uses the full window up to
the server cap (and will error rather than summarize if you exceed it). Leave it ON if you prefer
graceful degradation on very long sessions.

## Recommendation

1. Decide a target window. **32k is a reasonable default**; if sessions feel cramped, try **64k**
   (`make serve CTX=65536`) and watch Mac RAM/throughput.
2. Whatever `CTX` you pick, **set the matching `--context-window` in the crushrc** so Crush's
   compaction math lines up with the server (this is the piece most likely fixing "feels small").
3. Only disable auto-summarize if you specifically want no history trimming.

## Open questions

1. **What target context size do you want** — keep 32k, or go to 64k / higher? This drives the `CTX`
   value and the Mac RAM budget (larger = more KV RAM; 131k likely won't fit on 36 GB with Q4).
2. **Was the "small" feeling from the 32k cap, or from Crush compacting early?** A quick way to tell on
   the next session: if it degrades well before ~26k tokens, it's the `context_window`/auto-summarize
   side (fix in crushrc); if it degrades near 32k, raise `CTX`. Recommend setting the crushrc
   `--context-window` to match first (cheap), then raising `CTX` only if still cramped.

## Cross-links

- `tasks/suppress-embedded-provider-catalog.md` — its proposed crushrc already pins the model with
  `--context-window 32768`; these two tasks touch the same `model add` line.
- `tasks/reference/architecture.md` — server tuning (`CTX`, `--parallel`, the KV-cache-restore note).
