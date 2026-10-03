# Nested `dir`-store cleanup fails with "Permission denied" and leaks the store dir (client side)

## BLUF — FIXED (2026-10-02); maintainer verifies on next real exit

The Crush client's nested-podman `dir`-store cleanup trap ran `rm -rf "$STORE"` on the **host** as
the unprivileged user, but the inner **rootful** podman writes the store's image-layer `diff/` dirs
with the image's original **read-only** perms (`dr-xr-x---`) owned by **mapped subuids** — so the
host user could neither traverse the read-only dirs nor unlink the subuid-owned files, printing a
wall of `rm: cannot remove '…/storage/overlay/…/diff/…': Permission denied` and leaving the
`crush-nested.*` store dir behind on **every** normal exit (not only `SIGKILL`, as first believed).
**Fix:** clean via `$(CONTAINER_CMD) unshare rm -rf "$STORE"`, which runs inside podman's rootless
user namespace where the host user is root over its whole subuid range (`CAP_DAC_OVERRIDE`) and can
delete everything quietly. Applied to both the `shell` and `shell-exec` traps in `client/Makefile`.
"Done" = a real nested session exits with **no** `rm` errors and leaves **no** leftover dir under
`NESTED_PODMAN_STORE_BASE`.

**Status:** done — NOT YET ARCHIVED. The fix is implemented, dry-run-verified, and staged, but the
one check that matters (no `rm` errors + no leftover store dir on a real **host** exit) can only be
run by the maintainer on leaving a `make shell NESTED_PODMAN=1` client session, because the failure
reproduces only as the unprivileged host user, not from inside the uid-0 sandbox. Archive this once
that host-exit test passes. If it does NOT pass, reopen here.
**Priority:** 2 (a visible, every-exit failure that also silently fills the disk). **Difficulty:** 3.
**Created:** 2026-10-02 (William Emerison Six <billsix@gmail.com>). **Owner:** William Emerison Six
<billsix@gmail.com>.
**See also:** the substantive twin on the runClaude side,
`runClaudeInContainer/tasks/nested-store-cleanup-permission-denied.md` (identical fix, full root-cause
write-up and evidence); `tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md` (the task that
introduced the client's ephemeral `dir` store and this trap); `tasks/reference/nested-podman-design.md`
and its baked twin `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md`.

## Context — how to read this cold

The client ships the identical disk-store design as the runClaude sandbox (same Makefile store
block, `storage.conf`, `/etc` COPY). The `shell`/`shell-exec` recipes (`client/Makefile:355-361`
and `366-372`) `mktemp -d` a fresh `crush-nested.XXXXXX` dir under `NESTED_PODMAN_STORE_BASE`
(default `~/.cache`), bind it at the inner `/var/lib/containers`, and `trap … EXIT INT TERM HUP`.
The `mktemp` and `trap` run on the **host**; the inner rootful podman then populates the store
through the sandbox's user namespace, so the files land owned by the host user's **subuid range**
with the image layers' original (often non-owner-writable) modes. The host-side `rm` in the trap,
running as the unprivileged host user in the initial namespace, is therefore neither the owner nor
root over those files and fails — leaking the dir.

This is the client-perspective record; the full root-cause analysis, the on-disk evidence, and the
leaked-dir cleanup live in the runClaude twin (see **See also**). The change is byte-identical in
both sandboxes by design.

## The fix

In both `client/Makefile` recipe blocks, the trap changed from:

```sh
trap 'rm -rf "$$STORE"' EXIT INT TERM HUP;
```

to:

```sh
trap '$(CONTAINER_CMD) unshare rm -rf "$$STORE"' EXIT INT TERM HUP;
```

No fallback is wanted: this path is reached only when `NESTED_PODMAN=1` and
`NESTED_PODMAN_STORE=dir`, which is inherently a podman-nested run, so `$(CONTAINER_CMD)` is `podman`
by construction. Docs touched: the client's `tasks/reference/nested-podman-design.md` and its baked
twin `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md` (the trap bullet
now records the `podman unshare` requirement).

## Verification

- **Dry run** (`make -C client -n shell NESTED_PODMAN=1` and the `shell-exec` form): the emitted
  trap line reads `trap 'podman unshare rm -rf "$STORE"' EXIT INT TERM HUP`. Confirmed 2026-10-02.
- **Host, maintainer:** `make shell NESTED_PODMAN=1`, run an inner `podman build`/`pull` to populate
  the store, exit, and confirm (a) **no** `rm: cannot remove …` output and (b)
  `ls -d $NESTED_PODMAN_STORE_BASE/crush-nested.*` finds nothing from that session. Clean any
  straggler with `podman unshare rm -rf ~/.cache/crush-nested.*`.

## Open questions

None.
