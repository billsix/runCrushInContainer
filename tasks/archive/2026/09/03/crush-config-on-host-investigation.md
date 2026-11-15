# Why does host `~/.config/crush` have files? — investigation + decision

**Status:** complete
**Completed:** 2026-09-03

## What this did

Investigated why the host's `~/.config/crush` held files when all Crush config was expected to come
from the image. Found that exactly one thing in this repo wrote there: the `STACK_MOUNT` variable in
`client/Makefile`, which persisted the diversion stack across `--rm`. The maintainer then decided to
stop persisting the stack; that change was implemented in
`tasks/archive/2026/09/03/stack-in-session-only-harvest-at-sweep.md`.

## Findings (verified 2026-09-03)

- **The one writer:** `client/Makefile` had
  ```make
  STACK_FILE := $(HOME)/.config/crush/stack.md
  STACK_MOUNT := $(shell mkdir -p $(HOME)/.config/crush 2>/dev/null; touch $(STACK_FILE) 2>/dev/null; echo "-v $(STACK_FILE):/root/.config/crush/stack.md:Z")
  ```
  `:=` + `$(shell …)` runs at Makefile parse time on the host, so any `make` invocation created
  `~/.config/crush/` and an empty `stack.md`, then bind-mounted that file in. It was deliberate,
  mirroring runClaudeInContainer's host-persisted `~/.claude`, not a stray or a personalization leak.
- **What did not write there:** `PERSONAL_MOUNT` touches `$(HOME)/.ai-coding-conventions.personal.md`
  (a dotfile in `$HOME`, mounted to the container's `.config/crush/` path). All configs (`CLAUDE.md`,
  `crushrc`, `commands/`, `reference/`, the blank conventions default) are `COPY`'d into the image's
  `/root/.config/crush/`, never onto the host.
- Any other files in host `~/.config/crush` would come from running `crush` directly on the host,
  independent of this repo. Whether the maintainer saw files beyond `stack.md` was not recorded.

## Decision (maintainer, 2026-09-03)

Of the options considered (keep; relocate to e.g. `~/.local/state/crush/stack.md`; a named volume,
rejected for hiding the stack from host inspection as runClaudeInContainer did for `~/.claude`; stop
persisting), the maintainer chose **stop persisting**: the stack is purely in-session, and its
cross-session value is harvested into task/reference docs at the session-end sweep. The agent had
recommended keeping it.
