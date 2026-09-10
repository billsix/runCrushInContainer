# Give vim users a complete setup in the client image (vim is already there)

**Status:** **done 2026-09-10, archived** at the maintainer's word ("archive the vim task"); the host
`make -C client image` remains the maintainer's own check. Durable facts harvested to
`tasks/reference/architecture.md` (client section, "Editors"); this file is the work record. Mirrors
runClaudeInContainer's unit of the same slug. Created 2026-09-10 at the maintainer's request (William
Emerison Six <billsix@gmail.com>: "add vim, and whatever normally vim users want installed, to the base
install script").
**Priority:** 6
**Difficulty:** 2

## BLUF

`client/entrypoint/01-install-base.sh` **already installs `vim-enhanced` and `neovim`**, plus the
usual companions (`ctags`, `ripgrep`, `fd-find`, `fzf`, `bat`, `tmux`). What a vim user still lacks
is: vim as the default editor, a baked `.vimrc`, and the small set of Fedora-packaged plugins. Done
means those are in the base script/dotfiles, behind the same `FULL_TOOLCHAIN` split as everything
else, and `make image` builds.

## Context — read first

- `client/entrypoint/01-install-base.sh` — the alphabetical dnf list (`vim-enhanced` ~line 440,
  `neovim` present). Additions go alphabetically with a one-line reason, per `CLAUDE.md`.
- `client/entrypoint/dotfiles/` — currently `.config/` and `.extrabashrc`; no `.vimrc`. The
  Dockerfile bakes `dotfiles/` into `/root/`.
- `tasks/archive/2026/09/10/minimal-client-image.md` — `FULL_TOOLCHAIN=0` (the nested default); editors are arguably part of even the
  minimal image, plugins are not.
- The sibling task in runClaudeInContainer (same slug) — keep the two package lists identical so
  the sandbox and the Crush client feel the same.

## Plan (all Fedora rpms unless noted — verify names with `dnf search` in the image)

1. **`vim-default-editor`** — makes `vim` the system `$EDITOR`/`alternatives` default (git commit
   messages, `crontab -e`, …). Cheap; this is the one thing most "vim users" actually notice
   missing.
2. **Plugins from Fedora** (so no network at image *run* time and no plugin manager to bootstrap):
   `vim-fugitive` (git), `vim-airline` + `vim-airline-themes` (statusline), `vim-gitgutter`?,
   `vim-syntastic`/`vim-ale` (async lint), `vim-commentary`, `vim-surround`, `vim-nerdtree`,
   `vim-ctrlp`? — pick the ones that exist as rpms (`dnf search vim-` in the image); do not add a
   plugin manager.
3. **`.vimrc` in `dotfiles/`** — minimal, opinionated defaults: `syntax on`, `filetype plugin
   indent on`, `set number relativenumber`, `set hlsearch incsearch ignorecase smartcase`,
   `set expandtab shiftwidth=4 tabstop=4`, `set mouse=a`, `set clipboard=unnamedplus` (needs
   `vim-X11`/`gvim` for `+clipboard`, or `xclip` — decide), `let mapleader=","`. Keep it under 40
   lines; the maintainer's host `~/.vimrc` should be mountable over it like `~/.tmux.conf` is.
4. **Mount the host `~/.vimrc` conditionally** in `client/Makefile`, same idiom as
   `~/.tmux.conf` / `~/.gitconfig` (skipped if absent).
5. `universal-ctags` is what Fedora's `ctags` package provides — confirm, no change expected.

## Work record (2026-09-10)

- `client/entrypoint/01-install-base.sh`: `vim-ale`, `vim-commentary`, `vim-default-editor`,
  `vim-fugitive`, `vim-gitgutter`, `vim-nerdtree` (the six Fedora 44 packages; `vim-airline` and
  `vim-surround` are not packaged — rpm-only, so dropped). ~3 MB. The script is runClaudeInContainer's
  list + this repo's two language-server rpms + these six.
- `client/entrypoint/dotfiles/.vimrc`: runClaudeInContainer's file with this repo's paths in the header;
  baked by the existing `COPY entrypoint/dotfiles/ /root/`.
- `client/Makefile`: `VIMRC_MOUNT` (conditional, the tmux idiom) in `SHELL_RUN_FLAGS`; `make -n shell`
  emits no mount line when the host has no `~/.vimrc`.
- Docs: `CLAUDE.md` + `README.md` + `architecture.md` mount lists; `container-file-layout.md` **and its
  baked twin** got the two new rows (the baked `.vimrc`; the run-time mount). **Pre-existing drift
  found, not touched:** the twin and the `tasks/reference/` copy already differed — the 2026-09-03
  "stack does not persist" change updated only the baked twin's mounts table, and the reference copy
  still listed a `~/.config/crush/stack.md` mount. **Synced 2026-09-10** (maintainer: make them identical with the newest, by git date — the baked twin, `e13195f`): the reference copy is now a byte copy of the twin.
- Proof: throwaway `fedora:44`, nested — same harness as runClaudeInContainer's unit
  (`bash -lc 'echo $EDITOR'` → `/usr/bin/vim`; `vim -N -u /root/.vimrc -es` → all five plugin commands
  exist, `shiftwidth=4`, space leader).

## Verification / done-state

- [ ] **[HOST]** `make -C client image` builds; in `make -C client shell`: `git commit` opens vim,
      `:scriptnames` lists the baked `.vimrc` (or the mounted host one), `:Git` / `:NERDTreeToggle` work.
      Image-size delta (expected ~3 MB) recorded here.
- [x] Throwaway proof (2026-09-10, above).
- Note: the **minimal image** (`FULL_TOOLCHAIN=0`, the nested default) has no vim at all —
  `00-install-minimal.sh` ships `less` and no editor — so none of this applies there; by design
      (maintainer, 2026-09-10: "minimal doesn't need vim").

## Open questions

Resolved 2026-09-10 with runClaudeInContainer's twin (the maintainer: "do it for runCrushInContainer"):
rpm-only plugin set (the six Fedora ships), host `~/.vimrc` mounted conditionally, neovim left
unconfigured.
