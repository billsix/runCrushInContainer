# Install `hf` from the official dnf repo when available, else pip

**Status:** DONE 2026-08-25 (William Emerison Six <billsix@gmail.com>) — see Outcome.
**Priority:** 4
**Difficulty:** 2
**Created:** 2026-08-25 (William Emerison Six <billsix@gmail.com>)

## Outcome (2026-08-25)

Implemented in `client/entrypoint/02-install-vendor-tools.sh` and **verified in real containers** (nested
podman). Logic: try `dnf install python3-huggingface-hub` **and** confirm it actually provides `hf` (an
old package ships only `huggingface-cli`); on absence-or-too-old, fall back to pip —
`dnf install python3-pip` then `python3 -m pip install --break-system-packages huggingface_hub || python3
-m pip install huggingface_hub`. The `--break-system-packages` first-try covers Fedora's PEP-668
externally-managed Python; the plain-pip fallback covers RHEL9's older pip that doesn't know that flag.
The real gate is a final `command -v hf` that `exit 1`s if `hf` is still missing; `set -e` aborts on
genuine errors. The stale "single dnf is the gate" header was replaced.

**Verification (both branches, nested podman):**
- **`fedora:44` → dnf path** — `python3-huggingface-hub` *is* in Fedora's repos; installed `hf` **1.24.0**.
- **`ubi9` (RHEL9) → pip fallback** — package absent, fell through to pip, installed `hf` **1.8.0**.
- Static: `bash -n`, `shfmt -d`, `shellcheck` all clean.

**Open questions resolved:** (1) Fedora 44 *has* the package (dnf path); RHEL9 does *not* (confirmed by
Bill and by the ubi9 run) — so the fallback is a real fix, not just hardening. (2) pip mechanism =
`--break-system-packages` with a plain-pip fallback (chosen over venv/pipx for simplicity in a throwaway,
online-only vendoring image), plus `dnf install python3-pip` so the fallback works on a bare RHEL9 host.

## Goal

Make the `hf` CLI install robust across Fedora versions: **prefer the official dnf package
(`python3-huggingface-hub`) when the enabled repos carry it; fall back to the `pip` package
otherwise.** Today `client/entrypoint/02-install-vendor-tools.sh:21` hard-runs `dnf install -y
python3-huggingface-hub`, which fails the entire `VENDOR_TOOLS=1` image build if that package is
absent from the repos — and, silently worse, could install a version too old to provide the `hf`
command.

## Context

- `hf` is a **vendoring-only** tool: installed only when the client image is built with
  `VENDOR_TOOLS=1` (what `vendor.sh` / `make vendor` do), used by `server/`'s `make pull` to download
  the model GGUF during online vendoring. It is **never** in the normal or airgap image (see the
  script's own header comment) — so this install path only ever runs **online**, which is exactly what
  makes a pip fallback acceptable (no airgap-mirror impact).
- The contract the script must satisfy is narrow: **the `hf` command is on PATH afterward.** The PyPI
  package is `huggingface_hub`; the `hf` entry point exists only in recent releases (the old CLI was
  `huggingface-cli`), so a pip fallback must pull a new-enough version.

## Plan

1. **Probe repo availability, then branch** in `02-install-vendor-tools.sh`. Use an explicit
   availability test — `dnf list --available python3-huggingface-hub` (or `dnf -q repoquery
   python3-huggingface-hub`) returning success — rather than blindly attempting the install, so the
   chosen path is deliberate and loggable.
2. **dnf branch:** `dnf install -y python3-huggingface-hub`, as today. **Caveat, checked right here:**
   even when the package exists, an old Fedora build may ship only `huggingface-cli`, not `hf`; verify
   `hf` actually landed (step 4) and, if not, fall through to pip.
3. **pip branch:** `pip install "huggingface_hub>=<min-with-hf>"` (pin the first version that ships the
   `hf` entry point, not a bare `huggingface_hub`). **Caveat, at this step — PEP 668:** Fedora marks the
   system Python *externally-managed*, so a root `pip install` refuses without
   `--break-system-packages` (alternatives: a throwaway venv, or `pipx`). Pick one and keep it minimal —
   this is a disposable, online-only vendoring image.
4. **Verify + fail loudly:** after whichever branch, assert `command -v hf` (and ideally `hf --version`)
   and `exit 1` with a clear message if `hf` is missing. This preserves the script's "its own exit
   status is the gate" property — now the gate is "dnf-or-pip, and `hf` must exist," so **accumulate the
   outcome** instead of relying on a single dnf's exit (per this repo's multi-step-gate convention).

## Verify

- `cd client && make image VENDOR_TOOLS=1` (nested: add `--cgroups=disabled --network=host` to the inner
  run), then `hf --version` inside the image → works.
- Exercise **both** branches: the dnf path as-is, and the pip path by simulating repo-absence (a build
  arg, a temporary repoquery-miss, or a base where the package is genuinely missing).
- End-to-end: `./vendor.sh` still completes (it builds the `VENDOR_TOOLS` image and runs `make pull`).

## Open questions

1. **Does Fedora 44's official repo currently carry `python3-huggingface-hub`, and is its version new
   enough to provide the `hf` command?** This is the whole motivation and it sets the real priority: if
   the package is absent or too old *today*, the dnf path is already broken and this is a bug fix (raise
   priority); if it works today, this is portability hardening for other Fedora versions (leave at P4).
   **Recommend** running `dnf info python3-huggingface-hub` on the target base image before implementing.
2. **Which pip mechanism for the fallback** — plain `pip install --break-system-packages`, a venv, or
   `pipx`? **Recommend** `--break-system-packages` (simplest; this is a disposable, online-only vendoring
   image, not a durable environment).

## Cross-links

- `client/entrypoint/02-install-vendor-tools.sh` — the script to change (currently line 21).
- `client/Dockerfile` (the `VENDOR_TOOLS` ARG dispatch) · `client/Makefile` (`VENDOR_TOOLS ?= 0`).
- `tasks/reference/architecture.md` — the offline/airgap source-vendoring workflow and `hf` flag-gating.
