# Add Google Gemma 4 (Apache-2.0) alongside Muse Glimmer — one server, two models, two fixed ports

**Status:** complete
**Completed:** 2026-09-10
**Created:** 2026-09-10 from the maintainer's request (William Emerison Six <billsix@gmail.com>)

## What this did

Added Google's Gemma 4 26B-A4B (Apache-2.0, official Q4_0 QAT GGUFs) as a second model next to Muse
Glimmer: `make vendor` / `./vendor.sh` fetch both, `make serve MODEL=glimmer|gemma` serves either on
its own fixed port (8080 / 8081), the README documents both, and the baked crushrc offered exactly the
two providers, switched with Crush's models dialog. Implemented off the Mac and committed by the
maintainer as `b2e0eeb`. The Metal build, serve and smoke on the Mac plus the client two-model check
were split out to `tasks/verify-gemma-4-on-the-mac.md`. Design and rationale:
`tasks/reference/gemma-4-alongside-glimmer.md` (§4 constraints, §6 as implemented).

**Superseded:** the two-provider, two-port design was replaced on 2026-09-20 by five models on ports
8080–8084 with probe-based autodiscovery in the crushrc (`tasks/reference/model-registry-country-gate-and-checksums.md`).

## Decisions

- **Gemma 4, not Gemma 3:** only Gemma 4 is Apache-2.0 (earlier versions use the custom Gemma Terms of
  Use); the OSI licence bar is the point.
- **26B-A4B MoE** over the 31B dense (William Emerison Six <billsix@gmail.com>, 2026-09-10: "recommended").
- **`LLAMACPP_TAG` `b10353` → `b10883`**, the newest release after 2026-09-04 (maintainer: "I go with
  your recommendation", 2026-09-10). The bump shipped in the same commit; rollback is
  `make llama LLAMACPP_TAG=b10353`.
- **Fixed, non-configurable ports, by request:** Glimmer kept 8080 (every doc, the tunnel and the
  crushrc already used it), Gemma got 8081; the `PORT=` override went away.
- **Both providers are `llamacpp` on loopback**, so no egress patch or
  `tasks/reference/dependency-network-audit.md` entry changed.

## Changes (2026-09-10)

- **`server/Makefile`:** the single-model knobs became a two-row table (`MODELS := glimmer gemma`;
  `MODEL_REPO_<m>`/`MODEL_FILE_<m>`/`MODEL_ALIAS_<m>`/`MODEL_PORT_<m>`), selected by `MODEL ?= glimmer`
  into the old names so every recipe kept its spelling. `PORT` is `override`-assigned from the row
  (`make serve PORT=9999` still serves 8080, checked with `make -n`). An unknown `MODEL=` stops with
  `MODEL=bogus is not one of: glimmer gemma`. `pull` walks both rows with `$(foreach)` (a shell `eval`
  trick was tried first and replaced). `serve-mlx` refuses `MODEL=gemma` rather than serving Glimmer's
  MLX repo on Gemma's port.
- **`MODEL_FILES` changed meaning:** formerly the whole download set, it became an empty-by-default
  extra set pulled from the selected row's repo on top of the two defaults. `vendor.sh FULL=1` still
  presets it to `*.gguf`; `FULL_MODEL_*` stayed Glimmer-only; `make serve MODEL_FILE=<file>` still works.
- **`client/entrypoint/crushrc`:** `provider add gemma-4` on `127.0.0.1:8081` plus
  `model add gemma-4/gemma-4 --context-window 65536`; Glimmer stayed `large`/`small`.
  `client/entrypoint/shell.sh` printed the two-`-L` tunnel and dropped its auto-discovery claim;
  `vendor.sh` messages named both models.
- **Docs:** `README.md` (diagram, models table with the one-at-a-time RAM caveat, Server, download,
  Connecting, client, airgapped rebuild), `CLAUDE.md`, `tasks/reference/architecture.md`,
  `tasks/reference/crush-capabilities.md`.

## Verification (Linux sandbox, 2026-09-10)

`make -n serve|probe|pull|vendor|serve-mlx` for both `MODEL`s and `MODEL=bogus`; `make help`;
`make check-repo MODEL=gemma` → `repo OK: google/gemma-4-26B-A4B-it-qat-q4_0-gguf (2 GGUFs)`
(`gemma-4-26B-it-mmproj.gguf`, `gemma-4-26B_q4_0-it.gguf`); `make pull MODELS=gemma MODEL=gemma` exited
0 with `server/models/gemma-4-26B_q4_0-it.gguf` at 14,439,363,584 bytes (gitignored); `shfmt` clean on
`shell.sh` and `vendor.sh`; `+x` bits intact. Everything needing Metal or a display went to
`tasks/verify-gemma-4-on-the-mac.md`.
