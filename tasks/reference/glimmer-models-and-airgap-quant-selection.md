# Muse Glimmer model family & GGUF quant selection for airgap

**Reference document** — a survey of Meta's Muse Glimmer model family and the third-party
quantization landscape, plus a **hardware-deferred** recommendation for what to vendor to an
**airgapped** box where transfer bytes are expensive and **Apache-2.0 is required**. Not a task; no
resolution needed now — consult it when the airgap target hardware is chosen. **Everything below was
gathered from Hugging Face on 2026-08-25; sizes/licenses drift, so re-verify at vendoring time** (the
repo convention: confirm model identifiers against HF before hardcoding — see `CLAUDE.md`). Sources at
the bottom. Related: `tasks/verify-vendor-pulls-all-quants.md`, `tasks/reference/architecture.md`.

## TL;DR (the deferred recommendation)

- **Format: GGUF, always** — it's the only backend-agnostic option, so it works whatever the airgap box
  turns out to be (CPU / CUDA / Metal / ROCm via llama.cpp). Every other format is hardware-locked (see
  §4) — skip them.
- **Transfer ONE quant, not a ladder, and not the base weights.** High transfer cost ⇒ pick the single
  quant that fits the target box's RAM; you choose *before* transfer, so there is no reason to move the
  ~60 GB BF16 base.
- **Default pick: `Q4_K_M` (~16.8 GB) from Meta's own `meta-models/Muse-Glimmer-30B-GGUF`** —
  authoritative, `apache-2.0`, and it's exactly what this project already defaults to. Optionally add
  the **mmproj** (~1.4 GB) if you need image input and the **dflash** drafter (~1.6 GB) for
  speculative-decoding speed.
- **Decision rule by the airgap box's RAM/VRAM** (transfer only the one you land on):
  **≤16 GB → unsloth `UD-Q4_K_XL` (15.9 GB)** · **~24 GB → `Q4_K_M` (16.8 GB)** ·
  **~32 GB → `Q5_K_M` (~20 GB)** · **≥40 GB → `Q6_K` (~23 GB)**.

## 1. Meta's official Glimmer family (org `meta-models`, all `apache-2.0`)

| Repo | What it is | Format / size |
| --- | --- | --- |
| `meta-models/Muse-Glimmer-30B` | Full-precision base | BF16 safetensors, **59.6 GB** (2 shards) + config/tokenizer/`chat_template.jinja` |
| `meta-models/Muse-Glimmer-30B-GGUF` | llama.cpp quants | **only `Q4_K_M` 16.8 GB + `Q4_K_XL` 19.7 GB**, plus `mmproj` 1.4 GB (vision) and `dflash` 1.6 GB (drafter). **No Q5/Q6/Q8, no BF16** here — the card says "use the base repo for full precision." |
| `meta-models/Muse-Glimmer-30B-assistant` | Small drafter variant for speculative decoding | safetensors + GGUF. **Size unclear** — the org listing tagged it ~3B, the card text said 30B; verify before relying on it. |
| `meta-models/Muse-Glimmer-30B-ExecuTorch-PTE` | ExecuTorch `.pte` exports (CUDA sm80+, Metal) | **Not usable by llama.cpp** — needs the ExecuTorch runtime + a `muse_glimmer_worker` binary built from source. Skip for this project. |

The model is **multimodal** (a ~1.8-2B frozen ViT-G/14 "Perception Encoder" bolted onto a ~28B text
decoder, distilled from an internal "Muse"). Vision needs the **mmproj** GGUF alongside the text quant.

## 2. Third-party quant landscape

**Straight requants — trustworthy, `apache-2.0` (inherit it), fill the ladder Meta omits:**

- **`bartowski/Muse-Glimmer-30B-GGUF`** — the full ladder, `apache-2.0`, includes `mmproj` (f16/bf16).
  Sizes (GB): IQ2_XXS 8.92 · Q2_K 11.04 · Q3_K_M 13.96 · IQ4_XS 15.44 · Q4_K_S 16.32 · **Q4_K_M 17.31** ·
  Q4_K_L 18.30 · **Q5_K_M 20.11** · Q5_K_L 20.94 · **Q6_K 23.41** · Q8_0 29.61 · BF16 55.73. Card marks
  Q4_K_M / Q4_K_L / Q5_* / Q6_* "recommended."
- **`unsloth/Muse-Glimmer-30B-GGUF`** — "Unsloth Dynamic" calibrated quants, `apache-2.0`, includes the
  perception encoder. Notable sizes (GB): **UD-Q4_K_XL 15.9** (smaller than a plain Q4_K_M, calibrated) ·
  **UD-Q5_K_M 19.2** · UD-Q6_K_XL 26.3 · Q8_0 29.6 · BF16 55.7.

**Avoid — modified finetunes, not Meta's weights** (even when tagged `apache-2.0` — the license isn't
the problem, the provenance is): `mradermacher/…-uncensored-GGUF` (quant of TrevorJS's abliterated
finetune), `…-Abliterated-…`, `…-Heretic-Uncensored-…`, `…-CRACK-…`, `vcruz305/…-Hermes-Agentic`,
`sequelbox/…-Tachibana-Agent`, etc. These are re-tuned models, not the base coder.

## 3. Non-GGUF formats — skip for a hardware-independent airgap

All exist and are mostly `apache-2.0`, but each is **locked to one runtime/hardware**, so none survive
"I don't know the airgap hardware yet":

- **MLX** (`mlx-community/…-4bit/8bit`, `RadixArk/…-MLX`) — Apple-Silicon only. (Relevant *only* if the
  airgap box is also a Mac and you serve via `make serve-mlx`.)
- **exl3** (`turboderp/…-exl3`) — ExLlamaV3, NVIDIA-only.
- **ExecuTorch `.pte`** (Meta's own) — ExecuTorch runtime only.
- **FP8 / NVFP4 / INT4** (`RedHatAI/…`) — vLLM on specific NVIDIA GPUs.

## 4. Quant sweet spot for a coding agent

- Below Q4 (IQ2/Q2/Q3) coding quality degrades where it hurts (precise tokens) — **skip for a coder**.
- Q8_0 (~30 GB) and BF16 (~56-60 GB) are **wasteful** for the marginal quality — skip for transfer.
- The useful band is **Q4_K_M → Q6_K (~17-23 GB)**. Coding benefits from both model quality *and* a large
  context window, and on a fixed RAM budget those trade off — a bigger quant leaves less room for
  context. So prefer the **smaller end of the band unless the box has clear RAM headroom**: `Q4_K_M`
  (or unsloth `UD-Q4_K_XL`, ~1 GB smaller, calibrated) is the balanced default; step up to `Q5_K_M` /
  `Q6_K` only with spare RAM.

## 5. License summary

Meta's 4 repos and the straight requants (bartowski, unsloth) are all **`apache-2.0`** — unrestricted
commercial use/modification/redistribution. The Apache requirement is easily met; the real filter is
**"unmodified Meta weights"** (§2's "avoid" list), not the license tag.

## 6. Implication for this repo's vendor path (why the current "pull all" is wrong for airgap)

`vendor.sh`'s `FULL=1` presets `MODEL_FILES=*.gguf` (all Meta quants = just 2) **plus
`FULL_MODEL_FILES=*.safetensors` from the base repo (~60 GB)**. For a high-cost airgap transfer, pulling
the 60 GB base is precisely the wrong default. The airgap-optimal shape is **"select one quant," not
"pull everything"**:

- Add a single-quant selector (e.g. `QUANT=Q4_K_M`) as the vendoring default; make "everything" a rare,
  explicit opt-in.
- To reach quants **Meta doesn't publish** (Q5_K_M / Q6_K / the IQ ladder), point `MODEL_REPO` at
  **`bartowski/…-GGUF`** or **`unsloth/…-GGUF`** (both `apache-2.0`) — Meta's GGUF repo only has the two
  Q4 variants.
- `FULL_MODEL_FILES=*.safetensors` also omits `config.json`/tokenizer, so the vendored base is **not
  runnable as-is** — another reason not to make it the airgap default.

This reframes `tasks/verify-vendor-pulls-all-quants.md` from "prove pull-all grabs everything" toward
"airgap-optimal single-quant selection." Deferred until the airgap hardware — and thus the target
quant — is known.

## Sources (fetched 2026-08-25)

- Meta org: <https://huggingface.co/meta-models>
- Meta GGUF: <https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF> · Base (BF16):
  <https://huggingface.co/meta-models/Muse-Glimmer-30B/tree/main>
- bartowski GGUF: <https://huggingface.co/bartowski/Muse-Glimmer-30B-GGUF>
- unsloth GGUF: <https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF>
- HF blog "Muse Glimmer": <https://huggingface.co/blog/muse-glimmer>
