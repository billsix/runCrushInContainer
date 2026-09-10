# runCrushInContainer

Run a **local coding LLM** on your Mac and drive it from **[Crush](https://github.com/charmbracelet/crush)**
(Charm's terminal coding agent) in a disposable Linux container — a **tool for developing your own
codebases with a private, local coding assistant**, the way
[runClaudeInContainer](https://github.com/billsix/runClaudeInContainer) does with Claude Code. Its
job has two halves: it **runs the agent** in a throwaway container pointed at whatever project
you're working on, and it **delivers to the agent the conventions** that teach it how your projects
are structured and built (the ported working-method machinery — see "What's in use").

It's **fork-friendly** — the model, quant, serving port, and agent are Makefile variables you can
swap — so it's a starting point for *your own assistant-runner*. That is **not** the same as a
template for the codebases you build with it: those follow the container-per-project conventions the
agent is taught, which live in your personal overlay (`ai-coding-conventions.personal.md`), not here.

> **Status: working.** Both sides are built and running — the model serves on the Mac
> (Metal) and Crush in the Linux client container generates against it over the SSH tunnel.
> The `make` targets below are real. See `tasks/reference/architecture.md` for how it fits
> together and the gotchas, and `tasks/` for remaining polish.

## The idea

Two machines, one tunnel:

```
  [MAC STUDIO]  llama.cpp (Metal) serving Muse Glimmer  ──  127.0.0.1:8080  (OpenAI /v1)
                                     and/or Gemma 4   ──  127.0.0.1:8081  (fixed ports)
        ▲
        │   ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081  you@mac-studio   (Linux host)
        │
  [LINUX HOST]  localhost:8080 / localhost:8081
        │
  [CONTAINER]   crush  →  http://127.0.0.1:8080 | :8081          (podman run --network=host)
```

The model runs on the Mac (the strongest local hardware here — a 36 GB Mac Studio). The
agent runs in a throwaway container on Linux. The server listens on **loopback only**; the
one way in is an SSH port-forward, so nothing is exposed on the network.

## The models — Meta Muse Glimmer 30B and Google Gemma 4 26B-A4B

Two models, both **Apache-2.0** (OSI-approved), both served by the same llama.cpp build, each on
its own **fixed** port:

| `make serve MODEL=` | model | GGUF | port |
|---|---|---|---|
| `glimmer` (default) | [Muse Glimmer 30B](https://huggingface.co/blog/muse-glimmer), Meta's agentic coding model | Q4_K_M, ~16.8 GB | `8080` |
| `gemma` | [Gemma 4 26B-A4B](https://huggingface.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf), Google's MoE (3.8B active) | official QAT Q4_0, ~14.4 GB | `8081` |

Either fits a 36 GB Mac with room for a 64k context; **both at once (~31 GB of weights) does not** —
serve one at a time, or size the second's `CTX` down. The Glimmer quant ladder (Q5_K_M, Q6_K, …) and
the MLX backend are in `tasks/reference/architecture.md`; why Gemma 4 (and not 1–3, which are not
OSI-licensed) and why the 26B-A4B is in `tasks/reference/gemma-4-alongside-glimmer.md`.

llama.cpp gained Muse Glimmer support in release **`b10353`** (2026-08-10) and Gemma 4 vision
handling in PR #28335 (2026-09-04); the server pins **`b10883`** (2026-09-09).

## Server — on the Mac (native)

Prerequisites `[MAC]`: Xcode command-line tools (`xcode-select --install`), `cmake`
(`brew install cmake`), and Python with `huggingface_hub` (or `uv`).

```sh
cd server
make deps      # check the prerequisites above (Xcode CLT + cmake) are installed
make llama     # clone + build llama.cpp for Metal, pinned to a known-good tag
make pull      # download BOTH GGUFs (Glimmer Q4_K_M + Gemma 4 Q4_0, ~31 GB total) into ./models
make serve                # start llama-server for Muse Glimmer on 127.0.0.1:8080 (OpenAI /v1) ...
make serve MODEL=gemma    # ... or for Gemma 4 on 127.0.0.1:8081 -- one at a time on a 36 GB Mac
make probe [MODEL=gemma]  # (in another terminal) does it ANSWER? -- lists the model alias + live context size
make smoke [MODEL=gemma]  # (in another terminal) does it GENERATE? -- one chat round-trip that must reply "OK"
```
> `MODEL=` is the only switch: it picks the GGUF, the alias, and the port together. The ports are
> **not** configurable (the client's crushrc and the SSH tunnel hardcode them). Anything else you
> pass — `CTX`, `NGL`, `NP` — applies to whichever model you're serving.
> **New machine (airgap box, bigger or smaller Mac)?** Run `probe`, then `smoke`, then size the
> knobs in this order — quant → `NGL` → `CTX` → `NP` — following
> `tasks/reference/new-hardware-bringup.md`; it names the three server-log lines that decide it.

`make serve-mlx` runs the MLX backend instead (often faster on Apple Silicon; Glimmer only).
Quant file and context size are Makefile variables — override per run, e.g.
`make serve CTX=32768` or `make serve MODEL_FILE=<another downloaded quant>`.

**How much to download** — `make pull` always fetches the two default GGUFs; `MODEL_FILES` adds more
from the *selected* model's repo:

```sh
# DEFAULT: one GGUF per model — Glimmer Q4_K_M (~16.8 GB) + Gemma 4 Q4_0 (~14.4 GB):
make pull

# + EVERY Glimmer quant GGUF in its repo:
make pull MODEL_FILES="*.gguf"

# + Glimmer's full-precision (unquantized) weights too:
make pull MODEL_FILES="*.gguf" FULL_MODEL_FILES="*.safetensors" FULL_MODEL_REPO=meta-models/Muse-Glimmer-30B

# + Gemma 4's vision projector (not needed for coding):
make pull MODEL=gemma MODEL_FILES="*mmproj*"
```

- Each `MODEL_FILES` entry is an exact filename or an `hf --include` glob, resolved against the
  selected `MODEL`'s repo (Glimmer unless `MODEL=gemma`). `make check-repo [MODEL=gemma]` lists a
  repo's real filenames.
- The **full weights** are opt-in (`FULL_MODEL_FILES`, empty by default; Glimmer only) and live in the
  base `…-30B` repo, not the `…-GGUF` one — hence `FULL_MODEL_REPO`. Verify the exact repo/names on HF.
- Quant ladder + sizes: `tasks/reference/architecture.md`.

## Connecting — the SSH port-forward

From the **Linux host**, open the tunnel to the Mac and leave it running — forward **both** model
ports in one command (`-L` repeats), so switching models later never means touching the tunnel:

```sh
ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 you@mac-studio.local
```

- `-N` — don't run a remote command, just forward.
- `-L 8080:127.0.0.1:8080` — forward **Linux-host** port `8080` → over SSH → the Mac's
  `127.0.0.1:8080`, where `llama-server` serves Muse Glimmer; `-L 8081:127.0.0.1:8081` does the same
  for Gemma 4. A forward to a port nothing is serving costs nothing until something uses it.

**This command looks like it hangs — that is correct.** `-N` runs the tunnel in the
foreground with no output and no prompt; that terminal *is* the tunnel now. Leave it open and
use another terminal for everything else. To get your prompt back instead, add `-f` (fork to
the background after authentication):

```sh
ssh -fN -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 you@mac-studio.local   # returns immediately; runs in background
pkill -f 'ssh -fN -L 8080'                                                    # ...tear it down later with this
```

**Verify the tunnel** from a *second* terminal on the Linux host — a JSON model listing means
you're wired end-to-end (`8080` for Glimmer, `8081` for Gemma 4 — whichever you `make serve`d):

```sh
curl -s http://127.0.0.1:8080/v1/models     # Muse Glimmer  -> {"data":[{"id":"muse-glimmer",...
curl -s http://127.0.0.1:8081/v1/models     # Gemma 4       -> {"data":[{"id":"gemma-4",...
```

Connection-refused means that model's server or the tunnel is not up. The forward is *lazy* — it
only connects to the Mac's port when something (this `curl`, or Crush) actually uses the local end,
which is why the `ssh` command sits there quietly even before anything hits it, and why forwarding
the port of a model you aren't serving is harmless.

Now `localhost:8080` / `localhost:8081` on the Linux host reach the models on the Mac. The client's
crushrc reaches each provider on its own port; Crush's models dialog (`ctrl+l`) picks between them.
(Replace `you@mac-studio.local` with your Mac's user and hostname/IP.)

## Client — the container (on Linux)

```sh
cd client
make image     # build the image: full toolchain + Crush compiled from source (pinned)
make shell     # podman run --rm --network=host … then launch `crush`
make shell-exec SCRIPT=path/to/script.sh   # run a script in that same env (no TTY), then exit
make shell-exec CMD='some command'         # ^ or an inline command
make manifest  # print the container file layout (baked vs mounted paths; no build)
```

`make shell-exec` is the batch twin of `make shell`: same container and mounts, but it runs a
script (`SCRIPT=`, relative to the mounted PROJECT at `/work`) or an inline `CMD=` and exits,
instead of dropping you into an interactive shell — for ad-hoc/CI use.

`--network=host` makes the container share the host's network, so Crush talking to
`127.0.0.1:8080` / `:8081` hits the SSH-forwarded ports and, through them, the Mac. The baked
`crushrc` preconfigures exactly two local providers, **pins Muse Glimmer (`8080`) and Gemma 4
(`8081`) explicitly, preselects Glimmer, and suppresses Crush's built-in model catalog** so only
those two are offered; switch with the models dialog (`ctrl+l`).

## Airgapped rebuild — vendoring the sources

Rebuild the whole system on an airgapped machine. Only the three internet-sourced artifacts are
vendored — **Crush** (+ Go deps), **llama.cpp**, and the **model GGUFs** (both models). The Fedora base
image and dnf packages are the airgapped box's own (not vendored). Design details:
`tasks/reference/architecture.md`.

The airgap box is **hardware-independent** — it needn't be a Mac. llama.cpp is vendored as **source**, so
you build it for whatever backend you have there (e.g. CUDA on NVIDIA); the GGUF and Crush are
backend-agnostic. Building and running the *server* on the airgap box is up to you and your hardware —
this section covers only getting the vendored sources across. (The Mac/Metal + SSH-tunnel topology above
is the maintainer's dev setup, not a requirement.)

**1. Vendor — on the ONLINE box** (needs only `podman` + `make`):

```sh
./vendor.sh            # DEFAULT: Crush + llama.cpp source + BOTH models, one GGUF each (~31 GB)
FULL=1 ./vendor.sh     # FULL:    the above + ALL Glimmer quant GGUFs + Glimmer's full-precision weights
```

Builds the client image and runs all vendoring inside it, producing `client/vendor/crush`,
`server/llama.cpp` (full history), and `server/models/`. **Default vendors one GGUF per model —
Glimmer Q4_K_M and Gemma 4 Q4_0; `FULL=1` adds every Glimmer quant plus the unquantized weights.** For
a specific set instead, pass `MODEL_FILES="…"` / `FULL_MODEL_FILES="…"` (same meaning as in
`server/Makefile` — run `make -C server check-repo [MODEL=gemma]` to list a repo's real filenames; verify
the repo on HF). Override the Crush version with `CRUSH_TAG=vX.Y.Z ./vendor.sh`.

**2. Transport** — tar the repo (the vendored trees are gitignored but ride along) and copy it over:

```sh
tar czf runCrushInContainer-airgap.tgz runCrushInContainer/
```

> ⚠ Use a plain `tar`/`zip` of the directory — **not** `git archive`/`git bundle`, which would drop the
> gitignored vendored sources.

**3. Rebuild — on the AIRGAPPED box, no network.** The client (Crush) is hardware-agnostic:

```sh
cd client && make image CRUSH_VENDORED=1
```

> ⚠ `CRUSH_VENDORED=1` is required on the airgap build — a plain `make image` is the online path (it
> clones Crush and fails with no network). On enforcing SELinux, if the build mount is denied, set
> `CRUSH_VENDOR_FLAGS` in `client/Makefile` to `:ro,z`. The airgap build installs no `hf` (it's gated
> behind `VENDOR_TOOLS`, online-only), so the airgap dnf mirror needs nothing beyond the base packages.

> **RHEL 9 base?** RHEL 9 packages no Python language server, so Crush's `lsp_*` tools would have
> nothing for `.py`. `client/Dockerfile` carries a commented-out block that installs the vendored `ty`
> wheel (`./vendor.sh` fetches it; `TY_VERSION` in `client/Makefile`) into a python3.11 `/venv` —
> uncomment it there. Details: `tasks/reference/crush-lsp-integration.md` › "RHEL 9".

The **server** side you build and run to suit your hardware from the vendored `server/llama.cpp` source
(e.g. `cmake -DGGML_CUDA=ON` for NVIDIA) and the vendored `server/models/` GGUF — that part is yours to
set up. `server/`'s Makefile targets (`make llama`/`serve`) are Metal/macOS for the maintainer's dev box,
not the airgap path.

## Layout

| Path | Purpose |
| --- | --- |
| `server/` | macOS-native llama.cpp server (Makefile: `llama` / `pull` / `serve` / `serve-mlx`) |
| `client/` | Linux Podman image with Crush built in (Dockerfile + Makefile); `client/patches/` holds the local Crush patches (the `@`-import feature + the flag-guarded egress patch set — see `tasks/reference/dependency-network-audit.md`) |
| `tasks/` | Task docs (`tasks/`), durable reference docs (`tasks/reference/`), and the dated archive (`tasks/archive/`) |

## Beyond the basics (still local + keyless — no auth to set up)

The first cut was just "get it running"; the client has since grown a few things:

- **A local `@`-import patch for Crush** (`client/patches/`, applied at build when
  `CRUSH_AT_IMPORT=1`, on by default via `make image`) so a `@path` on its own line in a context
  file (`CLAUDE.md`/`AGENTS.md`/`CRUSH.md`) is recursively spliced in — a feature Crush lacks upstream.
- **Shell-style prompt history** (`client/patches/crush-shell-history.patch`, applied when
  `CRUSH_SHELL_HISTORY=1`, on by default via `make image`): Up recalls the prompt you just sent,
  history spans every session in the project rather than resetting with each one, same-second
  entries stop shuffling, and **`ctrl+r` opens a reverse search** — except while an attachment is
  pending, where `ctrl+r` remains Crush's attachment-delete prefix. How it all works:
  `tasks/reference/crush-prompt-history.md`.
- **Only the two local models are offered** — the baked `crushrc` pins Muse Glimmer (`8080`) and
  Gemma 4 (`8081`) explicitly and sets `option default-providers false` to suppress Crush's built-in
  provider catalog.
- **Host config mounts** — `~/.tmux.conf` / `~/.gitconfig` / `~/.gnupg` are mounted in when present,
  plus a baked `.extrabashrc` (prompt, aliases).

The runClaudeInContainer working-method machinery is now **ported** — the cross-project conventions
(a lean, always-loaded `CLAUDE.md`), the task-doc and reference-doc systems, the diversion stack
(host-mounted so it survives `--rm`), the personal-overlay layering, the 7 slash commands, and
nested-podman support (`make shell NESTED_PODMAN=1`). See `tasks/port-runclaude-conventions-systems.md`.

**Customize it for yourself — the personal overlay (`ai-coding-conventions.personal.md`).** The baked, always-loaded
`CLAUDE.md` (at `~/.config/crush/CLAUDE.md`) `@`-imports **`~/.config/crush/ai-coding-conventions.personal.md`**,
over which `make shell` mounts your host's **`~/.ai-coding-conventions.personal.md`** (auto-created
empty if absent). **That one mounted file is where your per-user config and instructions go** — your
identity, project→URL mapping, mount layout, standing authorizations, any personal guidance — and the
agent picks them up every session, while the conventions tracked in this repo stay maintainer-agnostic.
So you customize the setup without editing anything tracked: just fill in that host file. Start from
`client/entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.example.md`; see `FORKING.md`.

## Forking

runCrushInContainer is a fork-friendly **assistant-runner** — point it at a different model, quant,
serving port, or agent by editing the Makefile variables, and layer in your own personal conventions
(the ones the agent then follows). (It's a template for *this tool*, not for the projects you develop
with it.) See **`FORKING.md`** for
exactly what to change (and what's portable vs personal).

## License

**Apache-2.0** — see [`LICENSE`](LICENSE). Copyright © 2026 William Emerison Six.

The grant covers **this repository's own files** (the Makefiles, Dockerfile, entrypoint scripts,
`crushrc`, dotfiles, and docs). **Bundled and vendored components keep their own licenses** — llama.cpp
(MIT), Crush and its bundled Go modules under `client/vendor/crush` (**FSL-1.1-MIT** — Functional Source
License 1.1, © Charmbracelet, Inc., which converts to MIT two years after each release), and the Muse
Glimmer model weights (Apache-2.0, from Meta). A fork may relicense its own additions.
