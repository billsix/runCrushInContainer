# Diversion stack is IN-SESSION only — stop host-persisting it; harvest it at session-end instead

**Status:** complete
**Completed:** 2026-09-03

## What this did

Stopped creating and mounting the diversion stack (`~/.config/crush/stack.md`) on the host. The stack
now lives only inside the ephemeral container and dies with it; the session-end sweep consults it and
folds any still-open work into the persisted task/reference docs. This answered the open decision in
`tasks/archive/2026/09/03/crush-config-on-host-investigation.md`, which had found the host `STACK_MOUNT`.

## Decision (maintainer, 2026-09-03)

The stack's purpose is purely in-session: it is a depth gauge for the current diversion. A raw stack
file persisted across sessions goes stale; what matters between sessions is what work is still in
flight and why, and that belongs in versioned task/reference docs, not a scratch file on the host.

## Changes

1. **`client/Makefile`**: removed `STACK_FILE` and `STACK_MOUNT` and dropped `$(STACK_MOUNT)` from the
   run flags. The stack sits at `/root/.config/crush/stack.md` on the `--rm` overlay, created by the
   diversion-stack commands as needed.
2. **`client/entrypoint/dotfiles/.config/crush/CLAUDE.md`**, diversion-stack section: restated the stack
   as in-session only, discarded at exit.
3. **Same file, session-end sweep**: added a step to consult the stack at session end and record any
   open diversion's remaining work and reason in the relevant task doc (or a reference doc for durable
   knowledge).
4. **`client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md`**: removed the host
   `stack.md` mount row and noted the stack is container-only.

## Verification

The planned check was: `make -n shell` shows no `-v …/stack.md` mount and no parse-time
`mkdir …/.config/crush`. `client/Makefile` contains no `STACK` variable today; the run of that check
and of a fresh-session test was not recorded.
