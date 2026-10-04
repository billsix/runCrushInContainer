# Nested `dir`-store cleanup fails with "Permission denied" and leaks the store dir (client side)

## BLUF — FIX COMMITTED (2026-10-02, `e7f665e`); FIRST REAL HOST-EXIT TEST STILL PENDING

The Crush client's nested-podman `dir`-store cleanup trap ran `rm -rf "$STORE"` on the **host** as
the unprivileged user. The inner **rootful** podman writes the store's image layers with the image's
own modes, and each layer's `diff/` dir mirrors the image's `/` (mode 555 on Fedora; `/root` is
550). GNU `rm` never `chmod`s, so even as owner it cannot unlink the entries of a directory without
the owner-write bit — a wall of `rm: cannot remove '…/storage/overlay/…/diff/…': Permission denied`
and a leftover `crush-nested.*` dir on **every** normal exit (not only `SIGKILL`, as first believed).
**Fix:** clean via `$(CONTAINER_CMD) unshare rm -rf "$STORE"`, which runs inside podman's rootless
user namespace where the host user is root (`CAP_DAC_OVERRIDE` bypasses the write bits; the whole
subuid range is owned) and deletes everything quietly. Applied to both the `shell` and `shell-exec`
traps in `client/Makefile`. "Done" = a real nested client session **launched after the fix** exits
with **no** `rm` errors and leaves **no** leftover dir under `NESTED_PODMAN_STORE_BASE`.

**Status:** in progress — fix committed, awaiting the first exit of a post-fix session. No client
exit has been observed yet; the runClaude side observed one on 2026-10-04 that still failed, but it
was a session **launched before** its fix commit (`make` reads the recipe at launch), so it is not
evidence against the fix. The verification spans sessions, so the plan below gives a cold session a
ledger to fill and (after step 2) a log file to read. Archive once the ledger records one clean
post-fix client exit.
**Priority:** 2 (a visible, every-exit failure that also silently fills the disk). **Difficulty:** 3.
**Created:** 2026-10-02 (William Emerison Six <billsix@gmail.com>). **Owner:** William Emerison Six
<billsix@gmail.com>.
**See also:** the substantive twin on the runClaude side,
`runClaudeInContainer/tasks/nested-store-cleanup-permission-denied.md` (full root-cause write-up,
the 2026-10-04 leftover forensics, the fallback ranking, and the same plan with `runclaude-nested.*`
names); `tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md` (the task that introduced the
client's ephemeral `dir` store and this trap); `tasks/reference/nested-podman-design.md` and its
baked twin `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md`.

## Context — how to read this cold

The client ships the identical disk-store design as the runClaude sandbox (same Makefile store
block, `storage.conf`, `/etc` COPY). The `shell`/`shell-exec` recipes (`client/Makefile`, the two
blocks under the comment "Nested `dir` store") `mktemp -d` a fresh `crush-nested.XXXXXX` dir under
`NESTED_PODMAN_STORE_BASE` (default `~/.cache`), bind it at the inner `/var/lib/containers`, and
`trap … EXIT INT TERM HUP`. The `mktemp` and `trap` run on the **host**; the inner rootful podman
populates the store through the sandbox's user namespace. Rootless podman maps container uid 0 to
the **host user** (so image-root-owned files are host-user-owned) and uids 1–65535 to the subuid
range (those files the host user cannot touch at all). The blocker seen in practice is the mode,
not the owner: the 555 `diff/` roots and 550 `root/` dirs block a bare `rm` from unlinking their
direct children, while everything beneath them is deleted.

**Make detail that governs verification:** `make` reads the recipe when `make shell` starts, so
the fixed trap applies only to sessions **launched after** commit `e7f665e`; a client session that
was already running then exits with the old bare `rm` and will still print the wall.

This is the client-perspective record; the full root-cause analysis, on-disk evidence, and
fallbacks live in the runClaude twin (see **See also**). The change is byte-identical in both
sandboxes by design — so is the plan: whatever step 2 changes in runClaude's `Makefile` changes
here in `client/Makefile`, in the same session, kept identical.

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
records the `podman unshare` requirement and the mode-555 mechanism).

## Timeline / evidence ledger (append-only; a later session adds the next row)

| When (local) | Store | Launched with | Exit result | Source of evidence |
|---|---|---|---|---|
| 2026-10-02 | — | — | fix committed (`e7f665e`, local master; not yet pushed as of 2026-10-04) | `git log` |
| *next client launch* → *pending* | `crush-nested.??????` | **post-fix** trap | *to be recorded* | the maintainer's terminal at exit; `ls -d $NESTED_PODMAN_STORE_BASE/crush-nested.*` before any hand cleanup; the cleanup log after step 2 |

Caveat: the maintainer said (2026-10-04) they will clean stragglers **as root by hand**. A missing
store dir therefore proves nothing on its own; the row needs the exit output or the cleanup log.

## Plan — executing and verifying across sessions

- [ ] **Step 1 (maintainer, host) — observe the first post-fix client exit.** On leaving a
  `make shell NESTED_PODMAN=1` client session launched after `e7f665e`: note any `rm:` or
  `podman unshare` error text; run `ls -d $NESTED_PODMAN_STORE_BASE/crush-nested.*` **before**
  cleaning by hand; paste both into the next session, or write them to
  `$NESTED_PODMAN_STORE_BASE/exit-notes.txt` (readable from inside the next sandbox when the base
  is a bind-mounted disk such as `/mnt/sda1/tmpContainerStorage`). A clean exit = no error text and
  no dir for that session. **Gotcha:** a SIGKILL'd shell cannot run the trap — that leak is by
  design, not a fix failure.
- [x] **Step 2 — make the trap leave a log. APPLIED 2026-10-04 (go-ahead given; both
  `client/Makefile` blocks, `make -C client -n` verified, README repointed to `podman unshare`;
  effective from the next client launch)**, appending to `$(NESTED_PODMAN_STORE_BASE)/crush-nested-cleanup.log` (outside the store
  dir, so it survives). Same shape as the runClaude twin's step 2 (a `{ echo header; podman unshare
  rm -rf; echo rm exit; test -e → LEFTOVER/clean; } | tee -a LOG` trap, dry-run verified
  2026-10-04 in a scratch Makefile), with the `crush-nested` prefix; apply to both `client/Makefile`
  blocks and verify with `make -C client -n shell NESTED_PODMAN=1`.
- [ ] **Step 3 (any session) — read the evidence and fill the ledger.** The cleanup log first; else
  the pasted exit text / `exit-notes.txt`; for a leftover, the forensic commands in the runClaude
  twin's step 3 (`ls -ld --time-style=full-iso`, `du -sh`, `find ! -perm -u+w`, `find ! -uid 0`,
  `findmnt -no SOURCE /var/lib/containers` for the running session's store name).
- [ ] **Step 4 — decide.** One clean post-fix row → check the Verification box and archive (own
  commit, after the work commit). A leftover → pick the matching fallback from the runClaude twin
  ("Fallbacks if `podman unshare rm -rf` does not clean the store"), apply it identically to both
  `client/Makefile` blocks, add a ledger row.

## Cleaning already-leaked dirs (host)

```sh
podman unshare rm -rf ~/.cache/crush-nested.*     # adjust to NESTED_PODMAN_STORE_BASE
```

This is the exact command the trap runs, so running it by hand on a leftover is also a cheap
pre-test of the fix. Never clean the running session's store.

## Verification

- [x] **Dry run** (`make -C client -n shell NESTED_PODMAN=1` and the `shell-exec` form): the
  emitted trap line reads `trap 'podman unshare rm -rf "$STORE"' EXIT INT TERM HUP`. Confirmed
  2026-10-02.
- [ ] **Host, maintainer:** a client session launched after `e7f665e` exits with no `rm:`/`podman
  unshare` error output and no leftover `crush-nested.*` dir for that session (or a `== clean`
  block in the cleanup log after step 2). Recorded in the ledger.

## Open questions

None. (Step 2's go-ahead was given and applied 2026-10-04.)
