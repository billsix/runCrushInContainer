# Forking this template for your own model / agent / conventions

runCrushInContainer is a **fork-friendly assistant-runner** (a "template" only in the sense of *this
tool* — a starting point to fork, **not** a template for the codebases you develop with it): a local
coding LLM served on one machine (`server/`) driven by a terminal coding agent in a disposable
container (`client/`) over an SSH tunnel, used to develop your other projects. It's built to be
re-pointed at different **models**, **quants**, or an **agent version** — the swappable surface is
Makefile variables (the two serving ports are fixed on purpose; see step 1), and the maintainer's
personal layer is kept separate so you can adopt the machinery and pull upstream improvements without
conflicts.

## What's portable vs personal

- **Portable (use as-is):** the whole container build/run stack (`server/Makefile`, `client/Makefile`,
  `client/Dockerfile`, `client/entrypoint/`), the baked conventions `CLAUDE.md` + the reference docs,
  the 8 slash commands, and the nested-podman flag set.
- **Personal / swappable:** the model + quant + pinned tags (Makefile variables), the personal-overlay
  `@`-imported `~/.ai-coding-conventions.personal.md`, the dotfiles (`.extrabashrc`), and the SSH-tunnel
  target.

## What you must change

1. **Point it at your machine + models** (`server/Makefile`, all variables — this IS the template
   surface): the model table — one row per model, `MODEL_REPO_<m>` / `MODEL_FILE_<m>` /
   `MODEL_ALIAS_<m>` / `MODEL_PORT_<m>` for each name in `MODELS` — plus `LLAMACPP_TAG`, `CTX`/`NP`,
   and the quant. Verify each repo path + GGUF filename resolves on Hugging Face
   (`make check-repo MODEL=<m>`) before trusting it. Replace `you@mac-studio` in the README's
   `ssh -N -L …` with your server's `user@host`. A port lives in **three** places that must move
   together — the Makefile row, the crushrc `--base-url`, and the tunnel line in `README.md` /
   `client/entrypoint/shell.sh` — which is why `PORT` is not an override knob.

2. **Swap the agent version** (`client/Makefile`): `CRUSH_TAG` (the Crush release). The baked `crushrc`
   pins each model (`<provider>/$(MODEL_ALIAS_<m>)`) and its `--context-window`, and probes the two
   ports at load to preselect the served one — update the provider/model pairs, the probe URLs, and
   `--context-window` to your models + your server's `CTX`. The **`@`-import patch** (`client/patches/`) is pinned to a Crush tag —
   re-verify/regenerate on a `CRUSH_TAG` bump (see
   `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`), or build stock with
   `make image CRUSH_AT_IMPORT=0`.

3. **Your personal conventions.** Copy
   `client/entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.example.md` to
   `~/.ai-coding-conventions.personal.md` on your host and fill in your identity, project→URL mapping,
   and standing authorizations. The client Makefile mounts that file over the baked blank default
   (which the conventions `@`-import), creating it empty if absent. Empty is fine — you just get the
   portable conventions with nothing added.

4. **Your dotfiles.** Replace `client/entrypoint/dotfiles/.extrabashrc` (prompt/aliases) with your own.

5. **No auth to set up.** The endpoint is a local, keyless `llama-server` behind your SSH tunnel —
   nothing to sign into (unlike the Claude sibling, which mounts host auth).

## Forking to a *different agent* (not Crush)

The **`server/` side and the general container stack are agent-agnostic** — reuse them directly. The
**`client/` config layer is Crush-specific**: the `crushrc` (Bash config), the command format
(`~/.config/crush/commands/*.md`, `$UPPERCASE` args), the `@`-import patch, and how conventions are
delivered (a global-context-path registered in `crushrc`). To drive a different agent, redo just that
config layer for the new agent's mechanisms (how it auto-loads a conventions file, its command format,
its config file). `tasks/reference/crush-capabilities.md` documents what had to be mapped for Crush —
a useful template for the equivalent analysis of another agent.

## What you should NOT need to touch

The portable `CLAUDE.md` and the `tasks/reference/` docs are written maintainer-agnostic. A proper-noun
reference to the maintainer's repos, host, or identity leaking into those (rather than into the
personal overlay) is a bug in the separation — please report it.

## License

This template is **Apache-2.0** (see `LICENSE`); the grant covers the repo's own files, and bundled or
vendored components (llama.cpp, Crush, the model weights) keep their own licenses — see the README
"License" section. Your fork may relicense its own additions.
