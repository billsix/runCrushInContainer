# Porting against an output oracle — byte-identical when the same engine runs both sides

Durable, cross-project notes on verifying a **port** (a new front-end, a new build system, a
language translation, a modernization pass) by comparing its **output text** against the original's,
rather than by reading the code or eyeballing pictures. Distilled from the ePiX work
(github.com/billsix/epix-mirror, June 2026: autotools→Meson, C++03→C++20 with `enum class`, and
nanobind Python bindings with 80 notebooks each byte-identical to its C++ sample), but the shape
is general. Companion to `print-debugging.md` ("derive the before mechanically; diff outputs") and
`codegen-conventions.md` (which argues for *equivalence*, not byte identity — see the first section
for how the two reconcile). The in-project record is epix-mirror
`tasks/reference/verification-and-container-method.md`.

## Byte identity or equivalence? Decide by who produces the bytes

- **Same engine on both sides → demand byte identity.** When the port is a new *driver* of the same
  compiled core (Python bindings calling the C++ library; a Meson build of the same sources; a
  modernized library whose enum values are unchanged), every byte of output is produced by code you
  did not rewrite, so any difference is a real bug in the port. Set the bar at **exact text
  equality** and treat a one-character diff as a failure. ePiX: 96 figures, 0 differences, three
  times over (Meson port, modernization, bindings).
- **A formatter or unparser sits between you and the bytes → demand equivalence.** When the new side
  emits *canonical* form (an AST pretty-printer, `ruff format`, a serializer with its own wrapping),
  byte identity is unattainable without a one-time re-baseline; compare structure + behaviour
  instead (`codegen-conventions.md`).
- The question to ask before choosing: *if the two outputs differ by one byte, can that ever be
  benign?* If no, byte identity. If yes, you need an equivalence relation and a harness that
  implements it.

## Compare deterministic text, never rasterized pixels

Pick the **earliest deterministic textual artifact** in the pipeline and compare that. ePiX emits
LaTeX picture macros (eepic) before any TeX/dvips/ghostscript run; the eepic text *is* the figure,
and comparing it is exact, fast, and needs none of the heavy render toolchain (only `g++` and the
library). Pixels (after rasterization) carry anti-aliasing fuzz, font-hinting and version drift
that would make an exact comparison brittle and an approximate one unconvincing.

Two things to do to the text before comparing:

- **Strip volatile lines** (generation timestamps, tool version banners, absolute temp paths) —
  explicitly, by pattern, and say so in the harness.
- **Force the output format on the oracle side.** If a source can pick its own backend (ePiX
  samples may call `pst_format()`/`tikz_format()`), compile the oracle with the format pinned
  (`-DEPIX_FMT_EEPIC`) so both sides emit the same dialect and the comparison tests the port,
  not the format choice.

## One process per case when the library keeps global state

Many C/C++ libraries accumulate **hidden global state with no public reset** (ePiX: the colour
palette in `picture_data::m_palette` grows per render; drawing state persists). Then:

- **Run one case per process** in the verification harness. A second case in the same process
  inherits the first's state and produces a *silent* diff that looks like a port bug. ePiX's
  `verify_ports.py NAME` takes one name and `os._exit`s; the batch is a shell loop.
- **Fork per frame for animations** (or anything that renders repeatedly). Match what the native
  tool does — `flix` runs a fresh process per frame — so the port's `animate()` forks per frame:
  build + emit in the child, collect in the parent. (Caveat: `fork()` inside a threaded Jupyter
  kernel is a runtime risk to note.)
- **Pay container startup once per batch, not per case.** The expensive unit is `podman run`;
  the cheap unit is a fresh interpreter. Start one container, loop over cases inside it with a
  fresh process each, and mount a scratch dir for logs (anything written only inside the
  container dies with it).

## Floating-point text identity needs the same *expression structure*, not just the same math

When the output is printed floating-point and the port translates arithmetic between languages,
algebraically equal is not enough — the last printed digit depends on the rounding of each
intermediate. Three rules that each caused a silent diff in ePiX:

- **Reproduce constant folding as the source wrote it.** C's `5*M_PI_4` is `5*(math.pi/4)` in
  Python, **not** `5*math.pi/4` — the two products round differently.
- **Preserve grouping and associativity of sums.** `0.25*(p1+(p3+(p5+p7)))` must keep that
  nesting; a flattened `p1+p3+p5+p7` is a different sequence of roundings.
- **Check overloaded-operator precedence.** Python's `^` (bound to a cross product) binds *looser*
  than `+`/`-`, so `(b-a)^(d-a)` needs the parentheses the C++ `(b-a)*(d-a)` never needed.

Painter's-algorithm sorts port faithfully if you mirror build/sort/draw order exactly: Python's
stable `list.sort(reverse=True)` matches C++ `stable_sort` with `>` by construction.

## Run the harness, don't eyeball — and bind/port on demand

- **Verify every case with the harness, not by looking at a PNG.** The harness prints `PASS` /
  `FAIL` per case and exits nonzero on any failure, so it can gate a batch.
- **Work from the failures.** Port one case → it fails on a missing symbol / wrong digit → fix that
  one thing → re-verify. Don't try to translate the whole API up front; the oracle tells you the
  order of work (`print-debugging.md`: the tool is the to-do list).
- **Keep the originals as the permanent oracle.** The port is additive; the C++ samples stay in the
  tree exactly so the harness can always be re-run.

## Keep the old build alive until the new one passes the oracle

For a build-system port (autotools→Meson), run both in parallel until the new build reproduces
the render oracle (ePiX: 96/97 figures, 11/11 animations, identical to autotools) and the install
tree matches, then delete the old build in one commit — it stays in git. The old build is the
oracle for the new one; don't cut it over on "it compiles".
