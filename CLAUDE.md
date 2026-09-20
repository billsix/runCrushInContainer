# runCrushInContainer — project notes

**Status: working.** Both `server/` and `client/` are built and in use — the local model serves on
the Mac and Crush in the client container talks to it over the SSH tunnel, loads the ported
conventions, and follows them. Remaining work is tracked in `tasks/`.

**What this repo is for.** Like `github.com/billsix/runClaudeInContainer`, this is a **tool for
running a coding assistant in a disposable container to develop your *other* codebases** — here the
assistant is **Crush** (Charm's terminal agent, `github.com/charmbracelet/crush`) driving a **local
coding LLM** (Meta's **Muse Glimmer 30B**, or Google's **Gemma 4 26B-A4B** — both Apache-2.0,
`make serve MODEL=glimmer|gemma`) served on the Mac. Its job is two-fold: **run the agent** (in a
throwaway container, pointed at the project mounted at `/work`), and **deliver to the agent the
conventions** that teach it how your projects are structured and built. It is fork-friendly (model,
quant, pinned tool versions are Makefile variables); the template/fork rationale and why it is *not*
a template for the codebases you build with it are in `tasks/reference/architecture.md` ("What this is").

## Two parts, two machines

- **`server/` — macOS, native (NOT containerized).** llama.cpp built for Apple Silicon (Metal),
  serving one model at a time over an OpenAI-compatible HTTP endpoint bound to **loopback only**
  (`127.0.0.1`), each on its own **fixed** port. **As of 2026-09-20 there are FIVE OSI (Apache-2.0)
  models** — glimmer `8080`, gemma `8081`, granite `8082` (all US), devstral `8083` (FR), qwen `8084` (CN)
  — gated by the **`MODEL_COUNTRIES`** country allowlist (default `US`), pinned with multi-hash checksums,
  and autodiscovered by the client. Full design: `tasks/reference/model-registry-country-gate-and-checksums.md`.
  (`make serve MODEL=<m>`; ports are deliberately not knobs.)
- **`client/` — Linux, containerized.** A Podman image = the full runClaudeInContainer toolchain
  (~430 packages) plus **Crush built from source at a pinned tag**. It reaches the Mac through an
  **SSH port-forward** (`ssh -L`, run on the Linux host), with `podman run --network=host` so
  `127.0.0.1:8080` / `:8081` in the container are the forwarded ports (one tunnel forwards both).
  Opt-in `make shell LOCALHOST_ONLY=1` instead runs `--network=none` + a unix-socket/`socat` bridge so the
  container reaches **only** the model (no other egress); default stays `--network=host`. See the README
  "Network modes" and `tasks/archive/2026/09/20/localhost-only-network-mode.md`.

The pins (llama.cpp `LLAMACPP_TAG` `b10883`; floors `b10353` for Glimmer, PR #28335 for Gemma 4;
Crush `v0.89.0`; the MLX serve alternative), the quant ladder, and the serve tuning are in
`tasks/reference/architecture.md`. See `README.md` for the user-facing overview and the SSH recipe.

## Labels: which machine a command runs on

Three environments are in play; label instructions so it's unambiguous:

- **`[MAC]`** — the Mac Studio running `server/` natively (Homebrew, Xcode CLT, `make serve`).
- **`[LINUX HOST]`** — the Linux box running the client container and the SSH tunnel.
- **`[CONTAINER]`** — the Podman sandbox launched by `client/make shell`, where Crush runs.

## Conventions for changing this repo

- **Pin versions/knobs in Makefile variables, never hardcode inline.** Server: `LLAMACPP_TAG`, the
  model table (`MODELS`, per-row `MODEL_REPO_<m>` / `MODEL_FILE_<m>` / `MODEL_ALIAS_<m>` /
  `MODEL_PORT_<m>`; `MODEL=` selects a row), `CTX`, `NGL`, `NP`. **`PORT` is NOT a knob** — it is
  `override`-fixed per row. Client: `CRUSH_TAG`, `CRUSH_AT_IMPORT`, `CRUSH_VENDORED`, `VENDOR_TOOLS`.
  Three cross-file couplings to keep in sync: server `MODEL_ALIAS_<m>` ↔ the crushrc's pinned model
  IDs, server `MODEL_PORT_<m>` ↔ the crushrc `--base-url` ports (+ tunnel lines in `README.md` and
  `client/entrypoint/shell.sh`), and server `CTX` ↔ the crushrc `--context-window`. Rationale + the
  quant/serve lore: `tasks/reference/architecture.md`.
- **The client is always the full toolchain; `NESTED_PODMAN` is run-time only.** `make image` (on the
  host) builds the full ~430-package image with all the language servers the crushrc declares — there
  is no `FULL_TOOLCHAIN` flag. `NESTED_PODMAN` is purely a run-time launch capability, decoupled from
  image content, and deliberately not baked (`ENV NESTED_PODMAN=1`). Why they must be decoupled (and
  the LSP-broke-when-nested history): `tasks/reference/nested-podman-vs-image-content.md`.
- **The server binds loopback only.** Never bind llama-server to `0.0.0.0` / the LAN; the only ingress
  is the SSH tunnel.
- **The client image reuses runClaudeInContainer's full toolchain** (`01-install-base.sh`, sorted,
  maximal — don't prune) and bakes Crush-from-source (patched when `CRUSH_AT_IMPORT=1`), the `crushrc`,
  and dotfiles. The Makefile conditionally mounts host `~/.tmux.conf` / `~/.vimrc` / `~/.gitconfig` /
  `~/.gnupg`.
- **The crushrc is executed Bash; treat edits as code, and each `lsp add` flag takes ONE value.** A
  broken crushrc means Crush refuses to start. Use `--filetypes a --filetypes b`, never
  `--filetypes a b`. The cheap pre-`make image` gate (build the vendored tree + run `crush models`):
  `tasks/reference/crush-capabilities.md` (Config system) and `tasks/reference/crush-lsp-integration.md` §4.
- **Model preselection is probe-based.** The crushrc `curl`s `127.0.0.1:8080`/`8081` at load and
  preselects the model that answers (Crush never health-checks a pinned provider). A `ctrl+l` switch
  outranks it for the life of that container. Mechanism: `tasks/reference/crush-capabilities.md`
  § "Which model is active at startup".
- **Language servers: dnf only, declared explicitly in the crushrc.** Six `lsp add`s (python `ty`, go,
  c, rust, sh, glsl — all dnf, `01-install-base.sh`) so auto-detection's gates never decide; no
  npm/gem/opam/pip servers (the airgap rebuild has only a dnf mirror). The one exception is the RHEL 9
  variant (a commented-out `client/Dockerfile` block installs the `ty` wheel into a python3.11 `/venv`).
  Capability table + the RHEL 9 variant: `tasks/reference/crush-lsp-integration.md` §4 and § RHEL 9.
- **Verify model/tool identifiers before hardcoding them.** GGUF filenames, the HF repo path, and good
  llama.cpp / Crush tags drift; confirm against Hugging Face and the upstream release pages at
  implementation time.
- **Entrypoint scripts must stay executable (mode 755).** The Dockerfile invokes `01-install-base.sh`
  and `02-install-vendor-tools.sh` **directly**, and `vendor.sh` runs as `./vendor.sh`, so a dropped
  `+x` breaks `make image` / `make vendor`. After editing any `entrypoint/*.sh` or `vendor.sh`, confirm
  `git ls-files -s` still shows `100755` (a content rewrite resets it to 644 — this bit us 2026-08-25).

## What's ported / in use

The full runClaudeInContainer working-method machinery is ported and in use (task/reference-doc
systems, always-loaded conventions + personal overlay, in-session diversion stack, 8 slash commands,
`make shell-exec`, nested podman, fourteen local Crush patches, no-telemetry/no-phone-home). The full
inventory with per-item detail, and what was deliberately NOT ported, is in
`tasks/reference/architecture.md` § "Conventions machinery — ported" / "Ported machinery inventory".
The egress patch/flag system and the 213-Go-dep dependency network audit are in
`tasks/reference/architecture.md` and `tasks/reference/dependency-network-audit.md`.

## Reference docs

- `tasks/reference/architecture.md` — how the two halves fit, the pins, the quant ladder, serve
  tuning, the crushrc/`llamacpp` config, dotfiles/host-config mounts, the `@`-import patch, the
  offline/airgap source-vendoring workflow, the SELinux lesson, and the ported-machinery inventory.
  Read this first.
- `tasks/reference/crush-capabilities.md` — verified map of Crush `v0.89.0`'s features (context-file
  autoload, no native `@`-import, custom commands, hooks, provider/model selection + catalog
  suppression, context-window/compaction, crushrc-as-Bash + the edit gate).
- `tasks/reference/crush-lsp-integration.md` — what Crush asks a language server for, the four start
  gates, "no LSP client handles file", and the registry rows for every toolchain the image ships (§4
  + RHEL 9 venv variant).
- `tasks/reference/nested-podman-vs-image-content.md` — why `NESTED_PODMAN` (run-time) and image
  content are decoupled, and the LSP-broke-when-nested post-mortem.
- `tasks/reference/nested-podman-design.md` — nested-podman design/flags for the client (inner runs
  use the PODMAN_RUN_FLAGS convention + `--network=host`).
- `tasks/reference/container-file-layout.md` — the baked-vs-mounted map of the client container (every
  `COPY`, every `SHELL_RUN_FLAGS` mount, final runtime paths, the repo↔baked reference-doc mapping and
  **the cite-by-baked-path rule**). Printable via `make -C client manifest`. Consult before citing a
  container path.
- `tasks/reference/gemma-4-alongside-glimmer.md` — Google's open-weights models against the OSI-licence
  bar (Gemma 4 is Apache-2.0), the family table, and the two-models/two-fixed-ports design.
- `tasks/reference/new-hardware-bringup.md` — the first hour on a new box (`make probe`/`make smoke`,
  then quant → `NGL` → `CTX` → `NP`).
- `tasks/reference/crush-prompt-history.md` — how Crush's prompt history works at `v0.89.0` and what
  `crush-shell-history.patch` changes.
- `tasks/reference/glimmer-models-and-airgap-quant-selection.md` — survey of Muse Glimmer + the quant
  landscape, for deciding which GGUF to vendor to an airgap box.
- `tasks/reference/dependency-network-audit.md` — the 213-vendored-Go-dep audit and the twelve
  `PATCH_OUT_<X>` egress decisions.

A subset of docs is also **baked into the image** at `~/.config/crush/reference/` (agent-readable
on-demand): `llm-overused-phrases.md`, `print-debugging.md`, `sandbox-capability-map.md`,
`nested-podman-design.md`, `container-file-layout.md`, and `bluf-bottom-line-up-front.md`. **Cite a
baked doc by its `~/.config/crush/reference/…` path, never `tasks/reference/…`** (the latter is a repo
path absent inside the container); a baked doc copied from `tasks/reference/` must keep both copies in
sync. The baked-vs-repo mapping is in `tasks/reference/container-file-layout.md`.

## Tasks

Scan `tasks/` (top-level, not `tasks/archive/`) at session start for the current, prioritized list —
easy wins first (lowest priority-number, then lowest difficulty-number). Blocked tasks carry
`Blocked on:`/`Recheck:` and are excluded from that ranking; `/recheck-blocked` tests whether a gate
cleared. Completed work lives in `tasks/archive/<YYYY>/<MM>/<DD>/` and in git history.
