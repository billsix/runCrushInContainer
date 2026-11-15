# Decouple the lean-image signal from NESTED_PODMAN (MINIMAL_IMAGE) — Crush client side

**Status:** complete
**Completed:** 2026-09-27
Created 2026-09-27 (William Emerison Six <billsix@gmail.com>: "NESTED_PODMAN doesn't mean anything
other than let runClaudeInContainer/runCrushInContainer run podman nestedly. A name like MINIMAL_IMAGE
would make more sense."); implemented and verified the same day.

The fleet renamed the overloaded `NESTED_PODMAN` build-content signal (downstream
`FLAG ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)`) to an opt-in **`MINIMAL_IMAGE`**, leaving
`NESTED_PODMAN` meaning only "add the podman-in-podman run flags." For the Crush client this was
doc-only: the client is an excluded sandbox whose image content keys off neither flag, so only the
baked cross-project conventions Crush reads were updated. The substantive fleet work is the
runClaudeInContainer twin (See also).

## Background

The overload bug was found in this repo: the client had keyed `FULL_TOOLCHAIN` off `NESTED_PODMAN`
and silently built a language-server-less client under `make shell NESTED_PODMAN=1`. That was
reverted 2026-09-12 (`tasks/reference/nested-podman-vs-image-content.md`), establishing that a
sandbox's image content is never inferred from the nested launch flag; this task fixed the naming
fleet-wide. Once the inner store moved to disk
(`tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`), a full image built nested fine, so
the lean image became a deliberate opt-in rather than a nested necessity.

## Decisions (2026-09-27, William Emerison Six <billsix@gmail.com>)

1. **Name: `MINIMAL_IMAGE`** (rejected synonym: `LEAN_IMAGE`).
2. **Opt-in, NOT auto-exported.** The sandbox does not set `MINIMAL_IMAGE`; a nested `make image` builds
   FULL unless the user passes `MINIMAL_IMAGE=1`. `NESTED_PODMAN` keeps ONLY its run-capability role.
3. **Sandboxes stay excluded** — the client included. `MINIMAL_IMAGE` is only ever typed on a sandbox
   deliberately, never inferred; the client's own image content stays as-is.
4. **Atomic rename, no deprecated fallback** (the disk-store change had already landed, and only one
   downstream Makefile — `hanoi`, in another repo — actually needed the rename).

## What was done (client side)

- **`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`** now states `NESTED_PODMAN` is run
  capability only and documents `MINIMAL_IMAGE=1` as the opt-in image-content flag for a lean
  export/airgap image, never applied to the sandboxes, pointing at
  `~/.config/crush/reference/nested-podman-design.md`.
- No client `Makefile`/`Dockerfile` change. A grep across the mounted projects' Makefiles found only
  `hanoi` (another repo) keying content off `NESTED_PODMAN`.

## Verification

All `NESTED_PODMAN` mentions in the baked crush `CLAUDE.md` were confirmed to be run-capability, and
the new `MINIMAL_IMAGE` sentence matched the standard. The `hanoi` Makefile behaviour was verified on
the runClaudeInContainer side.

## See also

- `runClaudeInContainer tasks/archive/2026/09/27/decouple-minimal-image-from-nested-podman.md` — the
  substantive fleet rename.
- `tasks/reference/nested-podman-vs-image-content.md` — the original overload bug and its reversion.
- `tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md` — the storage half.
