# runCrushInContainer — architecture & operations

**Reference document** — how the two halves fit together, the pins, and the gotchas learned
during bring-up. Not a task; update in place. Last updated 2026-08-19.

## What this is

A local coding LLM (Meta **Muse Glimmer 30B**) served on a Mac, driven by **Crush** (Charm's
terminal agent, `github.com/charmbracelet/crush`) from a disposable Linux container. A
sibling/template of `github.com/billsix/runClaudeInContainer`. Two machines, one SSH tunnel:

```
[MAC]  llama.cpp (Metal) → llama-server on 127.0.0.1:8080 (OpenAI /v1)
          ▲  ssh -N -L 8080:127.0.0.1:8080 you@mac      (run ON the Linux host)
[LINUX HOST]  localhost:8080
[CONTAINER]  crush → http://127.0.0.1:8080  (podman run --network=host)
```

## Server (`server/`, macOS-native — NOT containerized)

- **llama.cpp pinned** via `LLAMACPP_TAG` (`server/Makefile`). Muse Glimmer support landed in
  release **`b10353`** (2026-08-10) — that's the floor. Decision: pin the newest *known-good*
  tag ≥ that, chosen when building on the Mac (a tag isn't "known-good" until it builds+serves
  there). Build is `cmake -DGGML_METAL=ON` — Metal.
- **Model + quant.** Repo `meta-models/Muse-Glimmer-30B-GGUF`. Default **Q4_K_M** (~16.8 GB) —
  the file `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf`. Quant ladder for a 36 GB unified-memory
  Mac (weights + KV-cache + OS share one pool; Metal wires ~24–28 GB by default,
  `sudo sysctl iogpu.wired_limit_mb=` raises it):
  - **Q4_K_M ~16.8 GB** — default; big context headroom, fast.
  - Q5_K_M ~20–21 GB — better quality, still comfortable.
  - Q4_K_XL (dynamic) ~19.65 GB — higher-quality 4-bit, present in the repo, still fits.
  - Q6_K ~24–25 GB — near-lossless, tight; smaller context, may need a higher wired limit.
  - Q8_0 ~31–32 GB — too tight on 36 GB once KV-cache+OS are added. Skip.
  Repo extras: `mmproj-*` (1.4 GB vision encoder — skip for coding), `dflash-*` (1.63 GB DFlash
  drafter for speculative decoding — future `run-fast`).
- **Serving tuning** (`make serve`, defaults set 2026-08-19):
  - **`--parallel 1`** — one KV-cache slot for the single Crush client. Multiple slots split
    the cache; with 2 slots and a 16k context each slot is ~8k cells, too small to restore a
    cached prompt → llama-server logs `failed to restore kv cache` and reprocesses the prompt
    every turn (non-fatal, just slow). One slot gives the whole context to the one client.
  - **`CTX=32768`** — bigger window so a coding agent's growing context AND prompt-cache
    restore both fit. Costs some KV-cache RAM; fine on 36 GB with Q4. Lower via `make serve
    CTX=16384`.
  - `-ngl 999` offloads all layers to Metal. **Confirm Metal engaged** from the serve log:
    healthy is ~20 t/s generation / ~170 t/s prompt eval (GPU-class; CPU would be ~1–3 t/s).
- **Bind loopback only** (`HOST=127.0.0.1`). The sole ingress is the SSH tunnel; never
  `0.0.0.0`.
- **Alternative backend:** MLX (`make serve-mlx`, `RadixArk/Muse-Glimmer-q4-MLX`) is often
  faster on Apple Silicon — documented, not default.
- **Download path is portable** (`make venv` + `make pull`, plain python3 + `huggingface_hub`),
  verified on Linux; only the Metal build/serve need the Mac.

## Client (`client/`, Linux container)

- Full runClaudeInContainer toolchain (`entrypoint/01-install-base.sh`, verbatim copy) +
  **Crush built from source at image-build time**, pinned `CRUSH_TAG` (default **`v0.89.0`**,
  the latest stable at bring-up; module path `github.com/charmbracelet/crush`, `go install`).
- **Crush config is `crushrc`, NOT `crush.json`** (`client/entrypoint/crushrc`; global path
  `~/.config/crush/crushrc`). `crush.json` is deprecated. The baked config declares a single
  **`llamacpp`**-type provider. **`base_url` is the bare root** (`http://127.0.0.1:8080`, no `/v1`) —
  Crush appends `/v1/models` itself (`internal/discover/llamacpp.go`). A trailing `/v1` would
  double-path.
- **Provider config: `disable_default_providers` + explicit pinned model (2026-08-20).** The crushrc
  sets `option default-providers false` (so Crush offers ONLY this provider, never its built-in
  ~15-20-model Catwalk catalog) and pins the model explicitly with `model add
  muse-glimmer/muse-glimmer --context-window 32768` + `model large|small` selections, rather than
  relying on runtime auto-discovery. **Why the change from the original auto-discovery design:**
  auto-discovery hits `/v1/models` with a 3s timeout at startup; if the tunnel/server isn't up, Crush
  deletes the provider and falls back to its onboarding catalog (the "15-20 models" symptom). An
  explicit model has no such dependency and works offline/airgapped. The server pins a matching stable
  ID via `--alias $(MODEL_ALIAS)` (`server/Makefile`), so `/v1/models` reports `muse-glimmer` instead
  of the raw GGUF path. Full rationale + the `crush models` before/after (1532 → 1):
  `tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md`.
- **`--network=host`** (Linux-only) so `127.0.0.1:8080` in the container is the host's
  SSH-forwarded port.
- **SELinux: runs UNCONFINED** (`SELINUX_OPT ?= --security-opt label=disable`, `client/Makefile`).
  Without it, on an enforcing host the confined container can't access bind-mounted host dirs
  and — the case that bit us — **can't follow symlinks that jump out to a host path** like
  `/mnt/sda1` (`permission denied`), even with `:z` on the mount. This matches how
  runClaudeInContainer runs under `NESTED_PODMAN=1`. The `/work` mount carries no `:Z` (would be
  redundant and would relabel the user's project). Note the client Makefile does **not**
  implement `NESTED_PODMAN` — passing it is a silent no-op.
- **Dotfiles + host config (2026-08-20):** the Dockerfile bakes `client/entrypoint/dotfiles/.extrabashrc`
  (prompt, `ls` alias, `GPG_TTY`) via `COPY … /root/` + a `~/.bashrc` source line, and the Makefile
  conditionally mounts host `~/.tmux.conf` / `~/.gitconfig` / `~/.gnupg` (runClaudeInContainer's
  `readlink -f` + existence-test idiom, `:Z`). See
  `tasks/archive/2026/08/20/dotfiles-and-host-config-mounts.md`.
- **`@`-import patch (2026-08-20):** the client builds a locally-patched Crush that recursively splices
  `@path` references inside context files (a feature stock Crush lacks). Gated on `CRUSH_AT_IMPORT`
  (Dockerfile ARG default `0` = stock `go install …@tag`; Makefile default `1` = clone the tag, `git
  apply client/patches/crush-at-import.patch`, build from source with a version-stamp). **Live-verified
  end-to-end 2026-08-21** (a real `@secret.md` spliced into a `CLAUDE.md`, model returned the
  import-only secret). Re-verify harness: `tools/at-import-live-test/run-live-test.sh`. Record:
  `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`; mechanism: `crush-capabilities.md`.

## Connecting

- On the **Linux host**: `ssh -N -L 8080:127.0.0.1:8080 you@mac`. **`-N` makes it look hung —
  that's correct** (foreground tunnel, no prompt); use another terminal, or `-fN` to background.
- **Pre-flight** (second terminal, host): `curl -s http://127.0.0.1:8080/v1/models` → JSON means
  wired end-to-end. The forward is *lazy* (connects to the Mac only when used).
- Order: server up → tunnel up → *then* `crush` (it discovers models at startup).

## Nested-build gotcha (if you build the client image nested)

The client image is **~22.3 GB**. Building it in a RAM-backed nested podman store fails at the
*layer commit* (not install) with `no space left on device` — commit peak (base+diff+temp)
exceeds the final size. A 32 GB store overflowed; `mount -o remount,size=50g
/var/lib/containers` (or a bigger `NESTED_PODMAN_TMPFS_SIZE`) fixed it. On a real disk-backed
host build there's no such ceiling. See runClaudeInContainer's
`tasks/reference/nested-podman-design.md` and its `dir-backed-nested-podman-storage.md`.

## Verification status (2026-08-19)

Verified: client image builds + `crush v0.89.0` runs + `crushrc` parses; HF download plumbing;
`base_url`/`/v1/models` wiring against Crush source; server serving on Metal (~21 t/s) and
producing output end-to-end through Crush. Not formally exercised: a multi-step tool-using
Crush edit (the real test of whether Muse Glimmer is a strong enough tool-caller to drive the
agent loop) — spot-check when convenient.

## Deferred

The task/stack/personal-overlay conventions machinery from runClaudeInContainer is intentionally
not ported — see `tasks/port-runclaude-conventions-systems.md`. No auth plumbing is needed (the
endpoint is a local, keyless llama-server behind SSH).
