# Binding a C++ library to Python (nanobind) — the traps that cost a day each

Durable, cross-project notes on writing **real bindings** (nanobind; pybind11 is the same shape)
over an existing C++ library so a Python front-end drives the *same* compiled core, verified
byte-identically against the C++ originals (`porting-with-an-output-oracle.md`). Distilled from
the ePiX bindings (github.com/billsix/epix-mirror `python/epix/_epix.cc`, June 2026; the in-project
gotcha list is its `CLAUDE.md`, "Python bindings + notebooks"). Companion to
`cpp-ownership-migration.md` and `print-debugging.md`.

## Bind only symbols the library actually *defines* — check with `nm` first

A method **declared in a header but never compiled** (ePiX: `axis::dec()`) binds fine and makes
the **whole extension module fail at import** with an undefined-symbol error — one bad binding
takes down every other one. Before binding anything, confirm it exists in the archive:

```sh
nm -C /path/to/libX.a | grep ' T ' | grep 'Class::method'
```

Corollary: **bind on demand**, driven by the oracle. Port one demo → it fails on a missing name →
`nm`-check and bind that one thing → re-verify. Binding the whole API up front means debugging
dozens of untested bindings at once.

## Function-pointer parameters need a trampoline

C APIs that take raw function pointers (`P f(double)`, `P F(double,double)`, two- and
three-function forms for parametric plots/surfaces) can't take a Python callable directly. The
pattern: a **module-global `nb::callable`** plus a **C trampoline** that calls it. One call at a
time (set global → call the C++ entry point → clear), which is fine for figure construction and
wrong for anything concurrent — say so in the binding.

**Objects that *sample* the function pointer at construction must build eagerly.** ePiX's
`scenery` samples its surface (and captures the current fill state) when added, so the Python
wrapper builds the C++ object immediately inside the trampoline window and **holds no callable
afterwards** — correct per-surface colours, no reference cycle for the GC to find.

## Dispatch 2-arg vs 3-arg callables by `inspect.signature`, never a trial call

Several C++ overloads share one Python signature (`plot(f, domain)` with `f` taking 1 or 2
arguments; `surface(..., color)`). Count parameters with `inspect.signature`. A probe call
(`f(0, 0)`) **cannot distinguish "wrong arity" from "the function raised at the probe point"**
(a `1/0` at the probe input looked like an arity mismatch). Caveat: nanobind-bound functions report
`(args, kwargs)` → 2 parameters, so when a *bound* function needs the 3-argument form, pass a
strict-arity lambda (`lambda x, y, z: epix.Point(x, y, z)`).

## Overloads resolve in registration order

nanobind (and pybind11) try overloads **in the order registered**. To add `arrow(tail, head, scale)`
without disturbing the existing 2-argument `arrow(tail, head)` (which routes to a different C++
form), register the new one **after** and give the distinguishing parameter **no default**, so a
2-argument call can never fall into the 3-argument overload.

## Hidden global state: one process per case, fork per frame

Libraries of this vintage accumulate per-render global state with no public reset (ePiX: the
colour palette). A naive in-process loop leaks state into later renders. Verification runs **one
case per process**; animations **`fork()` per frame** (as the native `flix` tool does). Details
and the harness shape: `porting-with-an-output-oracle.md`.

## Rename the API for Python; keep the C++ names as the oracle

Bind under the C++ names first (so the oracle comparison is a straight transliteration), then
rename the public Python surface to Python conventions as a separate, verified pass: CapWords
types (`P` → `Point`), snake_case functions, keyword arguments for every multi-scalar call
(`sph(radius=, theta=, phi=)`), readable `nb::arg` names instead of the C++ parameter
abbreviations (`sw`/`ne` → `lower_left`/`upper_right`). Type annotations in the notebooks are free:
they don't execute (`from __future__ import annotations`), so they can't change the output.

## Run the bound surface under ASan — a new caller exposes latent UB

A binding exercises the library in orders and lifetimes the original drivers never did. ePiX's
`screen::screen()` left its pimpl pointer uninitialized; it "worked" for 20 years because the
canvas lived in zero-initialized static storage, and the bindings' call pattern exposed it. The
fix was a default member initializer (`screen_data* m_screen = nullptr;`). Keep a **sanitizer
smoke test that mirrors the bound surface** (`build-aux/asan_smoke.cc` — every binding you add,
add a call there) and run it as you grow coverage; `print-debugging.md` has the ASan/gdb oracle
method, `cpp-ownership-migration.md` the lifetime traps.

## Build the extension against the *live* library, not the installed one

In a container workflow where each `make` target is a separate `podman run --rm`, a
`meson install` from one target does not survive into the next. Link the extension against the
**bind-mounted build tree's** `libX.a` when present (so edited C++ reaches the binding), falling
back to the image's installed copy only for a fresh image — and skip the relink when the `.so` is
newer than both inputs (`FORCE=1` to override). Standalone build, no CMake: `g++ -shared -fPIC
-std=c++20 -fvisibility=hidden _binding.cc nanobind/src/nb_combined.cpp libX.a`, with nanobind's
`include_dir()` and `ext/robin_map/include` on the include path.
