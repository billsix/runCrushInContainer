# Modernizing an existing C tree — preservation hazards and sweep mechanics

**Reference document** — the companion to `c-coding-standard.md` for the *other* direction: not
"what good C looks like" but **how to safely sweep modern idioms through an existing/legacy C tree
without changing behavior.** The standard says declare-late, `const`, `snprintf`, `bool`, fixed-width
types; this doc is the set of places where applying those to *existing* code is wrong, plus the
verification and mechanics a large sweep needs. Read on demand, before modernizing an old C codebase.
Portable rules only — names no one project's files. (Written 2026-10-16 — William Emerison Six
<billsix@gmail.com> — from a tree-wide C99→C23 modernization of a ~14 KLOC textbook example set.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep them in
> sync.** Canonical: runClaudeInContainer `tasks/reference/c-modernization-sweep.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/c-modernization-sweep.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/c-modernization-sweep.md`, and the
> baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/c-modernization-sweep.md`
> — delivered to a Crush session at `~/.config/crush/reference/c-modernization-sweep.md`. Edit the
> canonical, then re-copy it over the other two.

## The core move: preserve behavior, not source text

Modernizing *existing* code, the contract is **runtime behavior, not source text**
(`porting-with-an-output-oracle.md`). Every transform is "obviously correct" in the abstract; the
skill is noticing the specific lines where it silently changes behavior or destroys something
deliberate. Go class-by-class, re-verify after each, and where the obvious fix would break something,
**opt out in place with a one-line reason** rather than forcing it.

## Preservation hazards — where the "correct" modern transform is wrong

Each is a line where an idiom from `c-coding-standard.md` must NOT be applied:

- **`setjmp`/`longjmp` live locals — do not move or `const`.** A non-`volatile` automatic modified
  between `setjmp` and `longjmp` has indeterminate value after the return; declare-at-use or `const`
  can change what survives the jump. Leave every local in a function that uses these.
- **Loop-carried accumulators — do not move into the loop.** A counter/offset/flags value written in
  one iteration and read in the next (or read after the loop) stays declared in the enclosing scope.
  "Declare at first use" means first use, not inside the loop body.
- **Address-taken / output-filled locals — cannot be `const`, keep adjacent.** A variable passed as
  `&x` to be filled (`fstat`, `getaddrinfo`, `sigaction`, a `read` into a buffer) is written through
  the pointer; `const` is wrong, and it reads clearest declared right before the call.
- **Wire-/disk-serialized bytes — `strncpy`'s zero-fill can be load-bearing.** If a struct is sent or
  written as raw bytes (`write(fd, &req, sizeof req)`), a `strncpy(field, s, n)` that zero-pads the
  tail is doing real work; replacing it with `snprintf` leaves the tail uninitialized and leaks stack
  onto the wire. Here the usual "prefer `snprintf`" rule inverts — keep the bounded zero-filling copy.
- **Deliberate bug / teaching artifacts — preserve the behavior, don't "fix" it.** Old reference code
  often contains intentional defects: a `char` holding `getchar()`/`EOF` (can't represent EOF), a
  write through a non-`const` pointer to a string literal, a returned pointer to a dead local, a
  scope/shadowing demo, an intentional `SIGFPE` or data race. Recognize these and keep them working
  as-is — a `const`/`nullptr`/reorder "fix" destroys the lesson. If you must satisfy the compiler
  without killing the demo, do it behavior-preservingly (e.g. a `volatile` zero divisor keeps a
  divide-by-zero runtime demo without compile-time UB).
- **Correct domain typedefs are not a smell.** `pid_t`/`off_t`/`ssize_t`/`mode_t`/`size_t` are the
  right types; don't "modernize" them to `<stdint.h>` fixed widths. Fixed-width types are for when the
  width itself matters (wire format, register, bitmask) — most variables are not that.
- **Generated files — edit the generator, and watch the formatter.** Never edit a generated source;
  change its template/generator and regenerate. And a tree-wide reformat can silently break a
  generator or codemod that matches on line structure (a formatter joining a function onto one line
  once emptied a body a line-anchored `awk` extractor produced). After a reformat, re-run and
  re-verify any line-sensitive generator.

## Verifying a tree the test suite barely covers

Legacy trees are usually mostly untested (a handful of wired tests out of hundreds of programs). Per
change:
- **The build is the first gate:** a clean compile at a raised warning level catches a surprising
  share of real defects (an empty generated body, an uninitialized read, a pointer-decay `sizeof`).
- For the **tested** programs, output-equivalence (`porting-with-an-output-oracle.md`).
- For the **untested** majority, keep each transform **mechanical and behavior-preserving**, lean on
  clang-tidy-clean, and **state per change what went unverified** — don't claim a runtime guarantee the
  tests did not provide.

## Sweep mechanics — pitfalls that waste a pass

- **A warning-flag probe can silently no-op under a wrapper compiler.** `meson`'s
  `cc.has_argument('-Werror')` (and similar probes) compile a test program; if the toolchain wrapper
  emits its own warning, the probe fails and the flag is skipped with no error — you think `-Werror` is
  on and it is not. Prefer the build system's first-class option (`werror=true`) and **confirm the flag
  actually reached the compile** (grep `compile_commands.json`); don't trust exit 0.
- **`sizeof` on a pointer is the pointer size.** `strcpy`→`snprintf(dst, sizeof dst, …)` is valid only
  when `dst` is a real in-scope array; for a `char *` (param or `malloc`'d) use the known length or
  leave the call. A copy into an exactly-sized `malloc(strlen(s)+1)` gains nothing from `snprintf`.
- **A declaration-moving codemod must take the old declaration with it.** Rewriting `T x; … x = f();`
  to `T x = f();` while leaving the original `T x;` behind is a redefinition; match the whole span.
- **Keep include-purpose comments honest.** If the project annotates includes (`/* for strncpy */`)
  and the sweep removes the last caller, update or drop the comment (and the include) in the same
  change.

## Delegating a large sweep

For a bulk mechanical edit fanned out over a shared tree, use **fresh general-purpose subagents with
git/build/format forbidden** (Edit-only), one per disjoint directory, and **verify the on-disk state
yourself** afterward. Do **not** use context-inheriting "fork" workers: they inherit the coordinator's
context and begin acting like coordinators — one such worker ran a broad `git checkout` that silently
reverted five finished directories' *unstaged* edits (unrecoverable from git). A green build won't
catch a file reverted to its pre-sweep state, so audit each group's diff and stage it immediately.

## Cross-links

- `c-coding-standard.md` — the target idioms this doc tells you when *not* to apply.
- `porting-with-an-output-oracle.md` — proving the sweep changed no output.
- `cpp-build-modernization.md` — the build side (`-std` pin, warning level, the tree-wide reformat
  commit); the mechanics are the same for a C project.
- `code-style-conventions.md` — "use your discretion" (do the safe bulk, opt out of the unsafe) and
  the externally-defined-name exemption, which this doc specializes for a legacy sweep.
