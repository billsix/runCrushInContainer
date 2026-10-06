# Modernizing a legacy C++ library's build and standard — Meson port, pinned `-std`, `enum class`

Durable, cross-project notes from bringing a 2000s-era C++ library (ePiX,
github.com/billsix/epix-mirror, June 2026: autotools→Meson, unpinned→C++20, unscoped→`enum class`,
tree-wide clang-format) into the present **without changing a byte of its output**. The work
records are epix-mirror `tasks/archive/2026/06/09/{port-to-meson,modernize-cxx-standard}.md`.
Companion to `cpp-ownership-migration.md` (the ownership half of modernization, from SMC) and
`porting-with-an-output-oracle.md` (how "no output change" was proven). SMC's game-specific
worked example is `smc/tasks/reference/refactoring-to-modern-cpp.md`.

## Autotools → Meson

- **Take the source and header lists from `Makefile.am`, never from `ls *.cc`.** ePiX had
  `fmt_template.cc` sitting in the tree, `#include`-ing a header that doesn't exist — dead code
  that autotools never compiled. `ls` would have broken the build; `libepix_a_CXXSOURCES` was the
  truth (78 sources, 87 headers; the install set excluded two more). Put the lists in
  `meson.build` as the new authoritative manifest and say so in the project `CLAUDE.md`.
- **Before dropping autoconf feature checks, grep for their consumers.** `AC_HEADER_STDC`,
  `AC_C_CONST`, `AC_CHECK_FUNCS(strtod)` and friends are vestigial *only if* no `config.h`,
  `HAVE_*` or `STDC_HEADERS` is referenced in any source. Confirm, then drop them and emit no
  config header at all.
- **Templates (`*.in`) map to `configure_file(configuration: conf)`** with the same `@var@`
  syntax. Gotchas: configuration keys are **case-sensitive** and must match the token
  (`pkglibdir`, not `PKGLIBDIR`); substituted paths must be the **absolute, prefix-joined**
  values the autotools scripts baked in; Meson has **no built-in `docdir`** — compute it.
  Replace `AC_PROG_*` with `find_program()` and `--with-*`/`--enable-*` with `meson.options`.
- **Wrap generators that write into the source tree.** `make_header` hard-wrote `./epix.h`; a
  tiny `build-aux/gen_header.sh` redirects it to Meson's `@OUTPUT@` so the build stays
  out-of-source.
- **Committed generated artifacts let an optional heavy target build without its toolchain.**
  The 29 `.eepic` figures the manual `\input`s are committed, so `-Dmanual=true` needs only
  LaTeX, not an epix run. Keep heavy optional targets **off by default**.
- **Run both builds in parallel until the new one passes the oracle**, then delete the old build
  files in one commit (they stay in git). The oracle: render every sample with both and diff
  (`porting-with-an-output-oracle.md`); also diff the install trees and confirm zero leftover
  `@tokens@` in generated scripts.

## Pinning the standard — there may be *two* of them

1. **The library's own standard**: `default_options: ['cpp_std=c++NN']` in `meson.build`. An
   unpinned build compiles at whatever the installed compiler defaults to — non-reproducible.
2. **Any *downstream* compile against the installed headers.** ePiX's `epix`/`flix` drivers
   compile the user's `.xp` at runtime with `g++` and **no `-std`**. The moment the public headers
   use C++NN features, user code must compile at ≥ C++NN too, so the drivers (templates) must
   bake the matching `-std`. This coupling is the main correctness gotcha of a standard bump;
   look for it in any project that ships headers consumed by a separate compile.

Choose the floor by what the modernization needs: C++17 covers `override`/`nullptr`/`using`/
range-`for`/`= default`; C++20 adds `using enum` (below). Don't buy a higher standard than the
work uses.

## Mechanical tiers first, API-affecting last

Survey before touching anything (counts of `virtual` without `override`, `typedef`, `0`-as-null,
C-style loops, unscoped enums) so the plan has denominators. Then:

- **Tier 1, mechanical, output-neutral:** `override` on every override (the compiler then checks
  signature drift — ePiX had ~95 unmarked), `nullptr`, `typedef`→`using`, `= default`/`= delete`.
  `clang-tidy -fix` through the Meson compile database does most of it (`run-clang-tidy -p build
  -header-filter=...`); its misfires on old code are catalogued in `cpp-ownership-migration.md`.
- **Tier 2, per-site judgment:** range-`for` where a loop just walks a container, `auto` where the
  type is noise.
- **Tier 3, API-affecting, its own decision:** `enum class` (below), ownership
  (`cpp-ownership-migration.md`).

Verify each tier with the output oracle before starting the next. Keep `warning_level` as a
separate decision: raising it mines warnings (`-Wswitch` matters once enums are scoped) but
raising it mid-sweep mixes two kinds of churn.

## Migrating unscoped enums to `enum class` without breaking user code

The motivation is a real bug class: single-letter enumerators (`c`, `r`, `t`, `l`, `b` for label
positions) reach user scope through `using namespace`, and a local `double t` silently shadows
(or is shadowed by) an `int`. The technique that converted ePiX's four enums with zero output
change:

- **In the library:** `using enum T;` (C++20) at namespace scope in each `.cc` that uses the
  values — call sites stay terse, nothing leaks to users. **Qualify default arguments in public
  headers** (`epix_label_posn POSN = epix_label_posn::none`).
- **In user code you must keep compiling (samples, docs):** where a file has no name conflict, a
  one-line `using enum T;` keeps it unchanged. Where it *does* conflict, **qualify only the sites
  the compiler flags.** Use **clang with `-ferror-limit=0`** — it reports *every* undeclared
  identifier in one pass with a byte-precise column, where gcc suppresses repeats and forces
  iteration. A codemod maps each flagged identifier to its enum and inserts the qualifier at
  that column (ePiX: 61 sites across 24 files + 9 in a doc source, 0 column mismatches), and it
  **leaves a genuine `double t` alone** because the compiler never flagged it. This is
  `print-debugging.md`'s "collect the whole truth" applied to a refactor.
- **Prove output identity:** underlying values are unchanged, so every rendered figure must be
  byte-identical (ePiX: 96 figures, 0 differences).

## Raising `warning_level` on a legacy library — collect, classify, fix at the source

A 2000s-era library that "compiles clean" usually does so only because warnings are off. The sweep
that took ePiX from `warning_level=0` to **3** (`-Wall -Wextra -Wpedantic`, 2026-10-06) is the
template:

- **Inventory first, in a scratch build dir, keep-going** (`ninja -k 0`), and summarise by class ×
  count × file before touching anything. ePiX: 207 warnings, 7 classes — and the counts lie about
  the work: 138 `-Wignored-qualifiers` were **10 sites** (a `const bool` return type in a header,
  re-reported from every translation unit that included it).
- **Expect these classes, and fix each at the source rather than with `-Wno-`:** `const T` by-value
  return types (drop the `const`, header and definition); unused parameters in no-op overrides and
  stubs (`/*name*/` at the compiler's column — a codemod driven by the warning log's
  `file:line:col`, processed right-to-left per line, idempotent; or `[[maybe_unused]]` if the
  project already uses it); `catch (T)` → `catch (const T&)`; set-but-unused counters; a vexing
  parse (`double x();` declares a function).
- **The singletons are the payoff.** `-Winfinite-recursion` found `operator!=` defined as
  `return *this != arg;` — a stack overflow waiting for the first caller. `-Wparentheses` on
  `a && b || c` is a *behaviour* question: parenthesise as the compiler already reads it (output
  unchanged) and put the intent question to the maintainer rather than guessing.
- **Pick the level by the residue, not in advance.** The plan said 2; the residue at 3 was zero, so 3.
  `-Wswitch` over the project's `enum class` types reported nothing — every `switch` already covered
  its enum or had a `default:`.
- **Prove output identity** the same way as any other modernization step: render every sample before
  and after and `diff -r` ignoring only the timestamp header (`porting-with-an-output-oracle.md`).
- **Tag the inventory files** (`before`/`after`) before a second run — a re-run of the collector
  overwrote ePiX's before-log, and the before summary had to be reconstructed from the recorded counts.

## Isolate the tree-wide reformat, and tell `git blame` to skip it

A tree-wide `clang-format`/`ruff format` pass should be **its own commit containing nothing
else**, so `.git-blame-ignore-revs` can hide it without hiding real edits. ePiX's reformat commit
also carried a few real changes (Makefile, `format.sh`, `pyproject.toml`, a task doc), so ignoring
it costs the blame on those lines — tolerable, but avoidable. Add the file at the repo root,
list the SHA with a comment, and note in the project `CLAUDE.md` that a clone needs
`git config blame.ignoreRevsFile .git-blame-ignore-revs` (GitHub picks the file up automatically).
Formatting upstream-authored sources in a *mirror* is a deliberate exception to "keep upstream
intact" — record the maintainer's decision where the mirror rule is stated.

## Generated files: edit the source, record the mapping

Anything a build step produces — an umbrella header from a curated list (`make_header`), driver
scripts and man pages from `*.in` templates, `epix.el` — is **never hand-edited**; change the
list/template and regenerate. Record the mapping (output → source → generator) in the project
`CLAUDE.md` so the next reader doesn't "fix" the output. (`codegen-conventions.md` has the
generator-author side of this rule.)
