# License this project under Apache-2.0

**Status:** proposed — needs go-ahead. Not started.
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-08-25 (William Emerison Six <billsix@gmail.com>)

## Goal

Give runCrushInContainer an **explicit Apache-2.0 license**. Today there is **no `LICENSE` file** and the
only statement is vague — `README.md:214`: *"Follows the `runClaudeInContainer` family. Copyright © 2026
William Emerison Six."* Apache-2.0 fits: the model it runs (Muse Glimmer) is Apache-2.0, and the project
is meant to be a **fork-friendly template**, which wants a clear permissive license.

## Context (measured 2026-08-25)

- **No `LICENSE` file** anywhere in the repo's own tree.
- **No SPDX headers on the project's own files.** (The `SPDX-License-Identifier` hits in the tree are all
  under `server/llama.cpp/` — the **vendored** llama.cpp, which is MIT and keeps its own license.)
- The project's own source is small and glue-like: `vendor.sh`, `client/Dockerfile`, `client/Makefile`,
  `client/entrypoint/*.sh`, `server/Makefile`, `client/patches/*`, `entrypoint/dotfiles/*`, and the docs.

## Plan

1. **Add a root `LICENSE`** = the full Apache-2.0 text, with the copyright line **`Copyright 2026 William
   Emerison Six`** (match the README's existing attribution).
2. **State it in `README.md`** — replace the vague `## License` section with an explicit "Apache-2.0
   (see `LICENSE`)" line, **and** add the vendored-deps caveat from step 4.
3. **Add SPDX headers to the project's OWN files only** — `# SPDX-License-Identifier: Apache-2.0` plus a
   copyright line, on `vendor.sh`, the `Dockerfile`(s), `Makefile`(s), `entrypoint/*.sh`, and
   `client/patches/*`. Match the family's header style (`geometricalgebra` uses a two-line
   copyright + `SPDX-License-Identifier` block).
4. **Scope caveat — do this at the step above, before running any sweep:** apply headers and the license
   **only to the project's own files**. **Never touch the vendored trees** `client/vendor/crush`
   (Crush's own license) or `server/llama.cpp` (MIT) — relicensing vendored third-party code is wrong and
   those dirs are gitignored anyway. The README note should say the Apache-2.0 grant covers *this repo's
   own scripts/config*, and bundled/vendored components (llama.cpp MIT, Crush, Go deps, the model)
   retain their own licenses.
5. **Update `CLAUDE.md` / `FORKING.md`** if they state or imply a license (FORKING.md currently doesn't
   mention one — add a one-line "licensed Apache-2.0; your fork can relicense its own additions").

## Verify

- `LICENSE` present at root; `README.md` License section names Apache-2.0 and links it.
- A `grep -rL SPDX-License-Identifier` over the project's own scripts (excluding vendored trees) shows
  none missed; a `grep -r SPDX` shows the vendored trees were **not** touched.

## Open questions

1. **Is Apache-2.0 for *this repo* intended to diverge from the family, or should the family align?** The
   README says it "follows the `runClaudeInContainer` family," but that family's actual license isn't
   confirmed here (the sibling `geometricalgebra` is LGPL-2.1, so the family is *not* uniformly Apache).
   You asked for Apache-2.0 explicitly, so **this repo → Apache-2.0** is the decision; the open part is
   only whether `runClaudeInContainer` itself should also be relicensed for consistency (separate repo,
   separate task). **Recommend:** Apache-2.0 here now; leave the family-alignment question for you to
   decide separately.
2. **Redistribution check on Crush:** the client image builds Crush from vendored **source** (and applies
   a local patch). Confirm Charm Crush's own license permits that vendoring/patching + redistribution of
   the source tree in an airgap tarball, so the Apache grant on *our* glue doesn't imply anything about
   Crush's terms. **Recommend:** verify Crush's LICENSE at implementation time and note it in the README
   caveat; this doesn't block licensing our own files.

## Cross-links

- `README.md` (`## License`, line ~212) — the vague statement to replace.
- `FORKING.md` — template/fork guidance (add the license line).
- Vendored trees to leave alone: `client/vendor/crush`, `server/llama.cpp`.
