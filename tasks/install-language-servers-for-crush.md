# Install the language servers Crush's LSP tools need — Python first, then every toolchain the image ships

**Status:** approved 2026-09-10, no open questions, **not started — three parts** (status table
below). Part 1 = Fedora image: dnf servers + explicit `lsp add` lines (Python = **dnf `ty`**, the
earlier "pin via pip" reversed). Part 2 = **RHEL 9 path**: a `/venv` + vendored `ty` wheel, proven in
a throwaway CentOS Stream 9 container and then left as a **commented-out block in `client/Dockerfile`**
(maintainer's preferred form, 2026-09-10) so the airgap box can be brought up from the docs alone.
Part 3 = docs. Research done 2026-09-10 (William Emerison Six <billsix@gmail.com> asked, after Crush
repeatedly answered "no LSP client handles file" for a Python class on the **airgapped** box — a
non-fatal complaint: it still rewrote the code).

| Part | What | Status |
|---|---|---|
| 1 | Fedora: `nodejs-bash-language-server` + `glsl-analyzer` in `01-install-base.sh`; six `lsp add` lines in crushrc; throwaway-`fedora:44` handshake check; image rebuild | not started |
| 2 | RHEL 9: `python3.11` venv + vendored `ty` wheel, proven in a throwaway `centos:stream9`; commented-out Dockerfile block; wheel in `vendor.sh` | not started |
| 3 | Docs: `CLAUDE.md`, `architecture.md`, `crush-capabilities.md`, reference-doc table, README RHEL 9 note | not started |
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
- **The install rule (maintainer, 2026-09-10): language servers come from dnf only.** No `npm -g`,
  `gem`, `opam`, `cargo install` or upstream tarballs — the airgap rebuild has only the airgap's own
  dnf mirror (`tasks/reference/architecture.md` › "Offline / airgap rebuild"), so anything else would
  silently vanish there. The one exception: if Fedora shipped **no** Python server, Python would get a
  `/venv` the way geometricalgebra's Dockerfile does (`python3 -m venv --system-site-packages /venv/`
  + `uv pip install`). It does ship one, so **no venv**. "If the dnf environment has an LSP, use that
  one, not a venv" — and that reverses the pinned-`ty` idea: the image's `ty` is Fedora's.
- **Fedora 44 dnf survey (2026-09-10, `dnf repoquery` + `dnf search` from the sandbox):**
  packaged — `ty` 0.0.74, `python3-lsp-server` 1.13.1, `gopls` 0.18.1, `rust-analyzer` 1.98.0,
  `clang-tools-extra` (clangd) 22.1.8, `nodejs-bash-language-server` 5.6.0, `glsl-analyzer`.
  **Not packaged** — anything for JS/TS (`vtsls`, `typescript-language-server`), Lua
  (`lua-language-server`), LaTeX (`texlab`), Haskell (`haskell-language-server`), Java (`jdtls`),
  OCaml (`ocaml-lsp`), Ruby (`solargraph`), TOML (`taplo`), Markdown (`marksman`), YAML, Dockerfile.
  Those toolchains therefore get **no server** and the docs say so. Re-run the query on the day; Fedora
  adds packages between releases.

### RHEL 9 — what the airgap box can get from its own repos (queried 2026-09-10)

The airgap box is RHEL 9-class (its dnf mirror lacks `python3-huggingface-hub`, per the `hf`
fallback note in `tasks/reference/architecture.md`). Queried from the sandbox with
`dnf repoquery --repofrompath` against **CentOS Stream 9** AppStream + BaseOS (the closest public
proxy for RHEL 9 — RHEL's own repos need a subscription; re-check on the box with
`dnf repoquery '*lsp*' '*language-server*' ty python3-lsp-server`) and **EPEL 9**:

| Repo | Python LSP? | Other servers there | Notes |
|---|---|---|---|
| RHEL 9 / CS9 AppStream | **none** — no `ty`, no `python3-lsp-server`, no `pyright`, no `jedi-language-server` | `rust-analyzer` (1.94–1.97), `clang-tools-extra` → `clangd` (21.x/22.x) | Python: `python3` 3.9 (BaseOS), **`python3.11` 3.11.13 and `python3.12` 3.12.14** AppStream with their own `-pip`; `nodejs` 16; `golang` 1.26 |
| EPEL 9 | **none** — only `python3-jedi` 0.18.1 (a library, not a server), `geany-plugins-lsp` (Geany's client) | **`golang-x-tools-gopls`** 0.11.1 (the `gopls` binary, old but real) | no `bash-language-server`, no `glsl-analyzer`, no `ty` |

**Consequence for the airgap image: on RHEL 9 the "if dnf has it, use it" rule finds nothing for
Python, so that is the case where the venv exception applies** (maintainer, 2026-09-10: "unless it's
python, and then make a venv, like geometricalgebra does"). Options, all needing the wheel carried
across like the GGUF is:

- **`ty`** — a single Rust binary shipped as a manylinux wheel, no runtime deps; `pip download ty`
  on the online box, `python3.11 -m venv --system-site-packages /venv && /venv/bin/pip install
  --no-index --find-links <dir> ty` in the image. Same server as Fedora, so the crushrc line
  (`--command ty --args server`) is identical on both — **recommended**. Use **`python3.11`** (maintainer's choice, 2026-09-10; 3.12 would also do);
  BaseOS 3.9 is past the versions `ty` targets.
- `python-lsp-server` (pylsp) — pure Python but pulls jedi/rope/pluggy/…; a bigger `pip download`
  set and a different crushrc line. Fallback only.
- `pyright`/`basedpyright` — need Node ≥ 18; RHEL 9's `nodejs` is 16 (a `nodejs:20` AppStream
  module exists on RHEL proper). Not worth it.

This means the install script needs a **distro switch**: Fedora → `dnf install ty`; RHEL 9 →
`/venv` + vendored wheel, following the same dnf-or-pip shape `02-install-vendor-tools.sh` already
uses for `huggingface_hub`. The wheel goes in the vendored set (`vendor.sh`) so the airgap rebuild
never pip-downloads. Go on RHEL 9 gets EPEL's `golang-x-tools-gopls`; Bash and GLSL get nothing
there (document, don't fake).

## Plan

### 0. Diagnosis — not runnable here, and not needed for the fix

The failing project lives on the airgapped box (maintainer, 2026-09-10), so the `debug-lsp` /
`crush_logs` read can't be done from this side, and the complaint is non-fatal (Crush finishes the
rewrite without symbols). What we do know: the image already carries dnf `ty`, so gate 4 ("not on
PATH") is unlikely; the remaining candidates are the skip list / registry row for Python and the
root-marker gate (`/work` without `pyproject.toml`/`setup.py`/`.git` at top level). An explicit
`lsp add python` bypasses all of them, which is why §1 needs no diagnosis. If the maintainer ever
wants the confirmation: `option debug-lsp true` in a project crushrc on the airgap box, open a `.py`,
read `crush_logs` for `LSP server not installed` / `Doesn't handle file` / `initialization failed`.

### Part 1 — Fedora image: dnf servers, declared explicitly

**Python: dnf `ty`, nothing to install.** Already in `01-install-base.sh`; Fedora 44 ships 0.0.74,
which advertises definition/references/rename/documentSymbol/diagnostics in the `initialize`
handshake (reference doc). No pip, no venv, no pin — the version is whatever the dnf mirror has, like
every other tool in the image. `python3-lsp-server` (pylsp) is the dnf alternative if `ty` ever
disappoints; don't install both. `ruff` stays for `format.sh`; it is diagnostics-only and in Crush's
skip list, so it plays no LSP role — say so in a comment.

| Language (toolchain present) | Server | dnf state | crushrc line |
|---|---|---|---|
| Python | `ty` | already installed | `lsp add python --command ty --args server --filetypes py --root-markers pyproject.toml setup.py .git` |
| Go | `gopls` | already installed | `lsp add go --command gopls --filetypes go --root-markers go.mod .git` |
| C/C++ | `clangd` | already installed (`clang-tools-extra`) | `lsp add c --command clangd --filetypes c cpp h hpp --root-markers compile_commands.json CMakeLists.txt Makefile .git` |
| Rust | `rust-analyzer` | already installed | `lsp add rust --command rust-analyzer --filetypes rs --root-markers Cargo.toml .git` |
| Bash | `bash-language-server` | **add `nodejs-bash-language-server`** | `lsp add sh --command bash-language-server --args start --filetypes sh bash --root-markers .git` |
| GLSL (mvp's shaders) | `glsl-analyzer` | **add `glsl-analyzer`** (cheap; the shader-heavy repos benefit) | `lsp add glsl --command glsl-analyzer --filetypes glsl vert frag comp --root-markers .git` |
| JS/TS, Lua, LaTeX, Haskell, Java, OCaml, Ruby, TOML, Markdown, YAML, Dockerfile, Emacs Lisp | — | **not in Fedora 44** | none; documented as "no LSP in the image" |

Two dnf additions, six `lsp add` lines. "Install all" (question 2) means all that dnf offers.
Explicit config bypasses the skip list, the root-marker gate and the PATH-rescan latency — the
determinism question 3 chose.

Steps:

1. `nodejs-bash-language-server` and `glsl-analyzer` into `01-install-base.sh` alphabetically, in
   the dnf list, one-line reason each. `FULL_TOOLCHAIN=0` installs neither; the crushrc `lsp add`
   lines are harmless there (a declared server that isn't on PATH fails to start — confirm it logs,
   not crashes).
2. The six `lsp add` lines in `client/entrypoint/crushrc`, one comment block explaining the rule
   (dnf-only, explicit-not-auto, what has no server and why).
3. Cheap pre-check without the 22 GB build: throwaway `fedora:44` container, `dnf install` the six
   servers, run the `initialize` handshake per binary, record each one's capability set in the
   reference doc's table. **Verify the package names and the exact `--args`/root-marker spellings on
   the day** (`dnf repoquery`, `crush lsp add --help`).
4. `make -C client image`; in the container every `lsp add`ed command resolves (`command -v`),
   `crush_logs` shows each starting, `lsp_symbols` works on a sample file per language. `format.sh`
   green. Image-size delta recorded here (expected small — two packages).

### Part 2 — RHEL 9 path: `/venv` + vendored `ty` wheel, as a commented-out Dockerfile block

RHEL 9 packages no Python LSP (Context › "RHEL 9"), so this is the venv exception, done the
geometricalgebra way. **Deliverable form (maintainer, 2026-09-10): commented-out lines in
`client/Dockerfile`** that a RHEL 9 operator uncomments — tested for real first, then commented out.

1. **Prove the recipe in a throwaway container** (`[CONTAINER]`, nested podman):
   `podman run --rm -it quay.io/centos/centos:stream9` — `dnf install python3.11 python3.11-pip`;
   on the online side `python3.11 -m pip download ty -d /vendor/wheels` (note the exact wheel
   filename + version); then the offline-shaped install: `python3.11 -m venv --system-site-packages
   /venv && /venv/bin/pip install --no-index --find-links /vendor/wheels ty`; run the same
   `initialize` handshake against `/venv/bin/ty server` as Part 1 and confirm the capability set
   matches Fedora's. Record the wheel name, size, and the `ty --version` here.
2. **Write the block into `client/Dockerfile`, commented out**, next to the existing
   `01-install-base.sh` RUN: a `# --- RHEL 9 (UBI9 / Stream 9) base: no dnf Python LSP; venv + vendored
   ty wheel ---` header, the `dnf install python3.11 python3.11-pip`, the `venv` + `pip install
   --no-index` lines, and `ENV PATH=/venv/bin:$PATH` so `ty` resolves for the unchanged crushrc line.
   Each line carries a short reason. State plainly in the header that the rest of the Fedora
   `01-install-base.sh` list is **not** RHEL-portable and that Go on RHEL 9 is EPEL's
   `golang-x-tools-gopls`; Bash/GLSL get nothing there.
3. **Vendor the wheel**: `vendor.sh` (or `02-install-vendor-tools.sh`, whichever the dnf-or-pip
   `huggingface_hub` fallback lives closest to) gains a `pip download ty` into `client/vendor/wheels/`
   (gitignored, rides in the airgap tarball like the GGUFs). Pin the version there — it is the one
   place the RHEL path is pinned, because it is the one place there is no dnf mirror to defer to.
4. Re-run step 1 from the vendored wheel with the network off (`--network=none`) — that is the
   airgap proof. Then comment the Dockerfile block out and leave it.

### Part 3 — Docs with the unit

`CLAUDE.md` (what the image ships for LSP; servers are declared, not auto-detected; the RHEL 9
block exists and where), `tasks/reference/architecture.md` (client section + airgap section: the
wheel is now a fourth vendored artifact, RHEL-only), `tasks/reference/crush-capabilities.md`
("LSP — SUPPORTED" line gets the list), the reference doc's table (§4 "in the image today?" for
Fedora and RHEL 9 columns), and a README "RHEL 9" one-liner pointing at the Dockerfile block.

## Verification / done-state

- **Part 1:** the Python `lsp_symbols`/`lsp_definition`/`lsp_rename` tools work on a mounted repo
  without a root marker at `/work` and without waiting; `crush_logs` shows every declared server
  starting; the reference doc's table has no "no" in the Fedora "in the image" column for a toolchain
  Fedora packages a server for; image-size delta recorded here.
- **Part 2:** the Stream 9 throwaway ran `ty server` from `/venv` installed **offline** from the
  vendored wheel and answered `initialize` with the same capabilities as Fedora's `ty`; the Dockerfile
  block is present, commented out, and matches what was run byte-for-byte (copy the tested lines, don't
  retype); the wheel is in the vendored set with its version recorded here.
- **Part 3:** the five docs above updated; `format.sh` green.

## Open questions

1. ~~**Python server: `ty` (pinned) or `basedpyright`?**~~ **RESOLVED 2026-09-10: `ty`** (maintainer:
   "sure ty") — first as a pip pin, then **reversed to the dnf package** the same day (question 4).
2. ~~**Which of the large servers earn their bytes?**~~ **RESOLVED 2026-09-10: install all**
   (maintainer: "install all") — then narrowed by question 4 to all that **dnf** offers; `jdtls` and
   `haskell-language-server` are not packaged, so they drop out. Skip the additions under
   `FULL_TOOLCHAIN=0`.
3. ~~**Explicit `lsp add` for every language, or only where auto-start is unreliable?**~~
   **RESOLVED 2026-09-10: explicit for every one** (maintainer: "whatever you recommend") —
   determinism over the registry's PATH/root-marker gates.
4. **Install source?** **RESOLVED 2026-09-10: dnf only** (maintainer: "it should only be dnf tools, unless
   it's python, and then make a venv, like geometricalgebra does … obviously if the dnf environment has
   a lsp, use that one, not a venv. maybe reverse the decision about ty if that is the case"). Fedora
   has `ty`, so no venv and question 1 becomes **dnf `ty`, unpinned**.
