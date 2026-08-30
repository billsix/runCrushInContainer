# Document container file layout and manifest

**Status:** done — implemented and archived 2026-08-30  
**Priority:** 5  
**Difficulty:** 3  
**Started:** 2026-08-30

**Session log:** `crush.log` (sibling file in this archive directory) — verbose record of the
originating Crush session's reads, writes, and actions.

**Resolution (2026-08-30):** implemented with go-ahead from William Emerison Six
<billsix@gmail.com>. Deliverables: `tasks/reference/container-file-layout.md` (+ a synced baked
copy at `client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md`, so the
in-container agent can read it with no repo mounted — an addition beyond the original plan);
`make manifest` in `client/Makefile` (static `cat`, per open question 1's recommendation);
`architecture.md` + project `CLAUDE.md` pointers. Open question 2 resolved: no `server/` layout
doc (native macOS, not containerized). Also fixed en route: `client/entrypoint/shell.sh`'s
header comment claimed the file was baked-not-mounted — stale since `SHELL_RUN_FLAGS` gained
the `/shell.sh` bind mount; corrected to describe the baked-fallback + mounted-override reality.

## BLUF

The client image bakes many files and the Makefile mounts others over them, and reference docs exist in two locations (repo vs baked). That layering is easy to mis-cite and hard to audit. Create a durable reference doc mapping every baked file to its final container path and mount override status, and add a `make manifest` target that prints the layout.

## Context

Cold-start orientation:

* Read `tasks/reference/architecture.md` for the overall two-machine design and client build.
* Read `client/Dockerfile` and `client/Makefile` for baked vs mounted files.
* Read `client/entrypoint/dotfiles/.config/crush/` for what is baked into `~/.config/crush/`.
* Personal conventions: `~/.config/crush/CLAUDE.md` `@`-imports the personal overlay; the overlay is mounted by `Makefile` at `/root/.config/crush/ai-coding-conventions.personal.md`.

Current state:

* Dockerfile `COPY` bakes:
  * `entrypoint/00-install-minimal.sh`, `01-install-base.sh`, `02-install-vendor-tools.sh` → `/usr/local/bin/`
  * `patches/` → `/patches/`
  * `entrypoint/vendor/` → `/usr/local/bin/vendor/`
  * `entrypoint/03-build-crush.sh` → `/usr/local/bin/`
  * `entrypoint/dotfiles/` → `/root/` (bakes `~/.extrabashrc`, `~/.config/crush/CLAUDE.md`, `~/.config/crush/commands/`, `~/.config/crush/reference/`, `~/.config/crush/ai-coding-conventions.personal.md` blank)
  * `entrypoint/crushrc` → `/root/.config/crush/crushrc`
  * `entrypoint/shell.sh` → `/shell.sh` (immediately shadowed by mount)
* Makefile `SHELL_RUN_FLAGS` mounts:
  * `-v ./entrypoint/shell.sh:/shell.sh:Z` overrides baked `/shell.sh`
  * `-v $(PROJECT):/work` project mount
  * Conditional host mounts: `~/.tmux.conf`, `~/.gitconfig`, `~/.gnupg`
  * Unconditional mounts: personal overlay `~/.ai-coding-conventions.personal.md` → `/root/.config/crush/ai-coding-conventions.personal.md`; diversion stack `~/.config/crush/stack.md` → `/root/.config/crush/stack.md`
* Reference docs dual location: repo `tasks/reference/*.md` vs baked `~/.config/crush/reference/*.md`. Conventions say cite the baked path inside the container.

Confusion observed in session:

* Baked vs mounted identity for `shell.sh` and `ai-coding-conventions.personal.md`.
* Which reference docs are actually baked and which are repo-only.
* No single source of truth for final container paths.

## Goal

* Create durable reference doc `tasks/reference/container-file-layout.md` mapping baked files, mount overrides, and final runtime paths.
* Add `make manifest` target to `client/Makefile` that prints the layout for the current build flags.
* Update `tasks/reference/architecture.md` to point to the new layout doc.

## Plan

1. Inventory baked files
   * Parse `client/Dockerfile` COPY lines and `entrypoint/` tree.
   * List baked reference docs in `client/entrypoint/dotfiles/.config/crush/reference/`.
2. Inventory mounts
   * Parse `client/Makefile` `SHELL_RUN_FLAGS` and conditional mounts.
   * Note mount overrides: `shell.sh`, personal overlay, stack.
3. Write reference doc
   * `tasks/reference/container-file-layout.md` with sections:
     * Baked files table: source → container path → overrideable?
     * Mounts table: host path → container path → unconditional/conditional
     * Reference doc mapping: repo path ↔ baked path
     * Notes on `CRUSH_AT_IMPORT` patch and `crushrc` location.
4. Add manifest target
   * `client/Makefile`: `.PHONY: manifest` target prints the tables via `cat` of the reference doc or generates from `SHELL_RUN_FLAGS`.
   * Ensure target works with `FULL_TOOLCHAIN`, `NESTED_PODMAN`, etc.
5. Update architecture doc
   * Add link to `tasks/reference/container-file-layout.md` in Client section.
6. Stage files, report.

## Notes

* Keep reference doc updated in place; do not archive.
* `make manifest` should be read-only, no image build.
* The personal overlay mount is unconditional; `touch` at parse time guarantees path exists.

## Open questions

1. Should `make manifest` be generated dynamically from Dockerfile/Make variables, or just `cat` the static reference doc? Recommendation: start static, add dynamic generation later.
2. Do we want a similar layout doc for `server/`? Server is native macOS, not containerized. Recommendation: no, keep scope to client.
