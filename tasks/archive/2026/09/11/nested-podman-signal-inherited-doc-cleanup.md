# Nested-podman signal is inherited, not typed — doc cleanup

**Status:** complete
**Completed:** 2026-09-11

## What this did

Made the agent-facing docs say what the Makefiles already did: `NESTED_PODMAN=1` is set once, at the
outermost `make -C client shell NESTED_PODMAN=1` host launch, and every nested `make` the agent runs
inherits it, because each Makefile declares `NESTED_PODMAN ?= 0` and GNU make's `?=` respects an
environment value. The agent runs plain `make image` / `make shell` and never passes the flag
downstream. Doc-only; no Makefile change (commit `cd1591f`).

## What changed

- `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, "Running projects in a nested container": states
  the signal is inherited via `?=` and that the agent must never pass `NESTED_PODMAN=1` on a downstream
  command (the outermost host launch is the user's). The `$NESTED_PODMAN` env-var detection note, the
  `test -e /dev/fuse && podman info` probe, and the "both `--cgroups=disabled` and `--network=host`"
  requirement for inner runs were kept.
- `tasks/reference/nested-podman-design.md` (and its baked copy
  `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md`): a paragraph on the
  inheritance, and that the signal is deliberately not baked as `ENV NESTED_PODMAN=1`. A baked value
  would falsely advertise nested support on a plain launch without `/dev/fuse`/caps, and the runtime
  `-e NESTED_PODMAN=$(NESTED_PODMAN)` on `make shell` overrides it anyway.
- Root `CLAUDE.md`: the same "inherited, not baked" note in the nested-image bullet.

## Decisions

- **Scope (a), doc cleanup only** (William Emerison Six <billsix@gmail.com>, 2026-09-11).
- **Rejected (b), auto-detecting nested from a `/dev/fuse` probe in the Makefile:** `/dev/fuse` exists on
  most bare Linux hosts too, so it would false-positive and, through the then-current `FULL_TOOLCHAIN`
  coupling, silently build the lean image on a normal host `make image`. The env var + `?=` already
  detects correctly.

Superseded: the `FULL_TOOLCHAIN` flag (then `?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)`) was removed
2026-09-12; the client is always the full toolchain and `NESTED_PODMAN` is run-time only
(`tasks/reference/nested-podman-vs-image-content.md`).

## Verification

The mechanism was checked 2026-09-11 in a live nested session: with the signal in the environment,
`make -C client` resolved `NESTED_PODMAN=1` and `PODMAN_RUN_FLAGS=--cgroups=disabled` with no flag
typed; with it unset both reverted to the host defaults. The commit touched docs only.

## Related

runClaudeInContainer carries the twin task, `tasks/archive/2026/09/11/nested-podman-signal-inherited-doc-cleanup.md`.
