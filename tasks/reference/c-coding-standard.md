# C coding standard (shared, cross-project)

**Reference document** — shared cross-project C coding standard, the sibling of
`cpp-coding-standard.md` and `python-coding-standard.md`. Read on demand (NOT auto-loaded). Update
in place. A project's `CLAUDE.md`/`README.md` points here and keeps its own repo-specific
invariants, worked examples, and file paths in its own additions doc (see Cross-links). Portable
rules only: this doc names no one project's files. (Written 2026-10-15 — William Emerison Six
<billsix@gmail.com> — from the maintainer's own modern-C notes plus the SEI CERT C Coding Standard,
MISRA C:2023, Jens Gustedt's *Modern C*, the ISO C standards themselves (C99/C11/C17/C23), the
cppreference C23 feature list, and the clang-tidy / Cppcheck catalogs; sources at the end. It
corrects three unsafe-by-reputation items from the input notes inline where a reader would act on
them: `strncpy` is not a safe `strcpy`, Annex K `_s` functions are a largely-unimplemented design,
and stack-allocated VLAs are optional since C11 and a security risk.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/c-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/c-coding-standard.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/c-coding-standard.md`, and
> the baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/c-coding-standard.md`
> — delivered to a Crush session at `~/.config/crush/reference/c-coding-standard.md`. Edit the
> canonical, then re-copy it over the other two.

Written for both humans and AI agents: each rule is a statement + a one-line reason. **The
standard is split in two** — (a) what **the toolchain already enforces mechanically** (clang-format,
clang-tidy / Cppcheck, the compiler's warning level and sanitizers; if `make format` and the build
are green, these are done — don't hand-review or re-prose them), and (b) the **judgment calls no
tool can check** (spend attention here). C and C++ share the layout tooling and much of tier (b)
(initialization, scope, integer types, naming, comments, error strategy); the C-specific weight is
on manual memory and buffers, undefined behavior, and the preprocessor, because C gives you no
destructors, no references, and no templates to lean on.

## (a) Enforced by the toolchain — treat a green format/lint/build as authority

- **`clang-format` owns layout.** Every project ships a `.clang-format` (the fleet default is
  `BasedOnStyle: google` with `SortIncludes: Never`; a project may add keys) and a `make format`
  target that runs it in-container. Indentation, brace placement, wrapping, spacing, pointer
  alignment: **never argue about these or hand-format** — write the clearer form and let the
  formatter lay it out. Line length is the formatter's job, not a design input.
  (`SortIncludes: Never` is deliberate — in C, include order is often semantically load-bearing:
  a header that depends on a feature-test macro, a `config.h`, or a system header defined before
  it. Keep it as written.)
- **`clang-tidy` / Cppcheck own the mechanical modernization and the bug-pattern catalog.** Where a
  project has a `.clang-tidy` and a `lint.sh`, a clean run is authority on the C-relevant checks:
  `bugprone-*` (`-not-null-terminated-result`, `-signed-char-misuse`, `-narrowing-conversions`,
  `-suspicious-memory-comparison`, `-sizeof-expression`, `-integer-division`,
  `-misplaced-widening-cast`); `cert-*` (the CERT rules below, e.g. `cert-err33-c` = check the
  return value, `cert-dcl*`, `cert-str*`); `misc-*`; `readability-*` (`-braces-around-statements`,
  `-else-after-return`, `-isolate-declaration`, `-non-const-parameter`); and `clang-analyzer-*` (the
  static analyzer: leaks, use-after-free, null deref, uninitialized reads). Run Cppcheck too
  (`--enable=warning,style,performance,portability`) — it catches different bugs. Diff and build
  after every `-fix` run; never let it touch vendored code (`-header-filter` scoped to your
  sources).
- **The compiler's warning level and sanitizers are gates, not advice.** Pin the standard
  (`-std=c23` / `-std=c17`; `c_std=c17` in Meson; `CMAKE_C_STANDARD 17` — an unpinned build compiles
  at whatever the installed compiler defaults to, which is not reproducible). Build at
  `-Wall -Wextra -Wpedantic` and add the ones that catch real C bugs: `-Wconversion`
  `-Wsign-conversion` (silent integer-conversion bugs), `-Wshadow`, `-Wvla` (flag accidental VLAs,
  below), `-Wswitch-enum` and `-Wimplicit-fallthrough` (see "Dispatch" below), `-Wwrite-strings`, `-Wstrict-prototypes` `-Wold-style-definition` (K&R-style declarations
  that defeat argument checking), `-Wcast-align`, `-Wformat=2`. A new warning in code you touched is
  yours to fix **at the source**, never with a `-Wno-`. Where the gate runs sanitizers
  (`-fsanitize=address,undefined`), a report is a failure, not noise — UBSan is the practical way to
  catch the undefined behavior tier (b) warns about.
- **Suppressions are narrow and reasoned.** `// NOLINT(check-name)` / `// NOLINTNEXTLINE(...)` with
  the reason on the same line, a scoped `/* cppcheck-suppress id */`, or
  `/* clang-format off */ … /* clang-format on */` around an aligned table or ASCII diagram. Never a
  file-wide or check-wide suppression to make a run green.

## (b) Judgment calls — prose, because no tool can check them

### Scope and initialization — declare late, initialize always

- **Declare each variable at its first use, not at the top of the function** (C99 lets you; so do
  it). The narrowest scope that works is the right one: it shrinks the reader's live-variable set
  and makes "is this initialized yet?" un-askable. Loop counters go in the `for` initializer:
  `for (size_t i = 0; i < n; i++)`. **A block of declarations at the very top of a function — the
  C89 `int a, b; struct X y;` opener — is the anti-pattern this rule removes; treat any such opening
  block as a finding, including on code a modernization pass already touched** (a pass tends to fix
  the loop counters and the obvious new locals and leave the struct-typed openers behind — e.g. a
  function whose body already uses `nullptr` and `for (rlim_t i = …)` can still open with
  `int fd0, fd1, fd2; struct rlimit rl; struct sigaction sa;`). **No clang-tidy check moves a
  declaration to its first use** — `readability-isolate-declaration` only splits a comma declaration,
  `cppcoreguidelines-init-variables` only forces initialization — so **a green lint does not prove
  this is done; a sweep must grep for top-of-function declarations and judge each by eye.** When a
  variable genuinely can't move down because it is read across several phases, that is the signal to
  introduce the bare `{ }` phase blocks below (initialize it at the first phase that needs it), not
  to leave it at the top.
- **Write an infinite loop `while (true)`, not `for (;;)`** — the intent (loop until an inner
  `break`/`return`) is on its face, where `for (;;)` hides it in three empty clauses the reader must
  decode. (In C23 `true` is a keyword, so this is a pure swap; a pre-C23 file needs `<stdbool.h>`, so
  a mechanical `for (;;)` → `while (true)` sweep must add that include wherever a C99/C11 file it
  edits lacks it.)
- **Initialize at the point of declaration** (SEI EXP33-C — never read an uninitialized value; it
  is indeterminate and reading it is undefined behavior). There is no default-construction in C, so
  an uninitialized automatic variable holds garbage. `int n = 0;`, not `int n;` then assign later.
- **One declaration per line** (`readability-isolate-declaration`): `int *p, q;` declares a pointer
  and a plain `int`, a classic misread. Split them.
- **`const` by default** (SEI DCL00-C). Qualify every binding you do not intend to change, and every
  pointer-to-input parameter as `const T *` — it documents intent and lets the compiler reject an
  accidental write. **A pointer has two *independent* `const` opportunities — judge each on its own;
  you may want neither, either, or both (they do not imply each other):**
  - **Pointee-`const` (`const T *p`) — when nothing writes `*p` through this pointer.** The
    high-value one: the classic const-correctness that documents "input, not modified" and lets the
    compiler reject an accidental write. Apply it to every pointer-to-input, *especially* parameters.
    This holds independently of whether `p` is ever repointed.
  - **Top-level `const` (`T *const p`) — when the pointer itself is never repointed.** The
    binding-stability one, exactly like `const` on a non-pointer local (`const int n = …`). Reach for
    it on a *local* whenever you would `const` a scalar local; with pointee-`const` it reads
    `const T *const p`. This holds independently of whether `*p` is const. The change is
    behavior-identical (a `const` local compiles to the same code). **Finding candidates:** `clang-tidy
    misc-const-correctness` (with `WarnPointersAsValues: true` for this pointer form) runs on **C++ only**
    — it reports nothing on a `.c` file. In C, find never-repointed locals with a libclang/AST script or by
    review, and verify by compiling. Skip it on loop/list cursors, a local whose address is passed (`&p`,
    an out-param), setjmp-live locals, and a declared-then-assigned local unless the declaration can simply
    move to the assignment.
  - **File-scope tables of pointers get both `const`s: `static const char *const names[] = {…};`.** With
    only the pointee `const` (`const char *names[]`) the *array* is still writable, so it lands in `.data`;
    the second `const` makes the elements immutable, so the table moves to `.rodata` (`.data.rel.ro` under
    PIC). This is the one top-level `const` with a runtime benefit: write-protected memory, and an
    accidental `names[i] = …` becomes a compile error. The `extern` declaration in a header must carry the
    identical qualifiers (a cross-translation-unit mismatch is undiagnosed UB). Skip it only when the table
    is genuinely filled or patched at run time.
  - **On a function *parameter*, add the pointee-`const` (the caller-visible contract) but NOT the
    top-level `const`.** `T *const` on a parameter is a definition-only detail — not part of the type,
    no effect on the caller/ABI — and it clutters prototypes. Add it in a definition only if a
    function genuinely benefits, and never let a header and its definition disagree on it.
- **Give a phase its own scope with a bare `{ }` block, and label it with a comment.** When a
  function runs in distinct phases that each need their own locals, wrap each phase in a bare block
  and put a one-line comment before the opening brace saying what the block does. The block scopes
  its locals to the phase that uses them (`fd` can't leak into the "does it exist?" phase, `sbuf`
  can't leak into the "create it" phase) and the comment documents the function's structure where
  each phase starts:

  ```c
  void make_temp(char* template) {
    // create the temp file
    {
      const int fd = mkstemp(template);
      if (fd < 0) die("can't create temp file");
      printf("temp name = %s\n", template);
      close(fd);
    }
    // check whether it now exists, and remove it
    {
      struct stat sbuf;
      if (stat(template, &sbuf) < 0) {
        if (errno == ENOENT) printf("file doesn't exist\n");
        else die("stat failed");
      } else {
        printf("file exists\n");
        unlink(template);
      }
    }
  }
  ```

  It is the lighter move when the phases are not worth separate functions; when a phase is
  substantial, reused, or has a name worth stating, pull it into its own named function instead.

### Types — fixed width, the right size type, real booleans

- **Use the explicit-width types from `<stdint.h>`** (`int32_t`, `uint64_t`, `int_least16_t`,
  `uint_fast8_t`) when the width matters — a wire format, a register, a file layout, a bitmask.
  Plain `int`/`long` have implementation-defined width and sign behavior; naming the width removes a
  portability bug class.
- **`size_t` for sizes, counts, and indices; `ptrdiff_t` for pointer differences** (both from
  `<stddef.h>`). `sizeof`, `strlen`, and array indices are `size_t` (unsigned); mixing them with a
  signed `int` counter trips `-Wsign-conversion` and can loop forever or index out of bounds. Use
  `intptr_t`/`uintptr_t` only to round-trip a pointer through an integer.
- **Use `bool`, `true`, `false` from `<stdbool.h>`** (a keyword in C23) rather than `int` flags or
  `#define TRUE 1` — the type says "truth value," and a function returning `bool` can't be confused
  with one returning a count or an errno.
- **Know the integer conversions, because the compiler won't stop you.** Operands narrower than
  `int` undergo integer promotion before arithmetic; mixing signed and unsigned converts the signed
  operand to unsigned (so `-1 > 0u` is true). **Signed overflow is undefined behavior**
  (SEI INT32-C) — do not rely on wraparound; check before the operation
  (`if (a > INT_MAX - b) …`). **Unsigned arithmetic wraps** by definition (SEI INT30-C) — intended
  for modular math, a bug when it underflows a size. Avoid plain `char` for small integers (its
  signedness is implementation-defined); use `signed char`/`unsigned char`/`int8_t`.

### Memory and ownership — you are the destructor

- **Every allocation has exactly one owner and one documented free.** C has no RAII, so ownership is
  a convention you must state: who frees this, and when. Write it at the function that returns owned
  memory ("caller frees" / "borrowed, do not free"). A `[[nodiscard]]` (C23) on an allocator makes
  dropping the returned pointer a warning.
- **Check every allocation and every return value that can fail** (SEI ERR33-C, MEM32-C). `malloc`
  returns `NULL` on failure; dereferencing it is a crash or worse. The `cert-err33-c` check enforces
  this mechanically where configured.
- **Free once, then null the pointer.** A double `free` is undefined behavior (SEI MEM30-C) and a
  classic exploit primitive; `free(p); p = NULL;` makes a second free a harmless no-op and a
  use-after-free a null deref instead of silent corruption. Never `free` a pointer that didn't come
  from `malloc`/`calloc`/`realloc`, and never free a pointer into the middle of an allocation.
- **`realloc` into a temporary**, not back into the only pointer you hold: `p = realloc(p, n)` leaks
  the original block if `realloc` returns `NULL`. Use `void *t = realloc(p, n); if (t) p = t;`.
- **A `restrict` pointer promises no aliasing** (C99): the object it points to is reached only
  through that pointer for its lifetime. It lets the compiler optimize, but it is an unchecked
  contract — breaking it is undefined behavior, so add it only where the no-alias guarantee is real
  (e.g. `memcpy`-like APIs).
- **Prefer a flexible array member to a separate allocation** for a header-plus-payload struct
  (`struct msg { size_t len; char data[]; };`, C99) — one allocation, one free, and the payload is
  contiguous with its header.
- **For scope-bound automatic cleanup, the `cleanup` attribute is C's closest thing to a
  destructor** (a gcc/clang extension, spelled `[[gnu::cleanup(fn)]]` in C23 attribute syntax,
  `__attribute__((cleanup(fn)))` before it): the named `fn` is called with the variable's address
  when the variable leaves scope, so an owned resource frees itself on *every* exit path — the
  `defer`/RAII analog, and the per-variable counterpart to the `goto cleanup` idiom (Error handling).

  ```c
  static void free_ptr(int **p) { free(*p); }   /* runs with &buf at end of scope */
  [[gnu::cleanup(free_ptr)]] int *buf = malloc(n * sizeof *buf);
  if (!buf) return -1;                           /* free_ptr(&buf) runs here … */
  /* … and here, on the normal exit — no hand-written unwinding */
  ```

  Caveat: it is **not ISO C** (gcc/clang only), so a project that must also build on MSVC cannot use
  it — state the dependence where a project adopts it. The cleanup `fn` must tolerate being called on
  a partially/zero-initialized object (initialize the variable at its declaration so it always has a
  defined value to clean up).

### Arrays, bounds, and VLAs — document the size, don't allocate on the stack

- **Pass the length alongside every array** — a bare `T *` carries no size, and `sizeof` on a
  parameter gives the pointer size, not the array. The length is a `size_t` parameter next to the
  pointer.
- **Use `arr[static N]` to require a minimum length** (C99): `void f(int a[static 4])` tells the
  compiler and the analyzer that `a` is non-null and has at least four elements, turning a hidden
  buffer risk into a diagnosable one. For a runtime-sized 2-D argument, the
  variably-modified parameter form `void clear(size_t r, size_t c, int m[r][c])` lets sanitizers
  track the real bounds — this is the *useful* half of variable-length typing (pointer-to-VLA
  parameters), and it allocates nothing.
- **Avoid stack-allocated VLAs** (`int buf[n];` with a runtime `n`). They were made **optional in
  C11** (guard any real use with `__STDC_NO_VLA__`), and an attacker-influenced size is a stack
  overflow — the Linux kernel removed them wholesale for this reason. Use a fixed upper bound or
  `malloc`; keep `-Wvla` on so an accidental one is a warning. (The VM *parameter* types above are
  fine — they are pointers, not stack allocations.)

### Strings and buffers — the input-notes correction

- **The classic "n" functions are not the safe versions.** `strncpy` does **not** null-terminate the
  destination when the source is at least as long as the limit (it was designed for fixed-width
  fields, not strings), so a later read runs off the end — undefined behavior (SEI STR31-C,
  `bugprone-not-null-terminated-result`). `strncat`'s length argument is the space *remaining*, not
  the buffer size, which is routinely miscounted.
- **Prefer `snprintf` for building strings, `memcpy` for copying known-length bytes.** `snprintf`
  always null-terminates within the buffer and **returns the length it *would* have written** — so
  check it: a return `>= size` means it truncated. `snprintf(dst, sizeof dst, "%s/%s", a, b)`
  replaces `strcpy`+`strcat`. When you copy a known length, `memcpy(dst, src, n)` then set the
  terminator yourself; `sizeof dst` only works when `dst` is a real array, never a decayed pointer.
- **Name a buffer's size once and use that name for both the array and the bound.** A magic number
  duplicated in the declaration and in the `snprintf`/`fgets`/`memcpy` bound drifts when one side
  changes — `char buf[32]; … snprintf(buf, 16, …)` silently truncates, and the opposite (a bound
  larger than the buffer) overflows. Define the length as a single named constant (an `enum` or
  `#define` in C, a `constexpr`/`const size_t` in C++) and use it in both places:
  `enum { NAME_LEN = 32 }; char name[NAME_LEN]; snprintf(name, NAME_LEN, …);`. When the array is in
  scope, `sizeof name` as the bound is better still — there is no second number to drift. For a heap
  buffer (`malloc`/`new`), where `sizeof` gives the pointer size, the named constant *is* the single
  source of truth shared by the allocation and the bound.
- **Do not reach for Annex K `_s` functions** (`strcpy_s`, `sprintf_s`, …). They are an *optional*
  annex, not widely implemented (glibc never shipped them, even Microsoft's implementation doesn't
  conform to the spec), and WG14's own field-experience report (N1967) proposed removing them.
  Portable code can't rely on them; track lengths explicitly instead.
- **`gets` is gone** (removed in C11) — it could never be used safely. Use `fgets` with an explicit
  size.

### Error handling — one strategy per project, stated in its `CLAUDE.md`

- **Pick one convention and hold it:** an `int`/`enum` status return, a returned pointer with `NULL`
  for failure, or `errno`-style with the result in an out-parameter. Mixing them per-function makes
  every call site guess. State the chosen one in the project's additions doc, the same way the C++
  standard asks.
- **The `goto cleanup` idiom is idiomatic C, not a smell** — a single labelled cleanup block at the
  end that frees what was acquired, with early `goto` on each failure, is the standard way to get
  RAII-like unwinding without destructors. Acquire in order, free in reverse.
- **Report the failure from the function that discovers it** and let the caller decide; don't
  `exit()` or `abort()` from deep in a library (reserve those for truly unrecoverable invariants,
  with a message).

### Dispatch — a `switch` with a `default`, and one chain per decision

The C form of the cross-project "prefer total dispatch" rule (`code-style-conventions.md`), and of the
Python standard's `match`-with-`case _` and `if`/`elif`/`else` rules. (Learned from converting a
simulator's C engine, 2026-11-11, William Emerison Six <billsix@gmail.com>; worked example below.)

- **A decision on one value is a `switch`** when it has three or more outcomes, or when its tests list
  several constants with `||` (stacked `case` labels read better than an `||` list). A two-way test
  on one constant stays `if`/`else`. Equality on strings can't be a `switch`; leave the chain, or
  use a lookup table when it is long.
- **Every `switch` has a `default`.** Write the remaining outcome down:
  - **Other values are legitimate:** a `break` with a comment saying what happens to them ("any
    other opcode stores nothing").
  - **The cases cover every value:** call the project's fatal-error function with a message naming
    the function and the bad value. Add a comment saying it is never reached and why ("the test above
    admits only `s`, `t` and `d`", "byte is `addr & 3`, and each value has a case"). A message
    diagnoses a broken invariant; C23 `unreachable()` would make it undefined behavior instead.
- **A `default` turns off `-Wswitch`'s missing-enumerator warning, so build with `-Wswitch-enum`.**
  `-Wswitch-enum` warns about an unlisted member even when a `default` exists, so an exhaustive enum
  switch keeps its compile-time check and gains the run-time one. A switch that deliberately leaves
  most members to its `default` opts out at the site, with the reason in a comment:
  `#pragma GCC diagnostic push` / `ignored "-Wswitch-enum"` / `pop` around it (gcc and clang both
  accept it). A switch on an `int` holding enumerators (an anonymous `enum`, or a value stored in a
  narrower integer field) gets no check at all; name the enum type and give the subject that type
  if the check matters.
- **Before writing a fatal `default`, find every value that can reach the switch**, from the callers
  and the data, not from the case list. A switch that looks exhaustive may not be: a table row of the
  same type that nobody listed. (In the worked example, 16 table rows of the compare type reached a
  "complete" 32-case switch, and two opcodes reached a jump parser that emitted nothing for them.)
  Then a fatal `default` would be a behavior change, so keep the behavior, document it in the
  `default`, and file the bug.
- **A run of early-exit `if`s that make one decision is one chain.** Separate `if`s whose bodies all
  leave (`return`, `break`, `continue`, `goto`, a no-return call) are mutually exclusive. Write them
  as `if` / `else if` / `else`, with the code that followed the run in the final `else`, or as a
  `switch` if they test one value (by the rule above).
  - **Exempt:** a single guard before the main body; independent checks that can each fire.
  - **Also exempt:** a chain whose branches all leave and whose following code is the rest of a long
    body (a dispatch loop). Nesting all of it one level deeper doesn't read better.
- **Every `if` / `else if` chain ends in an `else`.** It holds a comment naming the remaining outcome
  ("below level 3 there is no bit layout", "no offset: `off` stays 0"), or the fatal call if that
  outcome is impossible. A chain inside a macro gets the `else` too, inside the macro.

**Converting a chain to a `switch` — the C-specific hazards:**
- **`break` changes meaning.** Inside a `switch`, `break` leaves the `switch`, not an enclosing loop
  or outer `switch`. Check every `break` in a converted body. `continue` and `return` are unaffected,
  so a guard run ending in `continue` inside a loop converts safely.
- **The subject is evaluated once.** A run of `if (peek() == X)` calls `peek` per test. Check that
  the call has no side effect a second call would see.
- **`case` labels are integer constant expressions.** Enumerators, character constants and literals
  qualify. A `const int` object doesn't; a C23 `constexpr` object does.
- **A `case` that declares a variable gets braces**, `case X: { int n = …; break; }`, so the name is
  scoped to its case.
- **Fall-through is checked** under `-Wimplicit-fallthrough`. Stacked labels with no statements
  between them are fine; deliberate fall-through is `[[fallthrough]];` (C23).
- **Comments move with their tests.** A comment above an `if` becomes the comment on its `case` or
  inside its branch. Check afterwards that every comment survived.

**Checking the rules:** `c_dispatch_check.py`, a SHARED, VENDORED tool that sits beside this doc
(canonical in github.com/billsix/runClaudeInContainer `tasks/reference/`). Vendor it into a C
project's `tools/` and run `python3 tools/c_dispatch_check.py BUILDDIR [SOURCE ...]` from the
project root. It reads clang's JSON AST through the build's `compile_commands.json` and lists
every one-value chain that should be a `switch`, chain with no `else`, guard run and `switch` with
no `default`. A `dispatch-check: ok` comment, with the reason, accepts a site. It exits 1 if
anything is left, so a clean project can gate on it.

**Verifying such a refactor:** it must not change behavior, so derive the "before" mechanically.
Build the unmodified tree, and run both binaries over every input the repo has: test programs,
examples, and the output modes that reach the changed code. Diff stdout, stderr and exit status.
Run the "before" binary twice per case, and skip a case where it disagrees with itself (a program
that reads the clock or hits the timeout), rather than chasing that diff. A text-rewriting codemod
must recognize a run exactly: no `else`, and a body that leaves. A looser match merges unrelated
`if`s into the chain. Worked example: github.com/billsix/spimulator
`tasks/archive/2026/11/11/c-switch-and-else-if-chains.md`.

### Structs, constants, and the preprocessor — prefer the language to the macro

- **Use designated initializers** (C99): `struct point p = { .x = 10, .y = 20 };` — order-independent
  and self-documenting, and any member you omit is zero-initialized. A **compound literal**
  `(struct point){ .x = 1 }` makes an unnamed object you can pass inline. This covers **static
  tables** too: an array of structs is written `{.name = "a0", .value = 4}` row by row, and a
  generated table changes in its generator. **Checking it:** `c_designated_init_check.py`, a SHARED,
  VENDORED tool beside this doc (canonical in github.com/billsix/runClaudeInContainer
  `tasks/reference/`); vendor it into the project's `tools/` and run `python3
  tools/c_designated_init_check.py BUILDDIR [SOURCE ...]` against any build with a compile
  database (gcc or clang; clang must be installed). It lists every positional struct/union
  initializer, takes a `designated-init-check: ok` comment
  (with the reason) to accept a site, and exits 1 if any are left. clang-tidy's
  `modernize-use-designated-initializers` reports nothing for C (clang-tidy 23), so it is no
  substitute. (Found 2026-11-14 in github.com/billsix/spimulator: three C23 passes had left 1082
  positional table rows, because no tool listed them.)
- **Zero-initialize with `{ }`** (C23; `{ 0 }` before C23) rather than `memset(&s, 0, sizeof s)` —
  it's checked by the type system and can't get the size wrong. (Note `memset`-zero is not
  guaranteed to produce a null pointer or a floating 0.0 on exotic targets; `{ 0 }` is.)
- **Reach for a real construct before a function-like macro** (SEI PRE00-C): an `enum` or a `const`
  for a constant, a `static inline` function for a small routine (type-checked, debuggable, no
  double-evaluation). When a macro is genuinely needed, parenthesize every parameter and the whole
  body, and never use an argument twice.
- **Use `_Generic` for type-generic interfaces** (C11) when you truly need to dispatch on argument
  type (the `tgmath.h` pattern): `#define absval(X) _Generic((X), int: abs, double: fabs)(X)`. It is
  the type-safe replacement for a macro that assumes one type.
- **Assert invariants at compile time with `static_assert`** (C11; a keyword in C23, `_Static_assert`
  the older spelling): `static_assert(sizeof(void *) == 8, "64-bit only");`,
  `static_assert(offsetof(...) == ...)`. Zero runtime cost, and it fails the build instead of a
  shipped product.

### C23 niceties — use them when the project pins `-std=c23`

- **`nullptr`** (type `nullptr_t`) replaces `NULL`: it converts to any pointer and to `bool` but
  **not** to an integer, so it catches pointer-vs-int mix-ups `NULL` (often `0` or `(void*)0`) hides.
- **Standard `[[...]]` attributes** replace non-portable `__attribute__`/`__declspec`:
  `[[nodiscard]]` (warn if a return — an error code or an allocation — is ignored),
  `[[maybe_unused]]` (silence a deliberately unused parameter), `[[deprecated("use X")]]`,
  `[[fallthrough]]` (an intentional `switch` fall-through), `[[noreturn]]`.
- **`auto` and `typeof`** give type inference for *objects* (not function returns or parameters, unlike
  C++): `auto node = get_node();`. Use it exactly where the C++ rule says — when the type is
  obvious, redundant, or unspellably long — and spell the type when a primitive or a domain meaning
  should be visible. `typeof(expr)` names a type for a macro or a declaration.
- **`constexpr`** for true compile-time object constants, and `_BitInt(N)` for an exact-width integer
  (e.g. a 24-bit field) when a standard width doesn't fit.

### Undefined behavior and strict aliasing — the part that bites silently

- **Type-pun through `memcpy` or a `union`, never a reinterpreting pointer cast.** Reading an object
  through a pointer of an incompatible type violates the strict-aliasing rule (C11 6.5) and is
  undefined behavior that an optimizer will exploit (SEI EXP39-C). `uint32_t u; memcpy(&u, &f, sizeof
  u);` is the portable bit-reinterpretation; `*(uint32_t*)&f` is not. `-fno-strict-aliasing` is a
  crutch for legacy code, not a license to write new aliasing.
- **Respect alignment.** Don't cast a `char *` to a wider type and dereference it unless the address
  is actually aligned (`-Wcast-align` flags it; `alignas`/`alignof` from C11 declare and query it).
- **Don't invoke the other common UB:** signed overflow, shifting by `>=` the width or by a negative,
  out-of-bounds access, modifying a string literal, reading an object past its lifetime, a data race.
  UBSan is the gate that catches most of these at runtime — keep it in the test build.

### Headers, translation units, and linkage

- **Every header is self-contained and idempotent:** an include guard (`#ifndef FOO_H` / `#define` /
  `#endif`, or `#pragma once` where the fleet allows it) and it includes what it uses, so a TU can
  include it first and still compile.
- **Give internal functions and file-scope data `static`** (internal linkage) so they don't leak
  symbols or collide at link time; expose only the declared public surface in the header. Avoid
  mutable globals; where one is unavoidable, it's `static` to its TU with an accessor.
- **A `.c` does one job**; declarations live in its header, definitions in the `.c`. Mark a small
  hot helper `static inline` in a header rather than duplicating it.

### Naming and comments

- **C is conventionally `snake_case`** for functions and variables, `UPPER_SNAKE` for macros and enum
  constants, with a project/module prefix on public names (C has one global namespace, so `png_read`
  not `read`). Follow the project's `.clang-format` / `readability-identifier-naming` where it sets
  casing; **an externally-defined name always wins** (a callback signature, a library-looked-up
  symbol, an ABI field) — match it exactly and suppress the linter narrowly with the reason at the
  site (see `code-style-conventions.md`).
- **Comments say *why*, in the present tense**, at the step they describe; the language-agnostic
  comment rules (reflow the whole paragraph, describe the present not the history) are in
  `code-style-conventions.md` and apply unchanged.

### Concurrency — the one-paragraph floor

- A **data race is undefined behavior.** Share nothing, or protect it. Prefer the project's
  established primitive; C11 offers `<threads.h>` and `_Atomic`/`<stdatomic.h>` (both optional —
  guard with `__STDC_NO_THREADS__` / `__STDC_NO_ATOMICS__`), and POSIX `pthreads` is the common
  real-world choice. `volatile` is **not** a threading tool (it's for memory-mapped I/O and signal
  handlers); use atomics or a mutex for cross-thread visibility.

### The feature ladder — what each standard added that this doc leans on

- **C89/C90** — the baseline: function prototypes, `const`/`volatile`, standard library.
- **C99** — `//` comments, mid-block and `for`-initializer declarations, `<stdint.h>`/`<stdbool.h>`,
  `inline`, designated initializers, compound literals, flexible array members, `restrict`,
  `snprintf`, `long long`, `arr[static N]`. (VLAs too — now discouraged, above.)
- **C11** — `_Static_assert`, `_Generic`, `<threads.h>` + `_Atomic`/`<stdatomic.h>`,
  `alignas`/`alignof`, anonymous struct/union members, `gets` removed, the optional Annex K (don't
  rely on it).
- **C17** — a bug-fix release: no new features, just defect corrections. A safe, well-supported pin
  when C23 isn't available yet.
- **C23** — `nullptr`, `bool`/`true`/`false`/`static_assert` as keywords, standard `[[...]]`
  attributes, `auto`/`typeof` type inference, `constexpr`, `_BitInt(N)`, empty `{ }` initializer,
  binary literals and digit separators, `#embed`, `#elifdef`. `__STDC_VERSION__ >= 202311L`.

### Things in the input notes to use with the caveat attached

- **`strncpy`/`strncat` as "safe"** — no; see Strings and buffers. Prefer `snprintf`/`memcpy` +
  explicit length.
- **Annex K `_s` functions** — not portable; see Strings and buffers (N1967).
- **Stack VLAs / `int m[rows][cols]` as a *local*** — the parameter form is good, the stack
  allocation is the risk; see Arrays, bounds, and VLAs.
- Everything else in the notes (narrow scope, fixed-width types, const correctness, immediate
  initialization, designated initializers, `<stdbool.h>`, static analysis, `nullptr`, standard
  attributes, `_Generic`, `arr[static N]`, empty initializers, `static_assert`, VM parameter types)
  is adopted above.

## Cross-links

- **Each project's own additions doc** — the repo-specific invariants, the chosen error strategy,
  the worked examples and file paths.
- `cpp-coding-standard.md` — the C++ sibling; the two docs share one shape on purpose, and a mixed
  C/C++ project reads both (the C++ doc's ownership/RAII material is what C emulates by hand).
- `python-coding-standard.md` — the Python sibling.
- `code-style-conventions.md` — the language-agnostic rules (comment reflow, line-length changes,
  externally-defined names, what earns an extraction, total dispatch) this standard specializes.
- `cpp-build-modernization.md` — pinning `-std`, raising the warning level, the tree-wide reformat
  commit; the build mechanics are the same for a C project.
- `porting-with-an-output-oracle.md` — proving a modernization changed no output.
- `c-modernization-sweep.md` — the companion for the *other* direction: modernizing an existing/legacy
  C tree. Where these idioms must **not** be applied (setjmp locals, loop-carried accumulators,
  deliberate teaching bugs, wire-serialized `strncpy` zero-fill), plus the sweep's verification and
  mechanics. Read it before sweeping this standard through an old codebase.
- `print-debugging.md` — the instrumentation-driven method (compiler, sanitizer, analyzer as the
  oracle) this standard's tier (a) relies on.

## Sources

- SEI CERT C Coding Standard (Carnegie Mellon SEI) — wiki.sei.cmu.edu/confluence/display/c; rule
  IDs cited inline (INT30-C, INT32-C, EXP33-C, EXP39-C, STR31-C, MEM30-C, MEM32-C, ERR33-C,
  DCL00-C, PRE00-C).
- MISRA C:2023 — the safety-critical ruleset; the parts this doc reflects are its undefined-behavior
  and essential-type guidance (not its full MISRA-compliance regime, which a non-safety project does
  not adopt wholesale).
- Jens Gustedt, *Modern C* (Manning, 2019; free PDF) — gustedt.gitlabpages.inria.fr/modern-c/; the
  narrow-scope, initialize-always, and variably-modified-type guidance.
- ISO/IEC 9899 — C99/C11/C17/C23; cppreference C23 feature list, en.cppreference.com/w/c/23.
- WG14 N1967, *Field Experience With Annex K — Bounds Checking Interfaces* —
  open-std.org/jtc1/sc22/wg14/www/docs/n1967.htm (why not to rely on the `_s` functions).
- clang-tidy check list — clang.llvm.org/extra/clang-tidy/checks/list.html (the `bugprone-`,
  `cert-`, `clang-analyzer-`, `readability-` families); Cppcheck — cppcheck.sourceforge.io.
- GCC/Clang warning documentation — the `-W` flags in tier (a).
