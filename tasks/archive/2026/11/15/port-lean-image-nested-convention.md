# Port the lean-image-when-nested convention to the Crush conventions: superseded

**Status:** superseded — closed 2026-11-15
**Completed:** 2026-11-15
**Priority:** 4
**Difficulty:** 1
**Created:** 2026-09-10 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §9.2 F15

## What happened

The task (2026-09-10) was to port into `client/entrypoint/dotfiles/.config/crush/CLAUDE.md` the
lean-image default keyed on `NESTED_PODMAN` (`FLAG ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)`),
for downstream projects only. On 2026-09-27 the idea was replaced: image content keys off a
separate opt-in `MINIMAL_IMAGE`, and `NESTED_PODMAN` is run capability only
(github.com/billsix/runClaudeInContainer `tasks/archive/2026/09/27/decouple-minimal-image-from-nested-podman.md`;
its umbrella task closed as superseded on 2026-11-15). The ported conventions already state the
current rule ("Running projects in a nested container": a nested `make image` builds full;
`MINIMAL_IMAGE=1` is the lean opt-in), so nothing is left to port.
