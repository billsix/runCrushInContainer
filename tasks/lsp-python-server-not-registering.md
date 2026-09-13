# Python LSP times out — powernap Router mis-routes ty's id-0 `workspace/configuration`

*(Filename slug is historical: the first symptom was "python absent from the sidebar" on the minimal
image; that was fixed by the full-toolchain decoupling, and the real, confirmed cause is a
powernap JSON-RPC routing bug. Slug kept to avoid breaking inbound links.)*

**Status:** DONE — verified 2026-09-13 on the maintainer's host image: `lsp_symbols` on
`src/gacalc/base.py` returns the full symbol table (106 symbols), sidebar server `ty`. Fix shipped:
`crush-lsp-router-notif.patch` (the cause) + `crush-lsp-async.patch` (defensive) + `python`→`ty`
rename, all verified in-build (`CRUSH_LSP_ROUTER_VERIFY`/`CRUSH_LSP_ASYNC_VERIFY: PRESENT`). Archive
after the work commit lands. Follow-up worth doing: file both powernap bugs upstream with charmbracelet.
**Priority:** 2
**Difficulty:** 4

## BLUF

`lsp_symbols` on a `.py` file fails with `context deadline exceeded`. The runtime log (with
`option debug-lsp true`) shows ty's own stderr: `Failed to deserialize client response
(method=workspace/configuration): invalid type: null, expected a sequence`. So **Crush replies
`null` to ty's `workspace/configuration` request**, ty (which gates `documentSymbol` on a valid
config reply) rejects it and never proceeds → 5 s timeout. The `null` is a **powernap Router bug**:
`Route` classifies a request as a notification with `req.ID == (jsonrpc2.ID{})`, but a real request
whose id is numeric **0** has a zero-value ID — and ty sends `workspace/configuration` with **id 0** —
so the handler is skipped and a `null` result is returned. **Fix = route on `req.Notif`** (the
jsonrpc2 field), shipped as `crush-lsp-router-notif.patch`. (The earlier AsyncHandler patch addressed
a *different*, latent deadlock and was NOT the fix; it's kept as defensive hardening.) No crushrc
`--timeout` helps (that only covers the 30 s init). **Done = `lsp_symbols` returns symbols for
`base.py` in the running client.**

## Confirmed root cause (2026-09-13, from the runtime log)

With the AsyncHandler patch verified in the binary, the client reached "ready" but `lsp_symbols` still
timed out. `crush logs` (debug-lsp on) showed, repeatedly, ty's stderr:
`ERROR Failed to deserialize client response (method=workspace/configuration): invalid type: null,
expected a sequence`. Reading powernap `pkg/transport/router.go` `Route`:
```go
if req.ID == (jsonrpc2.ID{}) {        // treats id==zero-value as a NOTIFICATION
    ... return nil, nil               // handler NOT called → caller replies null
}
if handler, ok := r.handlers[req.Method]; ok { return handler(...) }
```
`jsonrpc2.ID{}`'s zero value is numeric id `0`. ty sends `workspace/configuration` with **id 0**, so
`Route` misclassifies it as a notification, never calls Crush's registered
`HandleWorkspaceConfiguration` (which would return `[{}]`), and returns `nil` → Crush sends
`result: null`. ty rejects it ("expected a sequence"), never gets its config, and gates
`documentSymbol` forever. `jsonrpc2` itself detects notifications via `req.Notif`
(`request.go:108` sets it when there's no `id`; `handler_with_error.go:22` uses it) — so the fix is to
route on `req.Notif`, not `req.ID == zero`. My standalone probe passed because it replied using ty's
actual id; only powernap's Router mishandles id 0.

## Root cause — confirmed by experiment (2026-09-13)

Three direct LSP handshakes to the real `ty` 0.0.74, rooted at `/foo/opt/geometricalgebra` (2534
files), timing `documentSymbol` on `src/gacalc/base.py`. Reproduce with
`tasks/adhoc/lsp-python-server-not-registering/ty_lsp_probe.py <root> <file>`:

| mode | what it does | result |
|---|---|---|
| minimal | empty client capabilities (bare handshake) | documentSymbol **ok 0.18 s**, 106 symbols; ty sends nothing back |
| rich | powernap's caps (`configuration`/`workDoneProgress`/`dynamicRegistration`) + answer ty's callbacks on a background reader | documentSymbol **ok 0.18 s**; ty sends **`workspace/configuration`** |
| noconfig | same rich init, but leave `workspace/configuration` **unanswered** | documentSymbol **STILL PENDING after 20 s** |

So: `ty` is fast (minimal, and rich-when-answered), and it **gates `documentSymbol` on the
`workspace/configuration` reply** (noconfig hangs). The background-reader in "rich" is exactly what
`AsyncHandler` gives; it works. Crush does not have it:

- Powernap advertises `configuration: true` (`powernap/pkg/lsp/client.go:641-778`), so ty asks.
- Powernap builds the connection **without `AsyncHandler`** (`powernap/pkg/transport/connection.go:50-55`),
  so the sole `jsonrpc2` reader goroutine both dispatches ty's `workspace/configuration` request
  (running the handler + writing the reply, `sourcegraph/jsonrpc2` `HandlerWithError`) **and** must
  deliver the pending `documentSymbol` response — it cannot reliably do both.
- The documentSymbol request is wrapped in a **hardcoded 5 s** deadline (`crush
  internal/lsp/client.go:725`); when the response isn't delivered in time it returns
  `context deadline exceeded` (surfaced by `internal/agent/tools/lsp_symbols.go:38-40`).
- Aggravator: Crush's `workspace/configuration` handler returns a **fixed length-1 array regardless of
  requested count** (`internal/lsp/handlers.go:14-16`) — an LSP violation.

**Why no crushrc knob helps:** `--timeout N` sets only the 30 s *init* context
(`manager.go:233`, `config.go:256`); the 5 s (and 10 s) per-request deadlines
(`client.go:699-765`) are hardcoded.

## Implemented (2026-09-13, staged — awaiting host build-verify)

- **`client/patches/crush-lsp-router-notif.patch` — THE fix.** Routes on `req.Notif` instead of
  `req.ID == (jsonrpc2.ID{})` in powernap `pkg/transport/router.go`, so ty's id-0
  `workspace/configuration` is handled (returns `[{}]`) instead of getting `null`. Generated with
  `diff` and verified with `git apply --check --unidiff-zero -p1` against a fresh copy → applies
  cleanly.
- **`client/patches/crush-lsp-async.patch` — defensive.** Wraps powernap's handler in
  `jsonrpc2.AsyncHandler` (`connection.go:53`); prevents a latent single-reader-goroutine deadlock
  but was NOT the cause of this timeout. Kept; also verified to apply cleanly.
- **`client/entrypoint/03-build-crush.sh`** — applies both via `CRUSH_LSP_ASYNC` (default **1**,
  mandatory bugfixes; set `=0` to skip). Not plumbed through the Makefile/Dockerfile on purpose, so a
  bare build applies them too. A build-time self-check greps both patched files and **fails the build**
  if either didn't land (`CRUSH_LSP_ROUTER_VERIFY` / `CRUSH_LSP_ASYNC_VERIFY: PRESENT`), so a
  successful build proves both are compiled in.
- **`client/entrypoint/crushrc`** — server renamed `python` → `ty` (dodges the `resolveServerName`
  misfiling), `--filetypes py` unchanged.
- **NOT shipped:** the `handlers.go` length-1 fix — `ty` requests exactly 1 config item, so Crush's
  length-1 reply is already correct once the request is actually routed; defensive-only, left as a
  follow-up.
- **Cannot build-verify here:** the 22 GB client image only builds on the host. The prior build already
  confirmed `CRUSH_LSP_ASYNC_VERIFY: PRESENT`; the next build must also show `CRUSH_LSP_ROUTER_VERIFY:
  PRESENT`, then `lsp_symbols` should return symbols.

## Fix

1. **Primary (correct, server-agnostic): patch `powernap` to use `jsonrpc2.AsyncHandler`** at
   `pkg/transport/connection.go:53` (available at the vendored `sourcegraph/jsonrpc2/async.go`). The
   repo builds Crush from source and applies `client/patches/*.patch` in `03-build-crush.sh`, so add a
   new patch there; powernap is vendored inside the crush build tree. Re-verify on every `CRUSH_TAG`
   bump (like the other patches).
2. **Secondary (defensive): fix `internal/lsp/handlers.go:14`** to return a `workspace/configuration`
   array whose length matches the request's `items` count.
3. **Cheap cleanup: rename the crushrc server `python` → `ty`** (`client/entrypoint/crushrc`) —
   `resolveServerName` (`manager.go:322-332`) misfiles a server named `python` under the registry's
   `tvm_ffi_navigator` (whose command is `python`); naming it `ty` resolves cleanly. Doesn't change the
   spawned command, but avoids the misresolution.
4. **Report upstream** to charmbracelet (powernap: no `AsyncHandler` + a server that gates on
   `workspace/configuration` deadlocks; and the length-1 config reply). This is a genuine library bug.

**Verification:** rebuild the client on the host (the 22 GB image can't build in the nested store),
then in the running client `lsp_symbols` on `base.py` returns symbols; the probe's "rich" mode already
proves the AsyncHandler behavior works.

## Prior symptoms (history, superseded)

- 2026-09-12, **minimal image**: sidebar showed `c/glsl/go/rust/sh` but not `python`; `lsp_symbols`
  returned `no LSP client handles file`. Cause: the nested build installed no language servers (no
  `ty`). Fixed by `tasks/decouple-full-toolchain-from-nested-podman.md` (client always full toolchain).
- 2026-09-13, **init-timeout hypothesis**: once `ty` was installed, the error became `context deadline
  exceeded`; first theory was a slow/hung `ty` init on the large tree, fixable by `--timeout`. The
  experiments above **refuted** it — `ty` inits in 0.08 s and answers documentSymbol in <0.2 s.

## Open questions (for the maintainer)

1. Result of the host rebuild (`make -C client image` — the changed patch/script/crushrc invalidate
   the build-layer cache; `podman builder prune -f` first if paranoid) + a live `lsp_symbols` on
   `base.py`: does the `ty` server now return symbols (sidebar entry now named `ty`)? If yes, archive
   this task; if it still times out, capture `crush logs` and reopen.

## Related

- `tasks/decouple-full-toolchain-from-nested-podman.md` — prerequisite (got `ty` installed); done.
- `tasks/lsp-add-root-markers-gate-startup.md` — the distinct latent root-marker gate bug.
- `tasks/reference/crush-lsp-integration.md` — how Crush consumes LSPs.
- `tasks/adhoc/lsp-python-server-not-registering/ty_lsp_probe.py` — the reproducer for the three modes.
