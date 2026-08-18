# runCrushInContainer — project notes

**Status: working bring-up.** Both `server/` and `client/` are built and in use — the local
model serves on the Mac (Metal, ~21 t/s) and Crush in the client container talks to it over
the SSH tunnel and produces output. The `make` targets here exist and run. Remaining polish,
plus the deferred conventions machinery, are tracked in `tasks/`.

This repo runs a **local coding LLM** (Meta's **Muse Glimmer 30B**) and drives it with
**Crush** (Charm's terminal coding agent, `github.com/charmbracelet/crush`). It is a sibling
of `github.com/billsix/runClaudeInContainer` and is meant to become a **template**: the
model, quant, and pinned tool versions are Makefile variables a fork can swap.

## Two parts, two machines

- **`server/` — macOS, native (NOT containerized).** llama.cpp built for Apple Silicon
  (Metal) on a 36 GB Mac Studio, serving Muse Glimmer over an OpenAI-compatible HTTP endpoint
  bound to **loopback only** (`127.0.0.1`). A `Makefile` handles: build llama.cpp at a pinned
  tag (≥ `b10353`, the first release with Muse Glimmer support), pull the GGUF from Hugging
  Face, and `serve`. An MLX serve target is documented as the faster-on-Apple-Silicon
  alternative.
- **`client/` — Linux, containerized.** A Podman image = the **full runClaudeInContainer
  toolchain** (~430 packages) plus **Crush built from source at a pinned tag at image-build
  time**. It reaches the Mac through an **SSH port-forward** (`ssh -L`) run on the Linux host,
  with `podman run --network=host` so `127.0.0.1:8080` in the container is the forwarded port.

See `README.md` for the user-facing overview and the exact SSH recipe.

## Labels: which machine a command runs on

Three environments are in play; label instructions so it's unambiguous:

- **`[MAC]`** — the Mac Studio running `server/` natively (Homebrew, Xcode CLT, `make serve`).
- **`[LINUX HOST]`** — the Linux box running the client container and the SSH tunnel.
- **`[CONTAINER]`** — the Podman sandbox launched by `client/make shell`, where Crush runs.

## Conventions for changing this repo

- **Pin versions in Makefile variables, never hardcode inline.** `LLAMACPP_TAG`,
  `MODEL_REPO`, `MODEL_FILE`, `CRUSH_TAG`, `PORT`, `CTX`, `NGL`. The template value is
  swapping these.
- **The server binds loopback only.** Never bind llama-server to `0.0.0.0` / the LAN; the
  only ingress is the SSH tunnel. Keep it that way.
- **The client image reuses runClaudeInContainer's full toolchain** (`01-install-base.sh`,
  sorted, maximal — don't prune) but **omits** its auth/config layering for now (see below).
- **Verify model/tool identifiers before hardcoding them.** GGUF filenames, the HF repo path,
  and good llama.cpp / Crush tags came from a 2026-08-18 web search and drift; confirm against
  Hugging Face and the upstream release pages at implementation time.

## Deliberately deferred (do not add without the follow-up task)

Per the user (2026-08-18), v1 is *the basics* only. The runClaudeInContainer machinery —
task-doc system, diversion stack, personal-overlay/`@`-import layering, reference-doc
conventions — is **not** ported yet, and **no auth plumbing** is needed (the endpoint is a
local, keyless llama-server behind SSH). That work is tracked in
`tasks/port-runclaude-conventions-systems.md`.

## Reference docs

- `tasks/reference/architecture.md` — how the two halves fit, the pins (llama.cpp tag, Crush
  `v0.89.0`), the quant ladder, serve tuning, the crushrc/`llamacpp` config, the SELinux
  `label=disable` lesson, and the connection flow. Read this first when picking the project up.

## In-flight tasks

- `tasks/port-runclaude-conventions-systems.md` — **Priority 6, Difficulty 4** — port the
  runClaudeInContainer conventions machinery (task/stack/personal config) later. Deferred by
  design; not part of v1.

(The bring-up task is **complete** — archived at `tasks/archive/2026/08/19/crush-local-llm-bringup.md`,
knowledge harvested into the reference doc above.)
