# Python LSP timed out — powernap Router mis-routed ty's id-0 `workspace/configuration`

*(Filename slug is historical: the first symptom was "python absent from the sidebar" on the minimal
image; the real, confirmed cause turned out to be a powernap JSON-RPC routing bug. Slug kept to avoid
breaking inbound links.)*

**Status:** Done — verified 2026-09-13 on the maintainer's host image: `lsp_symbols` on
`src/gacalc/base.py` returned the full symbol table (106 symbols); sidebar server `ty`. Archived
2026-09-13.
**Priority:** 2
**Difficulty:** 4

## BLUF

`lsp_symbols` on a `.py` file failed with `context deadline exceeded`. The runtime log (with
`option debug-lsp true`) showed ty's own stderr: `Failed to deserialize client response
(method=workspace/configuration): invalid type: null, expected a sequence`. Crush was replying
`null` to ty's `workspace/configuration` request; ty gates `documentSymbol` on a valid config reply,
rejected the `null`, and never proceeded → 5 s timeout. The `null` was a **powernap Router bug**:
`Route` classified a request as a notification with `req.ID == (jsonrpc2.ID{})`, but a real request
whose id is numeric **0** has a zero-value ID — and ty sends `workspace/configuration` with **id 0** —
so the handler was skipped and a `null` result returned. The fix routed on `req.Notif`
(`crush-lsp-router-notif.patch`). A separate AsyncHandler patch addressed a *different*, latent
deadlock and was kept as defensive hardening, not the cause. No crushrc `--timeout` helped (that only
covers the 30 s init).

## Root cause (confirmed 2026-09-13)

The runtime log pinned it. With the AsyncHandler patch verified in the binary, the client reached
"ready" but `lsp_symbols` still timed out, and `crush logs` repeated ty's stderr
`invalid type: null, expected a sequence` for `workspace/configuration`. powernap
`pkg/transport/router.go` `Route` was:
```go
if req.ID == (jsonrpc2.ID{}) {        // treats a zero-value ID as a NOTIFICATION
    ... return nil, nil               // registered handler NOT called → caller replies null
}
if handler, ok := r.handlers[req.Method]; ok { return handler(...) }
```
`jsonrpc2.ID{}`'s zero value is numeric id `0`; ty sends `workspace/configuration` with id 0, so
`Route` misclassified it as a notification, never called Crush's registered
`HandleWorkspaceConfiguration` (which returns `[{}]`), and returned `nil` → `result: null`. `jsonrpc2`
itself flags notifications with `req.Notif` (`request.go:108` sets it when there is no `id`;
`handler_with_error.go:22` uses it), so routing on `req.Notif` was the fix.

**Supporting evidence — `tools/ty_lsp_probe.py`** (three direct stdio handshakes to `ty` 0.0.74, rooted
at the real 2534-file `geometricalgebra` tree, timing `documentSymbol` on `base.py`):

| mode | what it did | result |
|---|---|---|
| minimal | empty client capabilities | documentSymbol **ok 0.18 s**, 106 symbols; ty asked nothing back |
| rich | powernap-style caps + answered ty's callback on a background reader | documentSymbol **ok 0.18 s**; ty asked **`workspace/configuration`** (1 item) |
| noconfig | rich init, but the `workspace/configuration` reply withheld | documentSymbol **pending after 20 s** |

So ty is fast whenever its `workspace/configuration` request is answered with a valid array, and gates
forever when it isn't — which is exactly what powernap produced by never answering it (the id-0
misroute). The probe replied using ty's actual id (including 0), which is why it passed where powernap
failed. The per-request deadline that fired is a **hardcoded 5 s** (`crush internal/lsp/client.go:725`;
surfaced by `internal/agent/tools/lsp_symbols.go`); `--timeout` only sets the 30 s init context
(`manager.go:233`).

## What shipped

- **`client/patches/crush-lsp-router-notif.patch` — the fix.** Routed on `req.Notif` instead of
  `req.ID == (jsonrpc2.ID{})` in powernap `pkg/transport/router.go`, so ty's id-0
  `workspace/configuration` reached its handler (`[{}]`) instead of a `null`.
- **`client/patches/crush-lsp-async.patch` — defensive.** Wrapped powernap's handler in
  `jsonrpc2.AsyncHandler` (`connection.go`), removing a latent single-reader-goroutine deadlock; not
  the cause here, kept as hardening.
- **`client/entrypoint/03-build-crush.sh`** — applied both under `CRUSH_LSP_ASYNC` (default 1;
  script-level, not plumbed through the Makefile), with a build-time self-check that fails the build
  unless both patched files show the change (`CRUSH_LSP_ROUTER_VERIFY` / `CRUSH_LSP_ASYNC_VERIFY:
  PRESENT`).
- **`client/entrypoint/crushrc`** — renamed the Python server `python` → `ty`, dodging
  `resolveServerName` (`manager.go:322`) which misfiled a user server named `python` under the
  registry's `tvm_ffi_navigator` (command `python`). `--filetypes py` unchanged.
- **Not shipped:** a length-fix to `internal/lsp/handlers.go` (which returns a fixed length-1
  `workspace/configuration` array). ty requests exactly 1 item, so length-1 is already correct once the
  request is routed; the fix is defensive-only and left as a follow-up.
- **Verified** on the maintainer's host build: both VERIFY markers PRESENT, then `lsp_symbols` on
  `base.py` returned 106 symbols.

## History (superseded understandings, kept for the record)

- **Minimal image (2026-09-12):** the sidebar showed `c/glsl/go/rust/sh` but not `python`, and
  `lsp_symbols` returned `no LSP client handles file` — because the nested build had installed no
  language servers (no `ty`). Fixed by the full-toolchain decoupling
  (`tasks/archive/2026/09/13/decouple-full-toolchain-from-nested-podman.md`).
- **Init-timeout hypothesis (2026-09-13):** once `ty` was present the error became `context deadline
  exceeded`; the first theory (slow/hung `ty` init on the large tree, fixable by `--timeout`) was
  refuted by the probe — `ty` inits in 0.08 s and answers documentSymbol in <0.2 s.
- **AsyncHandler hypothesis (2026-09-13):** the next theory was a single-reader-goroutine deadlock, and
  the AsyncHandler patch was built and verified in — but `lsp_symbols` still timed out, which is what
  led to the runtime log and the true (router id-0) cause above.

## Follow-up

- `tasks/file-powernap-lsp-bugs-upstream.md` — holds the ready-to-send issue text for filing both
  powernap bugs (the id-0 routing and the missing AsyncHandler) with charmbracelet, so the local
  patches can be dropped on a future bump.

## Related

- `tasks/archive/2026/09/13/decouple-full-toolchain-from-nested-podman.md` — prerequisite (installed `ty`).
- `tasks/lsp-add-root-markers-gate-startup.md` — the distinct, still-open latent root-marker gate bug.
- `tasks/reference/crush-lsp-integration.md` §3a — the durable write-up of this cause.
- `tools/ty_lsp_probe.py` — the reproducer.
