# Wire the new-hardware bring-up runbook into the README, and validate it on real hardware

**Status:** in progress — the runbook is written and the README now points at it (Server section:
`probe`/`smoke` glossed + the pointer; Connecting: the two-port tunnel), both 2026-09-10 at the
maintainer's "document it for the user". **Remaining: walk it on a real second box** (plan §3–4).
This lives in runCrushInContainer because the llama.cpp server does; runClaudeInContainer has no
model server (Claude Code talks to Anthropic's API), so there is nothing to probe there. Created at the maintainer's request (William
Emerison Six <billsix@gmail.com>): explain concisely how to use `make probe` on new hardware so
Crush runs well there.
**Priority:** 5
**Difficulty:** 2

## BLUF

`make probe` and `make smoke` exist and the README mentions `probe` in one line, but there was no
"first hour on a new machine" sequence — which knob to size first, what the server log lines mean,
what to record. That is now `tasks/reference/new-hardware-bringup.md`. Done means the README's
Server section points at it in one line, the runbook has been walked once on a machine other than
the 36 GB Mac Studio (the airgap box is the obvious candidate), and the numbers it asks for are
recorded in `architecture.md` › "Verification status".

## Context — read first

- `tasks/reference/new-hardware-bringup.md` — the runbook (probe → smoke → quant → NGL → CTX → NP,
  the three log lines, the two silent failures).
- `README.md` § "Server — on the Mac (native)" — `make probe` is listed with no explanation of
  what a pass proves; `make smoke` is not listed at all.
- `server/Makefile` — `probe`, `smoke`, and the `CTX` comment block the runbook condenses.
- Note: this belongs to runCrushInContainer; runClaudeInContainer has no probe command (the
  request named that repo, but the server lives here).

## Plan

1. ~~README § Server:~~ DONE 2026-09-10 — add `make smoke` after `make probe` in the command block, one-line glosses
   for each ("answers?" / "generates?"), and a single pointer: "New machine? Follow
   `tasks/reference/new-hardware-bringup.md`." Keep the README commands-forward; the why stays in
   the runbook.
2. `README.md` § "Airgapped rebuild": one line (not yet done) — after `make llama` on the airgap box, run the
   runbook's §1–2 before wiring the client.
3. `tasks/reference/architecture.md` › "Verification status": add a per-box row template
   (box, quant, `CTX`/`NGL`/`NP`, tok/s, prompt-eval, peak memory).
4. On the next new machine: walk the runbook, fill the row, correct anything the runbook got
   wrong (its numbers are from the one Mac Studio).

## Verification / done-state

README diff is ≤ 6 lines; runbook walked once on a second box with its row recorded; `probe`/
`smoke` semantics in the runbook match what the targets actually do (re-read `server/Makefile`).

## Open questions

1. Should `make smoke` also print tokens/s (parse the server's timing from the response's
   `timings` field, which llama-server returns)? Recommend yes — it turns the runbook's
   "measure once" into one command. Small Makefile change; separate from this task if preferred.
