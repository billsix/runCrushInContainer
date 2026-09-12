# `lsp add python` (ty) not registering — Python absent from the LSP sidebar

**Status:** investigating — awaiting `crush logs` from the running container
**Priority:** 2
**Difficulty:** 3

## BLUF

With the Crush client rooted at `/foo/opt/geometricalgebra` (a project that HAS
`pyproject.toml`, `setup.py`, and `.git`), the LSP sidebar registers **five** servers —
`c, glsl, go, rust, sh` — but **not `python`**, and `lsp_symbols` on a `.py` file returns
`no LSP client handles file: …/src/gacalc/base.py`. Crush seeds every user-configured server
into the sidebar *before* any gate, so Python's total absence means the **`lsp add python` line
isn't producing a config entry at all**, while the other five do — a Python-line-specific
registration failure. **This is NOT the root-marker gate** (the working dir has the markers) and
NOT a missing binary (that would still show Python as "unstarted"). Root cause is not yet known;
it needs `crush logs` from the running container. **Done = `python` registers and `ty server`
handles `.py` files.**

## Context

**Evidence (2026-09-12, from the maintainer's running client, `crush v0.89.0+dirty`):**
- Working dir `/foo/opt/geometricalgebra` — confirmed to contain `pyproject.toml`, `setup.py`,
  and `.git` at its top level.
- LSPs panel: `● c unstarted / ● glsl unstarted / ● go unstarted / ● rust unstarted / ●
  sh unstarted` — **Python is absent** (alphabetically it would sit between `go` and `rust`; the
  panel shows `go` then `rust` with nothing between).
- Tool result: `ERROR no LSP client handles file: /foo/opt/geometricalgebra/src/gacalc/base.py`.

**Why this is a registration failure, not a gate or a binary miss (Crush v0.89.0 source, under
`client/vendor/crush/`):**
- `internal/lsp/manager.go` `TrackConfigured` (≈`:86-100`) seeds the sidebar with every
  **user-configured** server (`if !s.isUserConfigured(name) { continue }`) *before* startup and
  *before* any root-marker/PATH check. So if `python` never appears, its config entry was never
  created — `isUserConfigured("python")` is false.
- A **missing binary** for a user-configured server still leaves it seeded as "unstarted" (the
  `LookPath` gate is skipped for user-configured servers), so Python's *absence* is not "ty
  missing".
- The **root-marker gate** is ruled out here: the working dir contains Python's markers. (That
  gate is a separate latent bug — `tasks/lsp-add-root-markers-gate-startup.md`.)

**The config path:** `crushrc` is baked verbatim — `COPY entrypoint/crushrc
/root/.config/crush/crushrc` (`client/Dockerfile:146`). The **source** Python line
(`client/entrypoint/crushrc:113-114`) is:
```
lsp add python --command ty --args server --filetypes py \
    --root-markers pyproject.toml --root-markers setup.py --root-markers .git
```
Structurally this is the same repeated-flag pattern as `sh` (`--command bash-language-server
--args start …`), which *does* register — so nothing obvious distinguishes it. Config parsing
lives in `internal/shellconfig/lsp.go` + `flags.go` (`parseFlagValue`); a malformed flag
historically produced `lsp add: unknown flag setup.py` (the pre-fix space-separated form), but
the current line uses repeated `--root-markers`, which should be correct.

**Correction to earlier diagnosis (2026-09-12):** an earlier read claimed `grep -c 'lsp add'`
== 9 meant a stale image. It does not — that count includes ~3 comment lines mentioning "lsp
add"; the current source greps to 9 too (6 commands + 3 comments). The running crushrc is not
stale on that basis.

## Leading hypotheses (need the logs to decide)

1. **The `lsp add python` line is rejected at config-load and skipped** while the other five
   load — a parser edge case specific to this line (e.g. `--command ty --args server`, or the
   `python` name). `crush logs` would show the rejection (config errors log to file, never the
   TUI).
2. **`ty` / `ty server` invalid** in the image (wrong subcommand, or a `ty` that isn't Astral's)
   — though a bad binary should still show Python as "unstarted", so this is lower-likelihood
   for the *absence*.
3. **The running baked crushrc differs from source** (a typo or an unshipped fix) despite the
   `COPY` — confirm by grepping the running file.

## Recheck / diagnostics (run in the running container)

```
grep -n -A1 'lsp add python' ~/.config/crush/crushrc         # does the running line match source verbatim?
crush logs 2>&1 | grep -iE 'python|unknown flag|lsp|parse|ty ' | tail -40   # the real registration/parse error
command -v ty && ty --version && ty server --help 2>&1 | head -3            # is `ty server` valid?
```
Cleared when the logs/greps identify why `lsp add python` doesn't register; then fix (likely a
one-line crushrc change — coordinate with the sibling root-marker task if both touch the
crushrc) and confirm Python appears in the sidebar and `lsp_symbols` works on `base.py`.

## Open questions (for the maintainer)

1. Paste the output of the three diagnostics above (especially `crush logs …`) so we can pinpoint
   why `lsp add python` isn't registering while the other five servers are.

## Related

- `tasks/lsp-add-root-markers-gate-startup.md` — the distinct latent gate bug (not this issue).
- `tasks/reference/crush-lsp-integration.md` — how Crush consumes LSPs; §2 gate model.
