" Baked default .vimrc for the runCrushInContainer client (client/entrypoint/dotfiles/.vimrc).
" Shadowed by the host's ~/.vimrc when `make shell` finds one (VIMRC_MOUNT in client/Makefile),
" so this is what a vim user gets with NO dotfile of their own. Plugins are Fedora rpms
" (vim-fugitive, vim-commentary, vim-nerdtree, vim-ale, vim-gitgutter) — no plugin manager,
" nothing fetched at run time. Task: tasks/vim-user-toolkit-in-base-image.md.

set nocompatible
syntax on
filetype plugin indent on

set number relativenumber      " absolute line at the cursor, relative elsewhere
set hlsearch incsearch         " highlight matches, search as you type
set ignorecase smartcase       " case-insensitive unless the pattern has a capital
set expandtab shiftwidth=4 softtabstop=4 tabstop=4
set autoindent smartindent
set mouse=a                    " mouse works in the terminal (tmux passes it through)
set scrolloff=4                " keep context lines above/below the cursor
set backspace=indent,eol,start
set wildmenu wildmode=longest:full,full
set laststatus=2               " always show the status line (also where ale/fugitive report)
set showcmd ruler
set hidden                     " switch buffers without saving first
set updatetime=300             " snappier gitgutter signs
set signcolumn=yes             " gitgutter/ale signs don't shift the text
set nobackup nowritebackup noswapfile   " the tree is a bind mount; keep it clean
set encoding=utf-8

let mapleader = " "
nnoremap <leader>n :NERDTreeToggle<CR>
nnoremap <leader>g :Git<CR>
nnoremap <leader>/ :nohlsearch<CR>

" ale: lint on save only (the format gates run the real linters); fix nothing automatically.
let g:ale_lint_on_text_changed = 'never'
let g:ale_lint_on_insert_leave = 0
let g:ale_fix_on_save = 0
