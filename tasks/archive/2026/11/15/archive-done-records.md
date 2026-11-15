# Rewrote stale archive docs into done-records and repointed the archive's dangling references

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 7
**Difficulty:** 3
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §10.1, §10.2, §10.3 F20 F16

## What this did

Done by a delegated agent (edits only under `tasks/archive/`), reviewed and committed here.

- **46 archive docs** that carried Plan / Open questions / Next / Context scaffolding, unchecked
  boxes or a stale Status became past-tense done-records with `Status: complete` and
  `Completed:`. Among them `2026/09/11/nested-podman-signal-inherited-doc-cleanup.md` (was
  "proposed"; the work is commit `cd1591f`), `09/22/verify-localhost-only-network-mode.md`
  (superseded, archived unrun), `09/18/bulk-ops-shell-first-discovery.md` ("archive owed"),
  `08/29/extract-crush-build-to-script.md`, `08/19/crush-local-llm-bringup.md` and
  `09/10/vim-user-toolkit-in-base-image.md` (their boxes stated as done, or as not done or
  unrecorded), and `09/10/minimal-client-image.md` (Superseded: `FULL_TOOLCHAIN` removed
  2026-09-12). Superseded notes elsewhere: five-port autodiscovery, tmpfs → disk store, in-session
  stack. Steps never recorded are stated as unrecorded, not assumed done.
- **SHA:** `5d2515f` → `0f9548f` in `08/21/patch-crush-for-at-imports.md`.
- **Paths:** `tasks/decide-egress-verification.md`, the 09/09 history trio,
  `client/patches/crush-history-search.patch` → `crush-shell-history.patch`, the localhost-only
  pair, the bulk-ops self-path and the `../` link repointed to current homes.

## Verification

A scan of the 48 changed archive docs for `## Plan`, `## Open questions`, `## Next` and `- [ ]`
finds none. Every hex string in `tasks/archive/` resolves except `051a535` (a Crush upstream
commit), `7b33462` (resolves in runClaudeInContainer) and `5d2515f` (named in
`tasks/archive/2026/11/15/dangling-pointers.md` as the squashed SHA). Left on purpose: paths in other
repos, two paths that never existed here (`server/models.sha256`, `tasks/reference/ported-machinery.md`),
and removed one-shot paths described as removed.
