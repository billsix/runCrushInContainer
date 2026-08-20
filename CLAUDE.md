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

- **Pin versions/knobs in Makefile variables, never hardcode inline.** Server: `LLAMACPP_TAG`,
  `MODEL_REPO`, `MODEL_FILE`, `MODEL_ALIAS`, `PORT`, `CTX`, `NGL`, `NP`. Client: `CRUSH_TAG`,
  `CRUSH_AT_IMPORT`. The template value is swapping these. Two cross-file couplings to keep in sync:
  server `MODEL_ALIAS` ↔ the crushrc's pinned model ID, and server `CTX` ↔ the crushrc's
  `--context-window`.
- **The server binds loopback only.** Never bind llama-server to `0.0.0.0` / the LAN; the
  only ingress is the SSH tunnel. Keep it that way.
- **The client image reuses runClaudeInContainer's full toolchain** (`01-install-base.sh`,
  sorted, maximal — don't prune) and bakes: **Crush built from source** (patched with the
  `@`-import diff when `CRUSH_AT_IMPORT=1`), the **`crushrc`** (pinned model + catalog suppression),
  and **dotfiles** (`entrypoint/dotfiles/.extrabashrc`). It **omits** the auth/config-layering
  machinery for now (see below). The Makefile also conditionally mounts host `~/.tmux.conf` /
  `~/.gitconfig` / `~/.gnupg`.
- **Verify model/tool identifiers before hardcoding them.** GGUF filenames, the HF repo path,
  and good llama.cpp / Crush tags came from a 2026-08-18 web search and drift; confirm against
  Hugging Face and the upstream release pages at implementation time.

## What's in use vs. deferred

The **task-doc and reference-doc conventions are now in active use** here (`tasks/`,
`tasks/archive/<YYYY>/<MM>/<DD>/`, `tasks/reference/`) — use them normally. Still **deferred** (the
heavier runClaudeInContainer machinery): the **diversion stack**, the **personal-overlay / `@`-import
config layering**, and the **slash commands** (`/new-task`, `/stack-*`, …). **No auth plumbing** is
needed either (the endpoint is a local, keyless llama-server behind SSH). That deferred work is
tracked in `tasks/port-runclaude-conventions-systems.md`.

Note: the client image itself carries a **local `@`-import patch for Crush** (`client/patches/`,
`CRUSH_AT_IMPORT`) — that's a *Crush* feature, distinct from the deferred convention-delivery layering.

## Reference docs

- `tasks/reference/architecture.md` — how the two halves fit, the pins (llama.cpp tag, Crush
  `v0.89.0`), the quant ladder, serve tuning, the crushrc/`llamacpp` config (explicit model pin +
  catalog suppression), dotfiles/host-config mounts, the `@`-import patch, and the SELinux
  `label=disable` lesson. Read this first when picking the project up.
- `tasks/reference/crush-capabilities.md` — verified map of Crush `v0.89.0`'s features (context-file
  autoload, no native `@`-import, custom commands, hooks, provider/model selection + the
  `disable_default_providers` catalog switch, context-window/compaction). Read before touching
  Crush config or the port.

## In-flight tasks

Scan `tasks/` (top-level) at session start for the current list; as of 2026-08-20:

- `port-runclaude-conventions-systems.md` (P4/D5) — port the deferred convention machinery (stack /
  personal overlay / slash commands).
- `patch-crush-for-at-imports.md` (P5/D5) — the `@`-import patch; delivered + wired, kept open pending
  a live end-to-end check.
- `verify-provider-suppression-airgapped.md` (P5/D2) — confirm the catalog-suppression fix on the
  airgapped machine.
- `context-advisor-script.md` (P4/D2) — a host-run server/context advisor script (drafted, on hold).
- `crush-at-import-parity.md` (P6/D4) — bring the `@`-import patch to full Claude parity (follow-up).

Completed & archived (see `tasks/archive/2026/08/`): the bring-up, provider-catalog suppression,
dotfiles/host-config mounts, and context-window sizing.
