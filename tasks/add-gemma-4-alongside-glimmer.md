# Add Google Gemma 4 (Apache-2.0) alongside Muse Glimmer — one server, two models, two fixed ports

**Status:** approved 2026-09-10, no open questions — **Gemma 4 26B-A4B**, and **bump `LLAMACPP_TAG`**
to the newest release after 2026-09-04 (both the maintainer's decisions). Not started. Order of work:
this task first among the 2026-09-10 batch — everything but `make serve`/`make smoke` can be done
off the Mac; those two are the maintainer's final step. Created 2026-09-10 from
the maintainer's request (William Emerison Six <billsix@gmail.com>).
**Priority:** 4
**Difficulty:** 4

## BLUF

Google's **Gemma 4** family is **Apache-2.0** — the same OSI-approved bar Glimmer clears — and
ships **official Q4_0 QAT GGUFs**, so it slots into this project's existing llama.cpp path. Earlier
Gemma versions are NOT (custom Gemma Terms of Use). Done means: `make vendor` / `./vendor.sh`
fetch both models; `make serve MODEL=glimmer|gemma` runs either on its own **fixed** port (8080 /
8081); the README shows both; the baked crushrc offers exactly these two providers and the user
switches with Crush's models dialog. Research and trade-offs:
`tasks/reference/gemma-4-alongside-glimmer.md`.

## Context — read first

- `tasks/reference/gemma-4-alongside-glimmer.md` — the licence verification, the family table
  with exact GGUF filenames and sizes, llama.cpp support status, and why the **26B-A4B MoE** is
  recommended over the 31B dense.
- `server/Makefile` — today's single-model knobs: `MODEL_REPO`, `MODEL_FILES`, `MODEL_FILE`,
  `MODEL_ALIAS`, `PORT`, `CTX`; `vendor` → `pull`; `serve`/`probe`/`smoke`.
- `vendor.sh` — runs the server `vendor` inside the client image; forwards `MODEL_FILES` etc.
- `client/entrypoint/crushrc` — one `provider add muse-glimmer` on `127.0.0.1:8080`, explicit
  `model add`, `option default-providers false` (catalog suppressed), `model large/small` preselect.
- `tasks/reference/crush-capabilities.md` § "Provider & model selection" — why models are pinned
  explicitly (discovery deletes an unreachable provider), and that the built-in catalog stays off.
- `README.md` §§ "Server", "Connecting", "Client" — where the run instructions live.

**Decisions already made (with rationale):**

- **Gemma 4, not Gemma 3.** Only Gemma 4 is Apache-2.0; the licence bar is the whole point.
- **Ports are fixed and not configurable, by request:** Glimmer keeps **8080** (every doc, the
  tunnel and the crushrc already say so); Gemma gets **8081**. A `PORT=` override goes away.
- **Both providers are `llamacpp` on loopback**, so no egress patch or network-audit entry
  changes (`tasks/reference/dependency-network-audit.md` stays true).

## Plan

### 1. Server (`server/Makefile`) — a model table, one `MODEL=` argument

Replace the single-model variables with a two-row table keyed by `MODEL` (default `glimmer`, so
every existing invocation behaves exactly as today):

| `MODEL=` | `MODEL_REPO` | `MODEL_FILE` | `MODEL_ALIAS` | port |
|---|---|---|---|---|
| `glimmer` | `meta-models/Muse-Glimmer-30B-GGUF` | `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` | `muse-glimmer` | **8080** |
| `gemma` | `google/gemma-4-26B-A4B-it-qat-q4_0-gguf` | `gemma-4-26B_q4_0-it.gguf` | `gemma-4` | **8081** |

- `serve`, `probe`, `smoke`, `serve-mlx` (Gemma: skip or find an MLX repo — separate decision)
  read their file/alias/port from the selected row. Unknown `MODEL=` → a clear error listing the
  two names.
- `pull` and `vendor` iterate **both** rows (the airgap carries both GGUFs); `FULL_MODEL_*`
  opt-in stays Glimmer-only unless asked. `check-repo` takes `MODEL=` too.
- `CTX`/`NGL`/`NP` stay shared knobs; start Gemma at the same `CTX=65536` (§ trade-offs in the
  reference doc — 256K is the model's ceiling, RAM is the constraint).
- **Verify the filenames against Hugging Face first** (`make check-repo MODEL=gemma`), per
  `CLAUDE.md`; the names above came from the HF API on 2026-09-10.
- **Bump `LLAMACPP_TAG`** to a release after 2026-09-04 (Gemma 4 vision fix `#28335`); confirm
  with `make llama && make serve MODEL=gemma && make smoke MODEL=gemma`. Record the tag chosen.

### 2. `vendor.sh`

No structural change: the server `vendor` step now pulls both rows. Update its header comment
("ONE model quant" → "both models' official Q4 GGUFs") and the `FULL=1` note. Byte budget: +14.4 GB.

### 3. Client (`client/entrypoint/crushrc`)

```
provider add gemma-4 --name "Gemma 4 26B-A4B (local llama.cpp)" --type llamacpp \
  --base-url "http://127.0.0.1:8081" --api-key "local-no-key-needed"
model add gemma-4/gemma-4 --name "Gemma 4 26B-A4B" --context-window 65536
```

Glimmer stays preselected for `large`/`small`. `option default-providers false` unchanged, so the
models dialog (**`ctrl+l`** / `ctrl+m` in Crush v0.89.0) lists exactly the two. Keep the alias
`gemma-4` in sync with the server row, as `muse-glimmer` is today. Update the crushrc header
comment and the tunnel line (§4).

### 4. README + `client/entrypoint/shell.sh` hint

- "Server": `make serve MODEL=glimmer` and `make serve MODEL=gemma`, each labelled `[MAC]`, with
  the port each answers on, and the one-line RAM caveat: on a 36 GB Mac run one at a time.
- "Connecting": the tunnel forwards both ports —
  `ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 you@mac-studio`; `shell.sh` prints the
  same.
- "The model" section gains a short Gemma 4 paragraph pointing at the reference doc for the
  licence verification.
- "Airgapped rebuild": both GGUFs ride along.

### 5. Docs to touch with the unit (doc deltas ship with the code)

`CLAUDE.md` (server knobs list, the two ports), `tasks/reference/architecture.md` (server section
+ verification status), `tasks/reference/crush-capabilities.md` (two providers now), this task.

## Verification / done-state

- `make check-repo MODEL=gemma` lists `gemma-4-26B_q4_0-it.gguf`; `make pull MODEL=gemma` (and
  plain `make pull`) fetches it; `./vendor.sh` leaves both GGUFs in `server/models/`.
- `make serve MODEL=gemma` answers `make probe MODEL=gemma` on 8081 with alias `gemma-4`, and
  `make smoke MODEL=gemma` generates. Same for `glimmer` on 8080, unchanged.
- In the client, `ctrl+l` shows exactly two models; selecting Gemma routes a chat to 8081 (watch
  the llama-server log). No catalog entries appear.
- `client/entrypoint/format.sh` green; `make -C client image` builds.

## Open questions

1. ~~**Which Gemma 4?**~~ **RESOLVED 2026-09-10: 26B-A4B** (William Emerison Six <billsix@gmail.com>: "recommended").
2. ~~**Which `LLAMACPP_TAG`?**~~ **RESOLVED 2026-09-10: the newest release after 2026-09-04**
   (maintainer: "I go with your recommendation"), picked from the llama.cpp releases page at
   implementation and verified by `make smoke MODEL=gemma` on the Mac. The bump lands in the same
   commit as the Gemma rows, so if Glimmer misbehaves at the new tag, `make serve MODEL=glimmer
   && make smoke` is the first check and `LLAMACPP_TAG=b10353` on the command line is the
   one-flag rollback.
