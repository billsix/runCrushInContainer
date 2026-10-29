#!/usr/bin/env python3
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
"""Verification harness for the egress patch/flag system.

(tasks/archive/2026/08/29/implement-egress-patch-flags.md) -- proves that the patches in
``client/patches/`` apply cleanly in ANY flag combination, reverse cleanly, and that the
key combinations compile.

WHEN TO RUN: on every CRUSH_TAG bump -- after regenerating the vendored tree (./vendor.sh or
client/entrypoint/vendor/vendor-crush.sh) and re-porting the patches to the new tag -- and
after adding or editing any patch in ``client/patches/``. Keep ``ALL`` below in the same
canonical order as ``entrypoint/03-build-crush.sh``.

Method, per combination:
    1. forward-apply the selected patches in the canonical order (the same order
       entrypoint/03-build-crush.sh uses), with ``git apply --unidiff-zero`` (several patches
       use zero-context hunks because they edit the same files);
    2. optionally ``GOPROXY=off go build -mod=vendor`` (the build combos below);
    3. reverse-apply in reverse order (``git apply --unidiff-zero -R``);
    4. assert the tree is byte-identical to the pristine baseline (sha256 manifest over every
       file any patch touches).
A failure at any step aborts -- the combination that broke is the last one echoed.

Combinations tested: every single patch alone; none; all; the audit-default set; the full
power set of each group of patches that share files; and a fixed set of pseudo-random mixes.
Only a subset is compiled (builds cost ~30s each; applying is what can conflict, and the
per-patch builds were done when each patch was authored).

Run from the repo root; needs the vendored tree at ``client/vendor/crush``.
``--list`` prints the combination sequence and does nothing else (the dry run used to prove
this port matches the former bash).

Invoked through the ``tools/sweep_egress_patch_combos.sh`` shim (ported from that bash
2026-10-29, William Emerison Six <billsix@gmail.com>; the combination sequence is identical --
the former bash enumerated power sets with ``(1 << n)`` bit tests and a hand-rolled integer
hash, both of which read far more clearly as Python).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
CRUSH: Path = REPO_ROOT / "client" / "vendor" / "crush"
PATCHES: Path = REPO_ROOT / "client" / "patches"

# Canonical application order -- keep identical to entrypoint/03-build-crush.sh.
ALL: list[str] = [
    "crush-at-import.patch",
    "crush-shell-history.patch",
    "crush-no-update-check.patch",
    "no-telemetry.patch",
    "no-update-providers-cmd.patch",
    "no-web-tools.patch",
    "no-sourcegraph.patch",
    "no-google-provider.patch",
    "no-bedrock-aws.patch",
    "no-azure.patch",
    "no-openrouter.patch",
    "no-vercel.patch",
    "no-hyper.patch",
    "no-copilot.patch",
]

# The audit-default set (flags at their defaults: the two feature patches -- at-import and
# shell-history -- ON via Makefile, web-tools + sourcegraph kept, everything else patched out).
DEFAULT: list[str] = [
    "crush-at-import.patch",
    "crush-shell-history.patch",
    "crush-no-update-check.patch",
    "no-telemetry.patch",
    "no-update-providers-cmd.patch",
    "no-google-provider.patch",
    "no-bedrock-aws.patch",
    "no-azure.patch",
    "no-openrouter.patch",
    "no-vercel.patch",
    "no-hyper.patch",
    "no-copilot.patch",
]

# Combinations that also get compiled.
BUILD_COMBOS: list[str] = [" ".join(DEFAULT), " ".join(ALL), ""]


def run(cmd: list[str], *, cwd: Path, env_extra: dict[str, str] | None = None) -> None:
    """Run ``cmd`` in ``cwd`` and raise ``subprocess.CalledProcessError`` on failure (abort-on-error)."""
    env: dict[str, str] | None = None
    if env_extra is not None:
        env = dict(os.environ)
        env.update(env_extra)
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True)


def touched_files() -> list[str]:
    """Return every file any patch touches, sorted and deduped (the sha256-manifest scope).

    Reads the ``diff --git a/<p> b/<p>`` headers, the same set the former bash grepped out.
    """
    files: set[str] = set()
    for patch in sorted(PATCHES.glob("*.patch")):
        for line in patch.read_text(errors="replace").splitlines():
            if line.startswith("diff --git "):
                rest: str = line[len("diff --git ") :].removeprefix("a/")
                files.add(rest.split(" b/", 1)[0])
    return sorted(files)


def manifest(touched: list[str]) -> str:
    """Return a sha256 line per touched file (``ABSENT`` for files a patch adds that aren't present yet)."""
    lines: list[str] = []
    for rel in touched:
        path: Path = CRUSH / rel
        if path.exists():
            digest: str = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {rel}")
        else:
            lines.append(f"ABSENT  {rel}")
    return "\n".join(lines)


def in_order(selected: set[str]) -> str:
    """Return ``selected`` sorted into ALL's canonical order, as a leading-space-joined string.

    The leading space is deliberate -- it reproduces the former bash ``in_order`` verbatim,
    so the ``== combo`` lines stay byte-identical.
    """
    out: str = ""
    for patch in ALL:
        if patch in selected:
            out += f" {patch}"
    return out


class Sweep:
    """Applies/reverses patch combinations against the vendored crush tree and checks restoration."""

    def __init__(self, list_only: bool) -> None:
        self.list_only: bool = list_only
        self.count: int = 0
        self.touched: list[str] = touched_files()
        self.baseline: str = "" if list_only else manifest(self.touched)

    def apply_combo(self, combo: str) -> None:
        """Forward-apply each patch in ``combo`` (space-separated, canonical order)."""
        for patch in combo.split():
            run(["git", "apply", "--unidiff-zero", str(PATCHES / patch)], cwd=CRUSH)

    def reverse_combo(self, combo: str) -> None:
        """Reverse-apply ``combo``'s patches in reverse order."""
        for patch in reversed(combo.split()):
            run(
                ["git", "apply", "--unidiff-zero", "-R", str(PATCHES / patch)],
                cwd=CRUSH,
            )

    def check_clean(self, combo: str) -> None:
        """Assert the touched tree is byte-identical to the pristine baseline, else abort."""
        now: str = manifest(self.touched)
        if now != self.baseline:
            print(f"TREE NOT RESTORED after: {combo}", file=sys.stderr)
            raise SystemExit(1)

    def run_combo(self, combo: str, build: bool) -> None:
        """Run one combination: echo it, then (unless --list) apply, optionally build, reverse, verify."""
        mode: str = "build" if build else "nobuild"
        print(f"== combo [{mode}]: {combo if combo else '<none>'}")
        self.count += 1
        if self.list_only:
            return
        self.apply_combo(combo)
        if build:
            run(
                ["go", "build", "-mod=vendor", "-o", "/dev/null", "."],
                cwd=CRUSH,
                env_extra={"GOPROXY": "off", "GOFLAGS": ""},
            )
        self.reverse_combo(combo)
        self.check_clean(combo)

    def group_powerset(self, members: list[str]) -> None:
        """Run the full power set of ``members``, with the other DEFAULT patches fixed on, all built.

        These are the combinations where the file-sharing patches' zero-context hunks could interact.
        """
        base: set[str] = {p for p in DEFAULT if p not in members}
        for i in range(1 << len(members)):
            selected: set[str] = set(base)
            for j, member in enumerate(members):
                if (i >> j) & 1:
                    selected.add(member)
            self.run_combo(in_order(selected), build=True)

    def run_all(self) -> int:
        """Run the whole sweep in the former bash's order; return the exit status."""
        # 1. every single patch alone (apply/reverse only -- each was compiled when authored)
        for patch in ALL:
            self.run_combo(patch, build=False)

        # 2. build combos: default / all / none
        for combo in BUILD_COMBOS:
            self.run_combo(combo, build=True)

        # 3. power sets of the file-sharing groups (others at the default set), all built
        self.group_powerset(
            ["no-web-tools.patch", "no-sourcegraph.patch", "no-hyper.patch"]
        )
        self.group_powerset(["no-google-provider.patch", "no-bedrock-aws.patch"])
        self.group_powerset(["no-telemetry.patch", "no-update-providers-cmd.patch"])

        # 4. pseudo-random mixes (fixed seeds -> reproducible), apply/reverse only
        for seed in (3, 7, 11, 19, 42, 57, 99, 123, 200, 255):
            selected = {
                p for j, p in enumerate(ALL) if (seed * (j + 3) * 2654435761 >> 7) & 1
            }
            self.run_combo(in_order(selected), build=False)

        if self.list_only:
            print(f"SWEEP LIST: {self.count} combinations")
        else:
            print(
                f"SWEEP OK: {self.count} combinations applied, reversed, and verified byte-identical"
            )
        return 0


def main(argv: list[str]) -> int:
    list_only: bool = "--list" in argv
    return Sweep(list_only).run_all()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
