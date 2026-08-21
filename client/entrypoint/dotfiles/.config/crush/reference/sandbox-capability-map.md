# Sandbox capability map — what the Crush client image can do

**What this is:** an inventory of what the runCrushInContainer **client** container can do, for
answering "can the sandbox do X?" without re-reading the ~430-package install script. Adapted
2026-08-21 from runClaudeInContainer's copy — the client's toolchain (`entrypoint/01-install-base.sh`)
is **byte-identical** to runClaude's, so the toolchain inventory carries over directly; only the
agent, the GUI/controller passthrough, and the nested-podman specifics differ (noted inline).

## Base

Fedora 44, everything runs as container-root (= host UID 1000 under the rootless host podman).
Ephemeral `--rm` containers; persistent state only in host mounts. The agent is **Crush** (built from
source at image build), reaching a local LLM on a Mac over an SSH tunnel — not Claude Code.

## Language toolchains (compilers/interpreters in the image)

C/C++ (gcc, clang + analyzer/tools-extra, lld/mold/gold, ccache/distcc/bear), Rust (+ rust-analyzer,
rustfmt), Go (+ gopls — also builds Crush), Python 3 (scientific stack: numpy/scipy/pandas/matplotlib/
sympy, ipython, notebook, pytest(+xdist), mypy, pylint, black, ruff, ty, uv, cython, nanobind), Java
(OpenJDK 25 + latest, ant/maven), .NET SDK 8, Node.js/npm, Ruby, PHP, Perl, R, Julia, Octave, Haskell
(ghc, cabal), OCaml (+ dune, opam), Erlang, Elixir, Clojure, Racket, Common Lisp (sbcl, clisp), Lua
(+ luarocks), Zig, Swift, assembly (nasm, yasm), shells (bash, zsh, fish, ksh), TeX Live (with
dvipng/dvisvgm/standalone), WebAssembly (wabt).

## Build, debug, analyze

- **Build systems:** make, cmake, meson+ninja, autotools, scons, bison/flex, ragel/re2c, swig,
  protobuf, antlr4.
- **Debug/trace:** gdb, lldb, strace, ltrace, valgrind, radare2.
- **Profile/perf:** perf, heaptrack, google-perftools, kcachegrind, hyperfine, sysbench, stress-ng.
- **Sanitizer runtimes preinstalled:** libasan, libubsan.
- **Static analysis / lint:** clang-analyzer, cppcheck, ShellCheck, shfmt, ruff, ty, mypy, pylint,
  pre-commit.

## Cross-arch and emulation

- **qemu** (full package) — user-mode emulation for foreign-arch binaries.
- **mingw64-gcc** — Windows cross-builds. glibc-static / libstdc++-static for static linking.

## GUI, graphics, media

- **Headless GUI verification works with no changes:** the image ships `xorg-x11-server-Xvfb`, Mesa
  software GL (`mesa-dri-drivers`), and ImageMagick. Run `Xvfb :99`, point `DISPLAY` at it, screenshot
  with `import`, judge pixels. glfw reports `4.6 (Compatibility Profile) Mesa` through this path.
  **Caveat:** freeglut/GLUT demos won't render under Xvfb (X `BadAtom`, black capture) — GLFW-based
  demos render fine.
- **Interactive host display is NOT wired** in the client (unlike runClaude, which mounts the X11/
  Wayland sockets). If you need a nested GUI project to display on the host interactively, that
  passthrough would have to be added to `client/Makefile` (it isn't yet).
- Dev libraries for GL/Vulkan/SDL (glew, glfw, freeglut/-devel, SDL2_image, SDL3(+sound),
  vulkan-tools), GTK3/GTK4, Qt5/Qt6, cairo/pango/freetype. `aspell`+`aspell-en`; the Sphinx book
  toolchain → HTML+PDF via LuaLaTeX. Media: ffmpeg-free, sox, mpv, ImageMagick, gnuplot, graphviz,
  tesseract (OCR), poppler-utils (PDF).
- **Game controllers are NOT wired** in the client (no `USE_CONTROLLER`/`/dev/input` passthrough) —
  irrelevant to a coding agent.

## Network and services

Full client tooling (curl/wget/httpie/aria2, nmap, tcpdump, iperf3, mtr, mosh, wireguard-tools,
bind-utils) and local services for integration testing: postgresql, mariadb, redis, memcached, nginx,
sqlite. `gh` for GitHub, git-lfs, mercurial. The client itself runs `--network=host` so `127.0.0.1:8080`
reaches the SSH-forwarded model port. (systemd is not PID 1 — start services manually, e.g.
`redis-server`, `postgres -D …`.)

## Containers inside the client (nested podman)

Opt-in `make shell NESTED_PODMAN=1` (podman, buildah, skopeo, fuse-overlayfs are in the image) — lets
Crush build/run a project's own containers nested. **Inner runs need BOTH `--cgroups=disabled` and
`--network=host`.** Full design/flags/limits: `tasks/reference/nested-podman-design.md` (read that
before nested work).

## Hard limits (what the sandbox can NOT do)

- No host root, ever — the ceiling is host UID 1000 (rootless host podman).
- `/sys/fs/cgroup` and (by default) `/proc/sys` are read-only; no resource limiting of inner
  containers (`--cgroups=disabled` is mandatory nested).
- No udev events (device hotplug mid-session isn't seen).
- Nothing in the container survives exit except what's on a host mount.
- systemd is not PID 1 — services start manually.

## Growing the image

The package list is deliberately maximal — don't prune for cleanliness; add packages alphabetically to
`client/entrypoint/01-install-base.sh` (the host-runnable install script the Dockerfile sources).
Preserve the dnf cache mounts in the Dockerfile.
