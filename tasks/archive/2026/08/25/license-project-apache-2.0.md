# License this project under Apache-2.0

**Status:** complete
**Created:** 2026-08-25 (William Emerison Six <billsix@gmail.com>) · **Completed:** 2026-08-25

Gave runCrushInContainer an explicit Apache-2.0 license: a root `LICENSE`, an explicit README section with
a vendored-deps caveat, the same caveat in `FORKING.md`, and SPDX headers on the project's own source
files. Before this there was no `LICENSE` file, no SPDX header on any of the project's own files (the only
`SPDX-License-Identifier` hits were in the vendored, MIT-licensed `server/llama.cpp/`), and the README said
only that the project "follows the `runClaudeInContainer` family." Apache-2.0 fits a fork-friendly
template and matches the model it runs (Muse Glimmer, Apache-2.0).

## What was done (2026-08-25)

- **`LICENSE`**: the verbatim Apache-2.0 text (202 lines), fetched from
  `apache.org/licenses/LICENSE-2.0.txt` rather than hand-transcribed.
- **`README.md` `## License`**: rewritten to "Apache-2.0 (see `LICENSE`)" plus the caveat that the grant
  covers the repo's own files and bundled llama.cpp, Crush and the model keep their own licenses.
- **`FORKING.md`**: a new `## License` section with the same caveat and "your fork may relicense its own
  additions."
- **SPDX headers** (`# Copyright (c) 2026 William Emerison Six` / `# SPDX-License-Identifier: Apache-2.0`,
  the family's two-line style from `geometricalgebra`) on the 11 own source files at the time: `vendor.sh`,
  `client/Dockerfile`, `client/Makefile`, `server/Makefile`, the six `client/entrypoint/*.sh` (including
  `vendor/vendor-crush.sh`), `.extrabashrc` and `crushrc`. The header goes after the shebang where present;
  all shell scripts still passed `bash -n`.
- `CLAUDE.md` needed no change (it stated no license).

## Deliberately not headered

- The vendored trees `client/vendor/crush` and `server/llama.cpp`: they keep their upstream licenses, and
  relicensing third-party code would be wrong.
- `client/patches/crush-at-import.patch`: a diff against third-party Crush, and a header could break
  `git apply`.
- All `.md` docs and the baked family reference copies (prose; `LICENSE` + README cover them);
  `storage.conf` and the ignore files (config); `client/.crush/*` runtime state (gitignored).

## Decisions

- **This repo is Apache-2.0** (requested explicitly by the maintainer). Whether `runClaudeInContainer`
  should be relicensed for family consistency was left to the maintainer as a separate repo's question
  and not decided here; the family is not uniform anyway (`geometricalgebra` is LGPL-2.1).
- **Crush's license in the caveat**: at completion the README/FORKING caveat said "Charm's terms" without
  naming the license. The README now names it, **FSL-1.1-MIT**, in its License section.

## Related

- `README.md` (`## License`), `FORKING.md` (`## License`), `LICENSE`.
- `tasks/archive/2026/08/21/patch-crush-for-at-imports.md`: the FSL-1.1-MIT read on carrying a local
  Crush patch.
