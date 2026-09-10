# How Crush uses language servers — and what the image must install for them to work

**Reference document** — read from Crush v0.89.0's source (`internal/lsp/`, `internal/agent/tools/lsp_*`,
`internal/config`, `internal/shellconfig/lsp.go`) and its bundled server registry
(`github.com/charmbracelet/x/powernap v0.1.6`, `pkg/config/lsps.json`, 500+ entries), 2026-09-10.
Explains the "no LSP client handles file" message the maintainer keeps seeing, and what
"compatible" means for a server we install. The work is `tasks/install-language-servers-for-crush.md`.

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

## 4. The bundled registry, for the languages this image ships toolchains for

From `lsps.json` (powernap v0.1.6). The command must be on `PATH` **inside the client container**.

| Language | Registry name → command | Root markers | In the client image today? |
|---|---|---|---|
| Python | `ty` → `ty server` | `ty.toml`, `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements.txt`, `.git` | **yes** (`ty` via dnf) — advertises every capability in §1 (verified with ty 0.0.74 in the sandbox) |
| Python | `basedpyright` → `basedpyright-langserver --stdio`; `pyright`; `pylsp`; `jedi_language_server`; `pyrefly` | `pyproject.toml`, `setup.py`, `.git`, … | no |
| Python | `ruff` → `ruff server` | | yes, **but in the skip list** — diagnostics-only anyway |
| Go | `gopls` | `go.work`, `go.mod`, `.git` | **yes** |
| C/C++ | `clangd` | `.clangd`, `compile_commands.json`, `.git` | **yes** (`clang-tools-extra`) |
| Rust | `rust_analyzer` → `rust-analyzer` | (none) | **yes** |
| JS/TS | `vtsls --stdio`; `denols` (skip list) | (none) | no — `nodejs`/`npm` are present, so `npm i -g @vtsls/language-server typescript` is one line |
| Bash | `bashls` → `bash-language-server start` | `.git` | no (npm) |
| Lua | `lua_ls` → `lua-language-server` | `.luarc.json`, `.git` | no (Fedora `lua-language-server` rpm exists) |
| Java | `java_language_server`; (`jdtls` is a separate entry) | `build.gradle`, `pom.xml`, `.git` | no (`java-25-openjdk` present) |
| Haskell | `hls` → `haskell-language-server-wrapper --lsp` | `hie.yaml`, `stack.yaml`, `.git` | no (`ghc` present) |
| OCaml | `ocamllsp` | `dune-project`, `.opam`, `.git` | no (`ocaml` present; `opam install ocaml-lsp-server`) |
| Ruby | `solargraph stdio`; `rubocop --lsp` (skip list) | `Gemfile`, `.git` | no (`ruby` present; gem) |
| CMake | `cmake` → `cmake-language-server`; `neocmakelsp` | `CMakePresets.json`, `.git` | no (pip) |
| TOML / Markdown / YAML / Dockerfile | `taplo`, `tombi`; `marksman`; `ansiblels`/`azure_pipelines_ls`; `dockerls`, `docker_language_server` | various | no |
| LaTeX | `texlab`; `ltex` | `.git`, `.latexmkrc` | no (Fedora `texlab` rpm exists) |
| Makefile | `autotools_ls` | (none) | no |
| Emacs Lisp | — **no entry in the registry** | | n/a |
| Scheme/Racket | `racket_langserver` → `racket --lib racket-langserver` | `.git` | no |

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
the root-marker check and the PATH rescan latency (gate 1), and **pin the server versions in the
image** rather than trusting the distro's. Diagnose first, though: `option debug-lsp true` (or
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
