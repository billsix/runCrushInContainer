# The Emacs contract — how a project's vendored Emacs is set up in its container

**Reference document.** The maintainer's Emacs setup, as every container-template project carries it,
written as a contract in the same tiers as the Dockerfile/Makefile contract (personal overlay,
github.com/billsix/dotfiles `.ai-coding-conventions.personal.md`): **invariant** (true of every
config), **common** (most), **variant** (legitimately differs). Derived 2026-11-07 (William Emerison Six
<billsix@gmail.com> asked for it) by surveying all 34 vendored configs: the repos with a git-tracked
`.emacs.d/init.el` (billsEmacsConfigs' 20 language folders, Craft, apue, dotfiles = the host Emacs,
geometricalgebra, gltron, hanoi ×3, modelviewprojection, multivariate-math, runClaudeInContainer,
smalltalk, spimulator, texExpToPng), grouping identical files by hash and reading each variant.
**Read this before creating or changing a project's `.emacs.d`, or conforming a new project.** The
conformance snapshot at the end lists the known drift.

## Where it lives

```
<project>/entrypoint/dotfiles/.emacs.d/
├── init.el                     # invariant shape; the language block varies
├── helm.el                     # invariant, byte-identical everywhere
├── preferences.el              # common, byte-identical across most projects
├── install-melpa-packages.el   # invariant shape; the package list varies by language
└── elpa/                       # vendored packages, source only (.elc/.eln gitignored)
```

A subproject layout (hanoi) has one `.emacs.d` per language folder, each standalone. The host Emacs is
github.com/billsix/dotfiles `.emacs.d/` (same `helm.el`; its own `bills-preferences.el` and per-mode
files).

## Container side (summary; the authoritative rule is in the personal overlay)

- **Invariant:** Emacs is installed **binary-only** (`dnf install emacs …` plus the language server),
  gated by the `USE_EMACS` build flag (Makefile default `1`, Dockerfile ARG default `0`). **No MELPA
  download or compile runs at image build**: no `emacs --batch --load install-melpa-packages.el`, no
  `byte-compile`/`package-install` in any `RUN`. A build-time install is network-dependent, slow, re-runs
  whenever an earlier layer changes, and is hidden at `make shell` by the `elpa/` mount anyway.
- **Invariant:** the vendored packages are **byte-compiled at run time, by Emacs itself**, the first time
  Emacs starts in `make shell`: `init.el` calls `(byte-recompile-directory package-user-dir 0)` right after
  `(package-initialize)`, which compiles every `.el` in `elpa/` that has no `.elc` yet. The `.elc` files
  land in the bind-mounted host `elpa/`, so they persist across containers (only the first start after
  `make update-emacs-packages` is slow); they are gitignored and `update-emacs-packages` strips them, so
  git only ever holds source. Model: geometricalgebra and modelviewprojection `init.el`. (Decided by
  William Emerison Six <billsix@gmail.com>, 2026-11-08.)
- **Invariant:** packages are **vendored** in `elpa/`, committed source-only (`*.elc`/`*.eln` in
  `.gitignore`), refreshed by **`make update-emacs-packages`** (mounts `elpa/` + `install-melpa-packages.el`,
  wipes, reinstalls from MELPA, strips compiled files, `git add -f`).
- **Invariant:** `.dockerignore` excludes `entrypoint/dotfiles/.emacs.d/elpa`, so the vendored packages
  are never baked into the image.
- **Invariant:** the Makefile's **`ELPA_MOUNT`** bind-mounts **only `elpa/`**
  (`-v …/.emacs.d/elpa:/root/.emacs.d/elpa:U,z`), in `shell`/`shell-exec` only. Everything else in
  `.emacs.d` reaches the image through the Dockerfile's dotfiles `COPY`, so **an edit to `init.el`,
  `helm.el`, or `preferences.el` needs `make image`**; an `elpa/` change does not.
- **Common:** the install lives in an `entrypoint/0N-install-emacs.sh` group script dispatched by the
  `USE_EMACS` `if` (geometricalgebra `05-install-emacs.sh`, modelviewprojection `04-install-emacs.sh`).
- **Invariant (Python):** the Python language server is **npm `pyright`** (`npm install -g pyright`,
  driving `lsp-pyright`), never the pip `pyright` launcher, which downloads its server on first use and
  silently fails offline.
- **Invariant (Python):** the project's ruff config **excludes the vendored tree**:
  `extend-exclude = ["entrypoint"]` under `[tool.ruff]` in `pyproject.toml` (geometricalgebra adds
  `"tasks/adhoc"` too). `elpa/` ships third-party `.py` files (treemacs's helpers), so a `format.sh` that
  runs `ruff check .` / `ruff format` over the whole tree rewrites upstream code; the config-level exclude
  covers every invocation, including an editor's. Naming the source directories in `format.sh` instead
  (modelviewprojection's `ruff check src tests …`) also works but leaves a bare `ruff format` exposed.
  Learned 2026-11-07: hanoi `python/`'s `make format` reformatted six vendored treemacs files; fixed with
  the exclude.

## `init.el` — invariant order, then the language block

Every `init.el` follows this order (geometricalgebra's and modelviewprojection's are good models):

1. `(package-initialize)`, then `(byte-recompile-directory package-user-dir 0)` (the run-time compile;
   see "Container side").
2. `(load-file "~/.emacs.d/helm.el")`, then `(load-file "~/.emacs.d/preferences.el")`.
3. **Theme block:** exactly one active `(load-theme '<theme> t)` with the others commented out on the
   lines around it (`modus-vivendi`, `material`, `dracula`, `monokai`, `zenburn`). Which one is active
   is variant (`material` in geometricalgebra/modelviewprojection, `modus-vivendi` in the C projects and
   billsEmacsConfigs).
4. `(global-auto-revert-mode)` + `(setq auto-revert-avoid-polling t)`: buffers follow edits made
   outside Emacs (the agent, the host).
5. **The language block** (variant content, invariant rules):
   - **lsp-mode is the language client.** `use-package lsp-mode` hooked to the project's modes
     (`lsp` or `lsp-deferred`), plus `lsp-ui`, plus the language package (`lsp-pyright`, `rust-mode`,
     `go-mode`, `lsp-java`, …). The server comes from dnf or npm in the image.
   - **The LSP root is pinned to the repo's container mount path.** `(setq lsp-auto-guess-root nil)`
     and an `:override` advice on `lsp--calculate-root` returning the mount (`"/craft/"`,
     `"/gacalc/"`), which must equal the Makefile's `REPO_MOUNT`. Without it, lsp-mode asks which root
     to use, or guesses `/`. hanoi additionally ignores the build/cache dirs under the mount in
     `lsp-file-watch-ignored-directories`, and enables yasnippet (its `CLAUDE.md`).
   - `(add-hook 'prog-mode-hook #'lsp-deferred)`.
   - **One language client per buffer.** eglot serves emacs-lisp only; the project language is
     lsp-mode's. A config that also hooks eglot to the project language removes that hook
     (`(remove-hook 'python-mode-hook 'eglot-ensure)`), so two clients never attach to one buffer.
   - Language extras as needed: clang-format on `C-c f` (C/C++, `:after cc-mode`), clangd's
     `--compile-commands-dir` pointing at the build dir, `lsp-pyright-typechecking-mode "basic"`.
   - **Common:** `yafolding` and/or `hs-minor-mode` folding on `prog-mode`.

## `helm.el` — invariant, byte-identical

```elisp
;; sample `helm' configuration use https://github.com/emacs-helm/helm/ for details
(helm-mode)
(require 'helm-xref)
(define-key global-map [remap find-file] #'helm-find-files)
;; C-x C-f on a file name prefills it using Emacs's own find-file-at-point
;; guesser, which also looks in parent folders.  Docs cite files relative to the
;; repository root (tasks/reference/x.md written inside tasks/foo.md); without
;; this, helm prefills tasks/tasks/reference/x.md, which does not exist.
(setq helm-ff-guess-ffap-filenames t)
(define-key global-map [remap execute-extended-command] #'helm-M-x)
(define-key global-map [remap switch-to-buffer] #'helm-mini)
```

helm owns `C-x C-f`, `M-x`, and `C-x b`. The ffap setting makes `C-x C-f` on a repo-root-relative doc
path open the file (2026-11-07; check with `tools/check_helm_file_at_point.sh <.emacs.d>`, 7 ERT cases).

## `preferences.el` — common, byte-identical across 25 of 34 configs

Copy it from Craft's `entrypoint/dotfiles/.emacs.d/preferences.el`. What it sets:

- Look: black background, white foreground; `show-paren-mode`; no tool bar, no menu bar, no startup
  message; face height 180; in a terminal frame, an unspecified background ("force transparency for
  streaming").
- Editing: spaces, never tabs (`indent-tabs-mode nil`); `delete-trailing-whitespace` on save;
  `global-visual-line-mode`; `global-display-line-numbers-mode`; unix line endings; no backup files.
- `region-generate-sha1` (an interactive command that copies the SHA-1 of the region).
- eglot for **emacs-lisp only**, with the comment explaining the one-client rule.
- `global-company-mode` with `company-idle-delay 0` and `company-minimum-prefix-length 1`.

The Python projects' variant also binds `C-c C-SPC` to `company-complete`.

## `install-melpa-packages.el` — invariant shape, variant list

Shape: `(require 'package)`, add the `melpa` archive (`https://melpa.org/packages/`),
`(package-initialize)`, `(setq package-selected-packages '(…))`, then install them. The list, from the
34-config survey:

- **In every config (34/34):** `company flycheck magit markdown-mode projectile which-key yasnippet`.
- **Near-universal (26–33):** `material-theme dracula-theme lsp-mode hydra helm-xref org-modern
  better-defaults helm-lsp lsp-ui`. A new config includes these.
- **Common extras (≈11):** `yafolding fold-this markdown-preview-mode discover zenburn-theme
  monokai-theme`.
- **Per language:** `clang-format` (C/C++); `lsp-pyright elpy blacken` (Python); `rust-mode`, `go-mode`,
  `lsp-java`, `lsp-haskell`/`haskell-mode`, `kotlin-mode`, `scala-mode`/`lsp-metals`, `swift-mode`,
  `tuareg`, `racket-mode`, `csharp-mode`, `zig-mode`, `nushell-mode`, `smalltalk-mode`,
  `typescript-mode`, `cmake-mode`, `toml-mode` as the language needs.

## Checking a config

- `bash tools/check_helm_file_at_point.sh <path>/.emacs.d` (this repo): the helm `C-x C-f` behavior
  against the config's own vendored helm.
- `md5sum <path>/.emacs.d/helm.el` against the canonical (any conforming project's copy): it must match
  byte for byte. Same for `preferences.el` unless the project is a documented variant.
- In the container: `make shell`, open a source file (one LSP client attaches, rooted at the mount) and
  a task doc (`C-x C-f` on a `tasks/…` path opens it).

## Conformance snapshot (2026-11-07) — known drift

Fixing these is `tasks/emacs-contract-conformance.md`.

- **hanoi (`cpp/`, `python/`, `rust/`): the config conforms** since 2026-11-07 (hanoi
  `tasks/archive/2026/11/07/emacs-config-match-geometricalgebra.md`). Its vendored `elpa/` trees still
  predate helm until the maintainer runs `make update-emacs-packages` in each folder.
- **The shared `preferences.el` comment says "C/C++ are served by lsp-mode + clangd"** in every copy,
  including the Python, Rust, Go, … ones. The rule it explains, eglot for emacs-lisp only, is
  language-neutral, so the wording should be too.
- **Emacs install not in a `0N-install-emacs.sh` group script:** Craft and gltron list `emacs` in the
  base install; apue, billsEmacsConfigs' 20 folders, and smalltalk had no such script either (install
  path to be checked per project).
- **No `ELPA_MOUNT` / `update-emacs-packages`:** runClaudeInContainer (the sandbox installs its packages
  differently; `USE_EMACS_CONFIG` flag) and smalltalk.
- **Contradictory eglot hook:** geometricalgebra, modelviewprojection, multivariate-math, and
  runClaudeInContainer hook eglot to `python-mode` in `preferences.el`, then `init.el` removes that
  hook. It works, but the contract is "eglot for emacs-lisp only", stated once.
- **MELPA install at image build** (`emacs --batch --load install-melpa-packages.el` in a `RUN`; grep
  of every `Dockerfile` under the maintainer's project root, 2026-11-08): apue, gltron, smalltalk,
  spimulator, texExpToPng, and all 20 billsEmacsConfigs folders. Craft was fixed 2026-11-08
  (github.com/billsix/Craft `tasks/archive/2026/11/08/emacs-packages-not-built-in-dockerfile.md`) and is
  the worked example for a C project.
- **No run-time compile:** only geometricalgebra, modelviewprojection, and runClaudeInContainer have
  `(byte-recompile-directory package-user-dir 0)` in `init.el`; the other 31 configs load their vendored
  packages as uncompiled source.
- **spimulator's `preferences.el`** has no eglot block at all.
- **Theme:** `material` vs `modus-vivendi` as the active theme (a variant, unless one is chosen as the
  standard).
