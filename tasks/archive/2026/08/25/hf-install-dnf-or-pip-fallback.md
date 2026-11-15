# Install `hf` from the official dnf repo when available, else pip

**Status:** complete
**Created:** 2026-08-25 (William Emerison Six <billsix@gmail.com>) · **Completed:** 2026-08-25

Made the `hf` CLI install in `client/entrypoint/02-install-vendor-tools.sh` prefer the official dnf
package (`python3-huggingface-hub`) and fall back to pip when the package is absent or too old to
provide `hf`. Previously the script hard-ran `dnf install -y python3-huggingface-hub`, which failed the
whole `VENDOR_TOOLS=1` build when the package was missing and could silently install a version that ships
only `huggingface-cli`. Verified both branches in real containers.

## Background

`hf` is a vendoring-only tool: installed only when the client image is built with `VENDOR_TOOLS=1`
(`vendor.sh` / `make vendor`), and used by `server/`'s `make pull` to download the GGUF during online
vendoring. It is never in the normal or airgap image, so this path only runs online, which is what makes
a pip fallback acceptable (no airgap-mirror impact). The contract is narrow: `hf` is on PATH afterward.

## What was done

The script tries `dnf install python3-huggingface-hub` and then checks that it actually provided `hf`. On
absence or a too-old package it falls back to pip: `dnf install python3-pip`, then
`python3 -m pip install --break-system-packages huggingface_hub || python3 -m pip install huggingface_hub`.
A final `command -v hf` exits 1 if `hf` is still missing (the real gate); `set -e` aborts on genuine
errors. The stale "single dnf is the gate" header comment was replaced.

The plan's explicit availability probe (`dnf list --available` / `repoquery`) before branching and a
minimum-version pin on the pip install were not implemented; the post-install `command -v hf` check
covers both concerns.

## Decisions (2026-08-25)

1. **Fedora 44 carries the package; RHEL9 does not** (confirmed by the maintainer and by a `ubi9` run), so
   the fallback is a real fix rather than only hardening.
2. **pip mechanism: `--break-system-packages` with a plain-pip fallback**, chosen over a venv or `pipx` for
   simplicity in a disposable, online-only vendoring image. `--break-system-packages` covers Fedora's
   PEP 668 externally-managed Python; the plain retry covers RHEL9's older pip, which doesn't know the
   flag. `dnf install python3-pip` makes the fallback work on a bare RHEL9 host.

## Verification (nested podman)

- `fedora:44`: dnf path; installed `hf` 1.24.0.
- `ubi9` (RHEL9): package absent, fell through to pip; installed `hf` 1.8.0.
- `bash -n`, `shfmt -d`, `shellcheck` all clean.
- An end-to-end `./vendor.sh` run was not recorded here.

## Related

- `client/entrypoint/02-install-vendor-tools.sh`; `client/Dockerfile` (the `VENDOR_TOOLS` ARG dispatch);
  `client/Makefile` (`VENDOR_TOOLS ?= 0`).
- `tasks/archive/2026/08/22/vendor-via-client-image.md`: where `hf` was first baked behind `VENDOR_TOOLS`.
- `tasks/reference/architecture.md`: the offline/airgap vendoring workflow and `hf` flag-gating.
