# Repository review — 2026-11-15

**What this is:** a deep, read-only audit of runCrushInContainer, requested by William Emerison Six
<billsix@gmail.com> on 2026-11-15, run right after the deep review of its sibling
github.com/billsix/runClaudeInContainer (that repo's `tasks/review/2026/11/15/repo-review.md`, cited
below as "the runClaude record"). The maintainer mirrors runClaude's changes into this repo where
reasonable, so §0 maps each runClaude follow-up onto this repo.
**Snapshot warning:** this record is frozen. Re-check a finding against the tree before acting on it.
**Baseline:** none; this is the first review of this repo.

## Coverage

| # | Dimension | What was read | By |
|---|---|---|---|
| 0 | Mirror vs runClaude | `cmp`/`diff` of every file in `tasks/reference/` (45), the baked `client/entrypoint/dotfiles/.config/crush/reference/` (28) and `commands/` (12), `tools/check_helm_file_at_point.*`, `client/entrypoint/01-install-base.sh`; delivered `crush/CLAUDE.md` vs runClaude's by heading | reader |
| 1 | Docs ↔ docs | `CLAUDE.md`, `README.md`, `FORKING.md`, the 13 runCrush-specific reference docs, in full | reader; README by main thread |
| 2 | Docs ↔ code | every claim about a target, variable, port, mount, path or gate in those docs, against `client/Makefile`, `client/Dockerfile`, `server/Makefile`, the crushrc, the entrypoint and launcher scripts; `make -n shell` in both network modes | reader; HIGHs re-checked by main thread |
| 3 | Product content | `README.md` (main thread, in full); the delivered conventions `crush/CLAUDE.md` (by heading against runClaude's, reader) | main thread + reader |
| 4 | Code quality | `tools/*` (8), `server/tools/checksum.py`, `vendor.sh`, `client/entrypoint/0*.sh`, `install-lean.sh`, `vendor/*`, `runCrush*.sh` in full; ruff, ty, shellcheck, shfmt, `check_local_annotations.py` on each | reader |
| 5 | Generators and tools | the gates exercised on scratch inputs; the 17 patches `git apply --check`ed against `client/vendor/crush` (`v0.89.0`), applied and reversed together, and the default set's Go tests run in a scratch copy | reader |
| 6 | Tests | `check_launchers.sh` run (46/46 ok); untested paths listed | reader |
| 7 | Proofs | N/A | — |
| 8 | Build, container, CI | Makefiles and Dockerfile against the personal overlay's container-template contract; no CI workflow exists | reader |
| 9 | Open-task backlog | all 25 open `tasks/*.md` | reader |
| 10 | Archive hygiene | all 52 archive docs (5,884 lines; the largest by headings/Status/BLUF + greps), `tasks/adhoc/`; 619 backticked paths via `test -e`, every SHA via `git cat-file` | reader |

The shared mirrored tools and standards (byte-identical to runClaude's) were reviewed in the runClaude
record, not again here. Their findings carry over through §0.

## 0. The runClaude record's follow-ups, applied to this repo

### 0.1 Applies as-is (VERIFIED)

- **F1 native overlay:** `client/entrypoint/dotfiles/.config/containers/storage.conf:21` sets `mount_program = "/usr/bin/fuse-overlayfs"`, and its header carries the same overturned premise. The nested store is an ext4 host dir by default here too, and is baked three times (`~/.config/containers/`, `/etc/containers/storage.conf`, the `storage.conf.d/50-crush-nested.conf` drop-in).
- **F2 "build big images on the host" rule:** it rests on the same premise in `crush/CLAUDE.md:589`, `tasks/reference/nested-podman-design.md:20,28,97-106`, `image-build-and-storage-pipeline.md:92-100`, `README.md:229-236`, the project `CLAUDE.md:128-130` and `client/Makefile:222,240-241`. The tmpfs-mode note at `client/Makefile:240` needs re-testing too.
- **F3 vacuous passes:** the three checkers are byte mirrors (`check_local_annotations.py /nonexistent_dir_xyz` → rc=0).
- **F4 Python-deps contradiction:** `crush/CLAUDE.md:398` "venv copy wins" against the personal overlay, which `client/Makefile:211-212` mounts.
- **F6 `/archive-task` lifecycle:** `commands/archive-task.md` steps 8–11 do the same one-run rewrite → move → `git rm`, and step 9 even allows a plain `mv`. `commands/stack-pop.md:11` archives immediately.
- **F8, F9 tool bugs:** `check_local_annotations.py` and `review_status.py` are byte mirrors, in `tasks/reference/` and baked.
- **F12 C standard contradiction:** the C/C++ standards are byte mirrors, in the repo and baked.
- **F15 bare first-name stamps:** `llm-overused-phrases.md:10,11` (and two more), `python-coding-standard.md` (repo and baked), the baked `shell-and-gate-scripts.md`; and, in open tasks, `tasks/audit-baked-reference-doc-drift.md:3` and `tasks/standardize-project-container-template.md:17,40,50`.
- **F19 archive done-records:** 33 of 52 archive docs carry Plan/Open questions/Context headings. See §10.

### 0.2 Applies with variation (VERIFIED)

- **F10 stale infra facts:**
  - `:Z`: `client/Makefile:133` says never `:Z`, yet lines 161, 190, 194, 198, 204, 212, 300, 328 and 378 use it under `label=disable`, and so does `vendor.sh:69`. Whether that relabels the host files is a LEAD (check `ls -Z ~/.gnupg` after a run).
  - "~430 packages" in `CLAUDE.md:27,61`, `architecture.md:96,228`, `nested-podman-design.md:11`, `client/Dockerfile:19` and `01-install-base.sh:5`; the list has 458 entries.
  - "Fedora 44" in `crush-lsp-integration.md:97,100,123` and `nested-podman-design.md:66`.
  - The bare-`rm` sweep in `image-build-and-storage-pipeline.md:84,90,131`, while `client/Makefile:352-358,374,389` and `README.md:256-258` use `podman unshare rm -rf`.
  - The wrong clippy claim in `rust-gui-tui-and-ecosystem.md:24-26` (the client list installs clippy).
- **F11 dangling task pointers:** the in-repo ones are in §2.3; `client/Makefile:324` and `architecture.md:365` cite runClaude's archived `tasks/add-shell-exec-target.md`.
- **F13 layer order:** the dotfiles COPY is already late (`client/Dockerfile:157`), but the Lean install comes after the Crush build. See §8.1.
- **F14 mirrors:** wider here than the runClaude record listed. See §0.4.
- **F17 orphan docs:** `lean-proof-methodology.md`, `makefile-feature-flag-guards.md` and `emacs-container-contract.md` have no inbound link here (`git grep`).
- **F18 stack layout:** `commands/stack-push.md` is unsectioned, but this stack lives only for one session (`crush/CLAUDE.md:369`), so the impact is smaller.
- **F20 small build fixes, mixed:**
  - Applies: the unused `/etc/containers/storage.conf` COPY (`client/Dockerfile:169`); `.gitignore` `#*#` (`git check-ignore '#foo#'` exits 1).
  - Does not apply: `PODMAN_RUN_FLAGS` (present on all five `run` lines, `client/Makefile:175`), `.dockerignore` (present, though it lacks `**/__pycache__`), exec bits.
  - Variation: `shell-exec` has no `image` prerequisite, but is documented as "run `make image` first".
- **F21 small doc fixes:** container-absolute paths in `README.md:266,276` (`/mnt/sda1/tmpContainerStorage`) and `crush-context-assembly.md:101` (`/foo/opt/…`); `.keep` files are present.

### 0.3 Does not apply

- **F5:** the client ships no `.emacs.d`.
- **F7:** runClaude's own tasks; this repo's backlog is §9.
- **F16:** the delivered `crush/CLAUDE.md` is already a lean core (674 lines against 1,078).

### 0.4 Mirror map

VERIFIED by `cmp`/`diff`.

- `tasks/reference/` (45 files): 29 are byte-identical to runClaude's.
  - `token-and-context-economy.md` drifts by 7 lines. It lacks the "Save a subagent's report into the repo" bullet, and its banner claims byte-identity.
  - `image-build-and-storage-pipeline.md` and `nested-podman-design.md` are intentional adaptations. 13 Crush-only docs.
  - 13 runClaude docs are not ported (claude-config-layering, code-style-conventions, codegen-conventions, communication-, diversion-stack-and-scope, git-workflow-, minimal-nested-images, nested-run-and-gates, reference-doc-, script-language-choice, shell-exec-and-container-template, task-doc-, versioning-and-changelogs).
- Baked `crush/reference/` (28 files): 19 identical to the canonical.
  - Drift against a byte-identity banner: `recursive-design.md` (84 lines, the old Gram–Schmidt example), `rust-coding-standard.md` (no doctests link), `token-and-context-economy.md` (7 lines).
  - Drift without such a banner: `sandbox-capability-map.md` (cites the pre-archive path `tasks/vim-user-toolkit-in-base-image.md`).
  - Intentional adaptations: bluf, shell-and-gate-scripts (portable subset).
  - For `recursive-design.md` and `rust-coding-standard.md` the repo twin matches the canonical and the baked copy is stale, though `container-file-layout.md` says the two must stay in sync. Already tracked by `tasks/audit-baked-reference-doc-drift.md`.
- `commands/` (12 against 13): 11 are intentional ports. `new-reference-set.md` is an unported byte copy (§3.1). `recheck-blocked.md` is not ported (§3.4).
- `tools/check_helm_file_at_point.*`: identical. `01-install-base.sh`: intentional additions (SPDX header, `glsl-analyzer`, `nodejs-bash-language-server`).

## 1. Docs ↔ docs

### 1.1 The five-model, five-port design is missing from many docs

VERIFIED. The code agrees on 8080–8084 with autodiscovery: `server/Makefile:73-104`, crushrc `:83-87`, `client/entrypoint/shell.sh:26`, `client/runCrush-common.sh:44`. These docs still describe two models on 8080/8081:
- `CLAUDE.md:11` (`MODEL=glimmer|gemma`), `:29` ("one tunnel forwards both"), `:75` ("curls 8080/8081").
- `README.md:154,168,173,185` ("Connecting"), `:290-294` (the hand-run forward) and `:335-351` ("Network modes").
- `tasks/reference/architecture.md:15-18` (diagram) and `:122-128` ("exactly two `llamacpp` providers"); the same doc says "autodiscovers" at `:46`.
- `FORKING.md:8,33`; `new-hardware-bringup.md:20,37`; `crush-capabilities.md:175-177`.
- `gemma-4-alongside-glimmer.md:65-81` is a decision record and may stay as history.

This is the port ↔ crushrc ↔ README ↔ `shell.sh` coupling that `CLAUDE.md` asks to keep in sync.

### 1.2 Patch count wrong

VERIFIED. `CLAUDE.md:96`, `architecture.md:206,367` and `crush-capabilities.md:43` say "fourteen" local patches; `ls client/patches/*.patch | wc -l` gives 17. `architecture.md` and `dependency-network-audit.md` never mention `crush-lsp-async`, `crush-lsp-router-notif` or `crush-context-debug`. `architecture.md:220` says the sweep covers 42 combinations; `--list` prints 43.

### 1.3 `container-file-layout.md` has drifted

VERIFIED. The doc calls itself the single source of truth and `make manifest` prints it.
- It is missing the `01b-install-binary-tools.sh` COPY (`client/Dockerfile:32`) and the two storage COPYs (`:169-171`).
- Its run-time mounts table lacks the nested `dir` store (`client/Makefile:378`) and `/var/lib/shared-images:ro` (`:268`).
- `:91` calls the store "the tmpfs image store".
- It says 27 baked reference files; there are 28. The mapping table omits `javascript-coding-standard.md`, `reimplementing-third-party-libraries.md` and `token-and-context-economy.md`.

### 1.4 `nested-podman-design.md` header and defaults

VERIFIED. "Last updated 2026-08-21" while the body has 2026-11-15 content. `:13-14` says nested podman is "default off", but the launchers default to `NESTED_PODMAN=1` (`client/runCrush-common.sh:158`).

### 1.5 `image-build-and-storage-pipeline.md:119-124` documents `NESTED_PODMAN_RUNTIME_TMPFS`

VERIFIED by `grep -r` over `client/`. It exists nowhere there, and `nested-podman-design.md:31-37` says the client has no libpod-shadow tmpfs.

### 1.6 Low: history narration and stale counts

VERIFIED.
- History narration in present-tense text: `CLAUDE.md:21` ("As of 2026-09-20"), `:90` ("this bit us 2026-08-25"); `client/Makefile:26-30,179`; `client/Dockerfile:22-24`; crushrc `:55-56,122`; `server/Makefile:36-37,176-179,217-218`; `container-file-layout.md:82-83`; `README.md:431` ("The first cut was just …").
- `README.md:460` and `FORKING.md:16` say "8 slash commands"; there are 12 (which `CLAUDE.md:95` gets right).
- `README.md:461` calls the machinery "now ported" but points at the still-open `tasks/port-runclaude-conventions-systems.md`.
- `vendor.sh:7,15,65` and `README.md:379-388` say "BOTH models, one GGUF each (~31 GB)"; there are five models, gated by country (default US: three, ~53 GB).

## 2. Docs ↔ code

### 2.1 The server's "binds loopback only" rule is a knob, not enforced

VERIFIED.
- `server/Makefile:175` is `HOST ?= 127.0.0.1`, passed as `--host $(HOST)` (`:307`).
- So `make serve HOST=0.0.0.0`, or an exported `HOST` environment variable (`?=` reads the environment), binds the model server to the LAN.
- `CLAUDE.md:65` and `architecture.md:80` say "never". `PORT` is already `override`-fixed (`:147`); `HOST` is not.
- Whether any Mac shell exports `HOST` is a LEAD: zsh sets `HOST` but normally does not export it.

### 2.2 `CRUSH_LSP_ASYNC` cannot be set from `make`

VERIFIED. `client/entrypoint/03-build-crush.sh:50-64,106` reads `CRUSH_LSP_ASYNC`, but it is not a Makefile variable or Dockerfile `ARG`, so the documented "set `CRUSH_LSP_ASYNC=0`" never reaches the build.

### 2.3 Dangling pointers to tasks that were archived

VERIFIED with `test -e`.
- `client/Makefile:60` and `client/Dockerfile:98` → `tasks/investigate-context-bloat-geometricalgebra.md`.
- crushrc `:48` → `tasks/suppress-embedded-provider-catalog.md`.
- crushrc `:130` and `03-build-crush.sh:66,74,162` → `tasks/lsp-python-server-not-registering.md`.
- `client/Makefile:101`, `server/Makefile:234` and `.gitignore` → `tasks/vendor-build-sources-for-airgap-rebuild.md`.
- `client/Dockerfile:60` → `tasks/vendor-via-client-image.md`.
- `client/entrypoint/00-install-minimal.sh:14` → `tasks/minimal-client-image.md`.
- `crush-context-assembly.md:7,79`.
- Paths that never existed: `crush-lsp-integration.md:116` cites `archive/2026/09/10/crushrc-startup…` (the file is under 09/22), and `nested-podman-vs-image-content.md:114` cites `tasks/reference/minimal-nested-images.md` (a runClaude-only doc).

### 2.4 `00-install-minimal.sh:9-18,31` header is stale

VERIFIED. It describes the removed `FULL_TOOLCHAIN` and the two-port probe.

### 2.5 Granite's context window

LEAD. Granite is an 8k-context model (`server/Makefile:67`), but it is served with `-c 65536` and registered with `--context-window 65536` (crushrc `:85`), so Crush's compaction assumes 8× the context the model was trained for.

## 3. Product content

### 3.1 `commands/new-reference-set.md` was never ported

VERIFIED. `cmp` with runClaude's copy finds it identical: YAML frontmatter (lines 1-4), `$ARGUMENTS`, `~/.claude/CLAUDE.md`. `tasks/reference/crush-capabilities.md:53-54,79-80` says Crush commands have no frontmatter and no `$ARGUMENTS`, and that `$UPPERCASE` tokens become prompted arguments. So the frontmatter leaks into the prompt and the argument is prompted as `ARGUMENTS`. The other 11 commands were ported (e.g. `new-task.md` uses `$SLUG`).

### 3.2 The nested section of the delivered conventions is stale and contradicts itself

VERIFIED. `crush/CLAUDE.md:567-573` says every inner `podman run` needs `--cgroups=disabled` plus `--network=host`, and that "a project's Makefile won't have those flags — don't silently edit". `:561` says to run plain `make image`, and runClaude's version says converted Makefiles auto-apply `PODMAN_RUN_FLAGS` and that converting one is pre-authorized. `--network=host` is a legitimate Crush difference; "won't have those flags" is stale.

### 3.3 Sections of the runClaude conventions missing here

LEAD on whether each is intended.
- Probably drift: "Verification gates in nested containers" (no hits) and "Generating source code" (no hits; `codegen-conventions.md` not baked).
- Probably intentional: the "Blocked tasks" section, together with `/recheck-blocked` and `new-task`'s `blocked` bullet. But the not-ported list at `architecture.md:378` does not mention them, and the open task `tasks/port-blocked-task-convention.md` says they are still wanted.
- Plausibly trimmed for a local model: the two reference-set authoring sections and the standalone token-economy section.

### 3.4 Baked byte-mirrored docs cite paths that do not exist inside the Crush container

VERIFIED by grep.
- `~/.claude/` paths appear in 14 baked docs and `review_status.py:7`.
- Cites of docs that are not baked: `doctests-by-default.md` (`python-coding-standard.md:244,449`, `cpp-coding-standard.md:552,561`, `repo-review-conventions.md:82`) and `code-style-conventions.md` (`cpp-coding-standard.md:582`).
- The byte-identity rule rules out per-copy rewrites, so this needs a decision (§ open questions).

### 3.5 "Upstream-only checkout" is used but defined nowhere delivered

VERIFIED. It is used by `commands/audit-repo.md:12`, `findings-to-tasks.md:19` and `spell-out-names.md:19`; same as runClaude §1.12.

### 3.6 Personal details in portable files

VERIFIED. `williamsix@macmini` appears in `client/runCrush-common.sh:56` and at line 9 of both launchers. `FORKING.md:64-66` itself calls such leaks a bug.

## 4. Code quality

### 4.1 `tools/triage_dependency_egress.py` gives wrong per-module results for nested modules

VERIFIED.
- `scan_module` uses `os.walk(root)`, so a parent module also scans its child modules' source (modules.txt has 20 parent/child pairs).
- `cloud.google.com/go` has no `.go` files of its own, yet it is reported as `NETWORK | … http-client:20 … net/http:31`.
- The header promises NETWORK / maybe / no-network, but `classify` returns `imports-only` and `url-strings-only`, and the sort table lacks those tiers.

### 4.2 `server/tools/checksum.py` edge cases

VERIFIED.
- `cmd_write`'s `status` is never set non-zero: `write man nothere.gguf` prints "skip" and exits 0, so `checksums-refresh` succeeds with a file missing.
- `verify --quarantine` with no positionals raises `IndexError`.
- A manifest line missing one algorithm makes `write` raise `KeyError: 'MD5'`.
- The serve gate lets a model through on an empty manifest (§5.2).

### 4.3 Stale comments

VERIFIED.
- `vendor.sh:12,58,78` says "@-import patch applied" and "Crush, patched", but `vendor-crush.sh:10` applies no patches.
- The `tools/ty_lsp_probe.py` docstring says "three modes" (there are four) and that "the AsyncHandler patch alone suffices". `03-build-crush.sh:52-62` calls `crush-lsp-router-notif.patch` "THE fix" and AsyncHandler defensive.

### 4.4 Mechanical checkers

VERIFIED.
- `ruff check`: `triage_dependency_egress.py:1` EXE001 (mode 644 with a shebang), `:88` SIM115, `:98` PIE810; `ty_lsp_probe.py:34` I001.
- `ruff format --check` would reformat `checksum.py`, `triage_dependency_egress.py` and `ty_lsp_probe.py`.
- `ty`: 4 `invalid-assignment` errors in `ty_lsp_probe.py:78,81,90`.
- `check_local_annotations.py --include-module`: 38 findings (triage 20, probe 16, `sweep_egress_patch_combos.py:218` `selected`, `checksum.py:48` `HashConstructor`).
- `shellcheck`: SC2164 at `tools/check_launchers.sh:142,156,161,171`.
- `shfmt -d -i 4`: 8 files unformatted (`check_launchers.sh`, `03-build-crush.sh`, `02-install-vendor-tools.sh`, `vendor.sh`, `check_helm_file_at_point.sh`, `01b`, `vendor-crush.sh`, `runCrush-common.sh`).
- `client/entrypoint/format.sh:13` formats only `entrypoint/*.sh`, and three of those are still unformatted.

### 4.5 Low: unpinned and unverified downloads, and other leads

- `01b-install-binary-tools.sh` fetches shfmt and procs without checksum verification. VERIFIED.
- `install-lean.sh` / `vendor-lean.sh` take elan from `master` and the `stable` toolchain (unpinned, against "pin versions"), and run `curl | sh` without `pipefail`. VERIFIED by reading.
- `03-build-crush.sh:185` checks `crush --version` via PATH while the install goes to `${GOBIN:-/usr/local/bin}`. LEAD.
- `serve-mlx`'s model id may not match the pinned `muse-glimmer` alias. LEAD.

## 5. Generators and tools (as gates)

### 5.1 The egress sweep does not cover the shipped image

VERIFIED.
- `tools/sweep_egress_patch_combos.py:53-85` (`ALL`, `DEFAULT`) lists 14 patches. Missing: `crush-lsp-async.patch` and `crush-lsp-router-notif.patch` (both on by default, `03-build-crush.sh:106`) and `crush-context-debug.patch` (`grep` finds none of the three in the file).
- So the "audit-default" combination is not the image that ships, against the docstring's "keep ALL … in the same canonical order as 03-build-crush.sh".
- The two LSP patches have no `diff --git` header, so `touched_files()` misses their files.
- All 17 do apply and reverse cleanly together against `v0.89.0` today.

### 5.2 The serve checksum gate fails open on an empty or missing manifest

VERIFIED behaviour; whether it matters is a LEAD. `server/Makefile:305` runs `verify --warn-unpinned`, and with an empty `models.CHECKSUMS` `checksum.py` returns 0 with a warning that says "no manifest" for a file that exists. All five model files are pinned now, so `serve` could fail closed.

### 5.3 The sweep can pass while testing nothing

VERIFIED in scratch. If `client/vendor/crush` ever lacks its own `.git`, `git apply` inside the runCrush work tree silently skips the patches (rc=0, file unchanged), and every combination "passes".

## 6. Tests

### 6.1 Gates and untested paths

- `tools/check_launchers.sh` is a strong gate (46/46 ok, 7 cases plus static checks).
- The patches' Go tests (`at_import_test.go`, two `history_test.go`, `session_busy_test.go`) pass in a scratch copy, but no gate runs them: `03-build-crush.sh` only builds, the sweep only builds, and a repo-wide grep finds no `go test`. VERIFIED.
- `checksum.py` (which decides whether a model gets served) and `triage_dependency_egress.py` have no tests; §4.1 and §4.2 are cheap doctest material.

## 7. Proofs

N/A.

## 8. Build, container, CI

### 8.1 Dockerfile layer order

VERIFIED by reading.
- The Lean install (`client/Dockerfile:151-152`; an unpinned online fetch) sits after the Crush build and all 17 `ARG CRUSH_*`/`PATCH_OUT_*` declarations (`:93-112`), so any `CRUSH_TAG` bump, patch edit or flag flip re-downloads Lean.
- `ARG VENDOR_TOOLS` (`:61`) sits above everything after it, so the `vendor.sh` build and a normal build invalidate each other's Crush and Lean layers.

### 8.2 Makefile parse-time side effects

VERIFIED. `touch $(PERSONAL_FILE)` and `mkdir -p $(MUSE_SOCK_DIR)` run even for `make help` / `make -n`. `image-import` has no empty-`FILE` guard. `client/Makefile:59-65` uses `../tasks/…` paths.

### 8.3 Contract checks that pass

VERIFIED.
- `PODMAN_RUN_FLAGS` is on every `run` and on no `build`.
- `SHELL_RUN_FLAGS` is shared by `shell` and `shell-exec`.
- `-it` is only on `shell`, and there is a `help` target.
- The dnf-cache idiom is used and the group scripts accumulate status.
- Every committed `.sh` is 100755 (`update_dep_common.sh` is sourced, 644 is fine). The exception is `tools/triage_dependency_egress.py`, which is 644 with a shebang.
- `LOCALHOST_ONLY=1` really gives `--network=none` plus the socat bridge, the launchers bind `-L 127.0.0.1:port`, the socket dir is a per-run `mktemp -d`, and the API key is a dummy.

## 9. Open-task backlog

### 9.1 Two nested-storage tasks are code-done and need only a host check

VERIFIED.
- `tasks/nested-podman-host-image-store-ignored.md:3` says "implemented and staged … uncommitted", but the work is commit `e87b68a`. The drop-in is at `client/Dockerfile:170`, the warning at `client/entrypoint/shell.sh:58`. It needs `Status: blocked` on the host rebuild/launch check, with runClaude's 2026-11-13 verification as the Recheck.
- `tasks/nested-store-cleanup-permission-denied.md:43` says the launchers "never set NESTED_PODMAN=1". Since `e87b68a` they default to it (`client/runCrush-common.sh:158`) with `NESTED_PODMAN_STORE ?= dir`, so any clean launcher exit runs the trap. The Recheck (`~/.cache/crush-nested-cleanup.log` on the host) may already be satisfied (LEAD: not visible from the sandbox).

### 9.2 Overturned premises

VERIFIED.
- `tasks/port-lean-image-nested-convention.md:16` ports the old `FLAG ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` idiom, renamed to `MINIMAL_IMAGE` on 2026-09-27. The ported conventions already carry the current text (`crush/CLAUDE.md:577-580`).
- `tasks/port-runclaude-conventions-systems.md:242` tests "stack persists across `--rm`", overturned on 2026-09-03 (`tasks/archive/2026/09/03/stack-in-session-only-harvest-at-sweep.md`; `client/Makefile:214`).
- `tasks/force-read-diversion-stack-on-session-load.md:9` BLUF still says the stack "is mounted"; its own note at `:34` says otherwise.
- `tasks/offline-nested-podman-base-images.md`: approach (1) is in place, and it still names `fedora:44` (`:21,48`).

### 9.3 Header problems

VERIFIED.
- 11 open tasks lack `## BLUF`/`## Context`: bump-crush-to-v0.90.0, context-advisor-script, crush-at-import-parity, disable-crush-telemetry, offline-nested-podman-base-images, port-blocked-task-convention, port-runclaude-conventions-systems, standardize-project-container-template, verify-auto-allow-file-tools, verify-vendor-pulls-all-quants, verify-vendored-airgap-rebuild. Three more lack Context.
- Human-gated or deferred tasks are filed `proposed` with no `Blocked on`/`Recheck`: verify-vendored-airgap-rebuild, verify-auto-allow-file-tools, verify-vendor-pulls-all-quants, context-advisor-script.
- `bump-crush-to-v0.90.0.md:3` reads "proposed — BLOCKED".
- `verify-vendor-pulls-all-quants` lists an open question its Status marks done.
- `port-blocked-task-convention` is still needed (see §3.3).
- `tasks/reference/task-doc-conventions.md` is not in this repo, though the conventions cite it (one of the 13 unported docs, §0.4).

### 9.4 Backlog as the docs currently read

Lowest Priority, then Difficulty.

| Task | Status as written | P | D |
|---|---|---|---|
| lsp-add-root-markers-gate-startup | proposed (not done: 6 `--root-markers` still in crushrc) | 3 | 2 |
| verify-auto-allow-file-tools | proposed (human-gated) | 3 | 2 |
| verify-vendored-airgap-rebuild | proposed (human-gated) | 3 | 3 |
| nested-podman-host-image-store-ignored | code done; host check (§9.1) | 3 | 4 |
| file-powernap-lsp-bugs-upstream | proposed, 1 open question | 4 | 1 |
| port-lean-image-nested-convention | superseded (§9.2) | 4 | 1 |
| context-advisor-script | deferred | 4 | 2 |
| force-read-diversion-stack-on-session-load | proposed, 3 open questions | 4 | 2 |
| audit-baked-reference-doc-drift | proposed, 1 open question | 4 | 3 |
| verify-vendor-pulls-all-quants | deferred | 4 | 3 |
| offline-nested-podman-base-images | mostly superseded | 4 | 5 |
| port-runclaude-conventions-systems | testing deferred | 4 | 5 |
| model-probe-visibility | proposed, 1 open question | 5 | 2 |
| new-hardware-bringup-runbook | in progress, 1 open question | 5 | 2 |
| port-blocked-task-convention | proposed (still needed) | 5 | 3 |
| standardize-project-container-template | proposed | 5 | 5 |
| model-files-extras-country-gate | proposed | 6 | 2 |
| crush-at-import-parity | proposed, 1 open question | 6 | 4 |
| consider-dropping-shfmt-procs | proposed | 7 | 2 |
| trim-crush-context-files | parked | 8 | 3 |

**Blocked:** verify-gemma-4-on-the-mac (P3, D2); verify-language-servers-on-rhel9 (P3, D3); bump-crush-to-v0.90.0 (P4, D2, not literally `blocked`); disable-crush-telemetry (P6, D2); nested-store-cleanup-permission-denied (P8, D1; see §9.1).

## 10. Archive hygiene

### 10.1 Archived docs never rewritten into done-records

VERIFIED by heading and Status grep.
- Wrong Status: `tasks/archive/2026/09/11/nested-podman-signal-inherited-doc-cleanup.md:3` (proposed, work done; `crush/CLAUDE.md:561`), `09/22/verify-localhost-only-network-mode.md` (proposed, with a SUPERSEDED banner), `09/18/bulk-ops-shell-first-discovery.md:3` ("archive owed").
- Unchecked boxes: `08/29/extract-crush-build-to-script.md:97-103` (3), `08/19/crush-local-llm-bringup.md:149,157` (2), `09/10/vim-user-toolkit-in-base-image.md:71` (1).
- About 25 more archive docs still carry Plan or Open-questions sections.

### 10.2 Superseded without a note

VERIFIED. `tasks/archive/2026/09/10/minimal-client-image.md:3` reads "IMPLEMENTED", with no note that `FULL_TOOLCHAIN` was removed on 2026-09-12.

### 10.3 Dangling paths and SHAs

VERIFIED.
- `tasks/trim-crush-context-files.md:98` → `tasks/investigate-context-bloat-geometricalgebra.md` (archived 09/14).
- `tasks/decide-egress-verification.md`, cited in `08/29/audit-dependency-network-egress.md:8,29,266`, `09/10/minimal-client-image.md:46`, `09/20/localhost-only-network-mode.md:53,115` and `09/22/verify-localhost-only-network-mode.md:53`.
- The 09/09 history tasks cite `tasks/crush-up-arrow-skips-last-prompt.md`, `tasks/crush-history-across-sessions-and-days.md` and `client/patches/crush-history-search.patch` (now `crush-shell-history.patch`).
- `09/22/runcrush-launcher-scripts.md` → `tasks/localhost-only-network-mode.md`; `09/18/bulk-ops-shell-first-discovery.md` cites itself at its old path; `09/22/verify-localhost-only-network-mode.md:9` uses a `../`-style link; about 15 refs carry rotting `file:line` suffixes.
- SHA `5d2515f` in `08/21/patch-crush-for-at-imports.md:7,155` does not resolve. `architecture.md:184` says it was squashed into `0f9548f`, which resolves.

### 10.4 Clean

VERIFIED. `git ls-files --others tasks/` is empty (nothing archived by plain `mv`), and `tasks/adhoc/` has a `.keep` and no stale scripts.

## Suggested follow-ups

Where a follow-up mirrors one in the runClaude record, it says so; do the two together (the runClaude `CLAUDE.md` records that a task there may also edit this repo and the personal overlay).

- **Required:**
  - [F1] Mirror runClaude F1 (native overlay for the nested store) once validated there, re-testing this repo's tmpfs mode and the no-internet launcher (§0.1).
  - [F2] Mirror runClaude F2 (rewrite the "build big images on the host" rule and the fuse-overlayfs rationale) in the seven places listed (§0.1).
  - [F3] Pin the server to loopback: `override HOST := 127.0.0.1` in `server/Makefile` (§2.1).
  - [F4] Re-copy runClaude F3's checker fixes over the mirrored copies here (repo and baked) (§0.1).
  - [F5] Bring the egress sweep in line with the shipped image: add the three missing patches, regenerate the two LSP patches with `diff --git` headers, assert `set(ALL)` equals the patch directory, and guard against a missing `client/vendor/crush/.git` (§5.1, §5.3).
- **Recommended:**
  - [F6] Port `commands/new-reference-set.md` to Crush's command format (§3.1).
  - [F7] Rewrite the two-model text to the five-port autodiscovery design across `CLAUDE.md`, `README.md`, `architecture.md`, `FORKING.md`, `new-hardware-bringup.md`, `crush-capabilities.md`, `vendor.sh` (§1.1, §1.6).
  - [F8] Mirror runClaude F6 (the `/archive-task` and `/stack-pop` lifecycle) in the ported commands (§0.1).
  - [F9] Fix the stale nested section of `crush/CLAUDE.md:567-573` (§3.2), and mirror runClaude F4 (the Python-deps decision) (§0.1).
  - [F10] Bring `container-file-layout.md` up to date (COPYs, mounts, file count, mapping table) and re-sync the stale baked copies (`recursive-design.md`, `rust-coding-standard.md`, `token-and-context-economy.md`, `sandbox-capability-map.md`) (§1.3, §0.4).
  - [F11] Fix the patch count and document all 17 patches; thread `CRUSH_LSP_ASYNC` through the Makefile and Dockerfile or document it as script-only (§1.2, §2.2).
  - [F12] Fix `checksum.py` (non-zero on a missing file, `IndexError`, `KeyError`) and make `serve` fail closed on an unpinned or empty manifest; add doctests (§4.2, §5.2, §6.1).
  - [F13] Fix `triage_dependency_egress.py`'s nested-module walk and its tier labels (§4.1).
  - [F14] Run the patches' Go tests in a gate (§6.1).
  - [F15] Backlog: set the two nested-storage tasks to `blocked` on the host check and run their Rechecks; archive `port-lean-image-nested-convention` as superseded; fix the overturned premises in `port-runclaude-conventions-systems`, `force-read-diversion-stack-on-session-load`, `offline-nested-podman-base-images` (§9.1, §9.2).
  - [F16] Repoint the dangling task pointers in code and docs, and the archive's paths and SHA (§2.3, §10.3), together with runClaude F11.
  - [F17] Mirror runClaude F10's stale infra facts here (`:Z`, package count, Fedora 44, bare-`rm` sweep, clippy) and remove `NESTED_PODMAN_RUNTIME_TMPFS` from the pipeline doc (§0.2, §1.5).
- **Optional:**
  - [F18] Reorder the Dockerfile: Lean next to `01b` and pinned, `CRUSH_VENDORED`/`VENDOR_TOOLS` declared just before the layers that read them (§8.1).
  - [F19] Fix the header problems in the open tasks (BLUF/Context, `blocked` status for gated tasks) (§9.3).
  - [F20] Rewrite the archive docs into done-records and add the superseded note to `minimal-client-image.md` (§10.1, §10.2), with runClaude F19.
  - [F21] Small fixes: `williamsix@macmini` → a placeholder, history narration, the "8 slash commands" count, `00-install-minimal.sh` header, stale comments in `vendor.sh` and `ty_lsp_probe.py`, the ruff/ty/annotation/shfmt/shellcheck findings, `format.sh` coverage, Makefile parse-time side effects, the `nested-podman-design.md` header, `.gitignore` `#*#`, the unused `/etc/containers/storage.conf` COPY, unverified 01b downloads (§1.4, §1.6, §2.4, §3.6, §4.3–§4.5, §8.2, §0.2).
  - [F22] Decide the unported-doc questions: which of the 13 unported runClaude docs and the missing conventions sections (nested gates, codegen, blocked tasks) to bring over, and how baked byte-mirrors should handle cites of unbaked docs (§0.4, §3.3, §3.4).

## Open questions for the maintainer

1. Should this repo carry the "Blocked tasks" convention and `/recheck-blocked` (§3.3)? Recommended: yes, as `tasks/port-blocked-task-convention.md` already proposes; this repo has five blocked or gated tasks.
2. For byte-mirrored baked docs that cite docs not baked into the container (§3.4): bake the cited docs (`doctests-by-default.md`, `code-style-conventions.md`), or accept the dangling cites? Recommended: bake them; they are small.
3. Is Granite really meant to run with a 64k context (§2.5)? Recommended: set its context to the model's 8k unless a longer one was tested.

## Answers to the open questions (William Emerison Six <billsix@gmail.com>, 2026-11-15)

Dated note added after the review; the findings above are unchanged.

1. **Yes**: carry the "Blocked tasks" convention and `/recheck-blocked`
   (`tasks/port-blocked-task-convention.md`).
2. **(a)**: bake `doctests-by-default.md` and `code-style-conventions.md` into the image.
3. **Keep Granite's 64k context for now**; a follow-up task checks it:
   `tasks/verify-granite-context-window.md`.

The runClaudeInContainer record's answers apply here too where §0 mirrors them: native overlay
(F1), the Python-deps rule (the personal overlay's distro-first rule), "never `:Z`" for host trees,
and the RAM store kept behind the `NESTED_PODMAN_STORE=tmpfs` toggle with README, `CLAUDE.md` and
launcher documentation.

## Correction (William Emerison Six <billsix@gmail.com>, 2026-11-15)

Dated note correcting a reviewer error. **§1.1 is wrong, and F4 needs no change.** The review read
the personal overlay at `~/.claude/ai-coding-conventions.personal.md`, a copy mounted at session
start. The overlay itself (github.com/billsix/dotfiles `.ai-coding-conventions.personal.md`) had
already been revised on 2026-11-12, in "Python deps — every package in the venv (the venv copy
wins)", and agrees with the shared `CLAUDE.md` and `python-coding-standard.md`. The answer to open
question 2 ("the newer one") therefore means the venv-wins rule, which every file already states.
