# Use native kernel overlay for the nested store, and keep the RAM store behind its toggle

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 1
**Difficulty:** 4
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §0.1 F1 F2

## BLUF

Mirror of github.com/billsix/runClaudeInContainer `tasks/nested-native-overlay.md`: drop fuse-overlayfs from the client's nested store (native overlay measured 13 s against 62 s for the same build there), keep the RAM store behind `NESTED_PODMAN_STORE=tmpfs` with docs saying how, and rewrite the "build big images on the host" rule. Done means the client image carries the native config and the docs match; it ends `blocked` on the maintainer's host rebuild + relaunch check.

## Context

- `client/entrypoint/dotfiles/.config/containers/storage.conf:21` sets `mount_program`; it is baked three times (`~/.config/containers/`, `/etc/containers/storage.conf`, the `storage.conf.d/50-crush-nested.conf` drop-in).
- Docs asserting fuse-overlayfs is required (§0.1 F2): `crush/CLAUDE.md:589`, `tasks/reference/nested-podman-design.md:20,28,97-106`, `image-build-and-storage-pipeline.md:92-100`, `README.md:229-236`, `CLAUDE.md:128-130`, `client/Makefile:222,240-241`.
- The launchers (`client/runCrush*.sh`) default to `NESTED_PODMAN=1`; the no-internet launcher's nested builds have no network.

## Plan

1. Same storage.conf, containers.conf (`image_copy_tmp_dir`) and `shell.sh` warning as runClaude.
2. Rewrite the listed docs; document the RAM toggle in README and `CLAUDE.md` (no `exampleRunClaude.sh` here; the README's hand-run commands carry the commented variant).
3. `make image` (nested); then `blocked` on the host check.
