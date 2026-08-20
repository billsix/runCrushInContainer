# Bake dotfiles + mount host config (tmux, gitconfig, …) like runClaudeInContainer

**Status:** IMPLEMENTED + verified (2026-08-20). Full default-flags `make image` (22 GB) not re-run —
the dotfiles layer was verified in isolation instead (trivial COPY+source, low risk).
**Priority:** 5
**Difficulty:** 3
**Started:** 2026-08-20 · **Completed:** 2026-08-20

## Implementation (2026-08-20)

- **`client/entrypoint/dotfiles/.extrabashrc`** — created: `ls --color` alias, `GPG_TTY=$(tty)`, the
  PS1 prompt. No git-identity exports (maintainer: Crush doesn't need `CLAUDE_USER_*`).
- **`client/Dockerfile`** — added `COPY entrypoint/dotfiles/ /root/` + `RUN echo "source
  ~/.extrabashrc" >> ~/.bashrc` (and refreshed the now-stale crushrc comment to say "pinned model +
  catalog suppressed" instead of "auto-discovers").
- **`client/Makefile`** — added `TMUX_MOUNT` / `GITCONFIG_MOUNT` / `GNUPG_MOUNT` (the runClaudeInContainer
  `readlink -f` + `[ -f ]`/`[ -d ]` idiom, `:Z`, → `/root/…`) and appended them to the `shell` run.

**Verified:** `make -n shell` emits all three `-v …:Z` flags when the host files exist (they do in this
env); `make help` parses; a throwaway nested build proved `COPY entrypoint/dotfiles/ /root/` +
`source ~/.extrabashrc` works (`.extrabashrc` present, `~/.bashrc` sources it, `ls` alias loads in an
interactive shell).

## Goal

Make the client container as comfortable as the runClaudeInContainer sandbox: **bake a set of
default dotfiles into the image** and **conditionally mount the user's host config** (tmux, git,
gnupg) so an interactive Crush session has the maintainer's shell/tmux/git setup instead of a bare
root shell. Right now `client/` has neither — `shell.sh` just `cd /work` + `exec bash`, and the only
mount is the project at `/work`.

This is a template-conformance gap: runClaudeInContainer is the sibling template
(`github.com/billsix/runClaudeInContainer`), and this repo should follow the same two mechanisms.

## How runClaudeInContainer does it (the pattern to copy)

- **Baked dotfiles (Dockerfile):** `COPY entrypoint/dotfiles/ /root/` bakes `.extrabashrc` (prompt,
  `ls` alias, `GPG_TTY`, and `git config`-derived identity exports), and other dotfiles; then
  `echo "source ~/.extrabashrc" >> ~/.bashrc` so the shell picks it up.
- **Conditional host mounts (Makefile):** each optional host file is mounted only if it exists, via
  the `readlink -f` + `if [ -f … ]` idiom — e.g. `TMUX_MOUNT` (`~/.tmux.conf`), `GITCONFIG_MOUNT`
  (`~/.gitconfig`), `GNUPG_MOUNT` (`~/.gnupg`). Missing files are skipped cleanly, so the build/run
  still works on a machine that lacks them. These are appended to the `shell` target's `podman run`.

## Decisions (2026-08-20, maintainer: "whatever was done in runClaudeInContainer")

- **Host files to mount:** exactly runClaudeInContainer's set — **`~/.tmux.conf`, `~/.gitconfig`,
  `~/.gnupg`**, all conditional. Do NOT mount `~/.config/crush/` (the baked `crushrc` is the point of
  this repo; a host mount would shadow it).
- **Baked `.tmux.conf`:** NO — runClaudeInContainer bakes none; tmux config comes only from the host
  mount. The only baked dotfile is `.extrabashrc`.
- **Emacs:** SKIP — no `.emacs.d/`, no `USE_EMACS_CONFIG` flag (not wanted in a Crush client).

## Proposed changes (this repo) — copy runClaudeInContainer verbatim, minus emacs/.claude

1. **`client/entrypoint/dotfiles/.extrabashrc`** — the only baked dotfile. Copy runClaudeInContainer's
   **minus the git-identity exports** (decision 2026-08-20: Crush doesn't need `CLAUDE_USER_NAME`/
   `CLAUDE_USER_EMAIL`, and there's no `CRUSH_USER_*` equivalent to add). So it's just:
   ```sh
   alias ls='ls --color=auto'
   export GPG_TTY=$(tty)
   PS1='\[\e[36m\]┌─(\t) \[\e[32m\]\u@\h:\w\n\[\e[36m\]└─λ \[\e[0m\]'
   ```
2. **`client/Dockerfile`** — add, near the other COPYs:
   ```dockerfile
   COPY entrypoint/dotfiles/ /root/
   RUN echo "source ~/.extrabashrc" >> ~/.bashrc
   ```
3. **`client/Makefile`** — add the three mount vars verbatim from runClaudeInContainer (define `HOME`
   if not already), using `readlink -f` + an existence test (`-f` for the files, `-d` for `.gnupg`),
   `:Z`, mounted to `/root/…`:
   ```make
   TMUX_FILE := $(HOME)/.tmux.conf
   TMUX_REAL_PATH := $(shell readlink -f $(TMUX_FILE))
   TMUX_MOUNT := $(shell if [ -f $(TMUX_REAL_PATH) ]; then echo "-v $(TMUX_REAL_PATH):/root/.tmux.conf:Z" ; fi)
   GITCONFIG_FILE := $(HOME)/.gitconfig
   GITCONFIG_REAL_PATH := $(shell readlink -f $(GITCONFIG_FILE))
   GITCONFIG_MOUNT := $(shell if [ -f $(GITCONFIG_REAL_PATH) ]; then echo "-v $(GITCONFIG_REAL_PATH):/root/.gitconfig:Z" ; fi)
   GNUPG_FILE := $(HOME)/.gnupg
   GNUPG_REAL_PATH := $(shell readlink -f $(GNUPG_FILE))
   GNUPG_MOUNT := $(shell if [ -d $(GNUPG_REAL_PATH) ]; then echo "-v $(GNUPG_REAL_PATH):/root/.gnupg:Z" ; fi)
   ```
   Then append `$(TMUX_MOUNT) $(GNUPG_MOUNT) $(GITCONFIG_MOUNT)` to the `shell` target's `podman run`
   (alongside the existing `$(SELINUX_OPT) $(NET_FLAGS) -v $(PROJECT):/work $(EXTRA_MOUNTS)`).
4. **`:Z` note:** the client already runs `--security-opt label=disable`, so `:Z` is redundant but
   harmless; keep it for sibling parity. It's safe for these *config* files (the `:Z`-poisons-host-repo
   caveat in runClaudeInContainer is about relabeling whole project repos via `EXTRA_MOUNTS`, not dotfiles).

## Verification

`make -n shell` shows the mount flags appear only when the host files exist; `make image` builds with
the baked `.extrabashrc`; launch `make shell` and confirm the prompt, `ls` color, and (with a host
`~/.gitconfig`) that `git config user.name` resolves inside the container.

## Open questions

None — the three design questions are resolved above ("whatever runClaudeInContainer does"). Needs only
a go-ahead to implement.

## Cross-links

- Sibling implementation: `github.com/billsix/runClaudeInContainer` (`Dockerfile`, `Makefile`,
  `entrypoint/dotfiles/`).
- The project-template conformance conventions (mounts, dotfiles) — this repo's `CLAUDE.md` and the
  family template.
