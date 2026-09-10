# How Crush uses language servers — and what the image must install for them to work

**Reference document** — read from Crush v0.89.0's source (`internal/lsp/`, `internal/agent/tools/lsp_*`,
`internal/config`, `internal/shellconfig/lsp.go`) and its bundled server registry
(`github.com/charmbracelet/x/powernap v0.1.6`, `pkg/config/lsps.json`, 500+ entries), 2026-09-10.
Explains the "no LSP client handles file" message the maintainer keeps seeing, and what
"compatible" means for a server we install. **Implemented 2026-09-10** (§4 has the measured
capability table, § RHEL 9 the venv variant); the work record is `tasks/archive/2026/09/10/install-language-servers-for-crush.md`; the real-image and
RHEL 9 verification is `tasks/verify-language-servers-on-rhel9.md`.

## 1. What Crush does with an LSP client

Crush is a *client* of language servers; it does not bundle any. With at least one client running it
exposes these tools to the model (registry in `internal/config/config.go:798`):

| Tool | LSP requests it makes (powernap client) | Needs the server to advertise |
|---|---|---|
| `lsp_definition` | `Definition` | `definitionProvider` |
| `lsp_references` | references | `referencesProvider` |
| `lsp_symbols` | `DocumentSymbols` | `documentSymbolProvider` (and `workspaceSymbolProvider` for the symbol search) |
| `lsp_rename` | `RequestRename` → `workspace/applyEdit` | `renameProvider` |
| `lsp_replace_symbol` | `DocumentSymbols` + an edit | `documentSymbolProvider` |
| `lsp_call_hierarchy` | `PrepareCallHierarchy`, `IncomingCalls`, `OutgoingCalls` | `callHierarchyProvider` |
| `diagnostics` (+ `view`/`edit`/`multiedit`/`write`) | subscribes to `textDocument/publishDiagnostics`, `NotifyDidChangeTextDocument` | push diagnostics |
| `lsp_restart` | restart | — |

So "compatible" is concrete: a server must implement **definition, references, rename,
documentSymbol/workspaceSymbol, callHierarchy, and push diagnostics**. A linter-only server (e.g.
`ruff server`) satisfies diagnostics but not the navigation tools.

## 2. How a server gets started — the four gates

`internal/lsp/manager.go` `Start(path)` is called per file Crush touches, under the working dir
(`/work` in this container). For every server in the bundled registry, `startServer` runs:

1. **User-configured?** (`crushrc` `lsp add <name> …`) → start it, skipping gates 2–4.
2. **Not in `skipAutoStartCommands`** — a list of commands "too generic to auto-start": `python`,
   `python3`, `node`, `npx`, `java`, `deno`, `ruff`, `rubocop`, `dotnet`, `julia`, … (`manager.go:121`).
   **`ruff server` therefore never auto-starts**, even though it is in the registry and the image.
3. **`handles(server, file, workDir)`** — the file's suffix or detected language is in the server's
   `filetypes` **and** one of its `root_markers` globs matches in the working dir (non-recursive,
   `manager.go:356`). Most entries include `.git`, so a mounted repo passes; a bare directory of
   `.py` files may not.
4. **`exec.LookPath(command)` succeeds.** A miss marks the server unavailable for **30 s**
   (`unavailableRetryDelay`) and is logged only at *debug* level — which is why the user sees nothing
   until a tool fails.

Then `client.Initialize`; a failure is logged at error level and the client is dropped. `option
auto-lsp false` disables gates 2–4 entirely (only user-configured servers run).

## 3. Where "no LSP client handles file" comes from

`internal/agent/tools/lsp_helpers.go` `findLSPClient` iterates the **running** clients and returns
the first whose `HandlesFile(path)` is true — the file is under the client's cwd and matches its
`filetypes`. If no client is running for that language (any of the gates above failed), the tool
returns exactly `no LSP client handles file: <path>` (`lsp_symbols.go:35`,
`lsp_replace_symbol.go:80`). It is not an error from a server; it means **no server was started**.

## 4. What the image ships — six dnf servers, declared explicitly (measured 2026-09-10)

**The rule (maintainer, 2026-09-10): language servers come from dnf only** — the airgap rebuild has
only a dnf mirror, so an npm/gem/opam/pip server would silently vanish there. The baked crushrc
declares each one with `lsp add` (bypassing all four gates in §2); a toolchain Fedora packages no
server for gets **no** server, and that is documented rather than faked. Measured with one
`initialize` handshake per binary in a throwaway `fedora:44`
(`tasks/adhoc/verify-language-servers-on-rhel9/check_fedora_servers.sh` + `lsp_handshake.py`):

| Language | dnf package → binary (Fedora 44 version) | crushrc line | definition | references | rename | documentSymbol | callHierarchy | diagnostics |
|---|---|---|---|---|---|---|---|---|
| Python | `ty` → `ty` (0.0.74) | `lsp add python --command ty --args server --filetypes py --root-markers pyproject.toml setup.py .git` | yes | yes | yes | yes | yes | pull + push |
| Go | `gopls` → `gopls` (0.18.1) | `lsp add go --command gopls --filetypes go --root-markers go.mod go.work .git` | yes | yes | yes | yes | yes | push |
| C/C++ | `clang-tools-extra` → `clangd` (22.1.8) | `lsp add c --command clangd --filetypes c cpp h hpp --root-markers compile_commands.json CMakeLists.txt Makefile .git` | yes | yes | yes | yes | yes | push |
| Rust | `rust-analyzer` → `rust-analyzer` (1.98.0) | `lsp add rust --command rust-analyzer --filetypes rs --root-markers Cargo.toml .git` | yes | yes | yes | yes | yes | pull + push |
| Bash | `nodejs-bash-language-server` → `bash-language-server` (5.6.0) | `lsp add sh --command bash-language-server --args start --filetypes sh bash --root-markers .git` | yes | yes | yes | yes | **no** | push |
| GLSL | `glsl-analyzer` → `glsl_analyzer` (1.7.1; note the underscore) | `lsp add glsl --command glsl_analyzer --filetypes glsl vert frag comp --root-markers .git` | yes | **no** | **no** | **no** | **no** | push |

"push" = `textDocumentSync` advertised, so `publishDiagnostics` flows; "pull" = the newer
`diagnosticProvider` too. GLSL is definition-and-diagnostics only — kept because it is free and
mvp's shader trees get something rather than nothing.

**Toolchains in the image with NO server, and why (Fedora 44 `dnf repoquery`/`search`, 2026-09-10):**
JS/TS (`vtsls`/`typescript-language-server` are npm-only), Lua (`lua-language-server`), LaTeX
(`texlab`), Haskell (`haskell-language-server`), Java (`jdtls`), OCaml (`ocaml-lsp`), Ruby
(`solargraph`), TOML (`taplo`), Markdown (`marksman`), YAML, Dockerfile — none packaged by Fedora.
Emacs Lisp has no registry entry at all. `ruff` is present for `format.sh` only: diagnostics-only
and on Crush's skip list. `python3-lsp-server` (pylsp) is the dnf alternative to `ty` if it ever
disappoints; don't install both. Re-run the query at each Fedora bump — packages appear.

### The registry rows these lines replace (powernap v0.1.6 `lsps.json`)

Kept for reference — what auto-start *would* have used. Root markers are the registry's, which is
why the explicit lines above carry their own.

| Language | Registry name → command | Registry root markers |
|---|---|---|
| Python | `ty` → `ty server`; also `basedpyright`, `pyright`, `pylsp`, `jedi_language_server`, `pyrefly`; `ruff` → `ruff server` (skip list) | `ty.toml`, `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `.git` |
| Go | `gopls` | `go.work`, `go.mod`, `.git` |
| C/C++ | `clangd` | `.clangd`, `compile_commands.json`, `.git` |
| Rust | `rust_analyzer` → `rust-analyzer` | (none) |
| Bash | `bashls` → `bash-language-server start` | `.git` |
| JS/TS | `vtsls --stdio`; `denols` (skip list) | (none) |
| Lua / Java / Haskell / OCaml / Ruby / CMake / TOML / Markdown / YAML / Dockerfile / LaTeX / Makefile / Scheme | `lua_ls`; `java_language_server`, `jdtls`; `hls`; `ocamllsp`; `solargraph stdio`; `cmake`, `neocmakelsp`; `taplo`, `tombi`; `marksman`; `ansiblels`; `dockerls`; `texlab`, `ltex`; `autotools_ls`; `racket_langserver` | various |

## RHEL 9 — no packaged Python LSP; the `/venv` + vendored-wheel variant (proven 2026-09-10)

The airgap box is RHEL 9-class. Queried via `dnf repoquery --repofrompath` against CentOS Stream 9
AppStream/BaseOS (the public proxy for RHEL 9) and EPEL 9: **no `ty`, `python3-lsp-server`,
`pyright` or `jedi-language-server` anywhere**; EPEL 9 has only `python3-jedi` (a library) and,
usefully, `golang-x-tools-gopls`; AppStream has `rust-analyzer`, `clang-tools-extra` (clangd),
`python3.11`/`python3.12` with pip, `nodejs` 16, `golang` 1.26. Re-check on the box itself
(RHEL's real repos need a subscription): `dnf repoquery '*lsp*' '*language-server*' ty
python3-lsp-server`.

So RHEL 9 is the dnf-only rule's one exception ("unless it's python, and then make a venv, like
geometricalgebra does"). The variant, kept as a **commented-out block in `client/Dockerfile`**:

```
RUN dnf install -y python3.11 python3.11-pip && dnf clean all
RUN python3.11 -m venv --system-site-packages /venv && \
    /venv/bin/pip install --no-index --find-links /vendor/wheels ty
ENV PATH=/venv/bin:$PATH
```

- **`ty`, not pylsp/pyright**: a single prebuilt Rust binary shipped as a `py3-none-manylinux_2_17`
  wheel (13.7 MB; RHEL 9's glibc 2.34 ≫ 2.17), no dependencies, and the **same crushrc line** as
  Fedora — `/venv/bin` on `PATH` is the whole integration. pylsp drags jedi/rope/pluggy wheels;
  pyright needs Node ≥ 18 (RHEL 9 ships 16).
- **python3.11** (maintainer's choice; 3.12 would also work): BaseOS `python3` is 3.9, below what
  `ty`'s wheel targets.
- **The wheel is the one pinned server** — `TY_VERSION` in `client/Makefile` (0.0.80 at proof time),
  downloaded by `make -C client vendor` into `client/vendor/wheels/` (gitignored, rides in the airgap
  tarball) and mounted read-only at `/vendor/wheels` by `make image CRUSH_VENDORED=1` when the dir
  exists. Fedora's `ty` stays unpinned dnf; pinning applies only where there is no mirror to defer to.
- **Proof** (`tasks/adhoc/verify-language-servers-on-rhel9/check_rhel9_ty.sh`): a throwaway
  `quay.io/centos/centos:stream9` + `python3.11` image; the wheel `pip download`ed online; then, under
  `podman run --network=none`, the venv + `--no-index` install succeeded (`ty 0.0.80`, Python
  3.11.13) and `ty server` answered `initialize` with the full capability row above. That offline run
  is the airgap evidence.
- Everything else in `01-install-base.sh` is Fedora's list and does not apply as-is on RHEL 9; the
  Dockerfile block says so. Go there is EPEL's `golang-x-tools-gopls`; the Bash and GLSL servers do
  not exist there.

## 5. Why Python failed for the maintainer — the candidates, in order of likelihood

`ty` is installed and registered, so one of these:

1. **The Fedora `ty` rpm is older than `ty server`'s useful capabilities**, or `Initialize` failed.
   Sandbox `ty 0.0.74` is fine; the image's version is whatever dnf shipped at build time —
   check `ty --version` and `ty server` in the image. (Astral's `ty` is pre-1.0 and moves fast.)
2. **Root markers**: the mounted project had no `pyproject.toml`/`setup.py`/`.git` at `/work`'s
   top level (e.g. `/work` is a *subdirectory* of a repo). Gate 3 fails silently.
3. **The 30-second unavailability window** after a transient miss, plus debug-only logging, made a
   one-off failure look permanent.

The deterministic fix does not depend on which: **declare the servers explicitly in the baked
crushrc** (`lsp add python --command ty --args server --filetypes py`), which bypasses the skip list,
the root-marker check and the PATH rescan latency (gate 1). (The first draft also said "pin the
server versions in the image"; the dnf-only rule reversed that — Fedora's `ty` is whatever dnf
ships, and only the RHEL 9 wheel is pinned.) The diagnosis was never run: the failing project is on
the airgapped box and the complaint is non-fatal. If ever wanted there: `option debug-lsp true` (or
`debug true`) and read the `crush_logs` tool output for "LSP server not installed" vs
"initialization failed".

## 6. crushrc syntax (Crush's own `crush-config` skill)

```
lsp add <name> --command CMD [--args ARG ...] [--env KEY VALUE ...] [--filetypes TYPE ...]
    [--root-markers MARKER ...] [--timeout N] [--disabled BOOL] [--init-options JSON] [--options JSON]
lsp remove <name>
option auto-lsp false        # only explicitly added servers, if wanted
```

## Sources

- Crush v0.89.0: `internal/lsp/manager.go` (gates, skip list, 30 s retry), `internal/lsp/client.go`
  (`HandlesFile`), `internal/agent/tools/lsp_helpers.go` + `lsp_*.go` + `diagnostics.go`,
  `internal/config/config.go` (`LSPConfig`, `AutoLSP`), `internal/shellconfig/lsp.go`,
  `internal/skills/builtin/crush-config/SKILL.md`.
- powernap v0.1.6 `pkg/config/lsps.json` (fetched from GitHub at the tag).
- `ty` LSP capabilities: an `initialize` handshake against `ty server` 0.0.74 in the sandbox.
