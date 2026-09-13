# runCrushInContainer — project notes

**Status: working, conventions ported.** Both `server/` and `client/` are built and in use — the
local model serves on the Mac (Metal, ~21 t/s) and Crush in the client container talks to it over
the SSH tunnel, loads the ported conventions, and follows them. The runClaudeInContainer
working-method machinery is now ported (see "What's in use" below); remaining items are tracked in
`tasks/`.

**What this repo is for.** Like `github.com/billsix/runClaudeInContainer`, this is a **tool for
running a coding assistant in a disposable container to develop your *other* codebases** — here the
assistant is **Crush** (Charm's terminal agent, `github.com/charmbracelet/crush`) driving a **local
coding LLM** (Meta's **Muse Glimmer 30B**, or Google's **Gemma 4 26B-A4B** — both Apache-2.0,
`make serve MODEL=glimmer|gemma`) served on the Mac. Its job is two-fold: **run the agent**
(in a throwaway container, pointed at the project mounted at `/work`), and **deliver to the agent the
conventions** that teach it how your projects are structured and built — the ported working-method
machinery (see "What's in use"). It is **fork-friendly** — model, quant, and pinned tool versions are
Makefile variables a fork can swap — so it is a template for *the assistant-runner itself*. It is
**not** a template for the codebases you build with it: those follow the container-per-project
conventions the agent is taught (which live in the personal overlay (`ai-coding-conventions.personal.md`), not in this repo). This
repo does happen to follow those same conventions for its own `client/` image, but that's incidental
to its purpose.

## Two parts, two machines

- **`server/` — macOS, native (NOT containerized).** llama.cpp built for Apple Silicon
  (Metal) on a 36 GB Mac Studio, serving **one of two models** over an OpenAI-compatible HTTP
  endpoint bound to **loopback only** (`127.0.0.1`): Muse Glimmer on the **fixed** port `8080`,
  Gemma 4 on the **fixed** port `8081` (`make serve MODEL=glimmer|gemma`; the ports are deliberately
  not knobs). A `Makefile` handles: build llama.cpp at a pinned tag (`b10883`; floors `b10353` for
  Glimmer, PR #28335 for Gemma 4), pull both GGUFs from Hugging Face, and `serve`. An MLX serve
  target is documented as the faster-on-Apple-Silicon alternative (Glimmer only).
- **`client/` — Linux, containerized.** A Podman image = the **full runClaudeInContainer
  toolchain** (~430 packages) plus **Crush built from source at a pinned tag at image-build
  time**. It reaches the Mac through an **SSH port-forward** (`ssh -L`) run on the Linux host,
  with `podman run --network=host` so `127.0.0.1:8080` / `:8081` in the container are the
  forwarded ports (one tunnel command forwards both).

See `README.md` for the user-facing overview and the exact SSH recipe.

## Labels: which machine a command runs on

Three environments are in play; label instructions so it's unambiguous:

- **`[MAC]`** — the Mac Studio running `server/` natively (Homebrew, Xcode CLT, `make serve`).
- **`[LINUX HOST]`** — the Linux box running the client container and the SSH tunnel.
- **`[CONTAINER]`** — the Podman sandbox launched by `client/make shell`, where Crush runs.

## Conventions for changing this repo

- **Pin versions/knobs in Makefile variables, never hardcode inline.** Server: `LLAMACPP_TAG`,
  the model table (`MODELS`, and per row `MODEL_REPO_<m>` / `MODEL_FILE_<m>` / `MODEL_ALIAS_<m>` /
  `MODEL_PORT_<m>`; `MODEL=` selects a row), `CTX`, `NGL`, `NP`. **`PORT` is NOT a knob** — it is
  `override`-fixed per row so crushrc and the tunnel never need telling. Client: `CRUSH_TAG`,
  `CRUSH_AT_IMPORT`, `CRUSH_VENDORED` (offline build from `client/vendor/crush`), `VENDOR_TOOLS`
  (bake the vendoring-only `hf`; default off). The template value is swapping these. Three cross-file
  couplings to keep in sync: server `MODEL_ALIAS_<m>` ↔ the crushrc's pinned model IDs
  (`muse-glimmer`, `gemma-4`), server `MODEL_PORT_<m>` ↔ the crushrc `--base-url` ports (+ the
  tunnel lines in `README.md` and `client/entrypoint/shell.sh`), and server `CTX` ↔ the crushrc's
  `--context-window`.
- **The client is always the full toolchain; `NESTED_PODMAN` is run-time only (2026-09-12).**
  `make image` (on the host) builds the full ~430-package image with all the language servers the
  crushrc declares — there is no `FULL_TOOLCHAIN` flag any more. `NESTED_PODMAN` is purely a
  run-time launch capability (the podman-run flags that let Crush build/run *other* projects'
  containers nested), fully decoupled from image content. It is deliberately **not** baked into the
  image (`ENV NESTED_PODMAN=1`), which would falsely advertise nested capability on a plain
  non-nested launch. (Formerly `FULL_TOOLCHAIN` auto-defaulted to a minimal, language-server-less
  image when nested — that silently broke LSP on `make shell NESTED_PODMAN=1`, so it was removed;
  rationale and history: `tasks/reference/nested-podman-vs-image-content.md`.)
- **The server binds loopback only.** Never bind llama-server to `0.0.0.0` / the LAN; the
  only ingress is the SSH tunnel. Keep it that way.
- **The client image reuses runClaudeInContainer's full toolchain** (`01-install-base.sh`,
  sorted, maximal — don't prune) and bakes: **Crush built from source** (patched with the
  `@`-import diff when `CRUSH_AT_IMPORT=1`), the **`crushrc`** (pinned models + catalog suppression
  + six explicit `lsp add` lines), and **dotfiles** (`entrypoint/dotfiles/.extrabashrc`). It **omits** the auth/config-layering
  machinery for now (see below). The Makefile also conditionally mounts host `~/.tmux.conf` / `~/.vimrc` /
  `~/.gitconfig` / `~/.gnupg`.
- **The crushrc is executed Bash, and its `lsp add` flags take ONE value each (2026-09-10).** A
  broken crushrc means Crush refuses to start (`Failed to load config … unknown flag …`), so treat
  edits to `client/entrypoint/crushrc` as code: `--filetypes a --filetypes b`, never
  `--filetypes a b` (the usage text's `...` means repeat the flag). Cheap gate before a `make image`:
  build the vendored tree (`cd client/vendor/crush && GOPROXY=off go build -mod=vendor -o /tmp/crush .`)
  and run `crush models` with the edited file at `$HOME/.config/crush/crushrc` — a parse error shows
  there. Origin: `tasks/crushrc-startup-failure-and-model-preselect.md`.
- **Model preselection is probe-based (2026-09-10).** Crush never health-checks a pinned provider and
  shows no picker with two configured, so the crushrc `curl`s `127.0.0.1:8080`/`8081` at load and
  preselects the model that answers (Gemma only when 8081 alone answers; Glimmer otherwise). A
  `ctrl+l` switch outranks it for the life of that container (written to the ephemeral
  `~/.local/share/crush/crush.json`). Mechanism: `tasks/reference/crush-capabilities.md` § "Which
  model is active at startup". `curl` is in the base package set for this (`00-install-minimal.sh`).
- **Language servers: dnf only, declared explicitly (2026-09-10).** Crush's `lsp_*` tools need a
  server on `PATH`; the crushrc `lsp add`s one per toolchain Fedora packages (python `ty`, go, c,
  rust, sh, glsl — all dnf, `01-install-base.sh`), so auto-detection's four gates never decide.
  No npm/gem/opam/pip servers: the airgap rebuild has only a dnf mirror. The one exception is the
  **RHEL 9** variant, which packages no Python LSP: a commented-out block in `client/Dockerfile`
  installs the `ty` wheel (`TY_VERSION`, the one pinned server; vendored by `make vendor`) into a
  python3.11 `/venv`. Which server offers what: `tasks/reference/crush-lsp-integration.md` §4.
- **Verify model/tool identifiers before hardcoding them.** GGUF filenames, the HF repo path,
  and good llama.cpp / Crush tags came from a 2026-08-18 web search and drift; confirm against
  Hugging Face and the upstream release pages at implementation time.
- **Entrypoint scripts must stay executable (mode 755).** The Dockerfile invokes
  `01-install-base.sh` and `02-install-vendor-tools.sh` **directly** (`RUN /usr/local/bin/…`),
  and `vendor.sh` runs as `./vendor.sh`, so a dropped `+x` breaks `make image` / `make vendor`.
  After editing any `entrypoint/*.sh` or `vendor.sh`, confirm `git ls-files -s` still shows
  `100755`. A content rewrite (e.g. adding an SPDX header) resets the mode to 644 — this bit us
  2026-08-25.

## What's in use (the runClaudeInContainer machinery is ported)

The full working-method machinery is now **ported and in use** (Phases 0–4, 2026-08-21 —
`tasks/port-runclaude-conventions-systems.md`):

- **task-doc + reference-doc systems** (`tasks/`, `tasks/archive/<YYYY>/<MM>/<DD>/`, `tasks/reference/`);
- **cross-project conventions** — a lean, always-loaded `CLAUDE.md` baked at `~/.config/crush/CLAUDE.md`
  and registered as a `global-context-path` in `crushrc` (the reference docs + personal overlay pulled
  in via the `@`-import patch);
- **diversion stack** — in-session only at `~/.config/crush/stack.md` (on the `--rm` overlay; the
  session-end sweep folds still-open items into the task docs — decided 2026-09-03);
- **personal-overlay layering** — the everyday per-user customization path: the baked always-loaded
  `CLAUDE.md` (`~/.config/crush/CLAUDE.md`) `@`-imports `~/.config/crush/ai-coding-conventions.personal.md`
  (blank tracked default), over which `make shell` mounts the host's `~/.ai-coding-conventions.personal.md`
  (auto-`touch`ed if absent). **Filling in that one host file is how a user adds their own identity /
  project→URL mapping / mount layout / instructions** without editing anything tracked; the agent loads
  it every session and the tracked conventions stay maintainer-agnostic. Example to copy:
  `client/entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.example.md`; see `FORKING.md`;
- **8 slash commands** (`/new-task`, `/new-reference`, `/new-reference-set`, `/archive-task`,
  `/stack-*` — in Crush's `/` dialog under the **User** tab);
- **nested-podman** (`make shell NESTED_PODMAN=1`; inner runs: `--network=host` needed at this depth, and the cgroups flag auto-applies via the PODMAN_RUN_FLAGS convention — see `tasks/reference/nested-podman-design.md`);
- **`make shell-exec`** (`client/Makefile`) — the batch twin of `make shell`: `make shell-exec
  SCRIPT=<path under the mounted PROJECT at /work> | CMD='...'` runs a script/command in the same
  container env and exits (no TTY) — for ad-hoc/CI use. `shell` + `shell-exec` share one
  `SHELL_RUN_FLAGS` variable so they can't drift; `client/entrypoint/shell.sh` ends `set -e … exec
  bash "$@"`. Cross-project fan-out + design: `github.com/billsix/runClaudeInContainer`
  `tasks/add-shell-exec-target.md` and `.../fan-out-shell-exec-to-projects.md`. The general template
  contract for this lives in the personal overlay (`ai-coding-conventions.personal.md`), not here.
- **fourteen local Crush patches** (`client/patches/`), each behind its own defaulted build flag:
  two FEATURE patches — `crush-at-import.patch` (`CRUSH_AT_IMPORT ?= 1`) and
  `crush-shell-history.patch` (`CRUSH_SHELL_HISTORY ?= 1`: shell-style prompt history — Up recalls
  the prompt just sent, history spans sessions, deterministic ordering, and `ctrl+r` reverse search;
  see `tasks/reference/crush-prompt-history.md`) — plus twelve `PATCH_OUT_<X>` egress patches from
  the dependency network audit (update check, telemetry, `update-providers`, web tools, sourcegraph,
  Google/Vertex, Bedrock/AWS, Azure, OpenRouter, Vercel, Hyper, Copilot — defaults per
  `tasks/reference/dependency-network-audit.md` §5). ALL patches apply at **build time** in
  `client/entrypoint/03-build-crush.sh`, identically in both build modes; `vendor-crush.sh` vendors
  the **complete unpatched** tree so any flag combination builds offline. Every build clones (or
  copies the vendored tree) + builds from source (no plain `go install …@tag`). Combination-tested by
  `tools/sweep_egress_patch_combos.sh`.
- **no telemetry / no phone-home** — PostHog telemetry (`data.charm.land`) off three ways:
  Dockerfile `ENV CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1`, crushrc `option metrics false`, and the
  build-level `no-telemetry.patch` (`PATCH_OUT_TELEMETRY ?= 1`); the GitHub update check off via
  `crush-no-update-check.patch` (`PATCH_OUT_UPDATE_CHECK ?= 1`). The full audit of the **213
  vendored Go deps** is DONE (2026-08-29): `tasks/reference/dependency-network-audit.md` holds the
  findings and the twelve confirmed `PATCH_OUT_<X>` decisions (work records in
  `tasks/archive/2026/08/29/`; triage scanner `tools/triage_dependency_egress.py` + patch sweep
  `tools/sweep_egress_patch_combos.sh`, both re-run on every `CRUSH_TAG` bump). The invariant
  either way: **local/loopback to the model (`127.0.0.1:8080`) is essential — only external egress
  is ever a target.**

**Deliberately NOT ported:** auth plumbing (local keyless llama-server behind SSH — nothing to sign
into), interactive GUI/Wayland + gamepad passthrough (headless Xvfb still works), and a dedicated
`crush-config-layering.md` (optional — covered by `architecture.md` + `crush-capabilities.md`). Fork
guidance is in `FORKING.md`.

## Reference docs

- `tasks/reference/architecture.md` — how the two halves fit, the pins (llama.cpp tag, Crush
  `v0.89.0`), the quant ladder, serve tuning, the crushrc/`llamacpp` config (explicit model pin +
  catalog suppression), dotfiles/host-config mounts, the `@`-import patch, the offline/airgap
  source-vendoring workflow, and the SELinux `label=disable` lesson. Read this first when picking the
  project up.
- `tasks/reference/crush-capabilities.md` — verified map of Crush `v0.89.0`'s features (context-file
  autoload, no native `@`-import, custom commands, hooks, provider/model selection + the
  `disable_default_providers` catalog switch, context-window/compaction). Read before touching
  Crush config or the port.
- `tasks/reference/gemma-4-alongside-glimmer.md` — Google's open-weights models against the
  OSI-licence bar: Gemma 1–3 are custom-licensed, **Gemma 4 is Apache-2.0** with official Q4_0 QAT
  GGUFs; the family table, llama.cpp support status, and the two-models/two-fixed-ports design.
  Implemented 2026-09-10 (§6 there); the Mac verification is `tasks/verify-gemma-4-on-the-mac.md`.
- `tasks/reference/crush-lsp-integration.md` — what Crush asks a language server for, the four
  start gates (user-configured / skip list / filetype+root marker / on PATH), where "no LSP client
  handles file" comes from, and the registry rows for every toolchain the image ships. Work:
  Implemented 2026-09-10 (work record `tasks/archive/2026/09/10/install-language-servers-for-crush.md`); the image + RHEL 9 check is `tasks/verify-language-servers-on-rhel9.md`.
- `tasks/reference/new-hardware-bringup.md` — the first hour on a new box: what `make probe` and
  `make smoke` each prove, then quant → `NGL` → `CTX` → `NP`, the three server-log lines that
  decide it, and what to record. Work: `tasks/new-hardware-bringup-runbook.md`.
- `tasks/reference/crush-prompt-history.md` — how Crush's prompt history works at `v0.89.0` (what the
  history list holds, the Up/Down state machine, ordering, where it is persisted — `.crush/crush.db`
  in the launch directory, so `/work` — and what `ctrl+r` search needed), plus §7: exactly what our
  `crush-shell-history.patch` changes. Read before touching history, the editor keymap, or the data
  directory.
- `tasks/reference/nested-podman-design.md` — nested-podman design/flags for the client (inner runs
  use the PODMAN_RUN_FLAGS convention + `--network=host`; the `--network=host`-breaks-bridged finding).
- `tasks/reference/glimmer-models-and-airgap-quant-selection.md` — survey of Meta's Muse Glimmer model
  family + the third-party quant landscape (sizes, licenses — all Apache-2.0), with a hardware-deferred
  recommendation for which GGUF quant to vendor to an airgap box. Read when deciding what/how much to pull.
- `tasks/reference/container-file-layout.md` — the baked-vs-mounted map of the client container: every
  Dockerfile `COPY`, every `SHELL_RUN_FLAGS` mount, final runtime paths, and the repo↔baked
  reference-doc mapping. Printable via `make -C client manifest`; also baked into the image (below).
  Consult it before citing a container path.

Also **baked into the image** at `~/.config/crush/reference/` (agent-readable on-demand, NOT
always-loaded, to save the local model's context): `llm-overused-phrases.md`, `print-debugging.md`,
`sandbox-capability-map.md`, `nested-podman-design.md`, `container-file-layout.md` (the baked-vs-mounted
map — kept in sync with its `tasks/reference/` twin), and `bluf-bottom-line-up-front.md` (the full
write-up behind the `## BLUF` task-doc convention). **Cite a baked doc by its
`~/.config/crush/reference/…` path, never `tasks/reference/…`** — the latter is a repo path absent
inside the container, so the agent can't reach it (the offline miss fixed 2026-08-22; a baked doc that
is copied from `tasks/reference/` must keep both copies in sync).

## In-flight tasks

Scan `tasks/` (top-level) at session start for the current list; as of 2026-09-10 (easy wins first —
lowest priority-number, then lowest difficulty-number):

- `crushrc-startup-failure-and-model-preselect.md` (P2/D2, **implemented, awaiting the host rebuild**)
  — the 2026-09-10 crushrc shipped `lsp add … --root-markers a b c`, which Crush parses as an
  unknown flag and refuses to start; fixed (one value per flag occurrence) and, per the maintainer,
  the crushrc now probes 8080/8081 at load and preselects the served model. Proven in-sandbox against
  the vendored build; done-state = `make -C client image` on the host, `crush` starts, `ctrl+l` shows
  two models.
- `verify-auto-allow-file-tools.md` (P3/D2) — real-machine check that file tools don't prompt and
  everything else still does (needs a client-image rebuild).
- `verify-vendored-airgap-rebuild.md` (P3/D3) — real-machine check that the vendored offline rebuild
  actually works with no network (client image + Mac server). **Gates the Crush bump.**
- `port-lean-image-nested-convention.md` (P4/D1, proposed) — add the lean-image-when-nested paragraph
  to the baked conventions file once the runClaudeInContainer wording lands.
- `bump-crush-to-v0.90.0.md` (P4/D2, **blocked**) — investigated (patch ports clean); blocked on
  `verify-vendored-airgap-rebuild.md` and on the airgapped Go being ≥1.26.6 for v0.90.0.
- `context-advisor-script.md` (P4/D2) — host-run server/context advisor script (drafted, **on hold**).
- `force-read-diversion-stack-on-session-load.md` (P4/D2, proposed, do-not-implement) — its premise
  (a host-mounted stack) is outdated since 2026-09-03; needs re-scoping before any go-ahead.
- `verify-vendor-pulls-all-quants.md` (P4/D3) — **deferred** (needs the target airgap hardware/quant);
  model-universe research done in `tasks/reference/glimmer-models-and-airgap-quant-selection.md`.
- `offline-nested-podman-base-images.md` (P4/D5) — seed base images so *nested* project builds work
  offline (proposed).
- `port-runclaude-conventions-systems.md` (P4/D5) — Phases 0–4 implemented; **testing phase deferred**.
- `new-hardware-bringup-runbook.md` (P5/D2, in progress) — runbook written and linked; walk it on a
  second box.
- `port-blocked-task-convention.md` (P5/D3) — port the blocked-task convention + `/recheck-blocked`
  from runClaudeInContainer (three tasks here already use the `Blocked on:`/`Recheck:` shape).
- `standardize-project-container-template.md` (P5/D5, proposed) — adopt the cross-project
  container-template standard (the `shell`/`shell-exec` pair + `SHELL_RUN_FLAGS`, mount conventions)
  in this repo's docs + `client/`; sibling task in runClaudeInContainer.
- `decide-egress-verification.md` (P6/D3, proposed) — decide whether the audit needs an enforced
  runtime egress check (strace/tcpdump or firewall permitting only the local model endpoint), or
  whether the source-level audit suffices; real-machine if built.
- `crush-at-import-parity.md` (P6/D4) — bring the `@`-import patch to full Claude parity (follow-up).

**Blocked (human-gated; `/recheck-blocked` tests them):** `verify-gemma-4-on-the-mac.md` (P3/D2 —
`make llama` at `b10883`, Gemma `probe`/`smoke` on 8081, Glimmer re-`smoke`, two models in the rebuilt
client's `ctrl+l`); `verify-language-servers-on-rhel9.md` (P3/D3 — the rebuilt full image, built
2026-09-10: the six-binary check + a `.py` symbol query remain; then the RHEL 9 airgap box: vendored `ty`
wheel → uncommented Dockerfile block → offline build → `lsp_*` works); `disable-crush-telemetry.md`
(P6/D2 — the runtime egress watch: no traffic to `data.charm.land`/`api.github.com`; overlaps
`decide-egress-verification.md`; last gate before archive).

Completed & archived (see `tasks/archive/2026/08/`): the bring-up, provider-catalog suppression (+ its
airgapped verification), dotfiles/host-config mounts, context-window sizing, the `@`-import patch,
nested-podman support (+ the baked-doc reachability fix), the airgap **source-vendoring** work
(implementation + the podman+make `vendor.sh` running inside the client image, `hf` flag-gated), the
**file-tool auto-allow** (crushrc `permissions allow` for file R/W; conservative-ask everything else),
**multi-quant model vendoring** (`MODEL_FILES` list + opt-in full weights + `check-repo` discovery —
`MODEL_FILES` became the *extra* set on 2026-09-10, see `architecture.md`),
the **`hf` install dnf-or-pip fallback** (dnf `python3-huggingface-hub`, else pip — for RHEL9-style repos),
**Apache-2.0 licensing** of the project (root `LICENSE` + SPDX headers; vendored trees keep theirs), the
**`make shell-exec`** target (batch twin of `make shell`, shared `SHELL_RUN_FLAGS`; 2026/08/29), and the
**Crush-build extraction** into `entrypoint/03-build-crush.sh` (the inline Dockerfile `RUN` → a
flag-passing script; 2026/08/29), the **dependency network audit** (all 213 vendored Go modules
triaged, 66 deep-audited at source, twelve `PATCH_OUT_<X>` decisions confirmed — findings in
`tasks/reference/dependency-network-audit.md`; 2026/08/29), and the **egress patch/flag
implementation** (thirteen flag-guarded build-time patches, combination-tested by
`tools/sweep_egress_patch_combos.sh`; vendor-complete-unpatched + patch-at-build model; verified on
the real machine — default-flag image built, Crush connected to the local model; 2026/08/29), and the
**container file-layout map** (`tasks/reference/container-file-layout.md` + synced baked twin +
`make manifest`; grew out of an in-container Crush session that had to reverse-engineer its own
layout — see the archived task's `crush.log`; 2026/08/30). **2026/09/10** (`tasks/archive/2026/09/10/`):
**Gemma 4 alongside Glimmer** (the `MODEL=` model table, fixed ports 8080/8081, `LLAMACPP_TAG` →
`b10883`, second crushrc provider), **language servers for Crush** (six dnf servers declared
explicitly; the RHEL 9 `/venv` + `ty`-wheel block, proven offline in a throwaway Stream 9), the
**minimal client image as the nested default** (`FULL_TOOLCHAIN` auto-defaulted from `NESTED_PODMAN`;
**reverted 2026-09-12** — the client is always the full toolchain now, `NESTED_PODMAN` run-time only:
`tasks/reference/nested-podman-vs-image-content.md`), the `make llama` tag-checkout fix, and the
**vim user toolkit** (six Fedora vim plugin rpms, a baked `.vimrc`, a conditional host `~/.vimrc` mount).
