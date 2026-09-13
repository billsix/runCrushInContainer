# File the two powernap LSP bugs upstream (charmbracelet/x)

**Status:** proposed — needs go-ahead (maintainer files it; text is ready below)
**Priority:** 4
**Difficulty:** 1

## BLUF

While fixing "ty LSP times out in Crush" we found and locally patched **two bugs in
`github.com/charmbracelet/x/powernap`** (`client/patches/crush-lsp-router-notif.patch`,
`client/patches/crush-lsp-async.patch`). Filing them upstream means the fixes can land in powernap and
we can drop our local patches on a future `CRUSH_TAG` bump. This task holds the ready-to-paste issue
text. The primary bug (id-0 request misrouted) is the impactful, easily-reproduced one; the AsyncHandler
one is a related robustness fix — file as one issue with two parts, or split. Repo:
`https://github.com/charmbracelet/x` (the `powernap` module).

Background/analysis: `tasks/reference/crush-lsp-integration.md` §3a and
`tasks/archive/2026/09/13/lsp-python-server-not-registering.md`; reproducer
`tools/ty_lsp_probe.py`.

## Issue text (ready to paste)

**Title:** powernap: server→client request with id `0` is misrouted as a notification (breaks
`workspace/configuration`); handler also not run asynchronously

**Environment:** `github.com/charmbracelet/x/powernap` v0.1.6 (as vendored by Crush v0.89.0), driving
Astral `ty` 0.0.74 as an LSP server over stdio.

**Symptom:** `textDocument/documentSymbol` (and `definition`, etc.) always fail with `context deadline
exceeded`. The language server's stderr shows, repeatedly:
```
ERROR Failed to deserialize client response (method=workspace/configuration):
      invalid type: null, expected a sequence
```
`ty` gates its `documentSymbol` response on first receiving a valid `workspace/configuration` reply; it
gets `null`, rejects it, and never proceeds.

**Root cause (bug 1 — the impactful one):** `pkg/transport/router.go` `Route` classifies an incoming
message as a notification with:
```go
if req.ID == (jsonrpc2.ID{}) {
    // ... notification path, returns (nil, nil) — the registered request handler is NOT called
}
```
But `jsonrpc2.ID{}`'s zero value is the numeric id **`0`**. A real *request* whose id is `0`
(`ty` sends `workspace/configuration` with `id: 0`) therefore matches this check, is treated as a
notification, its registered handler (`workspace/configuration` → returns `[{}]`) is skipped, and the
caller replies with a `null` result. Any server that (a) is answered a request with id 0 and (b) gates
on that reply will hang.

**Fix:** distinguish notifications by `req.Notif` (which `jsonrpc2` sets during unmarshal when the
message has no `id`, and which the library itself uses in `handler_with_error.go`), not by comparing the
ID to its zero value:
```go
// Check if it's a notification (jsonrpc2 sets Notif when there is no "id").
if req.Notif {
    ...
}
```

**Root cause (bug 2 — related robustness):** the connection is created without wrapping the handler in
`jsonrpc2.AsyncHandler` (`pkg/transport/connection.go`):
```go
conn := jsonrpc2.NewConn(ctx, stream,
    jsonrpc2.HandlerWithError(c.handleRequest),   // handled on the single reader goroutine
    jsonrpc2.SetLogger(stdLogger))
```
So an incoming server→client request is serviced (handler run + reply written) on the same goroutine
that must also deliver the client's pending call responses. A server that sends a server→client request
while the client awaits a response can deadlock (jsonrpc2's own docs recommend wrapping in
`AsyncHandler`). **Fix:** `jsonrpc2.AsyncHandler(jsonrpc2.HandlerWithError(c.handleRequest))`.

**Reproducer:** a ~120-line stdio LSP client is attached in our tree
(`ty_lsp_probe.py`): advertise `workspace.configuration`, connect to `ty server`, request
`documentSymbol`. It succeeds when the client replies to `workspace/configuration` using the request's
actual id (including 0), and hangs when that reply is dropped — matching powernap replying `null`.

## Plan

- [ ] Maintainer opens the issue at charmbracelet/x with the text above (and optionally a PR: the two
      one-line-ish changes).
- [ ] On a future `CRUSH_TAG`/powernap bump that includes the fix, drop the corresponding local
      patch(es) and the `CRUSH_LSP_ASYNC` verify (re-check per the patch re-verify convention).

## Open questions (for the maintainer)

1. File as **one** issue covering both, or two separate issues? (Recommend one issue, two clearly-labeled
   parts — they're both in powernap's JSON-RPC layer.)
