#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# SHARED, VENDORED TOOL -- keep every copy byte-identical.
# Canonical: runClaudeInContainer tasks/reference/update_dep_common.sh
#   (github.com/billsix/runClaudeInContainer). Edit the canonical, then re-copy
#   it over every vendored copy.
# Vendored into a project's tools/ when it vendors SEVERAL third-party deps as
#   committed SOURCE (the C/C++ norm -- no package manager pulls them: imgui,
#   sqlite, glfw, gl3w, lodepng, ...). Each dep gets its own tools/update-<dep>.sh
#   that sources this and runs its recipe, plus a `make update-<dep> <DEP>_REF=<ref>`
#   target. A project with ONE such dep can skip this helper and write a single
#   standalone script (e.g. hanoi's cpp/tools/update-imgui.sh).
# NOT for package-manager ecosystems (Cargo/Go modules/pip/npm) -- those pin via
#   a lockfile already; see the "Self-contained images + live source" convention.
# Full pattern + per-dep recipes: tasks/reference/vendoring-third-party-source-deps.md
# ---------------------------------------------------------------------------
#
# This file is SOURCED, not run directly. A per-dep update-<dep>.sh does:
#     set -euo pipefail
#     source "$(dirname "${BASH_SOURCE[0]}")/update_dep_common.sh"
#     ...then its recipe, using the helpers below...
# Everything is repo-relative (derived from this file's own location) so the
# scripts run on the HOST from any checkout -- they need only the usual tools
# (git, curl, unzip, python3) + cp; no container.

# Repo root = one dir above tools/ (this file lives in tools/).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Where the vendored deps live, RELATIVE to the repo root. Default `deps/` (the
# common C/C++ layout, e.g. Craft's deps/<name>). A project that vendors a dep
# at the repo root (e.g. hanoi's cpp/imgui/) exports VENDOR_ROOT=. before
# sourcing this, so the destination is $REPO_ROOT/<name>.
VENDOR_ROOT="${VENDOR_ROOT:-deps}"
DEPS="$REPO_ROOT/$VENDOR_ROOT"

# clone_ref <url> <ref> <dest>
#   Full clone (NOT shallow, so an arbitrary commit SHA can be checked out) then
#   check out the ref (a branch, tag, or SHA).
clone_ref() {
    git clone --quiet "$1" "$3"
    git -C "$3" checkout --quiet "$2"
}

# vendor_archive <depname> <url> <ref>
#   Replace $VENDOR_ROOT/<depname> with the ref's tree via `git archive` -- the
#   "release" view that honours .gitattributes `export-ignore` (drops .git and
#   CI/.github while KEEPING .gitignore). This matches how upstream release
#   tarballs / vendored snapshots are produced, so it reproduces the trimmed
#   vendored tree rather than a raw working-tree checkout. For whole-tree deps.
vendor_archive() {
    local name="$1" url="$2" ref="$3" clone
    clone="$(mktemp -d)"
    git clone --quiet "$url" "$clone"
    rm -rf "${DEPS:?}/$name"
    mkdir -p "$DEPS/$name"
    git -C "$clone" archive --format=tar "$ref" | ( cd "$DEPS/$name" && tar -xf - )
    rm -rf "$clone"
}

# replace_tree <depname> <srcdir>
#   Replace $VENDOR_ROOT/<depname> wholesale with <srcdir>'s contents, minus any
#   VCS dir (--exclude-vcs drops .git/.svn/...). Use when the source is already a
#   local dir -- e.g. after clone_ref + a generator step (gl3w) -- rather than a
#   git ref to archive.
replace_tree() {
    local name="$1" src="$2"
    rm -rf "${DEPS:?}/$name"
    mkdir -p "$DEPS/$name"
    ( cd "$src" && tar --exclude-vcs -cf - . ) | ( cd "$DEPS/$name" && tar -xf - )
}

# copy_files <depname> <srcdir> <relpath>...
#   Overwrite just the named files in $VENDOR_ROOT/<depname>, each copied to its
#   BASENAME (flattened). For the "curated small file set" deps (an amalgamation:
#   sqlite3.c/.h; a single noise.c/.h; source/tinycthread.c -> tinycthread.c).
copy_files() {
    local name="$1" src="$2"
    shift 2
    local f
    for f in "$@"; do
        cp "$src/$f" "$DEPS/$name/$(basename "$f")"
    done
}

# show_version <depname/relheader> <pattern>
#   Print the first line of a vendored header matching <pattern> (a grep -E
#   regex), so the script can report the version it just vendored. Non-fatal if
#   absent (some deps have no version macro -- pin those by commit).
show_version() {
    grep -m1 -E "$2" "$DEPS/$1" 2>/dev/null | sed 's/^[[:space:]]*//' \
        || echo "(version line '$2' not found in $1)"
}
