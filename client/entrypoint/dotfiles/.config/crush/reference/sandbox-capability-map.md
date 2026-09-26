# Sandbox capability map — what the image and run flags actually provide

**What this is:** an inventory of what a `make shell` sandbox can do, for
answering "can the sandbox do X?" without re-reading the Dockerfile's ~300
package names and the Makefile's flag blocks. Compiled 2026-07-30. The
Dockerfile is the authority; this maps it by capability.

## Base

Fedora 44, everything runs as container-root (= host UID 1000 under the
rootless host podman). Ephemeral `--rm` containers; persistent state only in
host mounts (see `claude-config-layering.md`). Claude Code installed as the
native binary via the official installer, updated at image build.

**Editors:** Emacs (the vendored config, `USE_EMACS_CONFIG`), **vim** (`vim-enhanced` +
`vim-default-editor`, so `$EDITOR`/`git commit` open vim; plugins as Fedora rpms — fugitive,
commentary, nerdtree, ale, gitgutter — driven by the baked `~/.vimrc`, shadowed by the host's
`~/.vimrc` when `make shell` finds one; no clipboard/X11 build, so `"+y` is unavailable), neovim
(unconfigured), nano. Added 2026-09-10 (`tasks/vim-user-toolkit-in-base-image.md`).

## Language toolchains (compilers/interpreters in the image)

C/C++ (gcc, clang + analyzer/tools-extra, lld/mold/gold, ccache/distcc/bear),
Rust (+ rust-analyzer, rustfmt), Go (+ gopls), Python 3 (with scientific stack:
numpy/scipy/pandas/matplotlib/sympy, ipython, notebook, pytest(+xdist), mypy,
pylint, black, ruff, ty, uv, cython, nanobind), Java (OpenJDK 25 + latest,
ant/maven), .NET SDK 8, Node.js/npm, Ruby, PHP, Perl, R, Julia, Octave,
Haskell (ghc, cabal), OCaml (+ dune, opam), Erlang, Elixir, Clojure, Racket,
Common Lisp (sbcl, clisp), Lua (+ luarocks), Zig, Swift, assembly (nasm, yasm),
shells (bash, zsh, fish, ksh), TeX Live (with dvipng/dvisvgm/standalone),
WebAssembly (wabt), and Lean 4 (theorem prover / proof assistant — `lean` +
`lake`, installed via elan, not dnf; added 2026-09-26 — see `entrypoint/install-lean.sh`).

## Build, debug, analyze

- **Build systems:** make, cmake, meson+ninja, autotools, scons, bison/flex,
  ragel/re2c, swig, protobuf, antlr4.
- **Debug/trace:** gdb, lldb, strace, ltrace, valgrind, radare2.
- **Profile/perf:** perf, heaptrack, google-perftools, kcachegrind, hyperfine,
  sysbench, stress-ng.
- **Sanitizer runtimes preinstalled:** libasan, libubsan (projects don't need
  to add them).
- **Static analysis / lint:** clang-analyzer, cppcheck, ShellCheck, shfmt,
  ruff, ty, mypy, pylint, pre-commit.

## Cross-arch and emulation

- **qemu** (full package) — user-mode emulation for running foreign-arch
  binaries (the spimulator multi-arch shim verification path).
- **mingw64-gcc** — Windows cross-builds.
- glibc-static / libstdc++-static for static linking.

## GUI, graphics, media

- **Headless GUI verification needs no project changes:** the image ships
  `xorg-x11-server-Xvfb`, Mesa software GL (`mesa-dri-drivers`), and
  ImageMagick — run `Xvfb :99`, point `DISPLAY` at it (shareable into nested
  containers via `/tmp/.X11-unix`), screenshot with `import`, and judge pixels.
  glfw reports `4.6 (Compatibility Profile) Mesa` through this path.
  **Caveat (2026-08-02): freeglut/GLUT C++ demos won't render under Xvfb** — they
  fail with X `BadAtom` and capture black. GLFW-based demos render fine; for GLUT
  use the host display, not the headless path.
- **Host display passthrough:** X11 socket + Wayland (`$XDG_RUNTIME_DIR`)
  mounts are always on — GUI apps (GTK/Qt apps, Emacs-pgtk) display
  on the host in interactive use.
- Dev libraries for GL/Vulkan/SDL (glew, glfw, **freeglut/-devel** (added
  2026-08-02, for building nested GLUT C++ demos), SDL2_image, SDL3(+sound),
  vulkan-tools, **libshaderc-devel** (added 2026-09-22: the HarbourMasters N64 ports'
  libultraship Vulkan backend includes `shaderc/shaderc.hpp`; without it a PaperBoat/Ghostship
  build fails at the final link on `shaderc_*` undefined references), **opus-devel +
  opusfile-devel** (added 2026-09-22: Ship of Harkinian's cmake configure `find_package(Opus)`
  / `OpusFile` are REQUIRED; libogg/libvorbis-devel were already present)), GTK3/GTK4, Qt5/Qt6,
  cairo/pango/freetype.
- **aspell + aspell-en** (added 2026-08-02) — spellcheck; e.g. enumerate the words
  the mvp book's `aspell` gate would flag via `aspell --personal=… list < file`.
- **Sphinx book toolchain → HTML + PDF** (added 2026-08-02) — `python3-sphinx` +
  `python3-furo` + `python3-nbsphinx` + `myst-nb`; PDF via **LuaLaTeX**
  (`texlive-luahbtex` provides `lualatex`, NOT `texlive-luatex`) with
  `fontspec`/`gnu-freefont` and the Sphinx-LaTeX support set (fncychap, wrapfig,
  capt-of, needspace, tabulary, framed, titlesec, varwidth, fancyhdr, multirow,
  threeparttable, eqparbox) + `latexmk`. Used by the mvp and gacalc books. lualatex,
  not pdflatex, is required once autodoc pulls Unicode-math docstrings into the PDF —
  pdflatex aborts on characters like `√`/`∧`/`e₁`.
- Media: ffmpeg-free, sox, mpv, ImageMagick, gnuplot, graphviz, tesseract
  (OCR), poppler-utils (PDF).

## Game controllers (opt-out: `USE_CONTROLLER=0`)

`/dev/input` is bind-mounted with `--group-add keep-groups` so SDL apps see
host gamepads. Caveats, all real: plug the controller in **before** launching
(no udev hotplug in the container, SDL enumerates at startup only); readability
rides on systemd-logind's `uaccess` ACLs (works because rootless podman maps
container-root to the logged-in host user); if SELinux denies, add
`label=disable` for that run.

## Network and services

Full client tooling (curl/wget/httpie/aria2, nmap, nmap-ncat (`nc`/`ncat`), tcpdump,
iperf3, mtr, mosh, wireguard-tools, bind-utils) and local services for integration testing:
postgresql, mariadb, redis, memcached, nginx, sqlite. `gh` for GitHub, git-lfs,
mercurial, and **VCS-history tools** (`git-svn`, `cvs`, `cvsps`, `git-filter-repo` — added
2026-09-22 to reconstruct an old project's history from SourceForge/CVS/GitHub). Networking
in *nested* containers: see
`nested-podman-design.md` (bridged netavark works; `--network=host` fallback).

## Containers inside the sandbox

Opt-in `NESTED_PODMAN=1` (podman, buildah, skopeo are in the image). The
design, flags, constraints (the PODMAN_RUN_FLAGS convention for inner runs, RAM-backed
store) and operating lore live in **`nested-podman-design.md`** — read that
before nested work. Which project images fit the nested store, and the lean-image-when-nested
standard (2026-09-10): **`minimal-nested-images.md`**.

## Hard limits (what the sandbox can NOT do)

- No host root, ever — the ceiling is host UID 1000 (rootless host podman).
- `/sys/fs/cgroup` (historically ro; rw on the current stack) and (by default) `/proc/sys` restricted; no resource
  limiting of inner containers (inner runs use the PODMAN_RUN_FLAGS convention; the cgroups-ro wall is gone on the current stack but the flag is kept as belt-and-braces).
- No udev events (hotplug of any device won't be seen mid-session).
- Nothing in the container survives exit except what's on a host mount.
- systemd is not PID 1 — services start manually (`postgres -D …`,
  `redis-server`), not via `systemctl`.

## Conventions for growing the image

From root `CLAUDE.md`: the package list is deliberately maximal — don't prune
for cleanliness; add packages alphabetically in **`entrypoint/01-install-base.sh`**
(the host-runnable install script the Dockerfile sources — the list is no longer
inline in the `Dockerfile`); preserve the dnf cache mounts (those stay in the
`Dockerfile`); keep host mounts conditional (except `~/.claude` and the personal-overlay
mount `~/.ai-coding-conventions.personal.md`, both unconditional — see
`claude-config-layering.md` for why). The image's one build flag is **`USE_EMACS_CONFIG`**
(added 2026-08-14; Makefile default `1`, Dockerfile ARG `0`): `USE_EMACS_CONFIG=0` drops
the vendored `.emacs.d/` for a clean box, e.g. for a fork.
