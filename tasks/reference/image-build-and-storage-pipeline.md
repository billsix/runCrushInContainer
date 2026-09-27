# Image build & storage pipeline — where every layer actually lives

**What this answers:** when you `make image` (in `client/`), what happens and *where do the image
layers get written*? And separately, when you run `podman` **inside** the client sandbox (nested),
where do *those* layers go? These are two different podman engines writing to two different places;
conflating them is the usual source of confusion.

**The one-sentence answer.** `make image` (on the `[LINUX HOST]`) is an ordinary rootless build and
its ~22 GB of layers land in the **standard host store** `~/.local/share/containers/storage` —
nothing special, nothing ephemeral. The "base-image-from-the-host, own-layers-written-elsewhere,
not-the-standard-place, not-RAM" behavior is the **nested** podman *inside* the sandbox (`make shell
NESTED_PODMAN=1`), a separate engine with a separate, ephemeral, disk-backed writable store plus
read-only reuse of the host store.

---

## Two levels of podman — keep them separate

```
[LEVEL 1 — HOST]  make image                          [LEVEL 2 — INSIDE THE SANDBOX]  podman build (nested)
  host rootless podman                                  inner rootful-in-userns podman
  FROM fedora:44 → dnf → build Crush → COPY             FROM <base> → RUN … → COMMIT
        │                                                     │  writable layers ↓        base images ↑ (read-only)
        ▼                                                     ▼                           │
  ~/.local/share/containers/storage   ◄────reused read-only────┐                          │
  (STANDARD host store, persistent, ~22 GB,                    │                          │
   tagged `crushcontainer`)                     /var/lib/shared-images  ◄── bind ro ───────┘
                                                (= the host store, mounted read-only)
                                               /var/lib/containers  ◄── bind ── ~/.cache/crush-nested.XXXXXX
                                                (inner writable graphroot)         (ephemeral disk dir, rm'd on exit)
```

Level 1 builds the *client sandbox image you run Crush in*. Level 2 is you building/running *other*
containers from inside that sandbox (e.g. a downstream project's `make image`). The disk-dir +
reuse machinery is **only** Level 2.

---

## Level 1 — building the client image (`make image`, on the `[LINUX HOST]`)

`cd client && make image` runs `podman build -t crushcontainer` with the host's **rootless** podman.
Pipeline (see `client/Dockerfile`):

1. `FROM registry.fedoraproject.org/fedora:44`.
2. `RUN --mount=type=cache …; dnf upgrade` — the dnf cache is a **build-time cache mount**,
   discarded after the build (not a layer, not in the image).
3. Package install scripts (`00-install-minimal.sh`, `01-install-base.sh` — the shared ~430-package
   runClaude toolchain, `02-install-vendor-tools.sh`) — host-runnable scripts the Dockerfile sources.
4. `03-build-crush.sh` — **Crush compiled from source at the pinned `CRUSH_TAG`** (`v0.89.0`), with
   the local patches applied per the `PATCH_OUT_*` / `CRUSH_AT_IMPORT` / `CRUSH_SHELL_HISTORY`
   build-args (or, for the airgap path, `CRUSH_VENDORED=1` builds from `client/vendor/crush` with no
   network). This is the bulk of the ~22 GB and the build time.
5. `COPY entrypoint/dotfiles/ /root/` — dotfiles, incl. `.config/crush/` conventions and
   `.config/containers/storage.conf`.
6. `COPY entrypoint/dotfiles/.config/containers/storage.conf /etc/containers/storage.conf` — the
   *same* store config, delivered to the rootful path the **nested** podman reads (added 2026-09-27;
   needs a rebuild to take effect — see Level 2 and runClaudeInContainer
   `tasks/dir-backed-nested-podman-storage.md`).
7. `COPY entrypoint/crushrc …` and `COPY entrypoint/shell.sh /shell.sh`.

**Where the layers go:** the finished image and all its layers are committed to the host's rootless
containers/storage — by default `~/.local/share/containers/storage` — under the tag `crushcontainer`.
This is a normal, persistent overlay store, and at ~22 GB it is **the** place disk fills up. Manage
it with `podman images` / `podman rmi crushcontainer` / `podman system prune -a`, or delete the
directory (podman recreates it). See `README.md` → the storage note by the build step.

`make image` does **not** touch `/var/lib/containers`, use a temp dir, or use a tmpfs — those are
Level-2 concerns.

## Level 2 — nested podman *inside* the client sandbox (`make shell NESTED_PODMAN=1`)

`NESTED_PODMAN=1` lets the client sandbox run its own `podman` (podman-in-podman). That inner podman
is a **separate engine** with a **separate** store, and this is where the "reuse host base images,
write own layers elsewhere" model is exactly right. Three storage-related mounts are added (in
`NESTED_PODMAN_FLAGS`, `client/Makefile`):

### (a) The inner writable store — an ephemeral disk directory, not RAM, not the host store

The inner graphroot is `/var/lib/containers`. In the default `NESTED_PODMAN_STORE=dir` mode, the
`shell`/`shell-exec` recipes do:

```
mkdir -p ~/.cache
STORE=$(mktemp -d ~/.cache/crush-nested.XXXXXX)   # a fresh dir on the host's real disk fs
trap 'rm -rf "$STORE"' EXIT INT TERM              # removed when the run exits
podman run … -v "$STORE":/var/lib/containers:Z …
```

Every nested layer the inner podman **writes** lands in that per-session temp dir under `~/.cache/`
and is deleted on exit — **not** the host store `~/.local/share/containers/storage`, and **not** a
tmpfs. A hard-killed session can leak the dir → `rm -rf ~/.cache/crush-nested.*`.

**Why a dedicated real-fs dir?** The sandbox rootfs is itself an **overlay** mount; layering the
inner `fuse-overlayfs` on top is **overlay-on-overlay under a nested userns, which the kernel
rejects**. A tmpfs is a real (non-overlay) fs — the historical reason the store was tmpfs. A **host
directory on the real disk fs, bind-mounted in, is equally a real fs**, so it sidesteps the problem
with no RAM ceiling. That is the 2026-09-27 change: the ~22 GB client image and TeX-Live-sized
downstream builds used to fail at *layer-commit* (`no space left`) in the RAM tmpfs (needing
`remount,size=50g`). Opt back into RAM with `NESTED_PODMAN_STORE=tmpfs` (sized by
`NESTED_PODMAN_TMPFS_SIZE`, default 8g).

### (b) Read-only reuse of the host store — so a nested build doesn't re-pull

`NESTED_PODMAN_IMAGESTORE_MOUNT` bind-mounts the host store (`NESTED_PODMAN_HOST_IMAGESTORE`,
default `~/.local/share/containers/storage`) **read-only** at `/var/lib/shared-images` (emitted only
if that path exists). The inner `storage.conf`'s `additionalimagestores = [ "/var/lib/shared-images"
]` then lets the inner podman **read** the host's already-built images as read-only lower layers,
without copying; the writable layer still goes to the temp dir in (a).

**Rootful gotcha (fixed 2026-09-27, needs a rebuild):** the inner podman runs **rootful** (uid 0 in
the userns), so it reads `/etc/containers/storage.conf`, not the rootless
`~/.config/containers/storage.conf`. Delivering `storage.conf` only to the rootless path left
`additionalimagestores` silently ignored. The Dockerfile now also `COPY`s it to `/etc/containers/` —
effective after the next `make image`. Detail: runClaudeInContainer
`tasks/dir-backed-nested-podman-storage.md`.

### (c) A tmpfs over the host runtime dir's `libpod` state

`NESTED_PODMAN_RUNTIME_TMPFS` shadows `$XDG_RUNTIME_DIR/libpod` with an empty tmpfs so the inner
podman doesn't trip over the *host* podman's leftover runtime state. Runtime state, not image
storage. (Nested inner runs also need `--cgroups=disabled` and, for networking, `--network=host` —
see `tasks/reference/nested-podman-design.md`.)

## Disk-management cheat-sheet

| Place | What's there | Lifetime | Reclaim it with |
|---|---|---|---|
| `~/.local/share/containers/storage` (host) | `crushcontainer` (~22 GB) + anything built/pulled on the host | Persistent | `podman rmi` / `podman system prune -a` / delete the dir |
| `~/.cache/crush-nested.XXXXXX` | the nested session's *writable* layers | Ephemeral (rm'd on exit) | auto; leaked dirs → `rm -rf ~/.cache/crush-nested.*` |
| `/var/lib/shared-images` (in-sandbox) | a read-only *view* of the host store | Mount only (writes nothing) | n/a — it's the host store above, read-only |
| `crushcontainer-*.tar` (repo root) | `make image-export` archives | Persistent, gitignored | delete the tar |

## See also

- runClaudeInContainer `tasks/dir-backed-nested-podman-storage.md` — the disk-store change, the
  rootful-config fix, and the verification (canonical location; the client mirrors its Makefile change).
- `tasks/reference/nested-podman-design.md` — every nested flag and why (fuse-overlayfs,
  `--cgroups=disabled`, `--network=host`/netavark, the `libpod` tmpfs), plus the store-backend section.
- `tasks/reference/nested-podman-vs-image-content.md` — why `NESTED_PODMAN` (run-time) and image
  content are decoupled.
- `README.md` → the build step's storage note.
