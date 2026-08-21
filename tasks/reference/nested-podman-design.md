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
| `--tmpfs /var/lib/containers:rw,size=$(NESTED_PODMAN_TMPFS_SIZE)` | The inner image store — **RAM-backed**, default **8g** (`NESTED_PODMAN_TMPFS_SIZE` overrides). |

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

- **Every INNER `podman run` needs `--cgroups=disabled`.** The sandbox `/sys/fs/cgroup` is read-only,
  so without it every inner run dies with `cgroup.subtree_control: Read-only file system`. A project's
  Makefile won't have this flag — add it per inner run (or use the standing "transient add + revert"
  authorization). `--cgroupns=private` does NOT fix it (tested in runClaude).
- **Inner runs also need `--network=host` in this setup** (confirmed 2026-08-21). Bridged netavark
  fails here with `netavark: setns: Operation not permitted` — the inner container can't create its
  own network namespace at this nesting depth. `--network=host` sidesteps netavark (the container
  shares the client's network, which is already the host's via the client's own `--network=host`).
  Fine for building/testing (most project containers don't need isolated networking). So the working
  inner invocation is: `podman run --cgroups=disabled --network=host …`. (The image *pull* works
  without it — storage/fuse-overlayfs is fine; only container *networking* needs this.)
- **The inner store is RAM.** `/var/lib/containers` is a tmpfs; every pulled/built inner image costs
  RAM. Budget before big builds; bump `NESTED_PODMAN_TMPFS_SIZE`. Images don't survive the session.
- **Short names need `localhost/<tag>` and no TTY** in agent-driven runs; `make -n <target>` to print
  the expanded `podman run`, then re-run by hand with `--cgroups=disabled` added and `-it` dropped.
- **Networking just works** (bridged netavark, verified in runClaude); `--network=host` is a fallback.

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

The full rationale/declined-alternatives live in runClaudeInContainer's copy of this doc.
