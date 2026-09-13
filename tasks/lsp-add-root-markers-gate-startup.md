# crushrc `lsp add` `--root-markers` silently gate startup — drop them, fix the doc

**Status:** proposed — needs go-ahead
**Priority:** 3
**Difficulty:** 2

## BLUF

The baked `crushrc`'s six `lsp add` lines each carry explicit `--root-markers`, and both the
crushrc comment and `tasks/reference/crush-lsp-integration.md` (§2, §5) claim an explicit
`lsp add` "starts for its filetypes, full stop" / "bypasses … the root-marker check." **Crush
v0.89.0's source refutes that:** a user-configured server still must pass
`handles = handlesFiletype(...) && hasRootMarkers(workDir, markers)`; `lsp add` skips only the
generic-command skip-list, the `exec.LookPath` check, and the 30 s unavailable window — **not**
the root-marker gate. `hasRootMarkers` is a no-op **only when the marker list is empty**. So by
listing markers, the crushrc re-imposed exactly the gate it believed it removed: a `.c`/`.py`
file under a `/work` that lacks the listed markers (a **subdir mount with no `.git`**, an
**unbuilt autotools tree with no generated `Makefile`**, etc.) never gets its server started,
and the LSP tools return `no LSP client handles file`. **Done = the six `lsp add` lines start
for their filetypes regardless of markers (remove `--root-markers`), the crushrc comment is
corrected, and the reference-doc claim is fixed (plus any baked twin re-synced).**

## Context

**How this surfaced (2026-09-11 → 12):** while diagnosing an LSP complaint, a source study of
the vendored Crush turned up the root-marker gate below. **Scope note — this is a latent
robustness bug, NOT the cause of the Python failure the maintainer actually hit.** That failure
(Python absent from the LSP sidebar even when crush is rooted at a project that HAS
`pyproject.toml`/`setup.py`/`.git`) is a distinct `lsp add python` *registration* problem,
tracked separately in `tasks/archive/2026/09/13/lsp-python-server-not-registering.md`. Two earlier read-outs in
this diagnosis were mistaken and are corrected here: (1) `grep -c 'lsp add'` returning **9** is
**not** a stale-image tell — the count includes ~3 comment lines that mention "lsp add"; the
current source crushrc also greps to 9 (6 real `lsp add` commands + 3 comment mentions), so it
*matches* source. (2) The gate did not explain the observed Python case, because the working dir
did contain the markers. Where the gate genuinely bites: a `.c`/`.py` file under a working dir
whose top level lacks every listed marker — a **subdir mount with no `.git`**, or an **unbuilt
autotools tree with no generated `Makefile`** — where the server never starts and the tools
return `no LSP client handles file`.

**Read first**
- `client/entrypoint/crushrc:97-126` — the six `lsp add` lines and the (incorrect) "skips every
  gate" comment.
- `tasks/reference/crush-lsp-integration.md` — §2 "How a server gets started — the four gates"
  and §5, both of which state (wrongly) that `lsp add` bypasses the root-marker check. Fix these.
- Its baked twin, if present: `client/entrypoint/dotfiles/.config/crush/reference/crush-lsp-integration.md`
  (check; the nested-podman-design.md doc has such a twin — keep them byte-identical).

**Source evidence (vendored Crush v0.89.0, under `client/vendor/crush/`)**
- `internal/lsp/manager.go` — for a user-configured server: `if isUserConfigured { if
  !handles(server, filepath, workDir) { return } }`; `handles` (≈`manager.go:372-375`) =
  `handlesFiletype(...) && hasRootMarkers(workDir, server.RootMarkers)`; `hasRootMarkers` returns
  `true` for zero markers (≈`manager.go:357-359`). `TrackConfigured` (≈`manager.go:86-100`) seeds
  the sidebar with every **user-configured** server as `unstarted` but does **not** start it;
  startup is lazy per-file via `Start(ctx, path)`.
- Sidebar rendering: `internal/ui/model/lsp.go` — the panel is a union of user-configured
  servers (always shown, from `TrackConfigured`) and registry/auto-start servers (shown only
  after a successful start).
- `no LSP client handles file`: `internal/agent/tools/lsp_symbols.go:35`,
  `internal/agent/tools/lsp_replace_symbol.go:80` — returned when no running client handles the
  file (i.e. none started). Init/spawn failures log at **Error** to the log file only
  (`crush logs`), never the TUI.
- Patches (`client/patches/*.patch`) leave LSP start/handling/sidebar logic **stock upstream** —
  not a factor.

**Decision (William Emerison Six <billsix@gmail.com>, 2026-09-12): remove `--root-markers` from
the six `lsp add` lines.** Empty markers → `hasRootMarkers` is a genuine no-op → each server
starts for its filetypes regardless of build state or `.git`, still rooted at `/work` (Crush
passes `s.cfg.WorkingDir()` to `Initialize`, independent of the markers). This realizes the
crushrc's stated intent. Considered and rejected: keeping the markers and instead always
mounting a repo root with `.git` at `/work` — brittle, since subdir mounts are routine.
Downside accepted: a server may start for its filetype anywhere under `/work` (e.g. a scratch
dir) — harmless (it just runs rooted at `/work`).

## Work

1. **`client/entrypoint/crushrc`** — remove `--root-markers …` from all six `lsp add` lines
   (python, go, c, rust, sh, glsl); keep `--command`/`--args`/`--filetypes`.
2. **Correct the crushrc comment** — the "An explicit `lsp add` skips every gate: the server
   starts for its filetypes, full stop" text is only true with markers omitted; state that
   explicit `--root-markers` re-impose the root gate, which is why they're omitted.
3. **Fix `tasks/reference/crush-lsp-integration.md`** §2 and §5: a user-configured server still
   passes `handlesFiletype && hasRootMarkers`; `lsp add` bypasses only the skip-list, `LookPath`,
   and the 30 s window — the root gate applies unless `--root-markers` is omitted. Note this
   fix and its date.
4. **Re-sync the baked reference twin** if one exists (byte-identical), as with nested-podman-design.md.
5. **Rebuild + verify (host action, owed):** `make -C client image`, then in a client whose
   `/work` is a **subdir with no `.git`** and no `Makefile`, open a `.c` and a `.py` file and
   confirm the server reaches `ready` in the sidebar and `lsp_definition` works.
6. **Stage** the doc/config edits.

## Verification

- `grep -c -- '--root-markers' client/entrypoint/crushrc` → **0**.
- Rebuilt image, subdir `/work` without `.git`: `.c`/`.py` LSP tools return results (not
  `no LSP client handles file`); sidebar shows the servers `ready`.
- `crush logs` shows successful `Initialize`, no `Failed to create LSP client`.

## Related

- `tasks/reference/crush-lsp-integration.md` (the doc being corrected — its §2/§5 "lsp add
  bypasses the root-marker check" claim is wrong).
- `tasks/archive/2026/09/13/lsp-python-server-not-registering.md` — the **distinct**, currently-live issue (Python
  `lsp add` line not registering at all). This root-marker fix does not address that; if the
  Python diagnosis lands on a crushrc edit, coordinate the two edits (same file).
