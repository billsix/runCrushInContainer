# Verify the language servers — the rebuilt Fedora image, then `ty` from `/venv` on the RHEL 9 airgap box

**Status:** blocked — human-gated: needs the maintainer's 22 GB image rebuild on the Linux host and the
RHEL 9 airgap box (both unreachable from the sandbox). Created 2026-09-10 at the archive of
`tasks/archive/2026/09/10/install-language-servers-for-crush.md` (William Emerison Six <billsix@gmail.com> asked for the RHEL 9 test to be its own task).
**Priority:** 3
**Difficulty:** 3
**Blocked on:** the maintainer running step A on the Linux host and step B on the RHEL 9 box.
**Recheck:** `[CONTAINER]` (rebuilt Fedora image) `command -v ty gopls clangd rust-analyzer
bash-language-server glsl_analyzer` → six paths = step A's install half is done; `[RHEL 9 CONTAINER]`
`ty --version` printing `ty 0.0.80` from `/venv/bin/ty` = step B's install half is done. Both, plus a
Python `lsp_symbols` that answers on the airgap project, = cleared; tick the boxes and archive.

## BLUF

The language-server work is implemented and committed: six dnf servers declared in the crushrc for
Fedora, and a commented-out `client/Dockerfile` block that installs the vendored `ty` wheel into a
python3.11 `/venv` for RHEL 9, where no Python LSP is packaged. Both were proven in throwaway
containers, not in the real images. Done means: **(A)** the rebuilt Fedora image starts all six
servers and Crush stops saying "no LSP client handles file" for Python; **(B)** on the RHEL 9 box the
uncommented block builds offline from the vendored wheel and Crush's `lsp_*` tools work on the
Python project that originally complained.

## Context — read first

- `tasks/reference/crush-lsp-integration.md` §4 (the measured capability table, the six crushrc
  lines) and § "RHEL 9" (why a venv, why `ty`, the proof already run). §2 for the four gates if a
  server doesn't start.
- `client/Dockerfile` — the commented-out RHEL 9 block (three lines + `ENV PATH`).
- `client/Makefile` — `TY_VERSION` (0.0.80) and the `vendor` target's wheel download;
  `CRUSH_VENDOR_FLAGS` mounts `client/vendor/wheels` when it exists.
- `tasks/adhoc/verify-language-servers-on-rhel9/` — `lsp_handshake.py` (a stdlib-only LSP `initialize` client),
  `check_fedora_servers.sh`, `check_rhel9_ty.sh`: the throwaway proofs, re-runnable. Moved here from
  the implementing task because this task re-uses them.
- Work record of the implementation: `tasks/archive/2026/09/10/install-language-servers-for-crush.md`.

## Steps

### A — the rebuilt Fedora image `[LINUX HOST]` → `[CONTAINER]`

1. ~~`make -C client image`~~ — **done 2026-09-10** (maintainer: the host build "worked, and it seemed like it pulled everything in").
2. `make -C client shell` with a Python repo mounted **without** a top-level `pyproject.toml`/
   `setup.py`/`.git` at `/work` (the root-marker case that auto-start fails on):
   `command -v ty gopls clangd rust-analyzer bash-language-server glsl_analyzer` → six paths.
3. In `crush`, ask for a symbol in a `.py` file — no "no LSP client handles file"; run the
   `crush_logs` tool and confirm the six servers started (a server that isn't installed logs
   "LSP server not installed" — that would mean a dnf package name drifted).
4. `make -C client format` green (it will also reflow `02-install-vendor-tools.sh` and
   `03-build-crush.sh`, which were already non-conforming before this work — expected).

### B — RHEL 9 airgap box `[ONLINE]` → `[RHEL 9]`

1. `[ONLINE]` `./vendor.sh` — confirm `client/vendor/wheels/ty-0.0.80-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
   exists (13,705,988 bytes). Transport the repo as usual (README "Airgapped rebuild").
2. `[RHEL 9]` in `client/Dockerfile`, swap `FROM` to the RHEL 9 base you use and **uncomment the three
   RHEL 9 lines + `ENV PATH`**. Expect `01-install-base.sh`'s Fedora list not to apply as-is (the block's
   header says which servers RHEL 9 has: `rust-analyzer`, `clangd`, EPEL's `golang-x-tools-gopls`; no
   bash/glsl server) — trim to what the mirror has; that trimming is not this task's job to design, only
   to record.
3. `[RHEL 9]` `make -C client image CRUSH_VENDORED=1` (mounts `vendor/wheels` at `/vendor/wheels`
   automatically). **If pip says "No matching distribution"**, the mount is missing — check
   `make -n image CRUSH_VENDORED=1 | grep wheels` — or the wheel's Python tag needs the
   `python3.11` from AppStream (BaseOS 3.9 is too old).
4. `[RHEL 9 CONTAINER]` `command -v ty` → `/venv/bin/ty`; `ty --version` → `ty 0.0.80`; then open the
   Python project that produced the original complaint and use `lsp_symbols` / `lsp_definition` /
   `lsp_rename` — they answer, and `crush_logs` shows `python` starting.
5. Re-comment the block? No — on the RHEL 9 box's own checkout it stays uncommented; the repo's
   committed Dockerfile keeps it commented (that is the design: one Dockerfile, the variant opt-in).

## Record when done

- [ ] A: six binaries resolve in the rebuilt Fedora image; `crush_logs` shows six servers; the Python
      symbol query answered without the complaint.
- [ ] B: wheel vendored (size ______); RHEL 9 build succeeded offline; `ty 0.0.80` from `/venv`;
      `lsp_*` answered on the airgap project. Base image used: ______. Servers trimmed to: ______.

Then: update `tasks/reference/crush-lsp-integration.md` (§4 "measured in the image" instead of "in a
throwaway"; the RHEL 9 section's proof bullet → "verified on the box, <date>"), `tasks/reference/
architecture.md` verification status, and archive this task.
