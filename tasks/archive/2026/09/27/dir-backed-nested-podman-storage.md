# Crush client nested-podman inner storage: RAM tmpfs → disk directory (+ reuse host images)

**Status:** complete
**Completed:** 2026-09-27
Created 2026-07-06 (as the shared reconsideration); implemented and verified for the client
2026-09-27.

Moved the client's nested-podman inner image store (`/var/lib/containers`) from a RAM-backed tmpfs,
which OOM'd at layer commit on large images, to an ephemeral on-disk directory, and added read-only
reuse of the host's image store (`additionalimagestores`) so nested builds don't re-pull host-built
images. The tmpfs remains opt-in (`NESTED_PODMAN_STORE=tmpfs`). The change is byte-identical to the
runClaudeInContainer sandbox's; its twin is `runClaudeInContainer
tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`.

## Background

The client runs `podman` inside itself, and its inner store was a tmpfs (default 8 g,
`NESTED_PODMAN_TMPFS_SIZE`). On 2026-08-19, building the 22.3 GB client image nested failed at layer
commit with `no space left on device` in a 32 g tmpfs (the commit peak exceeds the final image size);
a `remount,size=50g` unblocked it. RAM was scarce, disk plentiful.

The store had been a tmpfs for a reason: a plain directory on the client's own rootfs is itself on an
overlay, and fuse-overlayfs on overlay under a nested userns is rejected by the kernel. A host
directory bind-mounted from a real disk filesystem (ext4/xfs/btrfs) is also a real filesystem, so it
avoids overlay-on-overlay like tmpfs does, without the RAM ceiling. (The host's own overlay graphroot
does not work as the store, being overlay-on-overlay again.)

## Decision (2026-09-27, William Emerison Six <billsix@gmail.com>)

**Option C (ephemeral disk dir, `rm`'d at session end) for the writable layer, plus
`additionalimagestores` mounting the host image store read-only for reuse**, with the tmpfs kept
behind `NESTED_PODMAN_STORE=tmpfs` for the rare all-RAM-speed case. It removed the RAM ceiling and
the OOM-at-commit class, matched the maintainer's "cleaned up at session end like the network files"
instinct, and reused host-built images. Rejected: the old tmpfs (RAM ceiling) and a persistent host
dir (accumulates, needs `podman system prune` and one-sandbox-per-dir locking). The maintainer
directed "also runCrush" alongside the runClaude change. This also made the lean image optional
rather than a nested necessity, which unblocked the `MINIMAL_IMAGE` rename
(`tasks/archive/2026/09/27/decouple-minimal-image-from-nested-podman.md`; doc-only for the client,
whose image content keys off neither flag).

## What was done (client side)

- **`client/Makefile`:** `NESTED_PODMAN_STORE` (default `dir`; `tmpfs` selects the old RAM store),
  `NESTED_PODMAN_STORE_BASE` (default `$(HOME)/.cache`, relocatable per launch), and
  `NESTED_PODMAN_HOST_IMAGESTORE` (default `$(HOME)/.local/share/containers/storage`). The old
  `--tmpfs /var/lib/containers` became `$(NESTED_PODMAN_STORE_FLAG)` (tmpfs mode only) plus a
  read-only `-v <hoststore>:/var/lib/shared-images:ro` (emitted only when the host path exists). In
  `dir` mode, `shell` and `shell-exec` `mktemp -d` a fresh `crush-nested.XXXXXX` under `STORE_BASE`,
  bind it at `/var/lib/containers`, and `trap rm -rf` on `EXIT INT TERM HUP` (only `SIGKILL` can still
  leak it).
- **`client/entrypoint/dotfiles/.config/containers/storage.conf`:** added
  `additionalimagestores = [ "/var/lib/shared-images" ]` (a missing path is tolerated), keeping
  `mount_program = /usr/bin/fuse-overlayfs`.
- **`client/Dockerfile` (mid-task fix):** also `COPY`s that `storage.conf` to
  `/etc/containers/storage.conf`. The nested podman runs rootful and reads only the `/etc` path, so
  without it `additionalimagestores` was silently ignored and `podman images` was empty.
- **Docs:** corrected every always-read doc that called tmpfs the default (the baked crush
  `CLAUDE.md`, `tasks/reference/architecture.md`, `tasks/reference/nested-podman-vs-image-content.md`,
  `tasks/reference/nested-podman-design.md` + its baked twin
  `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md`, the baked
  `sandbox-capability-map.md`); added `tasks/reference/image-build-and-storage-pipeline.md`; `CLAUDE.md`
  and `README.md` gained the disk-store note.

## Verification (in the relaunched client)

After the maintainer rebuilt and relaunched with `make shell NESTED_PODMAN=1`:

```sh
df -T /var/lib/containers | tail -1        # /dev/sda1 ext4  (host disk, NOT tmpfs)
mount | grep ' /var/lib/shared-images '    # /dev/sda1 ... /var/lib/shared-images ... ro
podman info --format '{{.Store.GraphRoot}} {{.Store.GraphDriverName}}'   # /var/lib/containers/storage overlay
grep -c additionalimagestores /etc/containers/storage.conf               # 1
podman images --format '{{.Repository}}:{{.Tag}} {{.ReadOnly}}'          # crushcontainer/claudecontainer/smc ... true
podman build -t t - <<<'FROM localhost/crushcontainer:latest'            # committed with NO pull (reuse works)
```

A 46 GB image (the `crushcontainer` base + a forced ~20 GB incompressible `dd` layer) built on the
same config committed with no `no space left on device`; free space dipped ~43 GB during the commit
and recovered (the read-only base stays in the shared host store).

## Sources (online research, 2026-09-27)

- Red Hat — [Exploring additional image stores in Podman](https://www.redhat.com/en/blog/image-stores-podman).
- Red Hat — [Podman is gaining rootless overlay support](https://www.redhat.com/sysadmin/podman-rootless-overlay).
- Red Hat — [How to use Podman inside of a container](https://www.redhat.com/en/blog/podman-inside-container)
  and containers/podman issue [#15419](https://github.com/containers/podman/issues/15419)
  (the overlay-on-overlay-under-nested-userns constraint).
