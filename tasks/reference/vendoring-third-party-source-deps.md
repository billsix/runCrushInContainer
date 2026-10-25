<!-- SHARED, MIRRORED REFERENCE DOC -- keep the runClaudeInContainer and
     runCrushInContainer copies byte-identical. Canonical:
     runClaudeInContainer tasks/reference/vendoring-third-party-source-deps.md
     (github.com/billsix/runClaudeInContainer). -->

# Vendoring third-party deps as committed source — the `update-<dep>` pattern

How a project that vendors third-party dependencies **as committed source** (no package
manager pulls them — the C/C++ norm) gets a repeatable, host-runnable way to re-fetch and
bump each one from its canonical upstream. This is the detail behind the Makefile-contract
bullet "`update-<dep>` targets for third-party deps vendored BY SOURCE" in the personal
overlay (`ai-coding-conventions.personal.md`). Written 2026-10-25 (William Emerison Six
<billsix@gmail.com>), generalized from the hanoi C++ subproject and the Craft 9-dep tree.

## When this applies (and when it does NOT)

- **Applies:** a dep whose source is **committed into the repo** because nothing else pulls
  it — Dear ImGui, SQLite (the amalgamation), GLFW, gl3w, LodePNG, tinycthread, noise, a
  bundled libcurl, etc. The pin lives only in git history (there is usually no lockfile), so
  without a target, bumping one means a hand `git clone` + copy that no one records.
- **Does NOT apply:** package-manager ecosystems — Rust/Cargo, Go modules, Python/pip, npm.
  Those pin + fetch through the manager and its lockfile, already covered by the
  "Self-contained images + live source" convention. They need **no** `update-<dep>` target.

This is the sibling of **`make update-emacs-packages`** (both refresh a committed/vendored
thing from upstream) and the controlled way to bump what the self-contained-image rule keeps
offline-reproducible.

## The three pieces

1. **The shared helper, `tools/update_dep_common.sh`** — vendored into the project's `tools/`
   from the canonical copy (`runClaudeInContainer tasks/reference/update_dep_common.sh`, mirror
   in runCrush), exactly like `check_local_annotations.py`. It is **sourced, not run**, and
   carries the `SHARED, VENDORED TOOL` banner (keep every copy byte-identical; edit the
   canonical, re-copy). A project with **one** vendored dep can skip the helper and write a
   single standalone script instead (see hanoi below).
2. **A per-dep `tools/update-<dep>.sh`** — `set -euo pipefail`, source the helper, run that
   dep's recipe. Repo-relative (derives paths from its own `BASH_SOURCE`), so it runs on the
   **host** from any checkout with just git/curl/unzip/python3 + cp — no container.
3. **A `make update-<dep> <DEP>_REF=<ref>` target** — `## `-documented, guards its own `*_REF`
   variable (`@[ -n "$($(DEP)_REF)" ] || { echo usage; exit 2; }`), calls the script. The ref
   is an env-var-style make variable so one target bumps to any branch / tag / SHA.

## `VENDOR_ROOT` — where the vendored deps live

The helper writes to `$REPO_ROOT/$VENDOR_ROOT/<depname>`. `VENDOR_ROOT` defaults to **`deps`**
(the common layout, e.g. Craft's `deps/<name>`). A project that vendors a dep **at the repo
root** (e.g. hanoi's `cpp/imgui/`) exports `VENDOR_ROOT=.` before sourcing the helper. That is
the only knob needed to reuse the same helper across both layouts.

## The helper API

- **`clone_ref <url> <ref> <dest>`** — full (non-shallow, so a SHA works) clone + checkout.
- **`vendor_archive <depname> <url> <ref>`** — replace the dep's dir from `git archive` of the
  ref: the "release" view honouring `.gitattributes export-ignore` (drops `.git`/CI, keeps
  `.gitignore`), matching how upstream release tarballs are cut. **The default for whole-tree
  deps** (imgui, glfw, curl) — byte-closer to a vendored snapshot than a working-tree copy.
- **`replace_tree <depname> <srcdir>`** — replace the dep's dir wholesale from a local dir
  (minus VCS), for when the source is produced locally (e.g. gl3w after its generator runs).
- **`copy_files <depname> <srcdir> <relpath>...`** — overwrite just the named files, each to
  its **basename** (flattened), for curated small-file deps (sqlite amalgamation; a lone
  `noise.c/.h`; `source/tinycthread.c` → `tinycthread.c`).
- **`show_version <depname/relheader> <pattern>`** — print the first matching header line so
  the script reports the version it vendored (`IMGUI_VERSION`, `SQLITE_VERSION`,
  `LIBCURL_VERSION`, `GLFW_VERSION_*`, …); non-fatal when a dep has no macro (pin by commit).

## The per-dep recipe shapes

- **Whole upstream tree, git:** `vendor_archive <name> <url> <ref>`. (imgui/glfw/curl.)
- **Curated file subset, git:** `clone_ref` into a tmp dir, then `copy_files` (or a direct
  `cp` for sub-dirs the helper's basename-flatten can't express — see hanoi's imgui below).
- **Amalgamation download (no git):** `curl` the release zip + `unzip` + `copy_files`. SQLite's
  URL embeds the release **year** (`https://sqlite.org/<year>/sqlite-amalgamation-<3MMPP00>.zip`);
  `download.html` lists only the current release, so bumping-to-latest can auto-detect the year
  but **pinning an older version needs the year passed in** (`SQLITE_YEAR=`).
- **Generated source:** `clone_ref`, run the generator (gl3w → `python3 gl3w_gen.py` against the
  Khronos registry), then `replace_tree`. A bump here **intentionally** refreshes generated
  coverage, so re-vendoring the current pin is **not** byte-idempotent — expected, not a bug.
- **Upstream-shape adaptations the recipe must encode** (these bit on first run): LodePNG ships
  `lodepng.cpp` but a C project vendors it as `lodepng.c` (rename + drop upstream's `Makefile`);
  whole-tree `git archive` can leave cosmetic CRLF on example `.vcxproj` files the project never
  compiles — review, don't chase.

## Verify idempotent, and record the pin

- **Idempotency check:** run `update-<dep>` with the **current** pin → `git diff <vendordir>`
  must be **empty** (proves the fetch + copy overwrite cleanly). The two exceptions above
  (gl3w's regeneration; whole-tree CRLF on uncompiled examples) are known and documented.
- **Record the pin in git:** commit each bump as subject **`<dep> <ref>`** — since source
  vendoring has no lockfile, the commit subject *is* the provenance (`git log --oneline --
  <vendordir>`).

## Worked examples

- **Craft** (`github.com/billsix/Craft`, `tasks/add-dep-update-targets.md`) — 9 deps under
  `deps/` (default `VENDOR_ROOT`), one `update-<dep>` each: imgui/glfw/curl via `vendor_archive`,
  sqlite via amalgamation download, gl3w via generator + `replace_tree`, lodepng/noise/
  tinycthread via `copy_files`. sqlite + lodepng verified byte-idempotent.
- **hanoi C++ subproject** (`github.com/billsix/towersofhanoi`, `cpp/tools/update-imgui.sh`) —
  the **single-dep standalone** variant: imgui is the only vendored dep and it sits at the repo
  root (`cpp/imgui/`, so `VENDOR_ROOT=.` if it used the helper), and it vendors a **curated
  subset with a `backends/` sub-dir** (which `copy_files`' basename-flatten can't express), so a
  one-off script with direct `cp` is clearer than sourcing the helper. The helper earns its keep
  with several deps, not one.

## Provenance

Canonical helper + this doc live in `runClaudeInContainer tasks/reference/`, mirrored
byte-identically in `runCrushInContainer tasks/reference/`. Edit the canonical, re-copy to the
mirror and to each project's `tools/`.
