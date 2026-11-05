# Upgrade the container base from Fedora 44 to Fedora 45

**Status:** in progress
**Priority:** 4
**Difficulty:** 5

## BLUF
Bump `client/Dockerfile` to `fedora:45` and build the Crush client sandbox image
nested. "Done" = the client image builds on 45.

## Context
Fleet-wide Fedora 44 → 45 bump (William Emerison Six <billsix@gmail.com>,
2026-11-05). Fedora 45: GCC 16.2 / clang LLVM 23, Python 3.15, glibc 2.44. This
is a sibling sandbox to runClaudeInContainer; its base-install lists mirror the
Claude sandbox. Risk: a package in the base lists renamed/dropped in F45, or a
language toolchain the client bakes.

## Plan
1. `client/Dockerfile`: `fedora:44` → `fedora:45`. 2. Build nested. 3. Fix
breakage minimally (discretion; log here). 4. Stage by path; archive.

## Notes / findings
(appended as the build runs)
