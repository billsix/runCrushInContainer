# Add nested-podman support to the Crush client

**Status:** COMPLETE + verified (2026-08-22). Implementation + nested runs verified 2026-08-21. A
2026-08-22 follow-up fixed an offline miss: the reference doc was **not reachable by the agent** —
the baked `CLAUDE.md` (and `sandbox-capability-map.md`) pointed at `tasks/reference/nested-podman-design.md`,
a repo-relative path absent inside the container (only three reference docs were baked; this was not
one), so on the **offline** system Glimmer looked for the nested-podman doc and could not find it.
Fixed by baking the doc into `~/.config/crush/reference/` and correcting both pointers; **verified in a
rebuilt image** both statically (file present, pointers correct) and behaviorally (Glimmer read the doc
live and returned the right path + both flags). See "Follow-up (2026-08-22)".
**Priority:** 3
**Difficulty:** 5
**Started:** 2026-08-21 · **Implemented:** 2026-08-21 · **Reopened:** 2026-08-22 · **Completed:** 2026-08-22

## Goal

Give the `client/` container the same **`NESTED_PODMAN=1`** capability the runClaudeInContainer
sandbox has, so that when Crush drives work on a project, it can **build and run that project's own
containers nested inside the Crush client** (`make image` / `make run` / `make shell` for
container-per-project repos like mvp, gacalc, spimulator, …). Right now the client Makefile does
**not** implement `NESTED_PODMAN` (passing it is a silent no-op — `architecture.md`).

## Why (this corrects a miss)

During the conventions port (`tasks/port-runclaude-conventions-systems.md`, P4.4) nested-podman was
**skipped** on the reasoning "the Crush client doesn't run nested containers." That was wrong: the
client is the **full runClaudeInContainer toolchain** (~430 packages) — a general dev sandbox — and
the maintainer's projects all build/run in their own containers. So driving Crush to build/test a
project means running its container nested, exactly the runClaude use case. Same need, so it should
have the same capability.

## Plan

- [x] **Client Makefile — the `NESTED_PODMAN` flag set** (port from runClaudeInContainer, opt-in,
      default off). Append to the `shell` target's `podman run` when `NESTED_PODMAN=1`:
      `--device /dev/fuse`, `--device /dev/net/tun`, `--security-opt label=disable`,
      `--security-opt unmask=ALL`, `--cap-add=sys_admin,mknod,net_admin`, a tmpfs
      `/var/lib/containers` sized by `NESTED_PODMAN_TMPFS_SIZE` (default 8g), and a tmpfs over
      `$XDG_RUNTIME_DIR/libpod`. (The client's SELinux `label=disable` is already always-on; keep it.)
- [x] **`storage.conf`** — bake `client/entrypoint/dotfiles/.config/containers/storage.conf`
      (points inner podman at `/usr/bin/fuse-overlayfs`); it rides the existing dotfiles `COPY`.
      *Verify:* the toolchain already ships `podman`, `buildah`, `skopeo`, `fuse-overlayfs`
      (`01-install-base.sh`), so no package changes.
- [x] **Conventions** — re-add a **terse** "Running projects in a nested container" note to the lean
      `CLAUDE.md`: the two prerequisites (launch with `NESTED_PODMAN=1`; every inner `podman run`
      needs `--cgroups=disabled`) and the RAM-store caveat. Keep it short (lean-core context budget);
      push the full rationale to the reference doc below.
- [x] **Reference doc** — port `nested-podman-design.md` from runClaudeInContainer into
      `tasks/reference/` (adapt: it's mostly tool-agnostic about the podman stack, but the banner,
      paths, and "runClaude" framing need updating for this repo).
- [x] **Un-skip P4.4** in `tasks/port-runclaude-conventions-systems.md` (point it at this task).
- [x] **Verify — prerequisites confirmed (2026-08-21):** in a rebuilt client launched with
      `make shell NESTED_PODMAN=1`, `$NESTED_PODMAN=1`, `/dev/fuse` is present, and `podman info`
      works (maintainer-confirmed).
- [x] **Verify — inner run (remaining):** confirm an actual nested container runs:
      `podman run --rm --cgroups=disabled --network=host fedora:44 echo nested-ok` inside the client,
      then a real project's `make image` (with both flags on its inner run).
      **Finding (2026-08-21):** the image *pull* works, but the inner run needs **both**
      `--cgroups=disabled` (read-only cgroup) **and `--network=host`** — bridged netavark fails nested
      with `netavark: setns: Operation not permitted`. Documented in the reference doc + conventions.

## Notes / decisions

- **Nested-in-nested caveat:** the Crush client is *itself* often run nested (inside the
  runClaudeInContainer sandbox). Building/running a project container inside the Crush client is then
  **podman-in-podman-in-podman**. runClaude's nested support is one level; three levels may hit
  limits (RAM store, cgroups). The realistic path is: run the Crush client **on the host** (or with
  the outer sandbox's `NESTED_PODMAN=1`), then this gives one level of nesting for project work.
  Document the depth limit; don't over-promise three-deep.
- The `--cgroups=disabled` requirement on inner runs can't be baked into *other* projects' Makefiles
  — same as runClaude, it's applied per inner run (or via the standing "transient add + revert"
  authorization in the personal overlay).

## Decisions (resolved 2026-08-21, maintainer: "your call")

1. **Conventions section → terse always-loaded**, self-contained (the 2 prerequisites +
   `--cgroups=disabled` + don't-edit-their-build-files); full detail in `tasks/reference/
   nested-podman-design.md` (repo doc, not baked/`@`-imported — keeps the lean-core context small).
2. **`nested-podman-design.md` → adapted, not verbatim.** Wrote a focused Crush-client version
   (flag set, the differences from runClaude, the depth caveat) that points to runClaude's copy for
   the full rationale/declined-alternatives.
3. **`NESTED_PODMAN_TMPFS_SIZE` → 8g default**, overridable.
4. **Omitted the `$XDG_RUNTIME_DIR/libpod` shadow tmpfs** (the plan listed it): it's only needed
   because runClaude bind-mounts the host `$XDG_RUNTIME_DIR`; the barebones client does NOT, so
   there's no host podman state to collide with. Documented in the reference doc — re-add only if
   X/Wayland passthrough is ever added to the client.

## Follow-up (2026-08-21): `-e NESTED_PODMAN` passthrough

Symptom: Crush "thought NESTED_PODMAN wasn't set" — because `NESTED_PODMAN=1` is a host-side **make
variable** that only adds run flags; it is **not** an env var inside the container, so the agent
checking `$NESTED_PODMAN` always saw it empty. Fix: the `shell` target now **always** passes
`-e NESTED_PODMAN=$(NESTED_PODMAN)` (definitive `0`/`1` inside). The conventions note + reference doc
now tell the agent to detect nesting via `$NESTED_PODMAN` (intent) **and** `test -e /dev/fuse &&
podman info` (works). Needs a client-image rebuild is NOT required for this (it's a `run` flag), but
the conventions note change IS baked — so `make image` to get both.

## Follow-up (2026-08-22): the reference doc wasn't reachable by the agent (offline miss)

Symptom: on the **offline** system Glimmer, driving nested work inside the client, went looking for the
document describing the nested-podman system and **couldn't find it**. Root cause: the doc was written
to `tasks/reference/nested-podman-design.md` (repo path) and the always-loaded `CLAUDE.md` pointed
there — but that path does not exist inside the container. Only three reference docs were baked into the
image (`~/.config/crush/reference/`: `llm-overused-phrases.md`, `print-debugging.md`,
`sandbox-capability-map.md`); `nested-podman-design.md` was **deliberately left un-baked** (Decision 1,
to keep the lean-core context small) — but "not always-loaded" was conflated with "not present at all."
The agent's `/work` is the *mounted project*, not the runCrush repo, so the `tasks/reference/…` pointer
dangles; offline there's no GitHub fallback either. This is the "never cite an artifact the reader
can't reach" rule, one step removed: the doc existed, just not from the agent's vantage point.

Fix (2026-08-22):

- [x] **Bake the doc** — copied `tasks/reference/nested-podman-design.md` →
      `client/entrypoint/dotfiles/.config/crush/reference/nested-podman-design.md` (rides the existing
      dotfiles `COPY`, joins the other three as an on-demand — not always-loaded — read, so no
      context-budget cost).
- [x] **Fix the pointer in the baked `CLAUDE.md`** — `tasks/reference/nested-podman-design.md` →
      `~/.config/crush/reference/nested-podman-design.md` (now matches how the other two on-demand docs
      are cited in the same file).
- [x] **Fix the same dangling pointer in `sandbox-capability-map.md`** (line ~69) — it had the identical
      `tasks/reference/nested-podman-design.md` reference; corrected to the baked path.
- [x] **Rebuild** the client image (`make image`) — done 2026-08-22. **Static verification passed** in
      the rebuilt image: `~/.config/crush/reference/` contains `nested-podman-design.md`, and both
      pointers (`CLAUDE.md:171`, `sandbox-capability-map.md:69`) now read
      `~/.config/crush/reference/nested-podman-design.md` (no bare `tasks/reference/...`). The doc is
      present and readable. This rebuild also folds in the `mounts.conf`-suppression change.
- [x] **Behavioral re-verify — PASSED (2026-08-22).** With the tunnel up (`n_ctx 65536` confirmed via
      `/v1/models`) and `make shell NESTED_PODMAN=1`, `crush run -q "…read the full nested-podman design
      doc, its path + the two flags every inner podman run needs"` answered:
      `Path: /root/.config/crush/reference/nested-podman-design.md`, `--cgroups=disabled`,
      `--network=host` — no "can't find". Glimmer now reads the doc live. Bug fully resolved.

**Similar-issue scan (2026-08-22):** grepped all baked files (`CLAUDE.md`, `reference/*`, `commands/*`)
for cross-references that won't resolve inside the container.

- The two above were the only true dangling "go read this baked doc" pointers.
- The **slash commands** (`archive-task.md`, `new-reference.md`) reference `tasks/reference/`, `tools/`,
  `CLAUDE.md` — these are **correct**: they operate on the *mounted project* at `/work`, where those are
  the right relative locations. Not bugs.
- `print-debugging.md` references the `CLAUDE.md` "Instrumentation-driven debugging" section, which
  exists in the baked `CLAUDE.md` — resolves. Not a bug.
- **Minor, deferred:** `reference/llm-overused-phrases.md` (line 7) still cites the runClaude source path
  `entrypoint/dotfiles/.claude/CLAUDE.md` (should be `.config/crush/`) — inherited provenance text, not
  an actionable pointer and not reachable either way. Left as-is; not worth a divergence from the
  verbatim runClaude copy.
- **Structural note:** baked reference docs are now copies of `tasks/reference/` originals and can drift
  (same accepted pattern as the other three, which are copies of runClaude's). Keep the two
  `nested-podman-design.md` copies in sync on future edits.

## Cross-links

- `tasks/port-runclaude-conventions-systems.md` (P4.4 — the skip this corrects).
- `tasks/reference/architecture.md` (notes the client doesn't implement `NESTED_PODMAN`; and the
  nested-*build* gotcha for the 22.3 GB client image).
- runClaudeInContainer: `Makefile` (the flag set), `entrypoint/dotfiles/.config/containers/storage.conf`,
  `tasks/reference/nested-podman-design.md` (the source reference doc).
