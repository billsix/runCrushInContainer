# Ad-hoc scripts must use repo-relative paths, never container-absolute

**Status:** near-complete — audit done, scripts comply; doc-propagation decided against
**Priority:** 7
**Difficulty:** 2
Created 2026-09-18 (William Emerison Six <billsix@gmail.com>).

> **Decision (William Emerison Six <billsix@gmail.com>, 2026-09-18):** the convention living in
> the **runtime** conventions `CLAUDE.md` (`client/.../crush/CLAUDE.md:198`) is sufficient — that
> is the always-loaded file a Crush session reads. Do NOT propagate it into a reference doc
> (open question 1 → answered (c)). The maintainer saw Glimmer emit absolute-path nonsense; since
> the rule is present and clear in the runtime CLAUDE.md, that is most likely a model/weights
> limitation, not a doc gap. This task is effectively closed pending only the trivial re-grep.

## BLUF

Audit every committed ad-hoc script (and any promoted `tools/` script) in this repo to make
sure none hard-codes a container-absolute *host mount* path (`/foo/opt/...`, an `EXTRA_MOUNTS`
path, the scratchpad); where one does, root it in a variable computed at the top so it survives
a re-run from another machine, user, or differently-mounted sandbox. "Done" = every script's
paths are derived from a computed root (or an argument), any offender is fixed and its codemod
re-proven, and a decision is taken on whether to surface the convention in a reference doc (it
currently lives only in the baked conventions `CLAUDE.md`). **As of the audit below, this repo's
existing ad-hoc scripts already comply** — so the substantive delta is the doc-propagation
decision (open question 1), not code fixes.

## Context (cold-start)

The rule already lives, verbatim, in the baked Crush conventions file
`client/entrypoint/dotfiles/.config/crush/CLAUDE.md:198` ("## Ad-hoc scripts", the "**Paths must
be relative … never container-absolute**" sentence, with the Python
`pathlib.Path(__file__).resolve().parents[3]` and shell `git rev-parse --show-toplevel` idioms
and the reads-**and**-writes point). **It is NOT in any `tasks/reference/*.md` or `tasks/*.md`
here** — the only durable statement is that baked CLAUDE.md, which is delivered into a Crush
session, not read by someone browsing the repo's reference docs. That gap is the interesting part
of this task (open question 1).

Why it matters: the mount path exists only because *this* sandbox launch had that `EXTRA_MOUNTS`
(this session mounted `/foo/opt`); it is ephemeral. The mechanism is documented in
`tasks/reference/container-file-layout.md:32` ("Any other repo path you find yourself in came
from `EXTRA_MOUNTS` — user-supplied, and invisible to these docs").

## Audit findings (as of 2026-09-18)

Committed ad-hoc scripts: `tasks/adhoc/verify-language-servers-on-rhel9/` —
`check_fedora_servers.sh`, `check_rhel9_ty.sh`, `lsp_handshake.py`.

- All three **already comply.** The shell scripts root themselves with the portable idiom
  `here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` and take outputs relative to `$here`
  (or a passed arg). `lsp_handshake.py` reads only `sys.argv`, no hard-coded paths.
- The `/venv`, `/wheels`, `/adhoc` paths inside `check_rhel9_ty.sh` are **in-image fixed paths
  of the target container it launches**, not host mount paths — they are legitimate and stay.
  (This is the distinction the audit must apply everywhere: an image's own layout is fine; a
  host `EXTRA_MOUNTS` path is not.)
- No offenders found. Check for a `tools/` dir at execution time (e.g.
  `tools/triage_dependency_egress.py`, run "from the repo root" per
  `dependency-network-audit.md:16`) and confirm the same.

## Plan (on go-ahead)

1. Re-grep the tree for host-absolute paths in scripts (`grep -rnE '/foo/opt|/mnt/sda1|scratchpad'`
   under `tasks/adhoc/` and `tools/`), applying the in-image-vs-host-mount distinction above; fix
   any real offender by rooting it, and re-prove any file-mutating codemod (revert inputs by path,
   run final script once, `git diff` empty).
2. Resolve open question 1 and, if yes, make the doc change and stage it.

## Open questions

None — the one open question (whether to surface the convention in a reference doc) was answered
(c) leave it in the runtime CLAUDE.md only. See the Decision box at the top.
