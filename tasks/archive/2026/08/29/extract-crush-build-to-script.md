# Extract the inline Crush build into `entrypoint/03-build-crush.sh`

**Status:** IMPLEMENTED 2026-08-29 — control-flow verified; full image build is the remaining gate.
`client/entrypoint/03-build-crush.sh` created (mode 755, build-logic comments migrated in); the
Dockerfile now `COPY`s it and `RUN`s it with the three `CRUSH_*` flags passed explicitly (build-logic
comments removed, orchestration comments + breadcrumb kept). Extraction is behaviour-preserving — the
script's commands are verbatim the old inline `RUN`. **Verified deterministically** with stubbed
`go`/`git` in a `fedora:44` container across all three cases: `CRUSH_VENDORED=1` → `cp` + `go build
-mod=vendor -o /usr/local/bin/crush`, **no patch application** (asymmetry preserved); `CRUSH_VENDORED=0`
→ clone + no-update-check patch always + at-import iff `CRUSH_AT_IMPORT=1` + `go install`; final `crush
--version` gate fires. **Remaining (real-machine gate):** a full `make image` (both modes) + the airgap
round-trip (`./vendor.sh` → `make image CRUSH_VENDORED=1`) — deferred (the image is ~22 GB and the
vendored tree needs Go 1.26.5, so a stock `golang` container can't stand in). Staged.
**Priority:** 5
**Difficulty:** 3
**Created:** 2026-08-29 (William Emerison Six <billsix@gmail.com>)

## Why

`client/Dockerfile` already follows the **"host-agnostic setup belongs in a script"** contract for
package installs (`01-install-base.sh`, `02-install-vendor-tools.sh`, each `COPY`'d then `RUN
/usr/local/bin/…`). But the **most important** setup step — building Crush from source — is inlined in
a ~12-line `RUN` (Dockerfile ~lines 77–88):

```dockerfile
RUN set -eux; \
    if [ "$CRUSH_VENDORED" = "1" ]; then \
        cp -r /vendor/crush /tmp/crush; \
        ( cd /tmp/crush && GOPROXY=off go build -mod=vendor -ldflags "-X …version.Version=${CRUSH_TAG}" -o /usr/local/bin/crush . ); \
    else \
        git clone --depth 1 --branch "$CRUSH_TAG" https://github.com/charmbracelet/crush /tmp/crush; \
        git -C /tmp/crush apply /patches/crush-no-update-check.patch; \
        if [ "$CRUSH_AT_IMPORT" = "1" ]; then git -C /tmp/crush apply /patches/crush-at-import.patch; fi; \
        ( cd /tmp/crush && go install -ldflags "-X …version.Version=${CRUSH_TAG}" . ); \
    fi; \
    rm -rf /tmp/crush; \
    crush --version
```

Building Crush from source is host-agnostic "install a tool" setup — the runCrush analog of "building
a pinned dependency from source," exactly the case the contract says belongs in a script. Consequences
of it being inline:

- **Can't build Crush on a bare host** (no podman) by running a script — the build+patch logic is
  buried in a `RUN`.
- **Inconsistent** with this repo's own `01`/`02` scripts, at the step where scripting pays off most.
- The build/patch policy (which patch always applies, which is flag-gated, vendored-vs-clone) isn't a
  legible, teachable, reusable file.

**No build-plumbing reason keeps it inline:** unlike `01`/`02`, this `RUN` does **not** use the
`--mount=type=cache` dnf cache, so nothing ties it to the Dockerfile. `/patches` and `/vendor` are
build-context artifacts, but a bare-host build has the repo checkout with `patches/` and
`entrypoint/vendor/`, so the script runs outside the container too — the whole point.

## Output path — NOT a bug (corrected during implementation)

An earlier draft flagged the two branches installing to different locations. **They don't** — the
Dockerfile sets `ENV GOBIN=/usr/local/bin`, so the non-vendored `go install` lands at
`/usr/local/bin/crush`, same as the vendored `go build -o /usr/local/bin/crush`. Both already land in
the same place; the two mechanisms (`go build -o` vs `go install`+`GOBIN`) were kept as-is for a
behaviour-preserving extraction. `GOBIN` is an `ENV` (inherited by the child script); the three
`CRUSH_*` are `ARG`s (NOT inherited), which is why the `RUN` passes them explicitly.

## Design decisions

- **The script owns the whole branch.** Unlike the package-group case (flag = *which optional groups*,
  Dockerfile owns the `if`), here `CRUSH_VENDORED`/`CRUSH_AT_IMPORT` change the *build method* and it's
  one cohesive "build Crush" operation — so `03-build-crush.sh` reads `CRUSH_TAG` / `CRUSH_VENDORED` /
  `CRUSH_AT_IMPORT` from the environment the Dockerfile exports (via `ARG`→`ENV` or `ARG` in scope) and
  does the vendored/clone dispatch itself. One natural unit, not two flat scripts glued by a `RUN if`.
- **Mirror `02-install-vendor-tools.sh`:** Apache SPDX header, an explanatory comment block (what it
  builds, the vendored/airgap vs clone paths, why `-ldflags` stamps the version instead of
  `go install …@tag`), `set -e`/`set -eux`, and the **final `crush --version` as the real gate**.
- **Stays in the Dockerfile:** the `ARG CRUSH_TAG/CRUSH_VENDORED/CRUSH_AT_IMPORT` declarations, the
  `COPY patches/ /patches/` and `COPY entrypoint/vendor/ …`, and the `RUN /usr/local/bin/03-build-crush.sh`
  that invokes it (with the ARGs in scope so the script sees them).
- **Executable bit:** the new script must be mode **755** (Dockerfile invokes it directly). Commit it
  +x and confirm `git ls-files -s` shows `100755` — a full-file rewrite drops +x (the runCrush SPDX-header
  incident, `CLAUDE.md`).
- **Comment placement — comments follow their code** (move most into the script). The Dockerfile
  currently carries a large comment block (~lines 37–62) explaining the build. Migrate the parts that
  explain the **build logic** into `03-build-crush.sh`, since that's where the logic now lives — and a
  bare-host user runs the *script*, not the Dockerfile, so the "why" must be where they read it (this is
  the convention's intent: a sourced script is meant to *teach*, so comment it well). Move: why it builds
  from source (patches need a source tree; can't `go install …@tag` a patched tree), the `-ldflags`
  version stamp, the two patches (no-update-check **always**, at-import gated), and — most importantly —
  the **patch asymmetry** (the vendored branch applies none; they're pre-baked), sitting right next to the
  `if` that implements it. **Keep in the Dockerfile** the comments about what the Dockerfile still *does*:
  the `ARG` declarations/defaults, how `CRUSH_VENDORED=1` wires to the Makefile's `--volume …:/vendor/crush:ro`
  mount, the `ENV CRUSH_DISABLE_METRICS/DO_NOT_TRACK` telemetry vars, and the `COPY patches/` + `COPY
  entrypoint/vendor/`. **Do NOT strip the Dockerfile bare** — leave a one-line breadcrumb at the `RUN`
  (e.g. `# Build Crush from source (vendored, or clone+patch); see entrypoint/03-build-crush.sh`) so a
  Dockerfile reader knows where the logic went.

## Plan

- [ ] Create `client/entrypoint/03-build-crush.sh` (mode 755, SPDX header, `set -e`) holding the
      vendored/clone dispatch verbatim, reading `CRUSH_TAG`/`CRUSH_VENDORED`/`CRUSH_AT_IMPORT` from env,
      installing to `/usr/local/bin/crush` in **both** branches, `rm -rf /tmp/crush`, `crush --version`.
- [ ] Dockerfile: `COPY entrypoint/03-build-crush.sh /usr/local/bin/`, and replace the inline `RUN` with
      `RUN --network=… set -eux; /usr/local/bin/03-build-crush.sh` (keep the ARGs in scope so the env is
      visible; the non-vendored branch needs network for `git clone`, the vendored branch does not).
- [ ] Prove the extraction changed nothing: diff the *built binary's* `crush --version` and the install
      path before/after; ideally build BOTH modes (`CRUSH_VENDORED=0` default, and `CRUSH_VENDORED=1`
      against vendored sources) and confirm each produces `/usr/local/bin/crush` reporting `${CRUSH_TAG}`.

## Verification

- `make image` (default, `CRUSH_VENDORED=0`) succeeds; `crush --version` reports the pinned tag; binary
  at `/usr/local/bin/crush`. The `crush-no-update-check.patch` is applied (and `crush-at-import.patch`
  when `CRUSH_AT_IMPORT=1`).
- If feasible, the **airgap/vendored** path (`CRUSH_VENDORED=1`) still builds offline — this is the same
  path exercised by [[verify-vendored-airgap-rebuild]]; fold the check in there.
- Cost note: the client image is ~22 GB and builds nested with `--cgroups=disabled --network=host` — a
  real-machine or careful nested build; the vendored path needs the vendored sources present first
  (`make vendor` / `CRUSH_VENDORED=1`).

## Vendoring impact — VERIFIED UNAFFECTED (2026-08-29, read the whole flow)

Traced `vendor.sh` → `client/Makefile` (`image`/`vendor` targets) → `entrypoint/vendor/vendor-crush.sh`
→ Dockerfile. **The extraction does not affect vendoring, provided three invariants are preserved.**

The flow (two separate things — don't conflate):
- **Vendoring PRODUCTION** = `entrypoint/vendor/vendor-crush.sh` (a **separate** script): clone Crush @
  `CRUSH_TAG` (full history) → apply patches (no-update-check always; at-import if `CRUSH_AT_IMPORT=1`)
  → `go mod vendor` → writes `$(VENDOR_DIR)/crush`. Run by `make vendor` inside the image with
  `-v $(VENDOR_DIR):/vendor:Z`. **This is NOT the build `RUN` being extracted — extracting the build
  touches nothing here.** ✓
- **The build (consumer)** — the `RUN` this task extracts — has two modes:
  - `CRUSH_VENDORED=0` (default/online): `git clone` + apply patches + build. This is what runs during
    the **vendoring image build** too (`make vendor`'s `image` prereq builds with the default flags,
    i.e. `CRUSH_VENDORED=0`). A behaviour-preserving extraction keeps it identical. ✓
  - `CRUSH_VENDORED=1` (airgap): `make image` adds `--volume $(VENDOR_DIR)/crush:/vendor/crush:ro
    --build-arg CRUSH_VENDORED=1` (Makefile `CRUSH_VENDOR_FLAGS`); the build `cp -r /vendor/crush
    /tmp/crush` and `GOPROXY=off go build -mod=vendor`, applying **NO patches**. ✓

**Invariants the extracted `03-build-crush.sh` MUST preserve (break any → vendoring/airgap breaks):**

1. **The `CRUSH_VENDORED=1` branch applies NO patches.** The vendored tree is **already patched** by
   `vendor-crush.sh` (its comment says so explicitly). Applying patches again would double-apply →
   `git apply` fails → airgap build breaks. Only the `CRUSH_VENDORED=0` (clone) branch patches.
2. **`cp -r /vendor/crush /tmp/crush` before building.** `/vendor/crush` is a **read-only build
   volume** (`--volume …:ro`), not COPY'd — you must copy it out to a writable dir first. Keep the `cp`.
3. **The `RUN` still provides the volume + the vars.** Keep `CRUSH_VENDOR_FLAGS` in the Makefile
   `image` recipe (so `/vendor/crush` is mounted at build for `CRUSH_VENDORED=1`), and keep the `ARG
   CRUSH_TAG/CRUSH_VENDORED/CRUSH_AT_IMPORT` in scope before the `RUN`. **Pass them to the script
   explicitly** — `RUN CRUSH_VENDORED="$CRUSH_VENDORED" CRUSH_TAG="$CRUSH_TAG"
   CRUSH_AT_IMPORT="$CRUSH_AT_IMPORT" /usr/local/bin/03-build-crush.sh` — rather than relying on
   ARG-as-RUN-env inheritance to reach a child script (bulletproof + self-documenting).

Also unaffected: the output-path unification (vendoring consumes the *source* tree, never the built
binary); `VENDOR_TOOLS`/`hf` (separate, `02-install-vendor-tools.sh`); and `COPY entrypoint/vendor/`
(the vendoring scripts, untouched). The extraction is purely a consumer-side refactor.

**Add to the verification plan:** after extracting, run **`./vendor.sh`** (online) end-to-end and then
a `make image CRUSH_VENDORED=1` from the produced `client/vendor/crush` — the exact airgap round-trip
of [[verify-vendored-airgap-rebuild]] — to confirm both the vendoring image build (clone branch) and
the airgap build (vendored branch, no-patch) still work through the script.

## Cross-links

- `tasks/standardize-project-container-template.md` — this is a concrete instance of the same
  template-standardization work (host-agnostic setup → script).
- [[verify-vendored-airgap-rebuild]] — the airgap build this touches; verify together.
- [[bump-crush-to-v0.90.0]] — adjacent (both touch the Crush build); do this extraction first so the bump
  edits a script, not an inline `RUN`.
- `entrypoint/vendor/vendor-crush.sh` — the *vendoring* script (creates the vendored sources); distinct
  from this *build* script. Keep the names distinct to avoid confusion.

## Open questions

1. **Script-owns-branch vs Dockerfile-if-dispatch** — recommend the script owns the whole
   vendored/clone branch (reads the three env vars), since it's one cohesive build, not a set of
   optional groups. Confirm, or prefer flat scripts + a Dockerfile `if`?
2. **Do the output-path unification (`/usr/local/bin/crush` in both branches) as part of this** —
   recommend yes; it's a real latent bug, cheap to fix while extracting.
