#!/usr/bin/env python3
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# Triage every vendored Go module for network capability — phase 1 of the dependency
# network audit (tasks/reference/dependency-network-audit.md; work record:
# tasks/archive/2026/08/29/audit-dependency-network-egress.md).
#
# WHEN TO RUN: after any `make vendor` regeneration, and on EVERY CRUSH_TAG bump —
# diff the new table against the reference doc's §3 to find modules that appeared,
# vanished, or changed tier, then deep-audit the changes per the reference doc's method.
#
# Reads client/vendor/crush/vendor/modules.txt for the module list, then scans each
# module's vendored .go source for cheap network signals:
#   - imports of net/http, net (raw sockets), crypto/tls, grpc, websocket, etc.
#   - client-side call sites (http.Get/Post/NewRequest, net.Dial, grpc.NewClient, ...)
#   - hardcoded http(s):// host literals (excluding the ubiquitous XML-namespace and
#     license-URL strings, which are not egress)
#
# Output: a markdown table to stdout, one row per module — module, version, signal
# summary, and a coarse NETWORK / maybe / no-network classification. The NETWORK and
# maybe rows are the work-list for the phase-2 deep audit; the table itself becomes
# the basis of the reference doc's triage section. Read-only: mutates nothing.
#
# Run from the repo root:  python3 tasks/adhoc/audit-dependency-network-egress/triage_modules.py
#
# The classification is deliberately coarse and errs toward flagging: importing
# net/http may mean an HTTP *client* (egress-relevant) or just status-code constants
# (irrelevant). Phase 2 reads the flagged modules' source to tell those apart —
# per the task doc, don't trust this grep, verify at source.

import os
import re
import sys
from collections import defaultdict

VENDOR = "client/vendor/crush/vendor"

# Signal -> regex, checked against whole-file text. Import signals match the quoted
# import path; call signals match client-side constructor/call names.
IMPORT_SIGNALS = {
    "net/http": re.compile(r'"net/http"'),
    "net(raw)": re.compile(r'"net"'),
    "crypto/tls": re.compile(r'"crypto/tls"'),
    "grpc": re.compile(r'"google\.golang\.org/grpc[/"]'),
    "x/net": re.compile(r'"golang\.org/x/net/(http2|proxy|websocket)'),
    "websocket": re.compile(r'"(github\.com/coder/websocket|github\.com/gorilla/websocket|nhooyr\.io/websocket)'),
    "net/smtp": re.compile(r'"net/smtp"'),
}
CALL_SIGNALS = {
    "http-client": re.compile(r'\bhttp\.(Get|Post|PostForm|Head|NewRequest|DefaultClient|Client\{)'),
    "dial": re.compile(r'\b(net|tls)\.(Dial|DialTimeout|Dialer)\b'),
    "grpc-dial": re.compile(r'\bgrpc\.(Dial|DialContext|NewClient)\b'),
}
# Hardcoded endpoint literals. Exclude the noise classes that are provably not egress:
# XML namespaces, schema/license/doc URLs, and example.com placeholders.
URL_RE = re.compile(r'https?://[a-zA-Z0-9._-]+')
URL_NOISE = re.compile(
    r'(www\.w3\.org|schemas\.|xmlns|example\.(com|org|net)|opensource\.org|'
    r'apache\.org/licenses|creativecommons\.org|golang\.org/(ref|doc)|pkg\.go\.dev|'
    r'github\.com/[^"]*(issues|blob|tree|pull|releases|#)|en\.wikipedia\.org)'
)


def module_dirs(vendor: str) -> dict[str, str]:
    """modules.txt '# <module> <version>' lines -> {module_path: version}."""
    mods = {}
    with open(os.path.join(vendor, "modules.txt")) as f:
        for line in f:
            if line.startswith("# "):
                parts = line[2:].split()
                # '# <module> <version>' (skip '## explicit' etc., handled by startswith)
                if len(parts) >= 2 and not parts[0].startswith("#"):
                    mods[parts[0]] = parts[1]
    return mods


def scan_module(root: str) -> tuple[dict[str, int], set[str]]:
    """Return ({signal: file-hit-count}, {non-noise URL hosts}) for one module tree."""
    hits: dict[str, int] = defaultdict(int)
    hosts: set[str] = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".go"):
                continue
            try:
                text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for name, rx in {**IMPORT_SIGNALS, **CALL_SIGNALS}.items():
                if rx.search(text):
                    hits[name] += 1
            # URLs only from non-comment lines, and only when inside a string
            # literal ("..." or `...`) — a URL in a doc comment is not egress.
            for line in text.splitlines():
                s = line.lstrip()
                if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
                    continue
                for m in URL_RE.finditer(line):
                    before = line[: m.start()]
                    if before.count('"') % 2 == 1 or before.count("`") % 2 == 1:
                        url = m.group(0)
                        if not URL_NOISE.search(url):
                            hosts.add(url.split("//", 1)[1])
    return hits, hosts


def classify(hits: dict[str, int], hosts: set[str]) -> str:
    """Coarse tiers, most to least suspicious:
    NETWORK          client-side call sites, or wire-protocol imports (grpc/websocket/
                     smtp/x-net), or endpoint literals in string constants
    imports-only     imports net/http, net, or crypto/tls but no client call sites and
                     no endpoint strings (often just status codes / server / types)
    url-strings-only URL literals in strings but no network code at all (templates,
                     help text) — near-certainly inert, one look in phase 2
    no-network       none of the above"""
    strong = {"http-client", "dial", "grpc-dial", "grpc", "websocket", "net/smtp", "x/net"}
    if any(hits.get(s) for s in strong):
        return "NETWORK"
    if hosts:
        return "NETWORK" if hits else "url-strings-only"
    if hits:
        return "imports-only"
    return "no-network"


def main() -> int:
    if not os.path.isdir(VENDOR):
        print(f"error: {VENDOR} not found — run from the repo root, after `make vendor`", file=sys.stderr)
        return 1
    mods = module_dirs(VENDOR)
    rows = []
    for mod, ver in sorted(mods.items()):
        root = os.path.join(VENDOR, mod)
        if not os.path.isdir(root):
            rows.append((mod, ver, "MISSING-DIR", "", ""))
            continue
        hits, hosts = scan_module(root)
        sig = " ".join(f"{k}:{v}" for k, v in sorted(hits.items()))
        host_s = " ".join(sorted(hosts)[:8]) + (" …" if len(hosts) > 8 else "")
        rows.append((mod, ver, classify(hits, hosts), sig, host_s))

    order = {"NETWORK": 0, "maybe": 1, "MISSING-DIR": 2, "no-network": 3}
    rows.sort(key=lambda r: (order.get(r[2], 9), r[0]))
    counts = defaultdict(int)
    for r in rows:
        counts[r[2]] += 1
    print(f"# Triage of {len(rows)} vendored modules — " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    print()
    print("| module | version | tier | signals (files hit) | non-noise URL hosts |")
    print("|---|---|---|---|---|")
    for mod, ver, tier, sig, host_s in rows:
        print(f"| {mod} | {ver} | {tier} | {sig} | {host_s} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
