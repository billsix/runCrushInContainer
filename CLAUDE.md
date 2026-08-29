# runCrushInContainer — project notes

**Status: working, conventions ported.** Both `server/` and `client/` are built and in use — the
local model serves on the Mac (Metal, ~21 t/s) and Crush in the client container talks to it over
the SSH tunnel, loads the ported conventions, and follows them. The runClaudeInContainer
working-method machinery is now ported (see "What's in use" below); remaining items are tracked in
`tasks/`.

**What this repo is for.** Like `github.com/billsix/runClaudeInContainer`, this is a **tool for
running a coding assistant in a disposable container to develop your *other* codebases** — here the
assistant is **Crush** (Charm's terminal agent, `github.com/charmbracelet/crush`) driving a **local
coding LLM** (Meta's **Muse Glimmer 30B**) served on the Mac. Its job is two-fold: **run the agent**
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
  `CRUSH_AT_IMPORT`, `CRUSH_VENDORED` (offline build from `client/vendor/crush`), `VENDOR_TOOLS`
  (bake the vendoring-only `hf`; default off). The template value is swapping these. Two cross-file
  couplings to keep in sync:
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
- **diversion stack** — host-mounted at `~/.config/crush/stack.md` (survives `--rm`);
- **personal-overlay layering** — the everyday per-user customization path: the baked always-loaded
  `CLAUDE.md` (`~/.config/crush/CLAUDE.md`) `@`-imports `~/.config/crush/ai-coding-conventions.personal.md`
  (blank tracked default), over which `make shell` mounts the host's `~/.ai-coding-conventions.personal.md`
  (auto-`touch`ed if absent). **Filling in that one host file is how a user adds their own identity /
  project→URL mapping / mount layout / instructions** without editing anything tracked; the agent loads
  it every session and the tracked conventions stay maintainer-agnostic. Example to copy:
  `client/entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.example.md`; see `FORKING.md`;
- **7 slash commands** (`/new-task`, `/stack-*`, … — in Crush's `/` dialog under the **User** tab);
- **nested-podman** (`make shell NESTED_PODMAN=1`; inner runs need `--cgroups=disabled --network=host`);
- **`make shell-exec`** (`client/Makefile`) — the batch twin of `make shell`: `make shell-exec
  SCRIPT=<path under the mounted PROJECT at /work> | CMD='...'` runs a script/command in the same
  container env and exits (no TTY) — for ad-hoc/CI use. `shell` + `shell-exec` share one
  `SHELL_RUN_FLAGS` variable so they can't drift; `client/entrypoint/shell.sh` ends `set -e … exec
  bash "$@"`. Cross-project fan-out + design: `github.com/billsix/runClaudeInContainer`
  `tasks/add-shell-exec-target.md` and `.../fan-out-shell-exec-to-projects.md`. The general template
  contract for this lives in the personal overlay (`ai-coding-conventions.personal.md`), not here.
- **thirteen local Crush patches** (`client/patches/`), each behind its own defaulted build flag:
  `crush-at-import.patch` (`CRUSH_AT_IMPORT ?= 1`) plus twelve `PATCH_OUT_<X>` egress patches from
  the dependency network audit (update check, telemetry, `update-providers`, web tools, sourcegraph,
  Google/Vertex, Bedrock/AWS, Azure, OpenRouter, Vercel, Hyper, Copilot — defaults per
  `tasks/reference/dependency-network-audit.md` §5). ALL patches apply at **build time** in
  `client/entrypoint/03-build-crush.sh`, identically in both build modes; `vendor-crush.sh` vendors
  the **complete unpatched** tree so any flag combination builds offline. Every build clones (or
  copies the vendored tree) + builds from source (no plain `go install …@tag`). Combination-tested by
  `tasks/adhoc/implement-egress-patch-flags/sweep_patch_combos.sh`.
- **no telemetry / no phone-home** — PostHog telemetry (`data.charm.land`) off via Dockerfile
  `ENV CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1` + `option metrics false`; the GitHub update check off
  via `crush-no-update-check.patch`. See `tasks/disable-crush-telemetry.md`. That covers **Crush's own
  code**; the full audit of the **213 vendored Go deps** is DONE (2026-08-29) —
  `tasks/reference/dependency-network-audit.md` holds the findings and the twelve confirmed
  `PATCH_OUT_<X>` decisions (implementation: `tasks/implement-egress-patch-flags.md`; triage
  scanner: `tools/triage_dependency_egress.py`, re-run on every `CRUSH_TAG` bump). Note the
  invariant either way: **local/loopback to the model (`127.0.0.1:8080`) is essential — only external
  egress is ever a target.**

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
- `tasks/reference/nested-podman-design.md` — nested-podman design/flags for the client (inner runs
  need `--cgroups=disabled --network=host`; the `--network=host`-breaks-bridged finding).
- `tasks/reference/glimmer-models-and-airgap-quant-selection.md` — survey of Meta's Muse Glimmer model
  family + the third-party quant landscape (sizes, licenses — all Apache-2.0), with a hardware-deferred
  recommendation for which GGUF quant to vendor to an airgap box. Read when deciding what/how much to pull.

Also **baked into the image** at `~/.config/crush/reference/` (agent-readable on-demand, NOT
always-loaded, to save the local model's context): `llm-overused-phrases.md`, `print-debugging.md`,
`sandbox-capability-map.md`, `nested-podman-design.md`, and `bluf-bottom-line-up-front.md` (the full
write-up behind the `## BLUF` task-doc convention). **Cite a baked doc by its
`~/.config/crush/reference/…` path, never `tasks/reference/…`** — the latter is a repo path absent
inside the container, so the agent can't reach it (the offline miss fixed 2026-08-22; a baked doc that
is copied from `tasks/reference/` must keep both copies in sync).

## In-flight tasks

Scan `tasks/` (top-level) at session start for the current list; as of 2026-08-29 (easy wins first —
lowest priority-number, then lowest difficulty-number):

- `disable-crush-telemetry.md` (P6/D2, **blocked**) — telemetry (`data.charm.land`) + GitHub
  update-check disabled in the client image (implemented + staged 2026-08-27). **Blocked on** a
  real-machine image-rebuild + runtime egress check (folds into `verify-auto-allow-file-tools.md`);
  `/recheck-blocked` tests it. Last gate before archive.
- `implement-egress-patch-flags.md` (P3/D6, **implemented 2026-08-29**) — the audit's thirteen
  flag-guarded build-time patches are authored, combination-tested (42-combo sweep), and wired
  through `03-build-crush.sh`/Dockerfile/Makefile; `vendor-crush.sh` now vendors complete +
  unpatched. Remaining gate: one real-machine default-flag `make image` (rides with
  `verify-vendored-airgap-rebuild.md`). Findings + flag index:
  `tasks/reference/dependency-network-audit.md`.
- `decide-egress-verification.md` (P6/D3, proposed) — decide whether the audit needs an enforced
  runtime egress check (strace/tcpdump or firewall permitting only the local model endpoint), or
  whether the source-level audit suffices; real-machine if built.
- `standardize-project-container-template.md` (P5/D5, proposed) — adopt the cross-project
  container-template standard (the `shell`/`shell-exec` pair + `SHELL_RUN_FLAGS`, mount conventions)
  in this repo's docs + `client/`; sibling task in runClaudeInContainer.
- `verify-vendored-airgap-rebuild.md` (P3/D3) — real-machine check that the vendored offline rebuild
  actually works with no network (client image + Mac server). **Gates the Crush bump.**
- `verify-auto-allow-file-tools.md` (P3/D2) — real-machine check that file tools don't prompt and
  everything else still does (needs a client-image rebuild).
- `bump-crush-to-v0.90.0.md` (P4/D2) — investigated (patch ports clean); **blocked on
  `verify-vendored-airgap-rebuild.md`** and on the airgapped Go being ≥1.26.6 for v0.90.0.
- `context-advisor-script.md` (P4/D2) — host-run server/context advisor script (drafted, **on hold**).
- `offline-nested-podman-base-images.md` (P4/D5) — seed base images so *nested* project builds work
  offline (proposed).
- `port-runclaude-conventions-systems.md` (P4/D5) — Phases 0–4 implemented; **testing phase deferred**.
- `crush-at-import-parity.md` (P6/D4) — bring the `@`-import patch to full Claude parity (follow-up).
- `verify-vendor-pulls-all-quants.md` (P4/D3) — **deferred** (needs the target airgap hardware/quant);
  model-universe research done in `tasks/reference/glimmer-models-and-airgap-quant-selection.md`.
- `port-blocked-task-convention.md` (P5/D3) — port the blocked-task convention from runClaudeInContainer.

Completed & archived (see `tasks/archive/2026/08/`): the bring-up, provider-catalog suppression (+ its
airgapped verification), dotfiles/host-config mounts, context-window sizing, the `@`-import patch,
nested-podman support (+ the baked-doc reachability fix), the airgap **source-vendoring** work
(implementation + the podman+make `vendor.sh` running inside the client image, `hf` flag-gated), the
**file-tool auto-allow** (crushrc `permissions allow` for file R/W; conservative-ask everything else),
**multi-quant model vendoring** (`MODEL_FILES` list + opt-in full weights + `check-repo` discovery),
the **`hf` install dnf-or-pip fallback** (dnf `python3-huggingface-hub`, else pip — for RHEL9-style repos),
**Apache-2.0 licensing** of the project (root `LICENSE` + SPDX headers; vendored trees keep theirs), the
**`make shell-exec`** target (batch twin of `make shell`, shared `SHELL_RUN_FLAGS`; 2026/08/29), and the
**Crush-build extraction** into `entrypoint/03-build-crush.sh` (the inline Dockerfile `RUN` → a
flag-passing script; 2026/08/29), and the **dependency network audit** (all 213 vendored Go modules
triaged, 66 deep-audited at source, twelve `PATCH_OUT_<X>` decisions confirmed — findings in
`tasks/reference/dependency-network-audit.md`; 2026/08/29).
