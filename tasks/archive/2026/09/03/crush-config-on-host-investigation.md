# Why does host `~/.config/crush` have files? — investigation + decision

**Status:** RESOLVED 2026-09-03 — decision made: **stop persisting** the stack; harvest it at session-end instead. Implementation tracked in `stack-in-session-only-harvest-at-sweep.md`. Archive once that lands.
**Priority:** 6
**Difficulty:** 2

## BLUF

The maintainer noticed files in the host's `~/.config/crush` and expected all crush config to come from the
image, not the host. **Answer: exactly one thing in this repo writes to host `~/.config/crush` — the
`STACK_MOUNT` variable in `client/Makefile:158-159`, which `mkdir -p ~/.config/crush` + `touch
~/.config/crush/stack.md` on the host at `make`-parse time so the diversion stack survives `--rm`.** This is
**by design** (the same host-persistence pattern runClaudeInContainer uses for `~/.claude`), not a stray or a
personalization leak. The actual *configs* (CLAUDE.md, crushrc, commands, reference docs, conventions) are
**baked into the image**, not host-mounted — so the maintainer's instinct ("configs should come from the repo")
is correct; only the **stack** is host-persisted. "Done" here = the maintainer decides whether to keep, relocate,
or stop persisting the stack; no code change unless they ask.

## Context / findings (verified 2026-09-03)

**The one writer to host `~/.config/crush`** — `client/Makefile:158-159`:
```make
STACK_FILE := $(HOME)/.config/crush/stack.md
STACK_MOUNT := $(shell mkdir -p $(HOME)/.config/crush 2>/dev/null; touch $(STACK_FILE) 2>/dev/null; echo "-v $(STACK_FILE):/root/.config/crush/stack.md:Z")
```
`:=` + `$(shell …)` evaluates at Makefile **parse time** (every `make` invocation), and `make` runs on the host —
so merely running any target creates the host `~/.config/crush/` directory and an (initially empty) `stack.md`,
then bind-mounts that one file into the container. The comment there states the rationale: *"the conventions
reference `~/.config/crush/stack.md`; keep it on the HOST so the global-across-repos stack survives the ephemeral
container."* This mirrors `claude-config-layering.md`'s `mkdir -p` inside `$(shell …)` for `~/.claude` — persistence
belongs in a host dir mounted in, not in the `--rm` overlay.

**What does NOT write there:**
- `PERSONAL_MOUNT` (`client/Makefile:152-153`) touches `$(HOME)/.ai-coding-conventions.personal.md` — a **dotted file in
  `$HOME`**, not under `.config/crush` (it mounts *to* the container's `.config/crush/…` path, but the host file is
  elsewhere). So it adds nothing to host `~/.config/crush`.
- All configs — `CLAUDE.md`, `crushrc`, `commands/`, `reference/`, the blank conventions default — are **`COPY`'d into
  the image** (`client/Dockerfile:121-123` for crushrc; dotfiles for the rest) to `/root/.config/crush/` **inside the
  container**, never onto the host.

**So:** the host `~/.config/crush/stack.md` (+ the dir) is expected and deliberate. If the maintainer sees *other*
files there, they were most likely written by running the `crush` app **directly on the host** (outside this
container), which is independent of this repo.

## The decision (for the maintainer)

Keep as-is (recommended — it's the working cross-repo diversion-stack persistence), or change it. If a change is
wanted, the options and their trade-offs:
1. **Relocate** the host stack file (e.g. `~/.local/state/crush/stack.md` or a repo-adjacent path) — keeps
   persistence, moves it out of `~/.config/crush`. Update the mount + the conventions' `stack.md` path references.
2. **Named volume** instead of a host bind — persists across `--rm` without a visible host file, but hides the
   stack from host inspection/backup (the same trade-off `claude-config-layering.md` rejected for `~/.claude`).
3. **Stop persisting** — drop `STACK_MOUNT`; the diversion stack then lives only in the ephemeral container and is
   lost on exit (defeats its "global-across-repos" purpose).

## Open questions

1. **Keep, relocate, or stop persisting the host stack file?** *Recommend keep — it's deliberate and matches the
   runClaudeInContainer `~/.claude` design; the file is just `stack.md`, not leaked config.* If relocating, which
   path?
2. **Did you see files beyond `stack.md`** in host `~/.config/crush`? If so, list them — anything other than
   `stack.md` is not written by this repo (likely host-run `crush`), and I'll trace whatever you name.
