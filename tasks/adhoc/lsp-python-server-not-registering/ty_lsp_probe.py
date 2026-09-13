#!/usr/bin/env python3
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
"""Prove WHY Crush's `lsp_symbols` times out on `ty` while `ty` itself is fast.

Background: Crush drives language servers through the `powernap` LSP library. On a Python file,
`ty server` answered a documentSymbol request in <1s in a plain handshake, yet Crush reported
`context deadline exceeded`. This probe isolates the cause by speaking LSP to `ty server` directly
in four modes and timing the documentSymbol request each time:

  minimal  : advertise NO client capabilities (like a bare handshake). ty never asks anything back.
  rich     : advertise powernap's capabilities (configuration/workDoneProgress/dynamicRegistration)
             AND answer ty's server->client requests on a background reader thread (this is what
             `jsonrpc2.AsyncHandler` would give Crush). ty asks `workspace/configuration`, we answer,
             ty returns symbols fast.
  crushcfg : like rich, but reply to workspace/configuration with a FIXED length-1 array, exactly as
             Crush's handler does (internal/lsp/handlers.go). ty asks for 1 item, so this is correct
             and ty is still fast -> proves the AsyncHandler patch alone suffices (no handler fix
             needed for ty).
  noconfig : same rich init, but DELIBERATELY do NOT answer `workspace/configuration`. ty then never
             returns documentSymbol -> it GATES on that reply. This is the exact condition Crush hits
             because powernap services that reply on its single JSON-RPC reader goroutine (no
             AsyncHandler, powernap/pkg/transport/connection.go), so it can't deliver the reply and
             the documentSymbol response before Crush's hardcoded 5s deadline (crush
             internal/lsp/client.go:725).

Conclusion the three modes establish: the fix is on the Crush/powernap side (wrap the handler in
jsonrpc2.AsyncHandler), not ty, and no crushrc `--timeout` helps (that only covers the 30s init).

Usage:  ty_lsp_probe.py <PROJECT_ROOT> <PYTHON_FILE>   # PYTHON_FILE absolute or relative to root
        ty_lsp_probe.py . src/gacalc/base.py
Needs only the python3 stdlib and `ty` on PATH. Read-only; kills ty after each probe.
"""
from __future__ import annotations
import json, subprocess, sys, threading, time, pathlib

def _send(p, m):
    b = json.dumps(m).encode()
    p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(b) + b); p.stdin.flush()

def _read(p):
    h = {}
    while True:
        ln = p.stdout.readline()
        if not ln:
            return None
        if ln in (b"\r\n", b"\n"):
            break
        k, _, v = ln.decode().partition(":"); h[k.strip().lower()] = v.strip()
    return json.loads(p.stdout.read(int(h["content-length"])))

RICH = {
    "window": {"workDoneProgress": True},
    "workspace": {"configuration": True,
                  "didChangeConfiguration": {"dynamicRegistration": True},
                  "workspaceFolders": True},
    "textDocument": {"synchronization": {"dynamicRegistration": True},
                     "documentSymbol": {"dynamicRegistration": True,
                                        "hierarchicalDocumentSymbolSupport": True}},
}

def probe(root: str, pyfile: str, mode: str) -> None:
    root = str(pathlib.Path(root).resolve())
    fpath = pathlib.Path(pyfile)
    fpath = fpath if fpath.is_absolute() else pathlib.Path(root) / fpath
    fpath = fpath.resolve()
    caps = {} if mode == "minimal" else RICH
    p = subprocess.Popen(["ty", "server"], cwd=root,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    st = {"done": False, "t": None, "n": None, "reqs": []}

    def reader():
        while True:
            m = _read(p)
            if m is None:
                return
            if "method" in m and "id" in m:                      # server->client REQUEST
                st["reqs"].append(m["method"])
                if m["method"] == "workspace/configuration":
                    items = (m.get("params") or {}).get("items") or [{}]
                    st["cfg_items"] = len(items)
                    if mode == "noconfig":
                        continue                                 # deliberately leave it unanswered
                    # "crushcfg" mimics Crush's handler: a fixed length-1 array regardless of count.
                    reply = [{}] if mode == "crushcfg" else [{} for _ in items]
                    _send(p, {"jsonrpc": "2.0", "id": m["id"], "result": reply})
                else:
                    _send(p, {"jsonrpc": "2.0", "id": m["id"], "result": None})
            elif "id" in m and ("result" in m or "error" in m) and m["id"] == 3:
                st["t"] = time.monotonic(); st["n"] = len(m.get("result") or []); st["done"] = True

    threading.Thread(target=reader, daemon=True).start()
    uri = f"file://{root}"
    _send(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "processId": None, "rootUri": uri, "capabilities": caps,
        "workspaceFolders": [{"uri": uri, "name": pathlib.Path(root).name}]}})
    time.sleep(0.3)
    _send(p, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
    furi = f"file://{fpath}"
    _send(p, {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
        "textDocument": {"uri": furi, "languageId": "python", "version": 1,
                         "text": fpath.read_text()}}})
    t0 = time.monotonic()
    _send(p, {"jsonrpc": "2.0", "id": 3, "method": "textDocument/documentSymbol",
              "params": {"textDocument": {"uri": furi}}})
    while not st["done"] and time.monotonic() - t0 < 20:
        time.sleep(0.05)
    got = (f"ok in {st['t']-t0:.2f}s — {st['n']} symbols" if st["done"]
           else f"STILL PENDING after {time.monotonic()-t0:.1f}s  <-- gated on the unanswered reply")
    print(f"[{mode:8}] documentSymbol: {got}")
    print(f"           ty server->client requests: {st['reqs'] or '(none)'}"
          + (f"  (workspace/configuration items={st['cfg_items']})" if "cfg_items" in st else ""))
    p.kill()

def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr); return 2
    for mode in ("minimal", "rich", "crushcfg", "noconfig"):
        probe(sys.argv[1], sys.argv[2], mode)
    return 0

if __name__ == "__main__":
    sys.exit(main())
