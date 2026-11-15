# Ad-hoc scripts must use repo-relative paths, never container-absolute

**Status:** complete
**Completed:** 2026-10-16
Created 2026-09-18 (William Emerison Six <billsix@gmail.com>).

Audited this repo's committed ad-hoc and `tools/` scripts for hard-coded container-absolute *host
mount* paths (`/foo/opt/...`, an `EXTRA_MOUNTS` path, the scratchpad). None were found, so no code
changed; the only decision was whether to surface the convention in a reference doc.

## Decision

> **Decision (William Emerison Six <billsix@gmail.com>, 2026-09-18):** the convention living in
> the **runtime** conventions `CLAUDE.md` (`client/.../crush/CLAUDE.md:198`) is sufficient — that
> is the always-loaded file a Crush session reads. Do NOT propagate it into a reference doc
> (open question 1 → answered (c)). The maintainer saw Glimmer emit absolute-path nonsense; since
> the rule is present and clear in the runtime CLAUDE.md, that is most likely a model/weights
> limitation, not a doc gap. This task is effectively closed pending only the trivial re-grep.

The rule lives in `client/entrypoint/dotfiles/.config/crush/CLAUDE.md`, § "Ad-hoc scripts"
(the "Paths must be relative … never container-absolute" sentence, with the
`pathlib.Path(__file__).resolve().parents[3]` and `git rev-parse --show-toplevel` idioms). A mount
path exists only because a particular sandbox launch had that `EXTRA_MOUNTS`; see
`tasks/reference/container-file-layout.md`.

## Audit findings (2026-09-18)

- `tasks/adhoc/verify-language-servers-on-rhel9/` (`check_fedora_servers.sh`, `check_rhel9_ty.sh`,
  `lsp_handshake.py`) already complied: the shell scripts root themselves with
  `here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"` and write relative to `$here` or an
  argument; `lsp_handshake.py` reads only `sys.argv`.
- The `/venv`, `/wheels`, `/adhoc` paths in `check_rhel9_ty.sh` are fixed paths inside the target
  container it launches, not host mounts, so they stayed. That is the distinction applied
  throughout: an image's own layout is fine, a host mount path is not.
- Final re-grep of `tasks/adhoc/` and `tools/` (2026-10-16) found no host-mount paths.
