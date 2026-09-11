# Nested-podman signal is inherited, not typed — doc cleanup

**Status:** proposed — needs go-ahead
**Priority:** 4
**Difficulty:** 2

## BLUF

`NESTED_PODMAN=1` is set exactly once, at the outermost `make -C client shell
NESTED_PODMAN=1` host launch, and from there it is inherited automatically by every nested
`make` the agent runs — because every Makefile declares `NESTED_PODMAN ?= 0` and GNU
make's `?=` respects a value already in the environment. So the agent never needs to type
`NESTED_PODMAN=1` on a `make image` / `make shell` command; the client's lean-image
selection and the podman-in-podman store already resolve correctly from a plain
invocation. The docs still imply the agent should pass the flag. **Done = the agent-facing
conventions reflect the auto-inheritance; no Makefile change.**

## Context

**Repo shape:** there is no top-level Makefile — all nested-podman machinery lives in
`client/Makefile`; the outermost host launch is `make -C client shell NESTED_PODMAN=1`.

**Read first**
- `client/entrypoint/dotfiles/.config/crush/CLAUDE.md` — the conventions baked into the
  container (`/root/.config/crush/CLAUDE.md`); section "## Running projects in a nested
  container" (~L294-312). Primary agent-facing doc to fix.
- Root `CLAUDE.md` — "Nested = the minimal image, automatically" (~L60-66) and the
  nested references at ~L125 and ~L277 (mostly keep).
- `tasks/reference/nested-podman-design.md` — "Operating it — the rules that bite",
  "The depth caveat — podman-in-podman-in-podman", "Detecting it inside the container".
- Baked reference docs with run-flag notes:
  `client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md` and
  `.../sandbox-capability-map.md`.

**Current state / mechanism (verified 2026-09-11 in a live nested session)**
- `client/Makefile:261` always passes `-e NESTED_PODMAN=$(NESTED_PODMAN)` on `make shell`;
  the device/cap/tmpfs block (`client/Makefile:202-217`) is added only under
  `NESTED_PODMAN=1`.
- `client/Makefile:37` — `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` — and
  `client/Makefile:147` — `PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)`
  — both key off the same signal. `NESTED_PODMAN ?= 0` (`client/Makefile:202`) means an
  env-provided value wins.
- **Proof:** from a runClaude session carrying the signal, `make -C client` resolved
  `NESTED_PODMAN=1 → FULL_TOOLCHAIN=0, PODMAN_RUN_FLAGS=[--cgroups=disabled]` with **no
  flag typed**; with `NESTED_PODMAN` unset it reverted to `FULL_TOOLCHAIN=1`, empty flags
  (the host case, which builds the full ~22 GB image).

**Decision (William Emerison Six <billsix@gmail.com>, 2026-09-11)**
- Scope **(a), doc-cleanup only**. No Makefile change.
- Rejected scope (b) — auto-detecting nested from a `/dev/fuse` probe in the Makefile —
  because `/dev/fuse` exists on most bare Linux **hosts** too; it would false-positive and,
  via the `FULL_TOOLCHAIN` coupling, silently build the lean image on a normal host
  `make image`. The env-var + `?=` inheritance already detects correctly.

**Boundaries to preserve**
- `make -C client shell NESTED_PODMAN=1` at the outermost host launch is the one correct
  human touch — keep it documented.
- Keep runCrush's real nested constraints: inner runs need **both** `--cgroups=disabled`
  **and** `--network=host`; the podman-in-podman-in-podman depth caveat (the client is
  itself often run inside a runClaude sandbox); and the `FULL_TOOLCHAIN` lean/full split.
- Do **not** bake `ENV NESTED_PODMAN=1` into the image; note here it is redundant anyway
  (the runtime `-e NESTED_PODMAN=$(NESTED_PODMAN)` at `client/Makefile:261` would override
  it on every `make shell`).

## Work

1. **`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, "## Running projects in a nested
   container":** trim any implication that the agent passes `NESTED_PODMAN=1` to
   nested/project make commands. State plainly: the signal is inherited from the outermost
   `make -C client shell NESTED_PODMAN=1` launch via `?=`, so **run plain `make image` /
   `make shell`**; the flag is needed only at the outermost host launch. Keep the
   `$NESTED_PODMAN` env-var detection note and the `test -e /dev/fuse && podman info`
   probe; keep the "both `--cgroups=disabled` and `--network=host`" requirement for inner
   runs.
2. **Add the "don't bake it into the image" note** (one line): the signal must stay coupled
   to the launch flags, and `-e NESTED_PODMAN=$(NESTED_PODMAN)` would override a baked `ENV`
   anyway.
3. **Consistency sweep** of root `CLAUDE.md` and the reference/baked docs listed above —
   keep host-launch/design/`FULL_TOOLCHAIN`/depth content; fix only agent-facing "type the
   flag downstream" phrasing.
4. **Stage** the doc edits.

## Verification

- `grep -rn 'NESTED_PODMAN=1'` over the touched docs; every remaining occurrence is either
  the outermost host-launch command or an explanatory mention — not an instruction to the
  agent to pass it to a nested/project target.
- `git status` shows **only doc files** changed (no Makefile), confirming scope (a).

## Sibling

runClaudeInContainer carries the twin task, `tasks/nested-podman-signal-inherited-doc-cleanup.md`.
