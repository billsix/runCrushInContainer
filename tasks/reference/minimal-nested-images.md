# The MINIMAL_IMAGE build option — what "minimal" means per project

**Reference document** — the convention that a containerized project can build a *lean* image on
demand by passing **`MINIMAL_IMAGE=1`**, while its default (host or nested) is the *full* image; the
idiom; the rules for what may and may not be trimmed; and the 2026-09-10 survey of every project under
the sandbox's project mounts with a `CLAUDE.md`. Work: `tasks/archive/2026/11/15/minimal-image-for-nested-podman-standard.md`
(umbrella) + one `tasks/minimal-nested-image.md` per project. Sibling of `nested-podman-design.md`
("The `PODMAN_RUN_FLAGS` convention"), which it does not repeat. Written 2026-09-10 (William Emerison
Six <billsix@gmail.com> asked for the standard).

> **The signal was renamed `NESTED_PODMAN` → `MINIMAL_IMAGE` (2026-09-27), and made an OPT-IN.**
> Originally the lean image was inferred from `NESTED_PODMAN=1` (auto-lean when built nested). Two
> things changed that: (1) `NESTED_PODMAN` overloaded one variable with two unrelated jobs — run-time
> nested capability *and* build-time image content — which caused a real bug (the runCrush client
> silently built minimal; reverted 2026-09-12); and (2) the nested inner store moved to disk
> (`tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`, 2026-09-27), so a full image now fits nested and lean
> is no longer a necessity there. So image content keys off a dedicated **`MINIMAL_IMAGE`** flag, which
> the sandbox does **not** auto-export: a nested `make image` builds FULL unless the user passes
> `MINIMAL_IMAGE=1` (for a small export/airgap image). `NESTED_PODMAN` keeps ONLY its
> `PODMAN_RUN_FLAGS` run-capability role. Decision + rollout:
> `tasks/archive/2026/09/27/decouple-minimal-image-from-nested-podman.md`.

> **Scope (2026-09-12): this applies to DOWNSTREAM container-per-project repos only — NEVER to
> runClaudeInContainer or the runCrushInContainer client themselves.** Those two are built on the host
> and merely *launched* nested (the maintainer types `NESTED_PODMAN=1` for run-time capability); a
> sandbox's own image is chosen explicitly on the host and never carries `MINIMAL_IMAGE` inference (the
> runCrush client once keyed its content off the nested flag and was **reverted 2026-09-12** —
> runCrushInContainer `tasks/reference/nested-podman-vs-image-content.md`). A "downstream project" here
> is one the *agent builds nested inside a sandbox*.

## 1. Why

When this was written the nested podman store was RAM (`NESTED_PODMAN_TMPFS_SIZE`, 8–16 GB), so a
batteries-included downstream image (a TeX distribution plus Emacs plus Jupyter) could not be built
nested at all — image-level verification of a project's build-file changes needed a real-machine visit.
The original standard therefore built lean *automatically* when nested. Since 2026-09-27 the inner store
defaults to an on-disk dir (`tasks/archive/2026/09/27/dir-backed-nested-podman-storage.md`), removing that size ceiling: a
full image builds nested fine. So the reason to build lean is no longer "it won't fit nested" but
**export size / airgap** — a smaller image to `make image-export` or ship. That is a deliberate choice,
so it is an opt-in flag (`MINIMAL_IMAGE=1`), not inferred from being nested. (History: the
runCrushInContainer client first proved the idiom — a `FULL_TOOLCHAIN` flag 2026-08-29, then defaulting
it from `NESTED_PODMAN=1` 2026-09-10 — but that was **reverted 2026-09-12** because the client is a
*sandbox*, not a downstream project; see the Scope note above.)

## 2. The standard

**Rule.** Every optional-feature build flag in a project Makefile defaults to its full value, and flips
to its lean value when **`MINIMAL_IMAGE=1`**:

```make
# Full by default (host OR nested); lean only when MINIMAL_IMAGE=1 is passed (a small export/airgap
# image). MINIMAL_IMAGE is build CONTENT and is independent of NESTED_PODMAN (run capability) — the
# sandbox does not set it, so a nested `make image` builds FULL unless asked. Override a single flag
# the other way on the command line (FLAG=1 with MINIMAL_IMAGE=1, or FLAG=0 without it).
USE_EMACS  ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)
BUILD_DOCS ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)
```

The Dockerfile side is unchanged: `ARG FLAG=0` + the `if [ "$FLAG" = "1" ]` dispatch the template
already uses; `--build-arg FLAG=$(FLAG)` on `image`. A bare `podman build` stays lean (ARG default 0).
`make image` is full by default — a **host** build is byte-identical to before, and a **nested** build
is now full too (it used to build lean off the inherited `NESTED_PODMAN=1`; the disk store makes full
fit). `make image MINIMAL_IMAGE=1` builds lean, host or nested.

**What flips (lean = off):** editors and their configs (`USE_EMACS`, Spyder), documentation toolchains
(`BUILD_DOCS`: TeX, sphinx, inkscape, ImageMagick, pandoc), notebooks (`USE_JUPYTER`), GUI/display
extras (`USE_GRAPHICS`, `USE_X_WINDOWS` — *unless* the project's headless verification runs on the
image's own Mesa, as modelviewprojection's does), any "full toolchain" superset (`FULL_TOOLCHAIN`).

**What never flips:** the project's **gates** — tests, sanitizer suites, tree-sitter grammar builds,
a docs build when `make html` *is* the gate (spimulator's `BUILD_TREE_SITTER`/`RUN_SANITIZERS`,
modelviewprojection's `BUILD_DOCS`) — and the **product's own build dependencies** (musl for apue, TeX
for texExpToPng and the osbooks, gst's GUI-package libs for smalltalk). A lean image that cannot run the
gate verifies nothing; the flag-coverage rule (cross-project `CLAUDE.md`, "Verification gates in nested
containers", the 2026-07-07 spimulator lesson) is the reason.

**Other rules carried from the reference implementation:** same image tag for both variants (a lean
host build replaces the full image until the next full rebuild — accepted); no language servers in a
lean image (maintainer, 2026-09-10 — a declared-but-absent server fails to start harmlessly, and
Crush's "no LSP client handles file" is expected there); measure both sizes and record them in the
project's `CLAUDE.md`; a project with nothing optional (pyNuklear) adopts the standard by stating so.

**For new projects:** the template's Makefile flag block uses the `MINIMAL_IMAGE`-keyed form above for
every optional flag. The template spec lives in the maintainer's personal overlay
(`~/.ai-coding-conventions.personal.md`, host-side); the line to add there is the `make` block above.
The tracked cross-project `CLAUDE.md` documents `MINIMAL_IMAGE` as an option under "Running projects in
a nested container".

## 3. The survey (2026-09-10) — every mounted project with a `CLAUDE.md`

Read from each Dockerfile, Makefile and `entrypoint/*install*.sh` in the sandbox; sizes are to be
measured at implementation (none of these images were built for the survey). Per-project detail and
plan: that project's `tasks/minimal-nested-image.md`.

| Project | Today's flags (host default) | Unconditional heavyweights | Lean variant | Notes |
|---|---|---|---|---|
| runCrushInContainer (client — a sandbox) | — | — | **N/A — excluded** (built on host, launched nested) | tried `FULL_TOOLCHAIN`, **reverted 2026-09-12**: `nested-podman-vs-image-content.md` |
| apue | none | emacs; musl from source (product) | new `USE_EMACS` | man pages stay |
| epix-mirror | `BUILD_DOCS`, `USE_JUPYTER` (**DONE 2026-10-06**) | — | — | full 2.49 GB vs lean 1.13 GB (1392 → 194 rpms); lib/py-ext/ASan/harness need none of the trimmed layers; guarded targets exit 2 with the flag to re-enable |
| geometricalgebra | `USE_EMACS`, `BUILD_DOCS`, `USE_JUPYTER`, `USE_LEAN`, `USE_EPIX` (all on the idiom; `USE_SPYDER` 0) | — | — (DONE; `USE_EPIX` added 2026-10-06 for the pinned ePiX build) | `make test` is the gate; lean 2.42 GB vs full 7.21 GB (before ePiX) |
| gltron | `USE_GRAPHICS` 1 | emacs, ffmpeg in base | `USE_GRAPHICS` flips; new `USE_EMACS` | confirm image-time `ctest` needs no X |
| hanoi | `BUILD_DOCS` 1 | — | `BUILD_DOCS` flips | trivial |
| programmingFromTheGroundUp | `BUILD_DOCS` 1, `USE_GRAPHICS` 1 | emacs; i686 glibc (product) | both flip; new `USE_EMACS` | check `gtk4` |
| pyNuklear | none | — | **none needed** (already lean) | add `PODMAN_RUN_FLAGS` auto-default (missing) |
| smalltalk | `USE_EMACS` 1 (plain `=`) | gst GUI-package build deps (product) | `USE_EMACS` flips | clang-tools-extra rides with emacs today |
| spimulator | `USE_EMACS`, `BUILD_TREE_SITTER`, `BUILD_DOCS`, `RUN_SANITIZERS` all 1 | — | `USE_EMACS`, `BUILD_DOCS` flip; **tree-sitter + sanitizers stay** | gates exempt |
| texExpToPng | `USE_EMACS` 1 (plain `=`) | TeX (product) | `USE_EMACS` flips | template for billsEmacsConfigs |
| billsEmacsConfigs ×20 | `USE_EMACS` 1 (plain `=`) | TeX + each toolchain | `USE_EMACS` flips (judgement call: Emacs is their point) | one codemod |
| modelviewprojection | `BUILD_DOCS`, `USE_EMACS`, `USE_JUPYTER`, `USE_X_WINDOWS` 1; `USE_SPYDER` 0 | — | `USE_EMACS`, `USE_JUPYTER` flip; **`BUILD_DOCS` (book gate) and `USE_X_WINDOWS` (headless Mesa) stay** | `morePorts` checkout has no `PODMAN_RUN_FLAGS` — verify master |
| runClaudeInContainer (sandbox image) | `USE_EMACS_CONFIG` 1 | `01-install-base.sh` ~460 pkgs | **N/A — excluded** (built on host, launched nested) | proposal dropped 2026-09-12 (`tasks/minimal-sandbox-image.md`) |
| imps/n64 ×4 | — | Ubuntu 22.04/24.04 mirrors of upstream CI | **N/A** — fidelity to CI is the design | |
| impo/openstax ×16 | hardcoded `PODMAN_RUN_FLAGS = --cgroups=disabled` | TeX schemes/collections (product) | **N/A** — nothing to cut | still want the `?=` PODMAN_RUN_FLAGS form |
| Craft, imps, impo | — | no container | **N/A** | |

**Containerized but outside the survey's criterion (no `CLAUDE.md`):** `lldbassemblyhelper` (Fedora 43;
emacs + npm pyright unconditional — would flip), `graphicalcontainer` (a GUI demo box; lean is
meaningless), `multivariate-math/multivariate-math`, `n64/billBuildMM`. Listed so nobody re-surveys.

**Side findings (pre-existing, not part of this work):** `PODMAN_RUN_FLAGS` in its `?= $(if …)` form is
absent from pyNuklear, texExpToPng, programmingFromTheGroundUp, lldbassemblyhelper, graphicalcontainer
and the mvp `morePorts` checkout, although the 2026-08-29 rollout record lists mvp, texExpToPng and
pgu as converted — re-check on `master` before assuming the record is wrong.

## 4. Re-sync check

`grep -ln 'MINIMAL_IMAGE)),0,1)' <mount>/*/Makefile <mount>/*/*/Makefile <mount>/*/client/Makefile` (`<mount>` = where the sandbox mounts your projects)
from the sandbox lists the projects that expose the lean option; a project in §3's "lean variant"
column that is missing from that list has not been done yet (or drifted back). As of 2026-09-27 only
geometricalgebra and hanoi expose it; the rest of §3's table is still a plan, not converted code.
