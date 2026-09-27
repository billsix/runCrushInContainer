# Decouple the lean-image signal from NESTED_PODMAN (MINIMAL_IMAGE) — Crush client side

**Status:** DONE 2026-09-27 — doc-only for the client (it is an excluded sandbox). The fleet renamed the
overloaded `NESTED_PODMAN` build-content signal to an opt-in `MINIMAL_IMAGE`; on the client that meant
updating the baked cross-project conventions Crush reads, so downstream builds are taught the right
signal. The client's own image content is keyed off neither flag and did not change.
**Priority:** 3. **Difficulty:** 2 (doc-only here; the substantive fleet work is the runClaude twin).
**Created:** 2026-09-27 (William Emerison Six <billsix@gmail.com>: "NESTED_PODMAN doesn't mean anything
other than let runClaudeInContainer/runCrushInContainer run podman nestedly. A name like MINIMAL_IMAGE
would make more sense."); implemented and verified the same day.

## BLUF

Downstream projects had keyed their lean-vs-full image off `NESTED_PODMAN`
(`FLAG ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)`), overloading one variable with two unrelated jobs —
run-time nested capability and build-time image content. The fleet renamed the build-content meaning to
a dedicated, opt-in **`MINIMAL_IMAGE`** and left `NESTED_PODMAN` meaning only "add the podman-in-podman
run flags." For the **Crush client** this task was doc-only: the client is a sandbox (built on the host,
launched nested), so it never keys its own content off either flag, but the **baked cross-project
`CLAUDE.md`** it ships to Crush (`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`) was updated to
state `NESTED_PODMAN` is run-capability only and to document `MINIMAL_IMAGE=1` as the opt-in
image-content flag — so a nested downstream `make image` a Crush session runs uses the right convention.

## Background — the client is where the overload bug was found

This rename exists because of a bug in this repo. The client had keyed a `FULL_TOOLCHAIN` flag off
`NESTED_PODMAN`, so it silently built a **language-server-less client** whenever
`make shell NESTED_PODMAN=1` was typed (the flag was meant to be run capability, not image content).
That was reverted 2026-09-12 (`tasks/reference/nested-podman-vs-image-content.md` § "The two meanings of
`NESTED_PODMAN`"), which established the rule that **a sandbox's image content is never inferred from the
nested launch flag**. That reversion fixed the client but left the fleet's downstream naming still
overloaded; this task fixed the naming everywhere. It was also entangled with the storage change
(`tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`): once the inner store moved to disk and
the RAM ceiling was gone, a full image built nested fine, so the lean image became a deliberate opt-in
rather than a nested necessity.

## What was decided (2026-09-27, William Emerison Six <billsix@gmail.com>)

1. **Name: `MINIMAL_IMAGE`** (rejected synonym: `LEAN_IMAGE`).
2. **Opt-in, NOT auto-exported.** The sandbox does not set `MINIMAL_IMAGE`; a nested `make image` builds
   FULL unless the user passes `MINIMAL_IMAGE=1`. `NESTED_PODMAN` keeps ONLY its run-capability role.
3. **Sandboxes stay excluded** — the client included. `MINIMAL_IMAGE` is only ever typed on a sandbox
   deliberately, never inferred; the client's own image content stays as-is.
4. **Atomic rename, no deprecated fallback** (the disk-store change had already landed, and only one
   downstream Makefile — `hanoi`, in another repo — actually needed the rename).

## What was implemented (client side)

- **`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`** (the cross-project conventions baked in for
  Crush): now states `NESTED_PODMAN` is run capability only and documents `MINIMAL_IMAGE=1` as the
  opt-in image-content flag for a lean export/airgap image, keyed nowhere on `NESTED_PODMAN`, never
  applied to the sandboxes themselves; it points at `~/.config/crush/reference/nested-podman-design.md`.
- **No client `Makefile`/`Dockerfile` change** — the client is an excluded sandbox, so its image content
  is not flag-inferred. This repo has **no downstream Makefile** that keyed content off `NESTED_PODMAN`
  (the re-sync grep across `/foo/opt/*/Makefile` found only `hanoi`, in another repo).

## Verification

Doc-only on the client, so verification was that the note is present and accurate — `NESTED_PODMAN`
mentions in the baked crush `CLAUDE.md` are all run-capability, and the new `MINIMAL_IMAGE` sentence
matches the standard. The fleet Makefile behavior (`hanoi`: full by default, lean on `MINIMAL_IMAGE=1`,
`NESTED_PODMAN=1` no longer affecting content) was verified on the runClaude side.

## See also

- `runClaudeInContainer tasks/archive/2026/09/27/decouple-minimal-image-from-nested-podman.md` — the
  substantive fleet rename (name decision, the `hanoi` Makefile, the reference-doc reframe, the personal
  template addition). This client doc is the runCrush-side record of the same task.
- `tasks/reference/nested-podman-vs-image-content.md` — the original `FULL_TOOLCHAIN`-off-`NESTED_PODMAN`
  overload bug in this client and its reversion (the origin of the "sandboxes excluded" rule).
- `tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md` — the storage half; the disk store is
  what made the lean image optional rather than a nested necessity.
