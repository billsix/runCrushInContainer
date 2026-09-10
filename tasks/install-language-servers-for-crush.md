# Install the language servers Crush's LSP tools need — Python first, then every toolchain the image ships

**Status:** approved 2026-09-10 — Python server = **`ty`, pinned** (question 1 resolved). Not started. Research done 2026-09-10 (William Emerison Six
<billsix@gmail.com> asked, after Crush repeatedly answered "no LSP client handles file" for a
Python class). Diagnosis step first, then the install; both below.
**Priority:** 3
**Difficulty:** 4

## BLUF

Crush bundles no language servers; it auto-starts registry-known servers that are **on `PATH`
inside the client container**, match the file's type, and find a root marker in `/work`. The error
means no server was running for that language. For Python the image already has `ty`, which is
registered and advertises every capability Crush calls — so the failure is either the Fedora
`ty` version, a missing root marker, or the 30-second retry window. Done means: the exact cause is
identified from Crush's log; Python works deterministically via an explicit `lsp add` in the baked
crushrc with a pinned server; and every language whose toolchain the image installs gets a
compatible, explicitly declared server. Mechanism and the full registry table:
`tasks/reference/crush-lsp-integration.md`.

## Context — read first

- `tasks/reference/crush-lsp-integration.md` — what Crush requests (definition, references,
  rename, symbols, call hierarchy, diagnostics), the four start gates, the skip list (`ruff`,
  `python`, `node`, `java`… never auto-start), the per-language registry rows, and the three
  Python hypotheses.
- `client/entrypoint/01-install-base.sh` — the dnf list: has `gopls`, `rust-analyzer`,
  `clang-tools-extra` (clangd), `ruff`, `ty`, plus `nodejs`/`npm`, `lua`/`luarocks`, `ruby`,
  `java-25-openjdk`, `ghc`, `ocaml`. No `basedpyright`, `vtsls`, `bash-language-server`,
  `lua-language-server`, `texlab`, `jdtls`, `hls`, `ocamllsp`, `solargraph`, `taplo`, `marksman`.
- `client/entrypoint/crushrc` — no `lsp` lines today; everything relies on auto-start.
- `client/entrypoint/03-build-crush.sh` — the egress patches; **language servers must not add
  network paths** (none of the ones below phone home when run locally, but `vtsls`/`typescript`
  updates and `npm` itself are online at *build* time only, like everything else the image bakes).
- `CLAUDE.md` › "Verify model/tool identifiers before hardcoding them" — same rule for server
  package names/versions.

## Plan

### 0. Diagnose the Python case before changing anything (one session)

1. In the client: `option debug-lsp true` (temporarily, in the baked crushrc or a project crushrc),
   open a Python file in a mounted repo, ask for a symbol, then read `crush_logs`. Look for
   `LSP server not installed` (gate 4), `Doesn't handle file` (gate 3), or `LSP client
   initialization failed` (Initialize).
2. `ty --version` and `printf '…' | ty server` in the image: the sandbox's 0.0.74 advertises all
   capabilities; record the image's version.
3. Check whether `/work` had `pyproject.toml`/`setup.py`/`.git` at top level in the failing case.
   Record the answer in this task — it decides how much of §1 was necessary versus prudent.

### 1. Python — deterministic

- **Pin the server.** Prefer `ty` (already in the image; Astral; fast; full capability set) but
  install a **pinned** version rather than the distro's moving target — `pip install ty==<ver>`
  in `01-install-base.sh` (or `uv tool install`), and drop the dnf `ty` to avoid two on `PATH`.
  Alternative for maximum maturity: `basedpyright` (`npm i -g basedpyright@<ver>`).
- **Declare it** in `client/entrypoint/crushrc`:
  `lsp add python --command ty --args server --filetypes py --root-markers pyproject.toml setup.py .git`
  (explicit config bypasses the skip list, the root-marker gate and the PATH-rescan latency).
- Keep `ruff` for `format.sh`; it is diagnostics-only and in Crush's skip list, so it plays no LSP
  role. Say so in a comment.

### 2. The other toolchains the image ships — install a compatible server for each and declare it

| Language (toolchain present) | Server to install | How (pinned) | crushrc line |
|---|---|---|---|
| Go | `gopls` | already dnf | `lsp add go --command gopls` (declare for determinism) |
| C/C++ | `clangd` | already `clang-tools-extra` | `lsp add c --command clangd --filetypes c cpp h hpp` |
| Rust | `rust-analyzer` | already dnf | `lsp add rust --command rust-analyzer --filetypes rs` |
| JS/TS | `vtsls` | `npm i -g @vtsls/language-server@<ver> typescript@<ver>` | `lsp add ts --command vtsls --args --stdio --filetypes js ts jsx tsx` |
| Bash | `bash-language-server` | `npm i -g bash-language-server@<ver>` | `lsp add sh --command bash-language-server --args start --filetypes sh bash` |
| Lua | `lua-language-server` | Fedora rpm `lua-language-server` (verify name) | `lsp add lua --command lua-language-server --filetypes lua` |
| Java | `jdtls` (registry entry `jdtls`) | Fedora `eclipse-jdtls`? else the upstream tarball | `lsp add java --command jdtls --filetypes java` |
| Haskell | `haskell-language-server-wrapper` | Fedora `haskell-language-server`? else ghcup | `lsp add haskell --command haskell-language-server-wrapper --args --lsp --filetypes hs` |
| OCaml | `ocamllsp` | `opam install ocaml-lsp-server` (or Fedora `ocaml-lsp`) | `lsp add ocaml --command ocamllsp --filetypes ml mli` |
| Ruby | `solargraph` | `gem install solargraph -v <ver>` | `lsp add ruby --command solargraph --args stdio --filetypes rb` |
| LaTeX | `texlab` | Fedora `texlab` rpm | `lsp add tex --command texlab --filetypes tex bib` |
| CMake, TOML, Markdown, YAML, Dockerfile | `cmake-language-server` (pip), `taplo`, `marksman`, `yaml-language-server` (npm), `docker-langserver` (npm) | as noted | one line each |
| Emacs Lisp | — no registry entry; nothing to install | | |

Each server's capabilities (§1 of the reference doc) should be checked once with the same
`initialize` handshake used for `ty`, and the result recorded in the reference doc's table.
**Verify every package name and pick a version on the day** — the names above are from the
registry and Fedora's usual naming, not from a build.

### 3. Image and gate

- Additions go in `01-install-base.sh` alphabetically (dnf) or in a clearly labelled "language
  servers" block for npm/pip/gem/opam installs, with the version pins and a one-line reason each.
  `FULL_TOOLCHAIN=0` (minimal image) should install **none** of them.
- `make -C client image`, then in the container: each `lsp add`ed command resolves
  (`command -v`), Crush starts them (`crush_logs` shows no "not installed"), and `lsp_symbols`
  works on a sample file per language. `format.sh` green.
- Image-size delta recorded here (the npm servers pull node_modules; jdtls and hls are large —
  decide per row whether they earn their bytes).

### 4. Docs with the unit

`CLAUDE.md` (what the image ships for LSP, and that servers are declared, not auto-detected),
`tasks/reference/architecture.md` (client section), `tasks/reference/crush-capabilities.md`
("LSP — SUPPORTED" line gets the list), and the reference doc's table (§4 "in the image today?").

## Verification / done-state

The Python `lsp_symbols`/`lsp_definition`/`lsp_rename` tools work on a mounted repo without a
root marker at `/work` and without waiting; `crush_logs` shows every declared server starting;
the reference doc's table has no "no" in the "in the image" column for a toolchain the image
installs; image size delta and pinned versions recorded here.

## Open questions

1. ~~**Python server: `ty` (pinned) or `basedpyright`?**~~ **RESOLVED 2026-09-10: `ty`, pinned** (maintainer: "sure ty").
2. **Which of the large servers earn their bytes** — `jdtls` and `haskell-language-server` are
   hundreds of MB each. Recommend: install both (the image is a full toolchain by design), skip
   only under `FULL_TOOLCHAIN=0`.
3. **Explicit `lsp add` for *every* language, or only where auto-start is unreliable?**
   Recommend **every** one — determinism over cleverness; the lines are cheap and self-documenting.
