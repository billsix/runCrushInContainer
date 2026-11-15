# Give vim users a complete setup in the client image (vim is already there)

**Status:** complete (archived at the maintainer's word, "archive the vim task")
**Completed:** 2026-09-10
Created 2026-09-10 at the maintainer's request (William Emerison Six <billsix@gmail.com>: "add vim, and
whatever normally vim users want installed, to the base install script"). Mirrors runClaudeInContainer's
unit of the same slug. Durable facts were harvested to `tasks/reference/architecture.md` (client
section, "Editors"); this file is the work record.

## What this did

`client/entrypoint/01-install-base.sh` already installed `vim-enhanced` and `neovim` with the usual
companions (`ctags`, `ripgrep`, `fd-find`, `fzf`, `bat`, `tmux`). This task added what a vim user still
lacked: vim as the default editor, a baked `.vimrc`, the Fedora-packaged plugins, and a conditional mount
of the host `~/.vimrc`.

- `client/entrypoint/01-install-base.sh`: `vim-ale`, `vim-commentary`, `vim-default-editor`,
  `vim-fugitive`, `vim-gitgutter`, `vim-nerdtree` (~3 MB). These are the six that Fedora 44 packages;
  `vim-airline` and `vim-surround` are not packaged and were dropped.
- `client/entrypoint/dotfiles/.vimrc`: runClaudeInContainer's file with this repo's paths in the header,
  baked by the existing `COPY entrypoint/dotfiles/ /root/`.
- `client/Makefile`: `VIMRC_MOUNT` (conditional, the tmux idiom) in `SHELL_RUN_FLAGS`; `make -n shell`
  emits no mount line when the host has no `~/.vimrc`.
- Docs: the mount lists in `CLAUDE.md`, `README.md` and `tasks/reference/architecture.md`; two new rows
  (the baked `.vimrc`, the run-time mount) in `tasks/reference/container-file-layout.md` and its baked
  twin.

## Decisions (2026-09-10, resolved with runClaudeInContainer's twin)

- Plugins from Fedora rpms only: no run-time network and no plugin manager to bootstrap.
- Host `~/.vimrc` mounted conditionally over the baked one, like `~/.tmux.conf`.
- neovim left unconfigured.
- Package lists kept identical to runClaudeInContainer's so the sandbox and the Crush client feel the
  same (this repo's list = runClaude's + its two language-server rpms + these six).

Superseded: the task scoped the additions to the full image only, since the then-minimal image
(`FULL_TOOLCHAIN=0`, the nested default) shipped no editor by design. `FULL_TOOLCHAIN` was removed
2026-09-12; the client is always the full toolchain, so vim and the plugins are always present.

## Drift found and fixed

`tasks/reference/container-file-layout.md` and its baked twin had already diverged: the 2026-09-03
"stack does not persist" change updated only the twin's mounts table, so the reference copy still listed
a `~/.config/crush/stack.md` mount. At the maintainer's direction (make them identical with the newest by
git date, the baked twin at `e13195f`), the reference copy was made a byte copy of the twin, 2026-09-10.

## Verification

- Throwaway nested `fedora:44` proof (same harness as runClaudeInContainer's unit):
  `bash -lc 'echo $EDITOR'` → `/usr/bin/vim`; `vim -N -u /root/.vimrc -es` showed all five plugin
  commands, `shiftwidth=4`, space leader.
- Not recorded here: the host `make -C client image` + in-shell check (`git commit` opens vim, `:Git` /
  `:NERDTreeToggle` work) and the image-size delta. That was left as the maintainer's own check.
