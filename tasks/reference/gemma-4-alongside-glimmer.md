# Google's open-weights models: Gemma 4 (Apache-2.0) alongside Muse Glimmer

**Reference document** — what Google's "open" models are, which of them clear this project's
**OSI-approved-license** bar, what it would take to serve one next to Glimmer, and the trade-offs.
Researched 2026-09-10 against Google's own terms page and the Hugging Face API; sizes, filenames
and llama.cpp support **drift** — re-verify at implementation time (`CLAUDE.md`: "Verify
model/tool identifiers before hardcoding them"). The implementation landed 2026-09-10 (§6; work
record `tasks/archive/2026/09/10/add-gemma-4-alongside-glimmer.md`); the Mac verification is `tasks/verify-gemma-4-on-the-mac.md`. Sibling of
`glimmer-models-and-airgap-quant-selection.md`, which this doc does not repeat.

## TL;DR

- **Yes — but only Gemma 4.** Google's earlier Gemma releases (1–3, 3n) are "open weights" under
  the **Gemma Terms of Use**, a custom licence that is *not* OSI-approved: a Prohibited Use
  Policy, redistribution that must carry the same terms, and a clause letting Google "restrict
  (remotely or otherwise)" usage it believes violates the agreement. **Gemma 4** (released
  2026-07) switched to **Apache-2.0**, verified on every `google/gemma-4-*` model card. So the
  licence bar Glimmer clears, Gemma 4 clears too; Gemma 3 does not.
- **Google ships official Q4_0 QAT GGUFs**, exactly Glimmer's "vendor-official GGUF" shape, for
  five sizes. The two that fit this project are the **26B-A4B MoE** (14.4 GB, 3.8B active —
  fast) and the **31B dense** (17.7 GB — Glimmer-class quality), both 256K context, both
  positioned by Google for coding and agentic use.
- **Recommendation: add `google/gemma-4-26B-A4B-it-qat-q4_0-gguf` as the second model**, on its
  own fixed port, as a second `provider add` in the baked crushrc. Reasons in §5.

## 1. The licence question, precisely

| Family | Licence | OSI-approved? | Where verified |
|---|---|---|---|
| Gemma 1, 2, 3, 3n (and ShieldGemma etc.) | Gemma Terms of Use (last modified 2026-04-01) | **No** — custom | `ai.google.dev/gemma/terms`: Prohibited Use Policy incorporated by reference; downstream must accept the same terms; Google "reserves the right to restrict (remotely or otherwise) usage" |
| **Gemma 4** (all variants) | **Apache-2.0** | **Yes** | HF API `license:apache-2.0` on every `google/gemma-4-*` repo; the terms page itself says Gemma 4 "uses a separate Apache 2.0 license" |

The distinction matters for this project specifically because the airgap story redistributes
weights (`vendor.sh`, "carry the repo to the airgap box"). Under the Gemma Terms that
redistribution carries obligations; under Apache-2.0 it does not.

## 2. The Gemma 4 family and its official GGUFs (HF, 2026-09-10)

| Repo (all `google/…`, all `apache-2.0`) | Params | GGUF file | Size | Context | Notes |
|---|---|---|---|---|---|
| `gemma-4-31B-it-qat-q4_0-gguf` | 31B dense | `gemma-4-31B_q4_0-it.gguf` (+ `gemma-4-31B-it-mmproj.gguf`) | **17.7 GB** | 256K | text + image; no audio |
| `gemma-4-26B-A4B-it-qat-q4_0-gguf` | 25.2B total, **3.8B active** (MoE) | `gemma-4-26B_q4_0-it.gguf` (+ `gemma-4-26B-it-mmproj.gguf`) | **14.4 GB** | 256K | text + image; Google's card: "reasoning, agentic workflows, coding" |
| `gemma-4-12B-it-qat-q4_0-gguf` | 12B dense | — | 6.98 GB | 256K | text + image + audio + video |
| `gemma-4-E4B-…` / `gemma-4-E2B-…` | edge sizes | — | small | | for mobile; not coding-agent material |

"QAT" = quantization-aware trained: Google trained these to be served at Q4_0, so a vendor Q4_0 is
closer to full quality than a post-hoc quant. Each repo also has a `…-it-assistant` sibling — a
**draft model for speculative decoding** — with the caveat on the card that the assistant must be a
QAT checkpoint of the same precision as the target. Third-party quant ladders (bartowski, unsloth)
exist as for Glimmer; the same provenance rule applies (straight requants only).

## 3. llama.cpp support

Gemma 4 landed in llama.cpp before the project's pinned `LLAMACPP_TAG` (b10353, 2026-08-10) — but
the conversion fix `#26882` merged 2026-08-12 and the **vision fix `#28335` merged 2026-09-04**.
Text-only serving at the current pin is plausible but **unverified**; bumping to a post-2026-09-04
tag is the safe choice, and `server/Makefile` already says to pin "the newest known-good release",
not the floor. Google's own cards drive `llama-server` with no special flags. **Verify before
pinning**: build at the candidate tag and run `make smoke` against the Gemma GGUF.

## 4. What "alongside" has to mean here — the constraints in the maintainer's ask

1. `make vendor` / `./vendor.sh` pull it too.
2. **One way to run a server, two models, two fixed non-configurable ports.** Today `make serve`
   takes `MODEL_FILE`/`PORT` variables; the ask is a *model argument* that selects the file, alias
   **and** port together, so a port never has to be remembered.
3. The README shows how to run both.
4. Crush offers exactly these two providers (the built-in catalog stays suppressed) and the user
   switches between them the normal Crush way.

Design that satisfies all four (detail in the task):

- **Server**: `make serve MODEL=glimmer` / `make serve MODEL=gemma`, each row of a small table
  selecting `MODEL_FILE`, `MODEL_ALIAS`, `MODEL_REPO` and a **hardcoded port**: Glimmer stays on
  **8080** (every existing doc, tunnel and crushrc references it), Gemma takes **8081**. `probe` and
  `smoke` take the same `MODEL=`. `vendor`/`pull` iterate both rows.
- **Client**: a second `provider add gemma-4 --type llamacpp --base-url http://127.0.0.1:8081`,
  a second `model add gemma-4/gemma-4 …`, `option default-providers false` unchanged. Glimmer
  stays the preselected `large`/`small`. Switching = Crush's models dialog (**`ctrl+l`**, also `ctrl+m`, in v0.89.0 — `internal/ui/model/keys.go:89`; only these two appear because the catalog is suppressed). The SSH tunnel forwards both ports.
- **Running both at once** is the point of two ports, but on the 36 GB Mac Studio Glimmer Q4 +
  64K context already sits near Metal's wired limit; Gemma 26B-A4B adds ~14 GB of weights plus its
  own KV cache. Expect to run **one at a time** on that box, or shrink `CTX` for the second. Two
  ports still pay off: no port juggling, and both can run on a bigger machine.

## 5. Trade-offs and the recommendation

| | Gemma 4 26B-A4B (MoE) | Gemma 4 31B (dense) |
|---|---|---|
| Weights | 14.4 GB | 17.7 GB |
| Speed on Metal | **fast** — 3.8B active per token | Glimmer-like (30B-class) |
| Quality | strong for its cost; Google cites Codeforces ELO 1718 | the top of the family |
| RAM headroom next to Glimmer | best of the two | tightest |
| Vision (mmproj) | optional, not needed for Crush | same |

**Recommend the 26B-A4B.** It is the variant that actually fits *alongside* Glimmer on the
existing box, it is the one Google positions for agentic coding, and its speed changes the
experience of an interactive agent more than the 31B's marginal quality would. The 31B is a
one-line change of the table row if the maintainer disagrees after trying it.

Things the maintainer should know before saying go:

- **Context sizing**: Gemma 4 supports 256K; the project sizes `CTX` by RAM, not by the model's
  ceiling. Start Gemma at the same 65536 and revisit (`tasks/archive/2026/08/20/context-window-sizing.md`).
- **The `crushrc` `--context-window` must match per model**; two `model add` lines, two values.
- **Egress patches**: adding a provider row in crushrc adds no network path — both are loopback
  `llamacpp` providers; nothing in `dependency-network-audit.md` changes.
- **Gemma 3 must not sneak in**: any `gemma-3-*` repo fails the licence bar. The `check-repo`
  step and the HF `license:` tag are the guard.

## 6. As implemented (2026-09-10) — how the two-model server actually works

Everything in §4 was built as designed; the details a maintainer needs when touching it:

- **The table is four variables per row** in `server/Makefile` — `MODEL_REPO_<m>`, `MODEL_FILE_<m>`,
  `MODEL_ALIAS_<m>`, `MODEL_PORT_<m>` for `MODELS := glimmer gemma` — and `MODEL ?= glimmer` copies
  the chosen row into the *old* names (`MODEL_REPO`, `MODEL_FILE`, `MODEL_ALIAS`, `PORT`), so every
  recipe and doc reference kept its spelling. Adding a third model is four lines plus a `MODELS`
  entry, a crushrc provider/model pair, and a tunnel `-L`. An unknown `MODEL=` is a `$(error …)`.
- **`PORT` is `override`-assigned** from the row: `make serve PORT=9999` still serves on 8080. That
  is the "non-configurable" in the ask made mechanical — the crushrc `--base-url`s, the README/`shell.sh`
  tunnel line and the Makefile row are the three places a port lives, and they must move together.
- **`pull`/`vendor` walk both rows with a make-time `$(foreach)`** (a shell-side `eval` of
  `MODEL_REPO_$m` was tried first and dropped — make can expand the row, the shell can't). For a
  one-row pull, override the list: `make pull MODELS=gemma MODEL=gemma` (how the 14.4 GB Gemma file
  was fetched in the Linux sandbox without also pulling Glimmer).
- **`MODEL_FILES` changed meaning**: it was *the* download set (with `MODEL_FILE` = its first entry);
  it is now an **empty-by-default extra set** from the *selected* row's repo, on top of the two
  defaults. `vendor.sh FULL=1` still presets `*.gguf` and yields the same Glimmer quant ladder as
  before, plus the Gemma default; `make pull MODEL=gemma MODEL_FILES="*mmproj*"` adds the vision
  projector. `FULL_MODEL_*` stays Glimmer-only. `make serve MODEL_FILE=<other quant>` still works —
  a command-line assignment beats `:=`.
- **`serve-mlx` refuses `MODEL=gemma`** (one-line message, exit 1): no MLX repo was chosen for
  Gemma 4, and serving Glimmer's MLX build on Gemma's port would be the worst kind of wrong.
- **`LLAMACPP_TAG` went `b10353` → `b10883`** (2026-09-09 release) in the same commit as the rows —
  the maintainer chose "newest after the 2026-09-04 vision fix (#28335)". Until the Mac `smoke`s both
  models at that tag it is a *candidate*; `make llama LLAMACPP_TAG=b10353` is the one-flag rollback.
- **Client**: `provider add gemma-4` on `127.0.0.1:8081` + `model add gemma-4/gemma-4
  --context-window 65536`; Glimmer stays `large`/`small`; `shell.sh` prints the two-`-L` tunnel and
  no longer says "auto-discovers" (models have been pinned since 2026-08-20).
- **Verified off the Mac**: `make check-repo MODEL=gemma` lists exactly `gemma-4-26B-it-mmproj.gguf`
  and `gemma-4-26B_q4_0-it.gguf`; the real `pull` target fetched the latter (14,439,363,584 bytes).
  **Not yet verified**: anything needing Metal — see `tasks/verify-gemma-4-on-the-mac.md`.

## Sources

- Gemma Terms of Use — https://ai.google.dev/gemma/terms (custom terms; notes Gemma 4 is Apache-2.0)
- Gemma 4 licence page — https://ai.google.dev/gemma/docs/gemma_4_license (linked from every card)
- HF API listing, `author=google&search=gemma-4` — licence tags per repo (2026-09-10)
- Model cards: `google/gemma-4-31B-it-qat-q4_0-gguf`, `google/gemma-4-26B-A4B-it-qat-q4_0-gguf`,
  `google/gemma-4-12B-it-qat-q4_0-gguf`; HF API `siblings` for the exact GGUF filenames
- llama.cpp merged PRs: `#26882` (2026-08-12, Gemma 4 conversion), `#28335` (2026-09-04, Gemma 4 vision)
