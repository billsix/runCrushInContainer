# Nested podman in the Crush client — design & operating notes

**Reference document** — how `make shell NESTED_PODMAN=1` lets the Crush client run `podman` inside
itself (to build/run a project's own containers), and the gotchas. Not a task; update in place. Last
updated 2026-08-21 by William Emerison Six <billsix@gmail.com>. Adapted from runClaudeInContainer's
`tasks/reference/nested-podman-design.md` — see that for the full rationale, declined alternatives,
and deeper lore; this doc covers what differs for the Crush client.

## Why

The Crush client is a full dev sandbox (the ~430-package runClaudeInContainer toolchain). When Crush
drives work on a container-per-project repo (mvp, gacalc, spimulator, …), building/testing it means
running that project's `make image`/`make run`/`make shell` — i.e. **podman inside the client**. Opt
in with `make shell NESTED_PODMAN=1` (default off, so a normal session stays minimal).

## The flag set (`client/Makefile`, applied only when `NESTED_PODMAN=1`)

| Flag | Why |
| --- | --- |
| `--device /dev/fuse` | Inner storage is fuse-overlayfs (overlay-on-overlay under nested userns is kernel-rejected). |
| `--security-opt unmask=ALL` | The inner rootful podman uses **netavark**, which writes per-interface sysctls to bring the bridge up; the sandbox `/proc/sys` is read-only without this, so bridged networking breaks. |
| `--cap-add=sys_admin,mknod,net_admin` | Baseline mount/device work + `net_admin` for netavark's veth/bridge over netlink (else `netavark: Operation not permitted`). |
| `--device /dev/net/tun` | Retained for the rootless/pasta path; harmless. |
| `--tmpfs /var/lib/containers:rw,size=$(NESTED_PODMAN_TMPFS_SIZE)` | The inner image store **in the opt-in `NESTED_PODMAN_STORE=tmpfs` mode** (the default is now an on-disk dir — see the disk-store bullet under "Operating it" below) — **RAM-backed**, default **8g** (`NESTED_PODMAN_TMPFS_SIZE` overrides). |

`--security-opt label=disable` is already **always-on** in the client (`SELINUX_OPT`), so it's not
repeated. Inner storage is driven by the baked `entrypoint/dotfiles/.config/containers/storage.conf`
(`mount_program = /usr/bin/fuse-overlayfs`). `podman`/`buildah`/`skopeo`/`fuse-overlayfs` already ship
in the image.

## Difference from runClaudeInContainer: no libpod-shadow tmpfs

runClaude also adds a `--tmpfs $XDG_RUNTIME_DIR/libpod` to shadow the *host* podman's rootless state,
because it bind-mounts the host's `$XDG_RUNTIME_DIR` (for Wayland/Pulse) which carries a host
`libpod/tmp/pause.pid`. **The Crush client does NOT mount the host `$XDG_RUNTIME_DIR`** (it's
barebones — no Wayland/X passthrough), so there is no host podman state to collide with, and the
shadow tmpfs is unnecessary. If X/Wayland passthrough is ever added to the client, re-introduce that
flag (see runClaude's doc).

## Operating it — the rules that bite

- **Inner `podman run`s and `--cgroups=disabled` — the `PODMAN_RUN_FLAGS` convention (2026-08-29).**
  Historically the sandbox `/sys/fs/cgroup` was read-only and every inner run died with
  `cgroup.subtree_control: Read-only file system`; on the current host stack cgroup2 mounts rw and
  flagless inner runs work (verified in runClaude), but the flag stays as harmless belt-and-braces.
  The standing convention: the sandbox exports `NESTED_PODMAN=1` into nested-capable sessions
  (this client's Makefile always did; runClaude's does as of 2026-08-29), and converted project
  Makefiles carry `PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)`
  threaded into their `run` lines (never `build`) — so containerized targets Just Work nested and
  are byte-identical on a host. This client's own Makefile follows the convention too (shell/
  shell-exec/vendor/format). Full design: runClaudeInContainer
  `tasks/reference/nested-podman-design.md`; for an unconverted project, add the flag per inner
  run (or use the standing "transient add + revert" authorization).
- **Inner runs also need `--network=host` in this setup** (confirmed 2026-08-21). Bridged netavark
  fails here with `netavark: setns: Operation not permitted` — the inner container can't create its
  own network namespace at this nesting depth. `--network=host` sidesteps netavark (the container
  shares the client's network, which is already the host's via the client's own `--network=host`).
  Fine for building/testing (most project containers don't need isolated networking). So the working
  inner invocation is: `podman run --cgroups=disabled --network=host …`. (The image *pull* works
  without it — storage/fuse-overlayfs is fine; only container *networking* needs this.)
- **A nested `podman build` needs `BUILDAH_ISOLATION=chroot` (diagnosed 2026-11-07, Fedora 45: podman
  6.1.3, buildah 1.45.1).** The sandbox is a rootless container on the host (`/proc/self/uid_map` maps
  uid 0 to the host user). The inner podman runs rootful, but buildah's `RUN` steps see the user
  namespace and take the rootless pasta path, so every networked `RUN` fails with `setup network: pasta
  failed … Couldn't open network namespace … Permission denied` (or `did not get container start message
  from parent`). The Fedora 44 sandbox did not hit this. `--isolation=chroot` / `BUILDAH_ISOLATION=chroot`
  (the `RUN` uses the sandbox's own network) and `--network=host` both work. **Launch with
  `EXTRA_PODMAN_FLAGS="… -e BUILDAH_ISOLATION=chroot"`** (EXTRA_PODMAN_FLAGS goes straight into `podman run`) so
  every nested build works unchanged; without it, add `--network=host` to the one `podman build`
  (`make -n image`, then run that line by hand). Diagnosis and test: runClaudeInContainer
  `tasks/reference/nested-run-and-gates.md`.
- **The inner store defaults to an on-disk DIR (2026-09-27) — IMPLEMENTED and VERIFIED in both sandboxes.**
  `/var/lib/containers` is now an ephemeral host directory (`NESTED_PODMAN_STORE=dir`; a `mktemp -d`
  under `NESTED_PODMAN_STORE_BASE`, default `~/.cache`, relocatable per launch — e.g. to an HDD to
  spare an SSD — and `rm`'d by an `EXIT INT TERM HUP` trap, via `podman unshare rm -rf` so it runs in
  the rootless userns as root: the image layers' `diff/` dirs mirror the image's `/` (mode 555) and
  `/root` (550), and GNU `rm` never `chmod`s, so a bare host `rm` cannot unlink their children and
  leaked the store on every exit — fixed 2026-10-02; the fix applies only to sessions launched after
  it. Each exit appends a `== <date> store=…` / `== rm exit=N` / `== clean` (or `== LEFTOVER: …`)
  block to `$(NESTED_PODMAN_STORE_BASE)/crush-nested-cleanup.log`, outside the store so it survives
  the `rm`. The runClaudeInContainer sandbox runs the same trap and logged 11 clean exits
  (2026-10-04 to 2026-11-08); a client exit is still to be read from this log, see
  `tasks/nested-store-cleanup-permission-denied.md`) with the host image store reused read-only
  (`additionalimagestores`) — no RAM ceiling. The RAM tmpfs is opt-in via `NESTED_PODMAN_STORE=tmpfs`
  (then bump `NESTED_PODMAN_TMPFS_SIZE`). **The store config is also installed as a drop-in**
  (`/etc/containers/storage.conf.d/50-crush-nested.conf`), because a containers-common vendor
  drop-in overrides a main-file `additionalimagestores` (see "Which storage config the nested
  podman reads" below).
  **Verified in-session in both sandboxes 2026-09-27** (each relaunched with the disk store): the store
  is on an `ext4` host disk (not tmpfs), `/var/lib/shared-images` is mounted read-only, host-built
  images (`crushcontainer`, `claudecontainer`, `smc`) list read-only, a
  `FROM localhost/crushcontainer:latest` build reused the base with no pull, and a forced ~20 GB fresh
  layer committed cleanly to the disk store (a 46 GB image, no `no space left on device` — the tmpfs
  OOM-at-commit class is retired). Host test + details: runClaudeInContainer
  `tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`.
- **Short names need `localhost/<tag>` and no TTY** in agent-driven runs; `make -n <target>` to print
  the expanded `podman run`, then re-run by hand with `--cgroups=disabled` added and `-it` dropped.
- **Networking just works** (bridged netavark, verified in runClaude); `--network=host` is a fallback.
- **The `Failed to mount subscriptions` WARN** on inner runs is suppressed — the client Dockerfile
  empties `/usr/share/containers/mounts.conf` (containers-common's `/usr/share/rhel/secrets:/run/secrets`
  entry is empty on Fedora and fails to mount nested). If you see the WARN, the image predates that
  fix — rebuild.

## The depth caveat — podman-in-podman-in-podman

The Crush client is *itself* often run nested (inside the runClaudeInContainer sandbox). Building a
project container **inside the Crush client** is then **three levels deep** of podman. runClaude's
design is validated at **one** level; three may hit RAM-store/cgroup limits. **The realistic path:
run the Crush client on the host** (or from an outer sandbox launched with `NESTED_PODMAN=1`), giving
one clean nesting level for project work. Don't rely on three-deep.

## Detecting it inside the container

The client `Makefile` passes **`-e NESTED_PODMAN=$(NESTED_PODMAN)`** into the container, so a definitive
`0`/`1` is available at `$NESTED_PODMAN` (the make *variable* is host-side and invisible inside — a
common trap). Pair the **intent** signal with a **works** signal:

```sh
# intent: was it launched with nesting?
[ "$NESTED_PODMAN" = "1" ] || echo "not launched with NESTED_PODMAN=1"
# works: is the device + daemon actually usable?
test -e /dev/fuse && podman info >/dev/null 2>&1 && echo "nested OK" || echo "nested NOT working"
```

- `$NESTED_PODMAN` != `1` ⇒ relaunch `make shell NESTED_PODMAN=1`.
- `$NESTED_PODMAN` == `1` but `/dev/fuse` absent / `podman info` fails ⇒ the **host** (or outer
  sandbox) lacks nested support, not the client config.

Because the signal is an env var and every Makefile reads it with `?=`, it propagates to every nested
`make` the agent runs (a project's `make image`/`make test`, this client's own `make image`) with
**nothing typed on the command line** — the agent never passes `NESTED_PODMAN=1` downstream; the flag
lives only on the outermost host launch. It is deliberately **not** baked into the image via
`ENV NESTED_PODMAN=1` (which the runtime `-e NESTED_PODMAN=$(NESTED_PODMAN)` would override anyway), and
must stay coupled to the actual capability flags: a plain non-nested launch would otherwise falsely
advertise nested support while `/dev/fuse`/caps/tmpfs are absent.

The full rationale/declined-alternatives live in runClaudeInContainer's copy of this doc.

## Which storage config the nested podman reads

The nested podman is rootful. Its storage config loads as containers-config(5) describes
(github.com/containers/container-libs `common/docs/containers-config.5.md`, "Load Order"):

1. **One main file**, the highest-precedence `storage.conf` that exists: `~/.config/containers/`, then
   `/etc/containers/`, then `/usr/share/containers/`. "Only one main file … will be loaded."
2. **Then every drop-in** from the `storage.conf.d/` and `storage.rootful.conf.d/` directories under
   `/usr/share/containers/` and `/etc/containers/` (and `~/.config/containers/storage.conf.d/`), sorted by
   **file name**, each file overriding settings from earlier ones.

containers-common 0.69 (Fedora 45, with podman 6.1.3) ships
`/usr/share/containers/storage.rootful.conf.d/00-vendor-rootful.conf`, which sets
`additionalimagestores = ["/usr/lib/containers/storage"]`. It applies after the main file, so it
**replaces** our `additionalimagestores`, and the host store at `/var/lib/shared-images` is silently
ignored. `podman images` then shows only images built inside the container, and in no-internet mode
a nested build can't get a base image at all.

**Fix (2026-11-12):** `client/Dockerfile` installs the same `storage.conf` a second time, as the
drop-in `/etc/containers/storage.conf.d/50-crush-nested.conf`, which sorts after the vendor's. The
`/etc/containers/storage.conf` copy stays for an older podman. `client/entrypoint/shell.sh` warns at
interactive start when `/var/lib/shared-images` is mounted but missing from
`podman info --format '{{json .Store.GraphOptions.additionalImageStores}}'`.

**The host store also serves as build cache (verified 2026-11-12).** A nested `make image` of a
project the host already built reuses the host's layers: github.com/billsix/spimulator hit the cache
on 42 of 43 steps. That holds only when `FROM` resolves to the same base image the host used. A newer
base pulled into the inner store (for example `fedora:45`, which then appears twice in
`podman images`, once with R/O false) shadows the host's and misses every step; untag the inner copy
to restore the hits.

The diagnosis was made in the runClaudeInContainer sandbox on 2026-11-12. That sandbox uses the same
Fedora 45 base, the same `storage.conf` and the same `/etc` `COPY`. `strace -e trace=openat podman
info` showed the main file and then the vendor drop-ins being read. Installing the drop-in by hand
there listed 85 read-only host images, and a `FROM` a host image used `/var/lib/shared-images` layers
with no pull. Before 2026-09-27 the file was delivered only to the rootless path; copying it to
`/etc` fixed that then. Under containers-common 0.69 the vendor drop-in breaks it again, whichever
main file is used.
