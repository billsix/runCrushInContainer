# runCrushInContainer

Run a **local coding LLM** on your Mac and drive it from **[Crush](https://github.com/charmbracelet/crush)**
(Charm's terminal coding agent) in a disposable Linux container. A sibling of
[runClaudeInContainer](https://github.com/billsix/runClaudeInContainer), built to be a
template you can point at a different model or agent.

> **Status: working.** Both sides are built and running — the model serves on the Mac
> (Metal) and Crush in the Linux client container generates against it over the SSH tunnel.
> The `make` targets below are real. See `tasks/reference/architecture.md` for how it fits
> together and the gotchas, and `tasks/` for remaining polish.

## The idea

Two machines, one tunnel:

```
  [MAC STUDIO]  llama.cpp (Metal) serving Muse Glimmer  ──  127.0.0.1:8080  (OpenAI /v1)
        ▲
        │   ssh -N -L 8080:127.0.0.1:8080  you@mac-studio      (run on the Linux host)
        │
  [LINUX HOST]  localhost:8080
        │
  [CONTAINER]   crush  →  http://127.0.0.1:8080/v1             (podman run --network=host)
```

The model runs on the Mac (the strongest local hardware here — a 36 GB Mac Studio). The
agent runs in a throwaway container on Linux. The server listens on **loopback only**; the
one way in is an SSH port-forward, so nothing is exposed on the network.

## The model — Meta Muse Glimmer 30B

[Muse Glimmer](https://huggingface.co/blog/muse-glimmer) is Meta's open-weights 30B agentic
coding model (Apache-2.0). We run the **Q4_K_M** GGUF quant (~16.8 GB) via llama.cpp — a
comfortable fit on 36 GB with room for a large context. Other quants (Q5_K_M, Q6_K, …) and
the MLX backend are covered in `tasks/crush-local-llm-bringup.md`.

llama.cpp gained Muse Glimmer support in release **`b10353`** (2026-08-10), so the server
pins llama.cpp to that tag or newer.

## Server — on the Mac (native)

Prerequisites `[MAC]`: Xcode command-line tools (`xcode-select --install`), `cmake`
(`brew install cmake`), and Python with `huggingface_hub` (or `uv`).

```sh
cd server
make deps      # check the prerequisites above (Xcode CLT + cmake) are installed
make llama     # clone + build llama.cpp for Metal, pinned to a known-good tag
make pull      # download the Q4_K_M GGUF from Hugging Face into ./models
make serve     # start llama-server on 127.0.0.1:8080 (OpenAI-compatible /v1)
make probe     # (in another terminal) confirm the server answers before wiring the client
```

`make serve-mlx` runs the MLX backend instead (often faster on Apple Silicon). Model, quant,
port, and context size are Makefile variables — override per run, e.g.
`make serve CTX=32768`.

## Connecting — the SSH port-forward

From the **Linux host**, open the tunnel to the Mac and leave it running:

```sh
ssh -N -L 8080:127.0.0.1:8080 you@mac-studio.local
```

- `-N` — don't run a remote command, just forward.
- `-L 8080:127.0.0.1:8080` — forward **Linux-host** port `8080` → over SSH → the Mac's
  `127.0.0.1:8080`, where `llama-server` is listening.

**This command looks like it hangs — that is correct.** `-N` runs the tunnel in the
foreground with no output and no prompt; that terminal *is* the tunnel now. Leave it open and
use another terminal for everything else. To get your prompt back instead, add `-f` (fork to
the background after authentication):

```sh
ssh -fN -L 8080:127.0.0.1:8080 you@mac-studio.local   # returns immediately; runs in background
pkill -f 'ssh -fN -L 8080'                             # ...tear it down later with this
```

**Verify the tunnel** from a *second* terminal on the Linux host — a JSON model listing means
you're wired end-to-end:

```sh
curl -s http://127.0.0.1:8080/v1/models
```

Connection-refused means the server or the tunnel is not up; a clean listing means Crush will
discover the model. The forward is *lazy* — it only connects to the Mac's `8080` when
something (this `curl`, or Crush) actually uses the local end, which is why the `ssh` command
sits there quietly even before anything hits it.

Now `localhost:8080` on the Linux host reaches the model on the Mac. (Replace
`you@mac-studio.local` with your Mac's user and hostname/IP.)

## Client — the container (on Linux)

```sh
cd client
make image     # build the image: full toolchain + Crush compiled from source (pinned)
make shell     # podman run --rm --network=host … then launch `crush`
```

`--network=host` makes the container share the host's network, so Crush talking to
`127.0.0.1:8080` hits the SSH-forwarded port and, through it, the Mac. Crush is preconfigured
as a custom OpenAI-compatible provider pointing at that endpoint.

## Layout

| Path | Purpose |
| --- | --- |
| `server/` | macOS-native llama.cpp server (Makefile: `llama` / `pull` / `serve` / `serve-mlx`) |
| `client/` | Linux Podman image with Crush built in (Dockerfile + Makefile) |
| `tasks/` | Task docs — the bring-up plan and the deferred conventions-porting follow-up |

## What's intentionally minimal (for now)

This first cut is just "get it running." The task/stack/personal-config machinery from
runClaudeInContainer is **not** here yet — see `tasks/port-runclaude-conventions-systems.md`.
No auth to set up: the endpoint is a local, keyless server behind your SSH tunnel.

## License

Follows the `runClaudeInContainer` family. Copyright © 2026 William Emerison Six.
