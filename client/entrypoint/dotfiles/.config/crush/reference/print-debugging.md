# Print-statement debugging — augment the source, read the output

**Reference document** — how to debug by adding print/trace statements to a program,
then removing them cleanly, with a correct per-language recipe. The hand-instrumentation
sibling of the cross-project `CLAUDE.md` **"Instrumentation-driven debugging"** section
(which is about compilers/linters/tracers as oracles); read them together. Agent-facing;
markdown on purpose. Last updated 2026-08-13.

When a debugger isn't handy or the bug is timing/ordering-dependent, a few well-placed
prints often localize it faster: they survive across runs, need no ceremony, and show
*control flow over time*, which a breakpoint snapshot doesn't.

## The method (language-independent — this is the reusable part)

- **Emit to stderr, not stdout.** stdout is usually the program's *data*; mixing debug
  text into it corrupts pipes and output comparisons. stderr is the debug channel.
- **Flush, or you will lie to yourself.** A print buffered and then lost to a crash points
  at the *wrong* line — the last thing you see is not where it died. When chasing a crash,
  flush after every probe (or unbuffer the stream once). This is the single most common
  print-debugging mistake; the per-language recipes below all show the flush.
- **Bracket the suspect region.** Print on *entry* and *exit* of the function/loop/branch
  with a tag, so you watch control flow reach (or skip) code, not just values.
- **One variable per probe, self-labeled.** `x=<value>`, not a bare value — so each line
  says what it is and you can't misread which probe fired.
- **Tag every line with a grep-able marker** (this doc uses `DBG`). A single
  `grep -rn DBG` then finds every temporary print for removal. Include `file:line`/function
  where the language makes it cheap.
- **Diff the trace against a known-good run** when one exists — capture both to files and
  `diff`; the first diverging line is the lead. (Ties into the "derive the before
  mechanically" convention — same idea, applied to traces.)
- **Narrow, then delete.** Once the trace localizes the bug, remove *all* the probes before
  calling the work done (see "Removal" at the end). Temporary prints are not a deliverable.

## Per-language recipes

Each: the stderr print + flush idiom, how to dump a compound value, and the gotcha.

### C
```c
#include <stdio.h>
fprintf(stderr, "DBG %s:%d %s: x=%d\n", __FILE__, __LINE__, __func__, x);
fflush(stderr);                 /* or once at startup: setvbuf(stderr, NULL, _IONBF, 0); */
```
- **Compound:** no reflection — write a field-by-field line (`fprintf(stderr, "DBG p={%d,%d}\n", p.x, p.y);`) or loop an array. For raw bytes, `for (size_t i=0;i<n;i++) fprintf(stderr,"%02x ",buf[i]);`.
- **Gotcha:** stdout is *fully* buffered when redirected to a pipe/file, so a segfault
  loses buffered `printf` — a classic "it printed less than it ran" trap. Use stderr and
  `fflush`. (stderr is not fully buffered, but flush anyway when a crash is in play.)

### C++
```cpp
#include <iostream>
std::cerr << "DBG " << __FILE__ << ':' << __LINE__ << ' ' << __func__
          << " x=" << x << '\n' << std::flush;
```
- **Compound:** range-for a container (`for (auto& e : v) std::cerr << e << ' ';`); for a
  struct give it an `operator<<` or print fields by hand. `__PRETTY_FUNCTION__` gives the
  full signature.
- **Gotcha:** `std::cerr` auto-flushes (it's unit-buffered); `std::clog` and `std::cout`
  do **not** — a buffered `std::cout` line vanishes on a crash. Prefer `std::cerr`, or add
  `std::flush`/`std::endl`. (`std::endl` = `'\n'` + flush; `'\n'` alone doesn't flush.)

### Python
```python
import sys
print(f"DBG {x=}", file=sys.stderr, flush=True)     # {x=}  ->  x=<value>  (self-labeling, 3.8+)
```
- **Compound:** `print(f"DBG {obj!r}", file=sys.stderr, flush=True)` (repr shows structure);
  for deep/large, `import pprint; pprint.pprint(obj, stream=sys.stderr)`. `breakpoint()`
  drops into pdb when you want to poke around instead.
- **Gotcha:** stdout is block-buffered when not a TTY (piped/redirected), so prints appear
  late or not at all on a crash — pass `flush=True` or use stderr. `python -u` unbuffers
  everything.

### Java
```java
System.err.println("DBG x=" + x);                    // System.err auto-flushes
```
- **Compound:** `Objects.toString(obj)`; `java.util.Arrays.toString(arr)` /
  `Arrays.deepToString(nested)`; records and most collections have a usable `toString()`.
  `new Exception().printStackTrace();` (or `Thread.dumpStack()`) prints how you got here.
- **Gotcha:** use `System.err`, not `System.out`, so debug text doesn't merge into the
  program's stdout; both are auto-flushing `PrintStream`s, so no manual flush is needed.

### Scheme (R7RS; Racket notes)
```scheme
(define p (current-error-port))
(display "DBG x=" p) (write x p) (newline p) (flush-output-port p)   ; R7RS
```
- **Compound:** `write` prints lists/vectors/pairs readably with quoting (`display` omits
  the quotes — use `write` for structure). In **Racket**: `(eprintf "DBG x=~s\n" x)` writes
  to stderr in one call; `~s` is `write`-style, `~a` is `display`-style.
- **Gotcha:** the flush procedure's name is implementation-specific —
  `flush-output-port` (R7RS), `flush-output` (Racket), `force-output` (Guile). The
  error port may be buffered, so flush it before a call that might not return.

### Haskell
```haskell
import Debug.Trace (trace, traceShow, traceShowId)
-- pure code (cannot do IO): trace threads a message past a value
f x = trace ("DBG f: x=" ++ show x) (x + 1)
g y = traceShowId (y * 2)      -- prints the value (Show) and returns it
-- in IO:
import System.IO (hPutStrLn, hFlush, stderr)
hPutStrLn stderr ("DBG got " ++ show v) >> hFlush stderr
```
- **Compound:** `traceShow expr rest` / `traceShowId x` use the `Show` instance; add
  `deriving Show` to your types.
- **Gotcha (the important one):** `Debug.Trace` is how you print from *pure* code — you
  can't `putStrLn` there. But it fires **only when the value is forced**: laziness means a
  trace on an unevaluated thunk may print late, out of order, or never. Force with
  `seq`/`traceShow`/`$!`/`deepseq` if a probe seems to be missing.

### Rust
```rust
eprintln!("DBG x={x:?}");                 // stderr; {:?} = Debug, {:#?} = pretty
let y = dbg!(compute());                  // prints `[src/main.rs:12:13] compute() = <value>` and returns it
```
- **Compound:** `{:?}`/`{:#?}` on any type that `#[derive(Debug)]`. `dbg!(x)` is ideal
  mid-expression — it shows file:line, the expression text, and the value, without changing
  types.
- **Gotcha:** `Debug` requires the type to derive it; `eprintln!`/`dbg!` go to stderr
  (good — stdout stays clean and `println!` to a pipe is line-buffered and can be lost on
  panic).

### Go
```go
import ("fmt"; "os"; "log")
fmt.Fprintf(os.Stderr, "DBG x=%+v\n", x)  // %+v adds struct field names; %#v = Go-syntax
log.Printf("DBG x=%+v", x)                // log writes to stderr by default, with a timestamp
```
- **Compound:** `%+v` (fields named), `%#v` (full Go literal). `runtime/debug.PrintStack()`
  prints the goroutine stack; `%T` prints the dynamic type.
- **Gotcha:** `os.Stderr` is unbuffered, so no flush needed; use it (or `log`, which
  targets stderr) rather than `fmt.Println` so debug text stays out of stdout.

### Shell (bash)
```sh
echo "DBG x=$x" >&2                        # >&2 sends it to stderr
printf 'DBG %s=%s\n' x "$x" >&2            # printf is safer for values with % or backslashes
set -x; PS4='+ ${BASH_SOURCE}:${LINENO}: ' # trace EVERY command with file:line, then `set +x` to stop
```
- **Compound:** `declare -p var` prints a variable's full definition, including arrays and
  associative arrays; `set` (no args) dumps all variables and functions.
- **Gotcha:** always redirect debug output with `>&2` so it doesn't pollute a command
  substitution's captured stdout. `set -x` (xtrace) is the shell's built-in
  auto-instrumentation — often faster than hand-adding echoes.

## Removal

Temporary prints ship nothing but noise and risk. Before calling the work done:

- `grep -rn DBG <paths>` and delete every hit (that is the whole point of the marker).
- Re-run the build/formatter/linter afterward — a deleted print can leave an unused
  variable/import (Go and Rust *error* on those; Python/Java linters warn).
- If a probe is worth keeping, promote it to real logging (the language's `logging`/`log`
  facility at an appropriate level), not a bare `DBG` print.

## See also

- Cross-project `CLAUDE.md` → "Instrumentation-driven debugging (make the tools tell you
  what to do)" — the oracle-driven half; this doc is the hand-instrumentation half.
