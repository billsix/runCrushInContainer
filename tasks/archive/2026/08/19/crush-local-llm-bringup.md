# Bring up Crush against a local Muse Glimmer server (the basics)

**Status:** complete
**Completed:** 2026-08-19
**Started:** 2026-08-18

## What this did

Stood up the minimal two-machine local-coding-LLM setup, confirmed end to end on 2026-08-19: Crush in
the client container generated against the local Muse Glimmer model over the SSH tunnel.

- **Server (macOS, native):** Meta's Muse Glimmer 30B on a 36 GB Mac Studio via llama.cpp built for
  Metal, serving an OpenAI-compatible endpoint on `127.0.0.1:8080` (loopback only; the sole way in is
  the SSH tunnel).
- **Client (Linux, containerized):** a Podman image with the full runClaudeInContainer toolchain and
  Crush built from source at a pinned tag, run with `--network=host` so `127.0.0.1:8080` in the
  container is the host's `ssh -N -L 8080:127.0.0.1:8080` forward.

Scope was deliberately minimal: no task/stack/personal-config machinery and no auth plumbing. Those were
deferred to `tasks/port-runclaude-conventions-systems.md`. Model, quant and both tool pins are Makefile
variables so a fork can swap them. The durable design and operations knowledge lives in
`tasks/reference/architecture.md`; this file is the work record.

## What was built

- `server/Makefile`: variables (`LLAMACPP_TAG`, `MODEL_REPO`, `MODEL_FILE`, `MODEL_DIR`, `HOST`, `PORT`,
  `CTX`, `NGL`) and targets `deps` / `llama` / `pull` / `serve` / `serve-mlx` / `probe` / `check-repo`,
  plus the repo-root `.gitignore` (models, `llama.cpp/`, venvs, build dirs). `run-fast` (DFlash
  speculative decoding) was noted for later, not built.
- `client/Dockerfile`, `client/Makefile` (`image` / `shell`, `--network=host`, `PROJECT=` mount), and
  `client/entrypoint/{01-install-base.sh,crushrc,shell.sh}`. `01-install-base.sh` was a byte-identical
  copy of runClaudeInContainer's.
- A baked `crushrc` declaring a `llamacpp` provider with the model list omitted, so Crush auto-discovers
  the served model.

## Decisions (2026-08-18)

- One repo, `server/` + `client/`, Makefile-variable template.
- The client runs on Linux and reaches the Mac via `ssh -L` on the host plus `--network=host`.
- Default quant **Q4_K_M** (~16.8 GB). On a 36 GB unified-memory Mac the safe GPU budget is ~24–28 GB:
  Q5_K_M (~20 GB) is the natural step-up, Q6_K is tight, Q8_0 (~31 GB) swaps. The quant ladder lives in
  `tasks/reference/architecture.md`.
- Scaffold both llama.cpp and MLX serve targets; llama.cpp is the default.
- Full toolchain image, everything else barebones.
- Pins: `CRUSH_TAG` = latest stable Crush at implementation time (`v0.89.0`, 2026-08-12, via the Go
  module proxy). `LLAMACPP_TAG` started at the `b10353` floor (first release with Muse Glimmer support),
  to be bumped only to a tag verified on the Mac; the current pin is recorded in
  `tasks/reference/architecture.md`.

## Findings (2026-08-19)

- **Config format:** the modern Crush format is `crushrc` at `~/.config/crush/crushrc` (`crush.json` is
  deprecated), confirmed by `crush dirs`.
- **`base_url` has no `/v1`:** Crush's llamacpp discovery appends `/v1/models` itself
  (`internal/discover/llamacpp.go` in the Crush source), so `http://127.0.0.1:8080` is correct.
- **Repo contents:** the Q4_K_M GGUF is 16.76 GB; a `KQuant-Dynamic-Q4_K_XL` (19.65 GB) is a
  higher-quality 4-bit that still fits; `mmproj` (1.40 GB, vision) is not needed for coding; the DFlash
  drafter is 1.63 GB. Model licence Apache-2.0.
- **Nested build gotcha:** the first nested image build failed at the layer commit with `no space left
  on device`; the 22.3 GB rootfs overflowed the default nested RAM store, fixed then by
  `mount -o remount,size=50g /var/lib/containers`. Superseded: the nested store moved from tmpfs to a
  disk-backed dir 2026-09-27 (`tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`).

## Verification

- On the Linux sandbox: `make venv` + `make check-repo` resolved the HF repo and `MODEL_FILE`; the
  `make pull` command shape pulled a file into `models/`; `go install …crush@v0.89.0` built; the nested
  client image built (22.3 GB) with `crush version v0.89.0` and the baked `crushrc` read by `crush dirs`.
- On the Mac: the Metal build and `serve` ran, and a live Crush session generated against the model
  over the tunnel (2026-08-19).
- Not checked in this task: a multi-step tool-using Crush edit (whether the local model drives the agent
  loop, not just chat).
