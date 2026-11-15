# Python LSP timed out — powernap Router mis-routed ty's id-0 `workspace/configuration`

*(Filename slug is historical: the first symptom was "python absent from the sidebar" on the minimal
image; the confirmed cause was a powernap JSON-RPC routing bug. Slug kept to avoid breaking inbound
links.)*

**Status:** complete
**Completed:** 2026-09-13

Fixed `lsp_symbols` on `.py` files failing with `context deadline exceeded`. Crush replied `null` to
ty's `workspace/configuration` request because powernap's Router treated ty's numeric id **0** as a
notification; ty gates `documentSymbol` on a valid config reply, so it never answered. Patched the
Router to route on `req.Notif`. Verified on the maintainer's host image: `lsp_symbols` on
`src/gacalc/base.py` returned 106 symbols, sidebar server `ty`.

## Root cause

With `option debug-lsp true`, `crush logs` repeated ty's stderr `Failed to deserialize client
response (method=workspace/configuration): invalid type: null, expected a sequence`. powernap
`pkg/transport/router.go` `Route` was:
```go
if req.ID == (jsonrpc2.ID{}) {        // treats a zero-value ID as a NOTIFICATION
    ... return nil, nil               // registered handler NOT called → caller replies null
}
if handler, ok := r.handlers[req.Method]; ok { return handler(...) }
```
The zero value of `jsonrpc2.ID{}` is numeric id `0`, so Crush's registered
`HandleWorkspaceConfiguration` (which returns `[{}]`) was never called. `jsonrpc2` itself flags
notifications with `req.Notif` (set in `request.go` when there is no `id`), so routing on that was the
fix.

**Supporting evidence — `tools/ty_lsp_probe.py`** (direct stdio handshakes to `ty` 0.0.74, rooted at
the 2534-file `geometricalgebra` tree, timing `documentSymbol` on `base.py`):

| mode | what it did | result |
|---|---|---|
| minimal | empty client capabilities | documentSymbol **ok 0.18 s**, 106 symbols; ty asked nothing back |
| rich | powernap-style caps + answered ty's callback | documentSymbol **ok 0.18 s**; ty asked **`workspace/configuration`** (1 item) |
| noconfig | rich init, `workspace/configuration` reply withheld | documentSymbol **pending after 20 s** |

The deadline that fired is Crush's hardcoded 5 s per-request timeout (`internal/lsp/client.go`,
surfaced by `internal/agent/tools/lsp_symbols.go`); crushrc `--timeout` only sets the 30 s init
context, so it could not help.

## What shipped

- **`client/patches/crush-lsp-router-notif.patch` — the fix.** Routes on `req.Notif` in powernap
  `pkg/transport/router.go`.
- **`client/patches/crush-lsp-async.patch` — defensive.** Wraps powernap's handler in
  `jsonrpc2.AsyncHandler`, removing a latent single-reader-goroutine deadlock; not the cause, kept as
  hardening.
- **`client/entrypoint/03-build-crush.sh`** applies both under `CRUSH_LSP_ASYNC` (default 1;
  script-level, not plumbed through the Makefile), with a build-time self-check that fails the build
  unless both patched files show the change (`CRUSH_LSP_ROUTER_VERIFY` / `CRUSH_LSP_ASYNC_VERIFY:
  PRESENT`).
- **`client/entrypoint/crushrc`** renamed the Python server `python` → `ty`, dodging
  `resolveServerName` (`manager.go`), which misfiled a user server named `python` under the registry's
  `tvm_ffi_navigator`. `--filetypes py` unchanged.
- **Not shipped:** a length fix to `internal/lsp/handlers.go` (fixed length-1
  `workspace/configuration` array). ty requests exactly 1 item, so it is defensive only and was not
  done.

## Hypotheses ruled out along the way

- **Minimal image (2026-09-12):** `python` missing from the sidebar was because the nested build had
  no `ty`; fixed by `tasks/archive/2026/09/13/decouple-full-toolchain-from-nested-podman.md`.
- **Slow init (2026-09-13):** refuted by the probe (`ty` inits in 0.08 s, documentSymbol <0.2 s).
- **AsyncHandler deadlock (2026-09-13):** the patch was built and verified in, but `lsp_symbols` still
  timed out, which led to the runtime log and the id-0 cause.

## Related

- `tasks/file-powernap-lsp-bugs-upstream.md` — issue text for filing both powernap bugs upstream so
  the local patches can be dropped on a future bump.
- `tasks/lsp-add-root-markers-gate-startup.md` — a distinct latent root-marker gate bug.
- `tasks/reference/crush-lsp-integration.md` §3a — the durable write-up of this cause.
- `tools/ty_lsp_probe.py` — the reproducer.
