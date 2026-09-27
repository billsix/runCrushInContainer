# Crush client nested-podman inner storage: RAM tmpfs → disk directory (+ reuse host images)

## BLUF — COMPLETE, verified end-to-end in the relaunched client (2026-09-27)

The Crush client's nested-podman inner image store (`/var/lib/containers`, used when the client runs
`podman` inside itself) moved from a **RAM-backed tmpfs** — which filled RAM and OOM'd at layer-commit
on large images — to an **ephemeral on-disk directory**, plus read-only **reuse of the host's image
store** (`additionalimagestores`) so nested builds no longer re-pull images built outside the project.
The RAM tmpfs remains as an opt-in (`NESTED_PODMAN_STORE=tmpfs`). The change is byte-identical to the
runClaudeInContainer sandbox's (they share this design); this doc records it from the client's side.

**Status:** COMPLETE 2026-09-27. Verified in-session in the relaunched client: the store is on a host
disk (not tmpfs), the baked `/etc/containers/storage.conf` is read by the rootful nested podman,
host-built images (`crushcontainer`, `claudecontainer`, `smc`) are reused read-only, and a
`FROM localhost/crushcontainer:latest` build committed with no pull. The OOM-at-commit class that
motivated this — a large layer that would not fit the size-limited tmpfs — was demonstrated retired by
building a 46 GB image (the `crushcontainer` base + a forced ~20 GB `dd` layer) on the identical
disk-store config, which committed cleanly with no `no space left on device`. One image-reuse bug was
found and fixed mid-task (rootful podman ignored the rootless-path `storage.conf`; the client Dockerfile
now `COPY`s it to `/etc/containers/storage.conf`), and the `mktemp` store trap gained `HUP` so a
terminal/SSH-drop cannot leak the throwaway dir.
**Priority:** 3. **Difficulty:** 6.
**Created:** 2026-07-06 (as the shared reconsideration); implemented and verified for the client
2026-09-27.
**See also:** `tasks/reference/nested-podman-design.md` and its baked twin
`client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md` ("Operating it" disk-store
bullet); `tasks/reference/nested-podman-vs-image-content.md`; `tasks/reference/architecture.md`;
`tasks/reference/image-build-and-storage-pipeline.md`. The runClaudeInContainer twin of this task (same
change, that sandbox's side) is `runClaudeInContainer tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`.

## Background — why the client OOM'd, and why the store was a tmpfs

The client is itself a sandbox (a full ~430-package dev box, built on the host and *launched* nested),
and it runs `podman` inside itself for downstream builds. Its inner store was a **RAM-backed tmpfs**
(default 8 g, `NESTED_PODMAN_TMPFS_SIZE`), and large inner builds overflowed it. The client's own image
was the motivating failure:
- **2026-08-19:** building the client image (a 22.3 GB full-toolchain rootfs) finished the `dnf install`
  but failed at the *layer commit* with `no space left on device` in a 32 g tmpfs — the commit peak
  (base + diff + temp) exceeds the final image size; a `mount -o remount,size=50g /var/lib/containers`
  unblocked it. (The same class hit a ~6 GB TeX-Live book on the runClaude side.)

RAM was the scarce resource; disk was plentiful. The store was a tmpfs for a real reason, not laziness:
leaving `/var/lib/containers` as a plain directory on the client's own rootfs fails, because that rootfs
is itself an **overlay** mount, and the inner podman's `fuse-overlayfs` layered on top is
**overlay-on-overlay under a nested userns, which the kernel rejects**. A tmpfs is a *real* filesystem,
so fuse-overlayfs runs on it cleanly. The realization for this task: a host **directory** bind-mounted
from the host's real disk fs (ext4/xfs/btrfs) is **also** a real filesystem, so it sidesteps
overlay-on-overlay exactly like tmpfs — but disk-backed, with no RAM ceiling. (Pointing the inner store
at the host's own overlay graphroot does *not* work — that is overlay-on-overlay again.)

## The decision

**Option C (ephemeral disk dir, `rm`'d at session end) for the writable layer, plus
`additionalimagestores` mounting the host image store read-only for reuse** (2026-09-27, William
Emerison Six <billsix@gmail.com>). The tmpfs was kept behind `NESTED_PODMAN_STORE=tmpfs` for the rare
all-RAM-speed case. Rationale: C removed the RAM ceiling and the OOM-at-commit failure class (the reason
the client image needed `remount,size=50g`), matched the maintainer's "cleaned up at session end like
the network files" instinct, and — via `additionalimagestores` — reused host-built images so a nested
`make image` was fast and a pre-built base need not be re-pulled. The alternatives were the old tmpfs
(RAM ceiling, OOMs) and a *persistent* host dir (survives sessions but accumulates and needs
`podman system prune` + one-sandbox-per-dir locking); the ephemeral dir was chosen to mirror the
client's existing network-file cleanup. The maintainer directed "also runCrush" alongside the runClaude
change, and this made the lean-image standard optional (a big image now fits on disk) rather than a
nested necessity — the pairing with the `MINIMAL_IMAGE` rename (below).

## What was implemented (client side)

- **`client/Makefile`:** new `NESTED_PODMAN_STORE` (default **`dir`** = ephemeral disk dir; `tmpfs`
  selects the old RAM store), `NESTED_PODMAN_STORE_BASE` (default `$(HOME)/.cache`; relocatable per
  launch, e.g. to an HDD), and `NESTED_PODMAN_HOST_IMAGESTORE` (default
  `$(HOME)/.local/share/containers/storage`). The old `--tmpfs /var/lib/containers` line became
  `$(NESTED_PODMAN_STORE_FLAG)` (set only in tmpfs mode) plus a read-only
  `-v <hoststore>:/var/lib/shared-images:ro` (emitted only when the host path exists). In `dir` mode,
  `shell` and `shell-exec` `mktemp -d` a fresh `crush-nested.XXXXXX` store under `STORE_BASE`, bind it
  at the inner `/var/lib/containers`, and `trap rm -rf` on `EXIT INT TERM HUP` (HUP added this session
  so a terminal/SSH-drop cannot leak the dir; only `SIGKILL` still can).
- **`client/entrypoint/dotfiles/.config/containers/storage.conf`:** added
  `[storage.options] additionalimagestores = [ "/var/lib/shared-images" ]` (a missing path is
  tolerated), keeping `mount_program = /usr/bin/fuse-overlayfs`.
- **`client/Dockerfile` (the mid-task fix):** now also `COPY`s
  `entrypoint/dotfiles/.config/containers/storage.conf` to `/etc/containers/storage.conf`. The nested
  podman runs **rootful**, so it reads `/etc/containers/storage.conf`, **not** the rootless
  `~/.config/containers/storage.conf` the dotfiles delivered — without the `/etc` copy,
  `additionalimagestores` was silently ignored and `podman images` was empty.
- **Docs:** the client's always-read docs that had said the RAM tmpfs was the *default* were corrected
  to the disk-dir default (RAM opt-in): the baked crush `CLAUDE.md`, `tasks/reference/architecture.md`,
  `tasks/reference/nested-podman-vs-image-content.md`, `tasks/reference/nested-podman-design.md` + its
  baked twin, and the baked `sandbox-capability-map.md`. The confirmed disk-store mechanics were folded
  into the "Operating it" disk-store bullet of both `nested-podman-design.md` copies; a new
  `tasks/reference/image-build-and-storage-pipeline.md` documents the two podman levels. `CLAUDE.md` and
  `README.md` gained the disk-store note.

## How it was verified (in the relaunched client)

After the maintainer rebuilt (`make image`, which bakes `storage.conf` → `/etc/containers/`) and
relaunched the client with `make shell NESTED_PODMAN=1`, the in-session check passed on every point:

```sh
df -T /var/lib/containers | tail -1        # /dev/sda1 ext4  (host disk, NOT tmpfs)
mount | grep ' /var/lib/shared-images '    # /dev/sda1 ... /var/lib/shared-images ... ro
podman info --format '{{.Store.GraphRoot}} {{.Store.GraphDriverName}}'   # /var/lib/containers/storage overlay
grep -c additionalimagestores /etc/containers/storage.conf               # 1
podman images --format '{{.Repository}}:{{.Tag}} {{.ReadOnly}}'          # crushcontainer/claudecontainer/smc ... true
podman build -t t - <<<'FROM localhost/crushcontainer:latest'            # committed with NO pull (reuse works)
```

The large-image OOM-at-commit retirement was demonstrated by building a 46 GB image (the
`crushcontainer` base + a forced ~20 GB incompressible `dd` layer) on this identical disk-store config:
the `COMMIT` completed cleanly with **no `no space left on device`**, free space dipping ~43 GB during
the commit and recovering after (the read-only base stays in the shared host store; only the new layer
is written locally). A `tmpfs` at the first line would have meant the relaunch used the old store; the
host-fs type confirmed the disk store was live. The cleanup trap removes the `~/.cache/crush-nested.*`
dir on exit (a hard `SIGKILL` is the only remaining leak path).

## The paired MINIMAL_IMAGE rename — client impact

The disk store made the lean image optional rather than a nested necessity, which unblocked renaming the
overloaded `NESTED_PODMAN` build-content signal to an opt-in `MINIMAL_IMAGE` (runClaudeInContainer
`tasks/archive/2026/09/27/decouple-minimal-image-from-nested-podman.md`). For the client this was a
**doc-only** touch: the baked crush `CLAUDE.md` now states `NESTED_PODMAN` is run-capability only and
documents `MINIMAL_IMAGE=1` as the opt-in image-content flag. The client's own image content is **not**
keyed off either flag — as a sandbox built on the host, it is excluded from the `MINIMAL_IMAGE` idiom
(the 2026-09-12 rule; the earlier `FULL_TOOLCHAIN`-off-`NESTED_PODMAN` attempt that silently downgraded
the client is the origin of that rule — `tasks/reference/nested-podman-vs-image-content.md`).

## Sources (online research, 2026-09-27)

- Red Hat — [Exploring additional image stores in Podman](https://www.redhat.com/en/blog/image-stores-podman).
- Red Hat — [Podman is gaining rootless overlay support](https://www.redhat.com/sysadmin/podman-rootless-overlay).
- Red Hat — [How to use Podman inside of a container](https://www.redhat.com/en/blog/podman-inside-container)
  and containers/podman issue [#15419](https://github.com/containers/podman/issues/15419)
  (the overlay-on-overlay-under-nested-userns constraint that makes a real fs necessary for the store).
