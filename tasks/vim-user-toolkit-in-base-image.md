# Give vim users a complete setup in the client image (vim is already there)

**Status:** proposed — needs go-ahead; small. Created 2026-09-10 at the maintainer's request
(William Emerison Six <billsix@gmail.com>: "add vim, and whatever normally vim users want
installed, to the base install script").
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
- `tasks/minimal-client-image.md` — `FULL_TOOLCHAIN=0`; editors are arguably part of even the
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

## Verification / done-state

`make -C client image` builds; in the container `vim --version` shows `+clipboard` (if chosen),
`:scriptnames` lists the baked `.vimrc`, `git commit` opens vim, and the plugins load
(`:AirlineToggle`, `:Git`). `FULL_TOOLCHAIN=0` still has `vim-enhanced` and the `.vimrc` but no
plugins. Image-size delta recorded here.

## Open questions

1. **Which plugins?** Recommend the git + statusline + comment/surround set above via rpms only.
2. **Clipboard support** — `vim-X11` pulls X libraries into a headless image. Recommend skip;
   note `"+y` is unavailable.
3. **Mount host `~/.vimrc`?** Recommend yes, conditional, matching the tmux/gitconfig idiom.
