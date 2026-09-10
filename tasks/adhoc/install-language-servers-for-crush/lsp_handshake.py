#!/usr/bin/env python3
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
"""Speak one LSP `initialize` handshake to a language server over stdio and report what it offers.

Usage:  lsp_handshake.py <label> -- <server command> [args...]
        lsp_handshake.py python -- ty server
        lsp_handshake.py go     -- gopls

Prints the server's name/version and, for each capability Crush's lsp_* tools rely on
(tasks/reference/crush-lsp-integration.md §1), whether the server advertises it. Exit 0 if
the handshake completed, 1 otherwise. Used by check_fedora_servers.sh and check_rhel9_ty.sh
inside throwaway containers, so it depends on nothing beyond the python3 stdlib.

How LSP framing works (the only non-obvious part): every message is JSON-RPC, prefixed by a
`Content-Length: N\r\n\r\n` header, in both directions. We send `initialize`, read messages
until the reply with our request id arrives (servers may emit log notifications first), then
send `initialized`, `shutdown`, `exit` so the process ends cleanly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time

# Capabilities Crush's tools need, keyed by the LSP ServerCapabilities field name.
WANTED = {
    "definitionProvider": "definition",
    "referencesProvider": "references",
    "renameProvider": "rename",
    "documentSymbolProvider": "documentSymbol",
    "callHierarchyProvider": "callHierarchy",
    "diagnosticProvider": "diagnostics (pull)",
    "textDocumentSync": "textDocumentSync (push diagnostics need this)",
}


def send(proc: subprocess.Popen, msg: dict) -> None:
    body = json.dumps(msg).encode()
    assert proc.stdin is not None
    proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    proc.stdin.flush()


def recv(proc: subprocess.Popen, deadline: float) -> dict:
    """Read one framed message; raise on EOF or when the deadline passes."""
    assert proc.stdout is not None
    headers: dict[str, str] = {}
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError("no reply before the deadline")
        line = proc.stdout.readline()
        if not line:
            raise EOFError("server closed stdout")
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode().partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers["content-length"])
    return json.loads(proc.stdout.read(length))


def main() -> int:
    if "--" not in sys.argv:
        print(__doc__, file=sys.stderr)
        return 2
    split = sys.argv.index("--")
    label = " ".join(sys.argv[1:split])
    cmd = sys.argv[split + 1 :]
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    deadline = time.monotonic() + 60
    send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": "file:///tmp",
                "capabilities": {},
                "workspaceFolders": [{"uri": "file:///tmp", "name": "tmp"}],
            },
        },
    )
    try:
        while True:
            msg = recv(proc, deadline)
            if msg.get("id") == 1:
                break
    except (TimeoutError, EOFError) as exc:
        print(f"[{label}] {' '.join(cmd)}: FAILED — {exc}")
        proc.kill()
        return 1
    result = msg.get("result", {})
    caps = result.get("capabilities", {})
    info = result.get("serverInfo", {})
    print(f"[{label}] {' '.join(cmd)}: {info.get('name', '?')} {info.get('version', '')}".rstrip())
    for field, what in WANTED.items():
        present = caps.get(field) not in (None, False)
        print(f"    {'yes' if present else 'NO '}  {what}")
    send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
    send(proc, {"jsonrpc": "2.0", "id": 2, "method": "shutdown"})
    send(proc, {"jsonrpc": "2.0", "method": "exit"})
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
