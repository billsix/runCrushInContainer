# Re-synced every mirror and baked copy, baked two cited docs, and fixed the layout map

**Status:** complete
**Completed:** 2026-11-15
**Priority:** 2
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.1, §0.4, §1.3, §3.4 F4 F10

## What this did

- **Mirrors.** A file here was treated as a byte mirror of github.com/billsix/runClaudeInContainer's
  when it equalled runClaude's `master` (pre-batch) copy, or was one of the review's known drifts;
  each got the current canonical. 24 files: in `tasks/reference/` the four shared tools (with
  runClaude's 2026-11-15 exit-2 fixes; `check_local_annotations.py` now executable), the C, C++,
  Python standards, `cpp-build-modernization.md`, `doctests-by-default.md`, `print-debugging.md`,
  `rust-gui-tui-and-ecosystem.md`, `token-and-context-economy.md`; in the baked
  `client/entrypoint/dotfiles/.config/crush/reference/` the same standards and docs plus
  `llm-overused-phrases.md`, `recursive-design.md`, `rust-coding-standard.md`,
  `sandbox-capability-map.md` and `review_status.py`. Left as deliberate adaptations: both
  `nested-podman-design.md` copies, `image-build-and-storage-pipeline.md`, the baked
  `bluf-bottom-line-up-front.md` and the baked portable subset of `shell-and-gate-scripts.md` (whose
  one bare-name stamp became `Name <email>`).
- **Baked two docs** (maintainer decision 2026-11-15): `doctests-by-default.md` and
  `code-style-conventions.md`, which the baked standards cite, are now in the baked reference dir.
- **`tasks/reference/container-file-layout.md`** (and its baked twin): lists the `01b` and
  `install-lean.sh` COPYs, both storage drop-ins and the `containers.conf` drop-in, the nested
  `dir` store and `/var/lib/shared-images` mounts, 30 baked reference files, and table rows for
  every one of them; "Last verified 2026-11-15".

This also completes runClaudeInContainer's `tasks/mirror-fixes-to-runcrush.md` (its F14).

## Verification

A classifier compared each runCrush copy with runClaude's current and `master` versions: after the
copy, every mirror equals its canonical and only the five adaptations differ. `cmp` of the four
shared tools against runClaude: identical. Every file in the baked reference dir appears in the
layout table (checked by name). `make -C client manifest` prints the new table.
