# Install the language servers Crush's LSP tools need — Python first, then every toolchain the image ships

**Status:** complete
**Completed:** 2026-09-10

## What this did

Crush on the airgapped box kept answering "no LSP client handles file" for a Python class (non-fatal);
William Emerison Six <billsix@gmail.com> asked for it fixed on 2026-09-10. Crush bundles no language
servers: it auto-starts registry-known servers that are on `PATH`, match the file type, and find a root
marker in `/work`. This task made every server explicit and dnf-sourced: two dnf additions and six
`lsp add` lines for the Fedora image (Part 1), a tested, commented-out RHEL 9 `/venv` + vendored `ty`
wheel block in `client/Dockerfile` (Part 2), and the docs (Part 3). All three parts were implemented and
committed by the maintainer. The checks needing real machines (the rebuilt Fedora image and the RHEL 9
airgap box) went to `tasks/verify-language-servers-on-rhel9.md`, which also took over the proof
harnesses in `tasks/adhoc/verify-language-servers-on-rhel9/`. Durable knowledge:
`tasks/reference/crush-lsp-integration.md` (§4 measured table, § RHEL 9).

## Decisions (maintainer, 2026-09-10)

1. **Install source: dnf only** ("it should only be dnf tools, unless it's python, and then make a venv,
   like geometricalgebra does … obviously if the dnf environment has a lsp, use that one, not a venv").
   The airgap rebuild has only its own dnf mirror, so `npm -g`, `gem`, `opam`, `cargo install` or
   tarballs would vanish there.
2. **Python server: `ty`** ("sure ty"), first as a pip pin, then reversed the same day to Fedora's dnf
   `ty`, unpinned, because decision 1 says use dnf when it has a server.
3. **Install all servers dnf offers** ("install all"); `jdtls` and `haskell-language-server` are not
   packaged, so they dropped out.
4. **Explicit `lsp add` for every language** ("whatever you recommend"): determinism over the
   registry's skip list, root-marker gate and PATH-rescan latency.
5. **RHEL 9 delivered as commented-out Dockerfile lines**, tested first, using `python3.11` (the
   maintainer's choice; BaseOS 3.9 is too old for `ty`).

**Superseded:** decision 3 also said to skip the additions under `FULL_TOOLCHAIN=0`; that flag was
removed 2026-09-12 and the client is always the full toolchain.

## Diagnosis

Not run: the failing project is on the airgapped box. Since dnf `ty` was already on `PATH`, the likely
causes were Python's skip-list/registry row or a missing root marker at `/work`; an explicit
`lsp add python` bypasses both. To confirm later: `option debug-lsp true` and read `crush_logs`.

## Surveys (2026-09-10)

- **Fedora 44 dnf:** packaged `ty` 0.0.74, `python3-lsp-server` 1.13.1, `gopls` 0.18.1, `rust-analyzer`
  1.98.0, clangd 22.1.8, `nodejs-bash-language-server` 5.6.0, `glsl-analyzer`. Not packaged: JS/TS, Lua,
  LaTeX, Haskell, Java, OCaml, Ruby, TOML, Markdown, YAML, Dockerfile, Emacs Lisp servers; those get none.
- **RHEL 9** (CentOS Stream 9 AppStream + BaseOS as proxy, plus EPEL 9): no Python LSP at all; has
  `rust-analyzer`, clangd, EPEL's `golang-x-tools-gopls` 0.11.1, `python3.11`/`python3.12`, `nodejs` 16.
  No bash or GLSL server. `ty` (a dependency-free Rust wheel) was chosen over pylsp (large dependency set)
  and pyright/basedpyright (need Node 18+).

## Work record (2026-09-10)

- **Part 1.** `client/entrypoint/01-install-base.sh` gained `glsl-analyzer` and
  `nodejs-bash-language-server` alphabetically (otherwise a verbatim copy of runClaudeInContainer's list;
  the sibling repo does not get them). `client/entrypoint/crushrc` gained one comment block and six
  `lsp add` lines (python `ty`, go, c, rust, sh, glsl). In a throwaway `fedora:44`,
  `check_fedora_servers.sh` + `lsp_handshake.py` (stdlib `initialize` client) showed all six installed and
  answering `initialize`; the GLSL binary is `glsl_analyzer` with an underscore. Capability sets went to
  reference §4 (bash lacks callHierarchy; GLSL has definition + diagnostics only, kept since it is free).
  Image delta is about 16 MB (nodejs already present). `make -C client image` was not run: the sandbox's
  16 GB nested store could not hold the 22 GB image.
- **Part 2.** `check_rhel9_ty.sh` in `quay.io/centos/centos:stream9`: `pip download --only-binary=:all: ty`
  gave `ty-0.0.80-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` (13,705,988 bytes); under
  `--network=none`, `python3.11 -m venv --system-site-packages /venv` + `pip install --no-index` produced
  `ty 0.0.80` on Python 3.11.13 advertising the same seven capabilities as Fedora's. The commented-out
  `client/Dockerfile` block uses those lines plus `ENV PATH=/venv/bin:$PATH` so the crushrc line is
  unchanged. `client/Makefile` got `TY_VERSION ?= 0.0.80`, a `vendor` step downloading the wheel to
  `client/vendor/wheels/` (gitignored), and a `$(wildcard)`-guarded wheels mount in `CRUSH_VENDOR_FLAGS`
  (checked with `make -n image CRUSH_VENDORED=1` with and without the dir).
- **Part 3.** `CLAUDE.md` (client bullet plus a "Language servers: dnf only" convention),
  `tasks/reference/architecture.md` (the wheel as a fourth, RHEL-only vendored artifact),
  `tasks/reference/crush-capabilities.md` (LSP line), `tasks/reference/crush-lsp-integration.md` (§4
  measured table, new RHEL 9 section), `README.md` (RHEL 9 callout), `vendor.sh` header.
- **Checks.** `bash -n`; `shfmt -d -i 4` and shellcheck clean on touched scripts; `+x` bits intact; no
  container-absolute paths. Pre-existing and left alone: `shfmt` would also reflow
  `client/entrypoint/02-install-vendor-tools.sh` and `client/entrypoint/03-build-crush.sh`.

## Not done here

The Fedora image rebuild and in-container check (`command -v` for all six servers; a Python project with
no top-level root marker gets symbols; `crush_logs` shows six servers starting) were moved to
`tasks/verify-language-servers-on-rhel9.md`.
