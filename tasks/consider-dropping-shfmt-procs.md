# Consider dropping shfmt and procs instead of vendoring upstream binaries

**Status:** proposed — needs go-ahead
**Priority:** 7
**Difficulty:** 2

## BLUF
The Fedora 45 upgrade kept `shfmt` and `procs` working by fetching their upstream
release binaries in `client/entrypoint/01b-install-binary-tools.sh` (both were
dropped from F45's repos). That adds a maintenance cost — pinned versions to bump,
a build-time network fetch from GitHub, and a bespoke script outside the clean
`dnf install` list. **Reconsider whether these two dev conveniences are worth it,
or whether they should just be dropped from the image.** "Done" = a decision:
keep the binary fetch, or remove `01b-install-binary-tools.sh` + its Dockerfile
layer.

## Context
Raised by William Emerison Six <billsix@gmail.com>, 2026-11-06, during the F45
upgrade (`tasks/archive/.../upgrade-to-fedora-45.md`). The base list is
"batteries-included" on purpose, so this is a judgement call, not an obvious cut.

What dropping each would cost:
- **shfmt** (shell formatter) — nothing else in the image formats shell;
  `ShellCheck` (still packaged) covers shell *linting* but not formatting. Dropping
  it means no in-image shell auto-format.
- **procs** (modern `ps`) — `procps-ng` (`ps`) stays, so this is pure convenience;
  lowest-cost to drop.

What keeping costs: the pinned-binary fetch in `01b-install-binary-tools.sh` (a
GitHub download at build, two version pins to maintain, x86_64-only).

## Options
1. **Keep both** (status quo) — the binary fetch stays.
2. **Drop `procs`, keep `shfmt`** — procs is pure convenience; shfmt has no
   in-image substitute for formatting.
3. **Drop both** — remove `01b-install-binary-tools.sh` and its Dockerfile `COPY`
   + `RUN`; simplest image, no out-of-dnf fetch.

Recommendation: at least drop `procs` (option 2); decide shfmt on whether in-image
shell formatting is actually used.

## Note
This is the client sandbox; the twin task lives in runClaudeInContainer (the
canonical base list). Decide both together and keep them in sync.
