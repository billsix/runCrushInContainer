#!/usr/bin/env python3
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
"""Show that `ty server` answers documentSymbol only after its configuration request is answered.

Background: Crush drives language servers through the `powernap` LSP library. On a Python file,
`ty server` answered a documentSymbol request in <1s in a plain handshake, yet Crush reported
`context deadline exceeded`. This probe speaks LSP to `ty server` directly in four modes and times
the documentSymbol request each time:

  minimal  : advertise NO client capabilities (like a bare handshake). ty never asks anything back.
  rich     : advertise powernap's capabilities (configuration/workDoneProgress/dynamicRegistration)
             AND answer ty's server->client requests on a background reader thread (what
             `jsonrpc2.AsyncHandler` gives Crush). ty asks `workspace/configuration`, we answer,
             ty returns symbols fast.
  crushcfg : like rich, but reply to workspace/configuration with a FIXED length-1 array, as
             Crush's handler does (internal/lsp/handlers.go). ty asks for 1 item, so this is
             correct and ty is still fast: the reply's shape is not the problem.
  noconfig : same rich init, but deliberately do NOT answer `workspace/configuration`. ty then never
             returns documentSymbol: it GATES on that reply.

What the four modes establish: ty is fast whenever its configuration request gets a valid reply,
and blocks without one; no crushrc `--timeout` helps (that covers only the 30s init). The probe does
not exercise powernap itself. The fix that matters is on the Crush/powernap side:
`crush-lsp-router-notif.patch` (powernap routed ty's id-0 configuration request as a notification,
so it got a null reply), with `crush-lsp-async.patch` (AsyncHandler) as a defensive second fix; see
`client/entrypoint/03-build-crush.sh` and `tasks/reference/crush-lsp-integration.md`.

Usage:  ty_lsp_probe.py <PROJECT_ROOT> <PYTHON_FILE>   # PYTHON_FILE absolute or relative to root
        ty_lsp_probe.py . src/gacalc/base.py
Needs only the python3 stdlib and `ty` on PATH. Read-only; kills ty after each probe.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import subprocess
import sys
import threading
import time
from typing import IO, Any

type Message = dict[str, Any]

RICH: Message = {
    "window": {"workDoneProgress": True},
    "workspace": {
        "configuration": True,
        "didChangeConfiguration": {"dynamicRegistration": True},
        "workspaceFolders": True,
    },
    "textDocument": {
        "synchronization": {"dynamicRegistration": True},
        "documentSymbol": {
            "dynamicRegistration": True,
            "hierarchicalDocumentSymbolSupport": True,
        },
    },
}


@dataclasses.dataclass
class ProbeState:
    """What the reader thread saw: the documentSymbol reply, and ty's requests to the client."""

    done: bool = False
    replied_at: float = 0.0
    symbols: int = 0
    requests: list[str] = dataclasses.field(default_factory=list)
    config_items: int | None = None


def _send(stdin: IO[bytes], message: Message) -> None:
    """Write one LSP message (Content-Length framed) to ``stdin``."""
    body: bytes = json.dumps(message).encode()
    stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    stdin.flush()


def _read(stdout: IO[bytes]) -> Message | None:
    """Read one LSP message from ``stdout``, or None at end of stream."""
    headers: dict[str, str] = {}
    while True:
        line: bytes = stdout.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key: str
        value: str
        key, _, value = line.decode().partition(":")
        headers[key.strip().lower()] = value.strip()
    return json.loads(stdout.read(int(headers["content-length"])))


def probe(root: str, pyfile: str, mode: str) -> None:
    """Run one handshake + documentSymbol request against `ty server` in ``mode`` and print the result."""
    root = str(pathlib.Path(root).resolve())
    given: pathlib.Path = pathlib.Path(pyfile)
    fpath: pathlib.Path = (
        given if given.is_absolute() else pathlib.Path(root) / given
    ).resolve()
    caps: Message = {} if mode == "minimal" else RICH
    proc: subprocess.Popen[bytes] = subprocess.Popen(
        ["ty", "server"],
        cwd=root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdin is not None and proc.stdout is not None
    stdin: IO[bytes] = proc.stdin
    stdout: IO[bytes] = proc.stdout
    state: ProbeState = ProbeState()

    def reader() -> None:
        """Answer ty's server->client requests (per ``mode``) and record the documentSymbol reply."""
        while True:
            message: Message | None = _read(stdout)
            if message is None:
                return
            if "method" in message and "id" in message:  # server->client REQUEST
                state.requests.append(message["method"])
                if message["method"] == "workspace/configuration":
                    items: list[Any] = (message.get("params") or {}).get("items") or [
                        {}
                    ]
                    state.config_items = len(items)
                    if mode == "noconfig":
                        continue  # deliberately leave it unanswered
                    # "crushcfg" mimics Crush's handler: a fixed length-1 array regardless of count.
                    reply: list[Message] = (
                        [{}] if mode == "crushcfg" else [{} for _ in items]
                    )
                    _send(
                        stdin, {"jsonrpc": "2.0", "id": message["id"], "result": reply}
                    )
                else:
                    _send(
                        stdin, {"jsonrpc": "2.0", "id": message["id"], "result": None}
                    )
            elif (
                "id" in message
                and ("result" in message or "error" in message)
                and message["id"] == 3
            ):
                state.replied_at = time.monotonic()
                state.symbols = len(message.get("result") or [])
                state.done = True

    threading.Thread(target=reader, daemon=True).start()
    uri: str = f"file://{root}"
    _send(
        stdin,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": uri,
                "capabilities": caps,
                "workspaceFolders": [{"uri": uri, "name": pathlib.Path(root).name}],
            },
        },
    )
    time.sleep(0.3)
    _send(stdin, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
    furi: str = f"file://{fpath}"
    _send(
        stdin,
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": furi,
                    "languageId": "python",
                    "version": 1,
                    "text": fpath.read_text(),
                }
            },
        },
    )
    started: float = time.monotonic()
    _send(
        stdin,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/documentSymbol",
            "params": {"textDocument": {"uri": furi}},
        },
    )
    while not state.done and time.monotonic() - started < 20:
        time.sleep(0.05)
    got: str = (
        f"ok in {state.replied_at - started:.2f}s — {state.symbols} symbols"
        if state.done
        else f"STILL PENDING after {time.monotonic() - started:.1f}s  <-- gated on the unanswered reply"
    )
    print(f"[{mode:8}] documentSymbol: {got}")
    config: str = (
        f"  (workspace/configuration items={state.config_items})"
        if state.config_items is not None
        else ""
    )
    print(
        f"           ty server->client requests: {state.requests or '(none)'}{config}"
    )
    proc.kill()


def main() -> int:
    """Probe each mode in turn; return 2 on a usage error."""
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    for mode in ("minimal", "rich", "crushcfg", "noconfig"):
        probe(sys.argv[1], sys.argv[2], mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
