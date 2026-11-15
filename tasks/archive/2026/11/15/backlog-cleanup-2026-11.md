# Cleaned up the open-task backlog the review found stale

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §9.1, §9.2 F15

## What this did

- `tasks/nested-podman-host-image-store-ignored.md`: Status `blocked` (the work is commit `e87b68a`,
  not "staged"), with `Blocked on:` the host rebuild + one launcher session and a `Recheck:` modelled
  on runClaudeInContainer's 2026-11-13 verification.
- `tasks/nested-store-cleanup-permission-denied.md`: the launchers now default `NESTED_PODMAN=1`
  with the `dir` store, so any launcher exit exercises the trap; step 1 and `Blocked on:` say so, and
  the Recheck may already be satisfied.
- `tasks/port-lean-image-nested-convention.md`: closed as superseded by `MINIMAL_IMAGE` and archived.
- `tasks/port-runclaude-conventions-systems.md`: the "stack persists across `--rm`" check became
  "stack is in-session only" (superseded 2026-09-03).
- `tasks/force-read-diversion-stack-on-session-load.md`: the BLUF no longer says the stack is
  mounted.
- `tasks/offline-nested-podman-base-images.md`: narrowed to the airgap case (the host store is
  already reused) and `fedora:44` → `fedora:45`.
