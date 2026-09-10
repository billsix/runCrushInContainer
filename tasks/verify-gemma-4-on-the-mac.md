# Verify Gemma 4 on the Mac — build at `b10883`, serve, smoke, and confirm the client sees two models

**Status:** blocked — human-gated; only the maintainer can run the Metal build and the display-side
Crush check. Created 2026-09-10 at the archive of `tasks/archive/2026/09/10/add-gemma-4-alongside-glimmer.md`
(William Emerison Six <billsix@gmail.com> asked for the test to become its own task).
**Priority:** 3
**Difficulty:** 2
**Blocked on:** the maintainer running the `[MAC]` and `[CONTAINER]` steps below on the Mac Studio +
Linux host.
**Recheck:** `[MAC]` `cd server && make probe MODEL=gemma` → JSON with `"id":"gemma-4"` means the Mac
side has been done; `[CONTAINER]` `crush models` listing both `muse-glimmer` and `gemma-4` means the
client side has. Both true = cleared; tick the boxes and archive.

## BLUF

The two-model server (`make serve MODEL=glimmer|gemma`, fixed ports 8080/8081, `LLAMACPP_TAG`
`b10883`) is implemented, committed (`b2e0eeb`) and exercised everywhere except on Metal. Done means:
`make llama` builds at `b10883`; Gemma 4 answers `probe` and `smoke` on 8081; Glimmer still answers
both on 8080 at the new tag (the regression check on the bump); and a rebuilt client shows exactly the
two models in `ctrl+l` and routes a Gemma chat to 8081. Then record the numbers and archive.

## Context — read first

- `tasks/reference/gemma-4-alongside-glimmer.md` §6 — how the table, `override PORT`, `MODEL_FILES`
  and the tag bump work; §4–5 for why 26B-A4B and why fixed ports.
- `tasks/reference/new-hardware-bringup.md` — what `probe` and `smoke` each prove, the three
  server-log lines that decide quant → `NGL` → `CTX` → `NP`. This run is that runbook applied to a
  second model on the same box.
- `server/Makefile` (the table, top of file) and `client/entrypoint/crushrc` (the two providers).
- Already verified off the Mac (2026-09-10): `make check-repo MODEL=gemma`; the real `pull` fetched
  `gemma-4-26B_q4_0-it.gguf` (14.44 GB); `make -n` for every target and both `MODEL`s; shfmt.
  Work record: `tasks/archive/2026/09/10/add-gemma-4-alongside-glimmer.md`.

## Steps

1. `[MAC]` `cd server && make llama` — first build at `b10883`. **If it fails to build**, that is the
   tag, not Gemma: `make llama LLAMACPP_TAG=b10353` restores the last known-good and this task's
   finding becomes "pick a tag between" (record it here).
2. `[MAC]` `make pull` (fetches both GGUFs; Glimmer is already there, Gemma is ~14.4 GB).
3. `[MAC]` `make serve MODEL=gemma`; second terminal: `make probe MODEL=gemma` (expect
   `"id":"gemma-4"` and the live `n_ctx`), then `make smoke MODEL=gemma` (expect `OK`). **Watch the
   serve log's memory line** — 26B-A4B Q4_0 + 64k KV should fit 36 GB alone; if it doesn't,
   `make serve MODEL=gemma CTX=32768` and write the number into
   `tasks/reference/new-hardware-bringup.md`. Note the t/s (Metal-class is tens of t/s; the MoE
   should be faster than Glimmer's ~21 t/s).
4. `[MAC]` stop it; `make serve` (Glimmer) + `make probe` + `make smoke` — the regression check on
   the tag bump. Rollback if it misbehaves: `make llama LLAMACPP_TAG=b10353`, and say so here.
5. `[LINUX HOST]` tunnel both ports: `ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081
   you@mac-studio.local`; `curl -s http://127.0.0.1:8081/v1/models` while Gemma is served.
6. `[LINUX HOST]` `make -C client image` (picks up the new crushrc), then `make -C client shell`;
   `[CONTAINER]` `crush models` → exactly `muse-glimmer` and `gemma-4`, no catalog entries; in
   `crush`, `ctrl+l`, pick Gemma 4, send one prompt, confirm the request lands in the 8081 serve log.

## Record when done

- [ ] `make llama` at `b10883` built (or the tag actually used: ______).
- [ ] Gemma `probe` + `smoke` OK on 8081; t/s ______; memory line ______; `CTX` used ______.
- [ ] Glimmer `probe` + `smoke` OK on 8080 at the new tag.
- [ ] Client: two models in `ctrl+l`; Gemma chat reached 8081.

Then: update `tasks/reference/architecture.md` "Verification status" (drop the *pending* sentence,
state the tag as known-good) and `tasks/reference/gemma-4-alongside-glimmer.md` §6 (last bullet),
add Gemma's numbers to `tasks/reference/new-hardware-bringup.md` if they differ from Glimmer's story,
and archive this task.
