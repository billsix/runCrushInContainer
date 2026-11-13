# Nested podman ignores the host image store (podman 6), and the launchers never offer it

**Status:** implemented and staged 2026-11-12; awaiting the host rebuild + launch check
(step 7). Steps 1–6 are done, with one difference: step 1 was reproduced in the
runClaudeInContainer sandbox (same base and `COPY`), not in the client, which can't be built
cheaply here.
- **Fix.** `client/Dockerfile` installs the drop-in `50-crush-nested.conf`, and
  `client/entrypoint/shell.sh` warns when the mounted store is unused (the same snippet as the
  sibling task's, which was tested there).
- **Launchers.** `client/runCrush-common.sh` passes `NESTED_PODMAN="${NESTED_PODMAN:-1}"`.
  `NESTED_PODMAN_HOST_IMAGESTORE` reaches `client/Makefile` from the environment unchanged, so no
  code was needed for it.
- **Gate.** `tools/check_launchers.sh` gained the default-on check, the opt-out case 7, and a
  `make -n` check that the store is mounted read-only. ALL PASS.
- **Docs.** README, the launcher headers, the `client/Makefile` `LOCALHOST_ONLY` comment, the
  reference docs and the baked `nested-podman-design.md` copy (byte-identical) are updated.
  `tasks/offline-nested-podman-base-images.md` is re-scoped.

**Remaining check (step 7, required, the maintainer's; the client can't be rebuilt cheaply from a
sandbox):**
1. [LINUX HOST] Optional: commit or stash the staged work first. It is staged on `master` and
   uncommitted.
2. [LINUX HOST] `make -C client image`.
3. [LINUX HOST] Run each launcher from a project directory:
   `/path/to/runCrushInContainer/client/runCrushWithInternet.sh you@mac ""`, then
   `…/runCrushNoInternet.sh you@mac ""`.
4. [CONTAINER] In each mode:
   - there was no `[nested podman]` warning at start;
   - `podman info --format '{{json .Store.GraphOptions.additionalImageStores}}'` prints
     `["/var/lib/shared-images"]`;
   - `podman images` lists host images with R/O true;
   - a `podman build` of a two-line Containerfile (`FROM localhost/crushcontainer:latest` plus
     `RUN true`) succeeds with no pull. This matters most in no-internet mode.
5. [LINUX HOST] Check the opt-out: `NESTED_PODMAN=0 …/runCrushWithInternet.sh you@mac ""` starts a
   client with no `/dev/fuse` and no `/var/lib/shared-images`.
6. If all of that passes, archive this task (done-record rewrite, then `git mv`, as its own commit
   after the work commit). Then re-check `tasks/offline-nested-podman-base-images.md` and close it
   if it no longer applies.

**Optional follow-up, not done.** A nested `podman build` whose `RUN` steps need the network still
needs `-e BUILDAH_ISOLATION=chroot` passed by hand (README, "Put that throwaway store on a different
disk"). Since the launchers now default to nested podman, they could add it whenever `NESTED_PODMAN`
is 1. It is only useful in with-internet mode. Not done yet; it needs the maintainer's yes.
**Priority:** 3
**Difficulty:** 4
**Started:** 2026-11-12
**Sibling:** runClaudeInContainer `tasks/archive/2026/11/13/nested-podman-host-image-store-ignored.md` (same podman 6
bug, found there first; fix both the same way).
**Related:** `tasks/offline-nested-podman-base-images.md`. Host image-store reuse is the natural
answer to that task's offline `FROM` problem, so re-scope or close it once this task lands.

## BLUF

The client image puts its nested-podman store config at `/etc/containers/storage.conf`. podman 6
on Fedora 45 no longer reads that file, so the host image store the client mounts read-only is
ignored. Separately, the two one-shot launchers (`client/runCrushWithInternet.sh`,
`client/runCrushNoInternet.sh`) never launch with `NESTED_PODMAN=1`, so the host store is never
mounted from them at all. Done means:
- the client image applies the store config through a mechanism podman 6 reads;
- the launchers launch nested with host image reuse, and `README.md` documents it;
- the reference docs and the baked doc copy are updated;
- nested-in-client podman lists host images read-only in both network modes.

## Context

- **The mechanism.** `client/Makefile`:
  - `NESTED_PODMAN_HOST_IMAGESTORE ?= $(HOME)/.local/share/containers/storage`;
  - `NESTED_PODMAN_IMAGESTORE_MOUNT` bind-mounts it read-only at `/var/lib/shared-images`;
  - both are inside `ifeq ($(NESTED_PODMAN),1)`, so they apply only to a nested-capable launch.
  
  `client/entrypoint/dotfiles/.config/containers/storage.conf` sets `additionalimagestores` and
  `mount_program`. `client/Dockerfile` copies it to `/etc/containers/storage.conf`; the comment
  above that `COPY` records the 2026-09-27 fix. Design: `tasks/reference/nested-podman-design.md`
  and `tasks/reference/image-build-and-storage-pipeline.md`. The baked copy is
  `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md`.
- **The podman 6 bug.** It was observed 2026-11-12 in the runClaudeInContainer sandbox, which uses
  the same Fedora 45 base and the same `COPY` (podman 6.1.3, containers-common 0.69.2-1.fc45).
  The full evidence is in the sibling task. In short:
  - plain `podman info` reports `additionalImageStores: ["/usr/lib/containers/storage"]`, the
    built-in default, even though `/etc/containers/storage.conf` names `/var/lib/shared-images`;
  - `CONTAINERS_STORAGE_CONF=/etc/containers/storage.conf` restored the store, and so did a
    drop-in under `/etc/containers/storage.conf.d/`; each listed 85 read-only host images.
  
  The client image **was not tested**. Step 1 re-checks it there before fixing.
- **The launchers.** `client/runCrush-common.sh` (`runcrush_main`) runs
  `make -C "$client_dir" shell PROJECT=… EXTRA_PODMAN_FLAGS=… LOCALHOST_ONLY=… MUSE_SOCK_DIR=…`,
  with no `NESTED_PODMAN`. Both wrapper headers say "Runs on the Linux HOST only (it drives podman
  directly); not for NESTED_PODMAN=1". That means a launcher can't itself run inside a nested
  sandbox; it doesn't say the launched client can't run podman. `README.md` shows the launchers at
  the top ("…runCrushNoInternet.sh you@mac-studio.local \"\"") and again around the
  "extra mount" example.
- **Why the no-internet launcher gains most.** That launch is `--network=none`, so a nested
  `podman build` can't pull a base image at all. Reusing host images is the only way such a build
  can work (`tasks/offline-nested-podman-base-images.md`).
- **Gate.** `tools/check_launchers.sh` is the launchers' regression test. Extend it for the new
  flag.

## Plan

1. **Reproduce in the client.** `make -C client shell NESTED_PODMAN=1`, then
   `podman info --format '{{json .Store.GraphOptions.additionalImageStores}}'` and
   `podman images`. Expect the default store, and no host images, if the bug reproduces.
2. **Fix in the image,** the same way as the sibling task. The recommended fix is a drop-in at
   `/etc/containers/storage.conf.d/50-crush-nested.conf` holding `additionalimagestores` and
   `mount_program`. Keep `/etc/containers/storage.conf` for older podman. Use
   `ENV CONTAINERS_STORAGE_CONF` only if the drop-in proves unreliable. Update the comment above
   the `COPY` in `client/Dockerfile` to describe the current mechanism.
3. **Launchers.** In `client/runCrush-common.sh`, pass `NESTED_PODMAN` (default 1, see Decisions) to
   `make shell`, so the client gets `/dev/fuse`, the capabilities and the read-only
   host store mount.
   - Pass `NESTED_PODMAN_HOST_IMAGESTORE` through if it's set in the environment, so a fork can
     point at a different store.
   - Correct the "not for NESTED_PODMAN=1" header line in both wrappers so it can't be misread.
     It means "don't run this launcher inside a nested sandbox", not "the client can't run podman".
   - Check that no-internet mode still works: `--network=none` plus the nested flags. The inner
     podman needs `--network=none` for its own containers there, since there's no bridge to
     route. Record what a nested `podman run` needs in that mode.
4. **README.md.** At the launcher examples, add one line saying the launched client can run
   podman and reuses host-built images read-only. Add a short subsection: what reuse gives, the
   `NESTED_PODMAN_HOST_IMAGESTORE` knob and its default, the check from inside (`podman images`
   shows read-only entries), and the no-internet consequence (only host images are available as
   `FROM` bases). Commands first, with a link to the reference doc for the why.
5. **Reference docs.** Update `tasks/reference/nested-podman-design.md`,
   `tasks/reference/image-build-and-storage-pipeline.md`, the baked copy under
   `client/entrypoint/dotfiles/.config/crush/reference/`, and
   `tasks/reference/client-network-modes-and-launchers.md` (the launcher design doc that
   `client/runCrush-common.sh` cites). Then re-scope `tasks/offline-nested-podman-base-images.md`.
6. **Regression warning.** Mirror the sibling task's step 3: the client's `shell.sh` warns when
   `/var/lib/shared-images` is mounted but not in podman's `additionalImageStores`.
7. **Verify.**
   - `bash tools/check_launchers.sh`, extended to assert `NESTED_PODMAN=1` reaches `make shell`.
   - A host rebuild of the client image. That's the maintainer's step: the sandbox can't build
     the ~22 GB client image cheaply, and the launchers are host-only.
   - Launch each mode and check from inside: host images listed read-only, and
     `podman build` of a `FROM <host image>` Containerfile succeeds with no pull. In no-internet
     mode, that build is the proof the feature works.

## Decisions

- **Both launchers default to `NESTED_PODMAN=1`** (William Emerison Six <billsix@gmail.com>,
  2026-11-12). This applies to the no-internet launcher too, despite the wider privileges it grants
  (`sys_admin`, `mknod`, `net_admin`, `/dev/fuse`, `unmask=ALL`). It defaults to on, so a launch can
  still turn it off: `runCrush-common.sh` reads it from the environment as
  `NESTED_PODMAN="${NESTED_PODMAN:-1}"` and passes it to `make shell`, so `NESTED_PODMAN=0` before
  the launcher opts out. Document the opt-out in `README.md`.
