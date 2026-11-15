# Bake dotfiles + mount host config (tmux, gitconfig, …) like runClaudeInContainer

**Status:** complete
**Started:** 2026-08-20 · **Completed:** 2026-08-20

Closed a template-conformance gap with the sibling `github.com/billsix/runClaudeInContainer`: the
client image now bakes a default `.extrabashrc` and conditionally mounts the user's host tmux, git and
gnupg config, so an interactive Crush session gets the maintainer's shell setup instead of a bare root
shell. Before this, `client/` had neither (`shell.sh` just `cd /work` + `exec bash`, and the only
mount was the project at `/work`).

## What was done

- **`client/entrypoint/dotfiles/.extrabashrc`**: created with the `ls --color=auto` alias,
  `GPG_TTY=$(tty)` and the PS1 prompt, copied from runClaudeInContainer minus its git-identity exports.
- **`client/Dockerfile`**: added `COPY entrypoint/dotfiles/ /root/` and
  `RUN echo "source ~/.extrabashrc" >> ~/.bashrc`; refreshed the stale crushrc comment to say "pinned
  model + catalog suppressed" instead of "auto-discovers".
- **`client/Makefile`**: added `TMUX_MOUNT` / `GITCONFIG_MOUNT` / `GNUPG_MOUNT` using the
  runClaudeInContainer `readlink -f` + existence-test idiom (`-f` for the files, `-d` for `.gnupg`),
  `:Z`, mounted to `/root/…`, and appended them to the `shell` target's `podman run`.

## Decisions (2026-08-20, maintainer: "whatever was done in runClaudeInContainer")

- **Mounted exactly runClaudeInContainer's set**: `~/.tmux.conf`, `~/.gitconfig`, `~/.gnupg`, all
  conditional. Did not mount `~/.config/crush/`, since a host mount would shadow the baked `crushrc`
  that is the point of this repo.
- **No baked `.tmux.conf`**: runClaudeInContainer bakes none; tmux config comes only from the host
  mount. `.extrabashrc` is the only baked dotfile.
- **No git-identity exports**: Crush doesn't need `CLAUDE_USER_NAME`/`CLAUDE_USER_EMAIL`, and there is
  no `CRUSH_USER_*` equivalent.
- **No emacs**: no `.emacs.d/`, no `USE_EMACS_CONFIG` flag (not wanted in a Crush client).
- **Kept `:Z`** for sibling parity even though the client runs `--security-opt label=disable` (so it is
  redundant). It is safe for config files; the `:Z`-poisons-host-repo caveat applies to relabeling
  whole project repos via `EXTRA_MOUNTS`.

## Verification

- `make -n shell` emitted all three `-v …:Z` flags when the host files existed; `make help` parsed.
- A throwaway nested build proved the `COPY` + `source ~/.extrabashrc` layer: `.extrabashrc` present,
  `~/.bashrc` sources it, the `ls` alias loads in an interactive shell.
- A full default-flags `make image` (22 GB) was not re-run; the dotfiles layer was verified in
  isolation instead (a trivial COPY + source, low risk). Checking `git config user.name` inside a live
  `make shell` was not recorded.

## Related

- Sibling implementation: `github.com/billsix/runClaudeInContainer` (`Dockerfile`, `Makefile`,
  `entrypoint/dotfiles/`).
- `tasks/reference/architecture.md`: dotfiles/host-config mounts.
