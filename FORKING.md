# Forking this template for your own model / agent / conventions

runCrushInContainer is a **template**: a local coding LLM served on one machine (`server/`) driven by a
terminal coding agent in a disposable container (`client/`) over an SSH tunnel. It's built to be
re-pointed at a different **model**, **quant**, **serving port**, or **agent version** — the swappable
surface is Makefile variables, and the maintainer's personal layer is kept separate so you can adopt
the machinery and pull upstream improvements without conflicts.

## What's portable vs personal

- **Portable (use as-is):** the whole container build/run stack (`server/Makefile`, `client/Makefile`,
  `client/Dockerfile`, `client/entrypoint/`), the baked conventions `CLAUDE.md` + the reference docs,
  the 7 slash commands, and the nested-podman flag set.
- **Personal / swappable:** the model + quant + pinned tags (Makefile variables), the personal-overlay
  `@`-imported `~/.ai-coding-conventions.personal.md`, the dotfiles (`.extrabashrc`), and the SSH-tunnel
  target.

## What you must change

1. **Point it at your machine + model** (`server/Makefile`, all variables — this IS the template
   surface): `MODEL_REPO`, `MODEL_FILE`, `MODEL_ALIAS`, `LLAMACPP_TAG`, `CTX`/`NP`, and the quant.
   Verify the repo path + GGUF filename resolve on Hugging Face (`make check-repo`) before trusting
   them. Replace `you@mac-studio` in the README's `ssh -N -L …` with your server's `user@host`. If you
   serve on a different `PORT`, change the crushrc `--base-url` to match.

2. **Swap the agent version** (`client/Makefile`): `CRUSH_TAG` (the Crush release). The baked `crushrc`
   pins the model (`muse-glimmer/$(MODEL_ALIAS)`) and `--context-window` — update both to your model +
   your server's `CTX`. The **`@`-import patch** (`client/patches/`) is pinned to a Crush tag —
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
