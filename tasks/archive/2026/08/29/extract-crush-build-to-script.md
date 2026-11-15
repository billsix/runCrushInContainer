# Extract the inline Crush build into `entrypoint/03-build-crush.sh`

**Status:** complete
**Completed:** 2026-08-29
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

## What this did

Moved the Crush build-from-source out of an inline ~12-line `RUN` in `client/Dockerfile` into
`client/entrypoint/03-build-crush.sh` (mode 755, SPDX header), following the "host-agnostic setup
belongs in a script" contract that `01-install-base.sh` and `02-install-vendor-tools.sh` already
followed. Building Crush is a "build a pinned dependency from source" step, so it can now run on a bare
host from the repo checkout (`patches/`, `entrypoint/vendor/`), and the build/patch policy is a legible
file. Nothing tied it to the Dockerfile: the `RUN` used no dnf cache mount.

The extraction was behaviour-preserving: the script's commands were verbatim the old `RUN`.

## Decisions

- **The script owns the whole vendored/clone branch.** Unlike package groups (flag = which optional
  groups, Dockerfile owns the `if`), `CRUSH_VENDORED` / `CRUSH_AT_IMPORT` change the build *method* of
  one cohesive operation, so the script reads `CRUSH_TAG` / `CRUSH_VENDORED` / `CRUSH_AT_IMPORT` from
  the environment and dispatches itself.
- **The three `CRUSH_*` are passed explicitly** (`RUN CRUSH_VENDORED="$CRUSH_VENDORED" CRUSH_TAG=… 
  /usr/local/bin/03-build-crush.sh`): they are `ARG`s, which a child script does not reliably inherit;
  `GOBIN` is an `ENV` and is inherited.
- **No output-path change.** An earlier draft flagged the two branches as installing to different places
  and proposed unifying them; that was wrong. `ENV GOBIN=/usr/local/bin` puts the clone branch's
  `go install` at `/usr/local/bin/crush`, the same place as the vendored `go build -o`. Both mechanisms
  were kept as they were.
- **Comments followed their code.** The build-logic commentary (why build from source, the `-ldflags`
  version stamp, no-update-check always vs at-import gated, and the patch asymmetry) moved into the
  script beside the `if` that implements it. The Dockerfile kept the comments about what it still does
  (`ARG` defaults, the `CRUSH_VENDORED=1` → `--volume …:/vendor/crush:ro` wiring, the telemetry `ENV`s,
  the `COPY`s) plus a one-line breadcrumb at the `RUN`.

## Vendoring invariants (traced 2026-08-29; the extraction preserved all three)

Vendoring *production* is the separate `client/entrypoint/vendor/vendor-crush.sh` (clone, patch,
`go mod vendor`) and was untouched; this task only changed the consumer side.

1. The `CRUSH_VENDORED=1` branch applies **no** patches: the vendored tree is already patched, and
   re-applying would make `git apply` fail.
2. It does `cp -r /vendor/crush /tmp/crush` first: `/vendor/crush` is a read-only build volume.
3. The Makefile's `CRUSH_VENDOR_FLAGS` still mounts the volume at build, and the `ARG`s stay in scope.

## Verification

- Control flow verified 2026-08-29 with stubbed `go`/`git` in a `fedora:44` container across all three
  cases: `CRUSH_VENDORED=1` → `cp` + `go build -mod=vendor -o /usr/local/bin/crush` with no patching;
  `CRUSH_VENDORED=0` → clone + no-update-check patch + at-import iff `CRUSH_AT_IMPORT=1` + `go install`;
  the final `crush --version` gate fires.
- The default (`CRUSH_VENDORED=0`) real build was not run in this task (the image is ~22 GB); every
  later `make image` goes through this script, including the rebuilt image the maintainer verified
  2026-09-22 (`tasks/archive/2026/09/22/crushrc-startup-failure-and-model-preselect.md`).
- Not done here: the airgap round-trip (`./vendor.sh` → `make image CRUSH_VENDORED=1`). It belongs to the
  open task `tasks/verify-vendored-airgap-rebuild.md`.

## Related

- `tasks/standardize-project-container-template.md` — the broader template-standardization work.
- `tasks/verify-vendored-airgap-rebuild.md` — the airgap build this touches.
- `tasks/bump-crush-to-v0.90.0.md` — adjacent; the bump now edits the script, not an inline `RUN`.
- `client/entrypoint/vendor/vendor-crush.sh` — the vendoring script, distinct from this build script.
