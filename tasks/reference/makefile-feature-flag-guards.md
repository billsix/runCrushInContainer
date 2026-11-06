# Guarding feature-flag-gated make targets with a helpful preflight

Durable pattern for the container-per-project template. States what's true, not what to do next.

## The problem

Template projects gate optional image content behind build-time feature flags (`USE_JUPYTER`,
`BUILD_DOCS`, `USE_LEAN`, `USE_EPIX`, `USE_GRAPHICS`, `USE_SPYDER`, …) read at `make image` time.
A *run* target (`make jupyter`, `make docs`, `make lean`) then starts a container and runs the
gated tool. If the image was built without that feature, the tool is absent and the user gets a raw
`exec: "jupyter": executable file not found` / shell `command not found` — a cryptic failure with
no hint about which flag turns it back on.

The fix: a **preflight guard** at the top of the gated target that detects the missing capability
and prints a specific, actionable error — the capability, the flag, and the exact command to get it
back — then exits nonzero.

## Two detection mechanisms — pick by target structure

The guard must answer "is this capability actually in the image?" Two ways, and which is correct
depends on whether the target rebuilds the image:

1. **Flag echo** — `@[ "$(FLAG)" = 1 ] || { …; exit 2; }`. Correct **when the target has an
   `: image` prerequisite and `image` is `.PHONY`** (the fleet norm): `make docs` re-runs
   `podman build` with the *current* flags before the recipe, so `$(BUILD_DOCS)` genuinely reflects
   what the image will contain. Makefile-only, no container start. Used by gacalc, spimulator, hanoi.
2. **Runtime capability probe** — `command -v <sentinel>` inside the image; if absent, print and
   exit 2. Correct **when the target runs against a pre-built image without rebuilding it** (no
   `: image` prereq, e.g. targets wired to a bare `$(RUN)`): there the make variable can't reflect
   what was actually baked, so you must ask the image. The probe also catches the
   built-lean-then-run-plain case the flag echo misses. Used by **epix-mirror** (its `examples`/
   `examples-anim`/`jupyter`/`notebooks` scripts probe `command -v latex|jupyter|jupytext`).

A third mechanism already in the fleet: `update-emacs-packages` forces `$(MAKE) image USE_EMACS=1`
as a prerequisite (force-the-flag-and-rebuild). Fine for a cheap image; too heavy to auto-trigger
for a 7 GB Lean image, so not the general answer.

## The message — name the capability, then set-the-flag → rebuild → re-run

These are **build-time** flags: the fix is to get the flag set when `make image` runs. The
maintainer's preferred message (William Emerison Six <billsix@gmail.com>, 2026-11-06) walks the user
through the persistent path:

    ERROR: make docs needs the Sphinx + TeX docs toolchain,
           gated by the build-time flag BUILD_DOCS (currently BUILD_DOCS=0).

    Enable it persistently, then rebuild and run:
      echo 'export BUILD_DOCS=1' >> ~/.bashrc && source ~/.bashrc
      make image
      make docs

    (This session only: run  export BUILD_DOCS=1  instead of the echo/source line.)

**An exported env var genuinely works** (this was verified; my first draft wrongly said "never an
env var"). In GNU Make an environment variable has origin `environment`, which `?=` treats as
already-defined, so it **overrides the `?=` default** — even the `?= $(if $(filter
1,$(MINIMAL_IMAGE)),0,1)` form. So `export BUILD_DOCS=1` makes the next `make image` build the
feature in, and the flag-echo guard then reads the same value and passes. The one thing that does
**not** work is exporting the flag and *skipping* the rebuild on a stale image — which can't happen
for a target with an `: image` prereq (it rebuilds). `make image BUILD_DOCS=1` on the command line
is the one-shot equivalent.

Message details: show the live value with `(currently BUILD_DOCS=$(BUILD_DOCS))` — make expands it.
Caveat worth knowing (not in every message): `~/.bashrc` persists across sessions only for a bash
login shell; a zsh host needs `~/.zshrc`, though `source ~/.bashrc` still applies it to the current
session since `export FOO=1` parses in both. Where a target needs two flags (gacalc `docs` →
`BUILD_DOCS` + `USE_EPIX`) use one combined guard so the user sets both at once rather than hitting a
second error after the first rebuild.

## How this compares to autoconf/automake (the detect/record/fail-fast model)

The GNU autotools treat a missing capability as a **configure-time, detected, recorded, fail-fast**
condition — the opposite of trusting a flag at build time:

1. **Detection, not assumption.** `./configure` probes the real system (`AC_CHECK_PROG`,
   `AC_CHECK_LIB`, `AC_CHECK_HEADER`, `PKG_CHECK_MODULES`). It never assumes a feature is present
   because a variable says so.
2. **Fail-fast with a fixable message.** A missing *required* dep aborts configure immediately —
   `configure: error: GL/gl.h not found; install mesa-libGL-devel` — naming the missing thing and
   how to get it. You never reach `make` in a broken state.
3. **The decision is recorded in an artifact.** Optional features are written to `config.status` /
   `config.h` (`#define HAVE_JUPYTER 1`) and Makefile vars (`AC_SUBST`, `AM_CONDITIONAL`); `make`
   then trusts a verified, recorded fact, not a flag the user might re-type.
4. **automake's `missing` script** is the direct analogue of this pattern: when a maintainer tool
   (autoconf, help2man) is absent it prints `WARNING: 'autoconf' is missing on your system …`
   instead of a raw `command not found`.

Mapped onto the podman-image fleet:
- `make image --build-arg FLAG=…` is our "configure step" — but nothing *detects* anything; the
  flags are *assumed* from Makefile defaults. The gap autoconf closes by recording detection in
  `config.status` is what the two mechanisms above close in their own ways:
- The **capability probe** is the practical autoconf analogue (`AC_CHECK_PROG`, deferred to run
  time) — detect the artifact's real capability instead of trusting the user's word.
- The **flag echo** leans on the `: image` rebuild to make the flag an honest proxy for the image —
  acceptable only because the rebuild reconciles the two, where autoconf would have recorded it.
- A fourth option not used here, the closest *structural* analogue of `config.h`: bake a feature
  manifest into the image (`LABEL …feature.docs=$BUILD_DOCS`) and read it back with `podman inspect`
  — the image recording its own build-time decisions. Rejected for this fleet (needs a Dockerfile
  edit + rebuild in every repo; the `: image` targets don't need it).
- Our error message mirrors autoconf's: **name the missing capability and the exact command to
  obtain it**, not a bare flag echo.

## Worked examples

- Flag echo (`: image` targets): github.com/billsix/geometricalgebra `make jupyter`/`docs`/`lean`
  (docs guards both `BUILD_DOCS` and `USE_EPIX`), github.com/billsix/spimulator `make html`/`pdf`/
  `epub`, github.com/billsix/towersofhanoi `make docs`.
- Capability probe (run-against-prebuilt): github.com/billsix/epix-mirror
  `entrypoint/examples.sh`/`examples-anim.sh`/`jupyter.sh`/`percentToIpynb.sh` — the existing model
  that predates and informed this pattern.

Not applicable: a target whose tool is **always** installed (no gating flag) — e.g.
github.com/billsix/multivariate-math `make jupyter`/`pdfs` (JupyterLab + TeX are unconditional).
