# Audit & re-sync drifted baked reference docs (+ guard against recurrence)

**Status:** proposed — needs go-ahead (Bill, 2026-09-26)
**Priority:** 4 **Difficulty:** 3 **Created:** 2026-09-26 **Updated:** 2026-09-26
(William Emerison Six <billsix@gmail.com>)

## BLUF

Several reference docs exist in **two (or three) places** that are supposed to stay byte-identical,
but they **silently drift** because editing one copy doesn't re-sync the others. A 2026-09-26 spot
check already found **≥3 drifted**. This task: audit every baked/synced reference doc, re-sync the
stale copies from their authoritative source, and add a **check-script gate** so drift can't recur
unnoticed. "Done" = all copies in sync, and a `make`/CI check fails on any future drift.

## Context — the copy topology

runCrush delivers reference docs to a Crush session at `~/.config/crush/reference/`. Their in-repo
**baked source** is `client/entrypoint/dotfiles/.config/crush/reference/`, copied wholesale into the
image (`client/Dockerfile` `COPY entrypoint/dotfiles/ /root/`). The mapping + the "keep the two
copies in sync" rule is in `tasks/reference/container-file-layout.md` (§ Reference-doc mapping).
Three source relationships exist:

- **runClaude-canonical, 3-copy shared** (byte-identical across runClaude + runCrush's two): carry a
  `> **Shared across both sandboxes …**` banner naming runClaude as canonical. Confirmed:
  `python-coding-standard.md`, `sphinx-book-conventions.md`.
- **runClaude-canonical, baked-only into runCrush** (no runCrush `tasks/reference/` twin; the baked
  copy should match runClaude's): `bluf-bottom-line-up-front.md`, `llm-overused-phrases.md`,
  `sandbox-capability-map.md`, `bulk-edit-shell-first.md` (and check `print-debugging.md` — see
  below).
- **runCrush-internal** (`tasks/reference/` ↔ baked, kept in sync within runCrush):
  `container-file-layout.md`, `nested-podman-design.md`.

Authoritative source per doc: its `Canonical:` banner if present, else the mapping table + git
history. **Re-sync direction is source → copies** (never the reverse).

## Evidence — drift already found (2026-09-26, `diff` baked vs `tasks/reference/` twin)

- **`print-debugging.md`** — baked ≠ runCrush `tasks/reference/` twin. **DRIFTED.**
- **`python-coding-standard.md`** — baked ≠ runCrush `tasks/reference/` twin. **DRIFTED** (and it's a
  3-copy doc, so also check both against the runClaude canonical).
- **`container-file-layout.md`** — was drifted (baked stale: missing the `python-coding-standard`/
  `bulk-edit` rows, `MUSE_SOCK_DIR`, `NET_FLAGS`, wrong file count); **re-synced 2026-09-26** in the
  session that filed this task.
- **`sphinx-book-conventions.md`** — was partially mirrored/stale; **re-synced 2026-09-26** (made a
  proper 3-copy doc with a banner).
- `nested-podman-design.md` — in sync at audit time.
- The baked-only docs (`bluf`, `llm-overused-phrases`, `sandbox-capability-map`, `bulk-edit-shell-first`)
  have no runCrush twin to diff against — they must be diffed against the **runClaude** source.

## Plan

1. **Enumerate** the baked set: `ls client/entrypoint/dotfiles/.config/crush/reference/`.
2. **For each**, determine its authoritative source (banner / mapping table) and `diff` the baked
   copy against it (and, for 3-copy docs, diff the runCrush `tasks/reference/` copy against the
   runClaude canonical too). Cross-repo sources live at `/foo/opt/runClaudeInContainer/tasks/reference/`
   in-sandbox (cite the GitHub URL, not the container path, in committed docs).
3. **Re-sync** each stale copy `source → copy` (`cp`), verify byte-identical, and check nothing
   *semantically* regressed (a stale copy might be stale in BOTH directions if someone edited the
   wrong one — inspect the diff, don't blindly overwrite a copy that has unique newer content).
4. **Add a guard** (see below). 5. Update `container-file-layout.md`'s mapping table if the set
   changed.

## Recommendation — a check-script gate (the real fix)

The root cause is manual copying with no enforcement. Add **`tools/check_reference_docs_in_sync.py`**
(or a shell script) that, for every synced doc, asserts the copies are byte-identical to their
source and **exits nonzero on any diff** — then wire it into the repo's `format`/check target and
CI (the same shape as the existing gates). Follow the multi-step-gate rule: run every check, but
`exit 1` if any failed. This makes "did I forget to re-bake?" a build failure, not a latent drift.
(Same idea would help runClaudeInContainer for its half of the 3-copy docs.)

## Verification

- After re-sync: the check script passes (all copies byte-identical to source).
- `make image` still builds (the baked dir is COPY'd wholesale; content-only changes are safe).
- No behavioral change — these are docs delivered to the agent, not code.

## Open questions

1. Shell script or Python for the sync-check gate? (Recommend Python `tools/…` to match the repo's
   other `tools/` checkers, but a `diff`-based shell one is fine and simpler.)

## See also

- `tasks/reference/container-file-layout.md` — the reference-doc mapping table + the sync rule.
- The shared-doc banner pattern in `python-coding-standard.md` / `sphinx-book-conventions.md`.
- runClaudeInContainer — the canonical home of the cross-repo docs; its `tasks/reference/`.
