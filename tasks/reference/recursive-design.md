# Recursive and functional design — schemes, structure, and when to hand-roll

**Reference document** — shared cross-project guide to designing recursions and choosing the
functional combinators (map / filter / fold) over hand-written recursion. Read on demand (NOT
auto-loaded). **Trigger: before writing or reviewing a non-trivial recursion, or choosing a
recursion scheme.** Update in place. Portable, language-agnostic rules (Lisp/Haskell-rooted,
applied in Python/Rust/C alike); a project keeps its own worked examples in its additions doc.
(Created 2026-10-23 — William Emerison Six <billsix@gmail.com>.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/recursive-design.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/recursive-design.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/recursive-design.md`, and the
> baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/recursive-design.md`
> — delivered to a Crush session at `~/.config/crush/reference/recursive-design.md`, which is how
> a project developed *with Crush* gets this guide. Edit the canonical, then re-copy it over the
> other two.

## The rule in one paragraph

Reach for the **most specific** sequence operation that expresses the intent. A 1:1 transform is
a **map**; a selection is a **filter**; a combine-into-one-running-value is a **fold** (reduce).
Hand-write recursion only when the computation fits none of those named schemes. When you do
recurse, let the recursion's shape **follow the data's shape** — the nil/cons split, a base case
and a recursive case — and do the per-element work by **mapping over the tail**, not by threading
a hand-rolled accumulator through an extra parameter. Keep an accumulator parameter only when the
computation genuinely needs one (a true left-fold of state, or a tail-recursive/iterative
reformulation); then name it `acc`/`accumulator` and put it in the conventional position. This is
SICP's "conventional interfaces," Norvig & Pitman's *be specific* / *be conventional*, Graham's
recursion-on-cdrs, and the reason Python demoted `reduce` out of the builtins.

## map, filter, and fold are named recursion schemes

The three combinators are not a different paradigm from recursion — they are the **names of the
three recursions everyone keeps hand-writing** over a list:

- **map** — "transform each element." The recursion that rebuilds the list applying `f` to each
  car. A 1:1 shape: *n* in, *n* out, order preserved.
- **filter** — "keep the elements that pass a predicate." The recursion that conses an element
  onto the recursive result only when `p` holds.
- **fold** (a.k.a. reduce / accumulate / `foldr`/`foldl`) — "combine all elements into one value
  with a binary op and an identity." The recursion that threads a running accumulated value.

So *"prefer map/filter/fold"* is really: **recognize which of these three your recursion is an
instance of, and call the named one** — it states the intent in a word, cannot get the base
case or the accumulator wiring wrong, and lets a reader stop reading once they see the name.
Hand-write the recursion only when the shape matches none of them (tree walks with sharing,
generative recursion, mutually recursive descents, early exit with state).

Fold is the most general of the three (map and filter are both expressible as a fold), which is
exactly why it is the **least specific** and the **last** to reach for: a bare fold tells the
reader only "some combination happens here," where a `map`/`filter`/comprehension tells them
*what*. Reserve the explicit fold for a genuine reduction the more specific schemes can't say.

## Structural recursion: shape the recursion to the data

A structural recursion over a list is the **nil/cons template** — one case per constructor:

```
f([])          = <base value>
f([head, *tail]) = <combine head with f(of the tail)>
```

The base case is the empty list; the recursive case does a bounded amount of work on the `head`
and recurses on the `tail`. When the "work on the head" is *"relate the head to every element of
the tail,"* that work is a **map over the tail** — not an accumulator carrying the already-seen
elements forward. Letting the recursion follow the data this way is the difference between a
function a reader can see is correct and one they have to simulate.

**Worked example — orthogonalizing a frame (github.com/billsix/geometricalgebra, `frame.py`).**
Gram–Schmidt over a list of vectors. The first draft used *accumulator-passing*: carry the
already-orthogonalized vectors in a `done` parameter, and for each new vector `reduce` the
rejection over all of `done`.

```python
# BEFORE — accumulator threaded through a parameter; reduce folds the rejection;
# the accumulated value sits first in the reduce lambda (w) but second in the helper (done);
# the empty case is an "unreachable" catch-all.
def reject_span(v, prior):
    return functools.reduce(lambda w, p: w.rejected_away_from(p), prior, v)

def orthogonalize(remaining, done):
    match list(remaining):
        case [v]:        return [*done, reject_span(v, done)]
        case [v, *rest]: return orthogonalize(rest, [*done, reject_span(v, done)])
        case _:          return done          # "unreachable"
return orthogonalize(vectors, [])
```

The natural structural recursion keeps the head (it is already orthogonal to everything finalized
before it), **maps** its rejection over the tail, and recurses on the mapped tail:

```python
# AFTER — nil/cons structural recursion; the per-element work is a map (comprehension)
# over the tail; no accumulator, no reduce, no reversed arguments; a real base case.
def orthogonalize(remaining):
    match list(remaining):
        case [v, *rest]:
            rest_orthogonal_to_v = [w.rejected_away_from(v) for w in rest]
            return [v, *orthogonalize(rest_orthogonal_to_v)]
        case _:                       # the empty list -- base case
            return []
return orthogonalize(vectors)
```

The `after` is Modified Gram–Schmidt and the `before` is Classical; in exact arithmetic they
produce identical results, so the behavior is unchanged. What improved is the *design*: the
recursion follows the list's nil/cons shape, the per-element work is a named map, there is no
accumulator to place or reverse, and the base case is a real, reachable branch (the empty list)
instead of a `case _` labelled "unreachable."

**A note on the base case and type-checkers.** In principle `case []` + `case [v, *rest]` is the
exhaustive nil/cons split, so you might expect to spell the base case `case []` and omit any
wildcard. But some type-checkers (e.g. gacalc's `ty`) do **not** prove a list-pattern match
exhaustive, and warn that the function can implicitly return `None`. Spell the base case as the
wildcard **`case _`** (as above) — it is still reachable and meaningful (the empty list), not a
dead "unreachable" branch — or add an explicit fallback. This keeps the "total dispatch"
convention (a complete match, no silent fall-through) *and* satisfies the checker; it is the same
reason the sibling "Prefer total dispatch" rule says to always write the default branch.

## Accumulator-passing style: only when warranted, and name it

Accumulator-passing (an extra parameter carrying state built up so far) is the right tool for a
**genuine left-fold of state** or for turning a non-tail recursion into a **tail-recursive /
iterative** one (so a language with tail-call optimization runs it in constant stack). It is the
*wrong* tool when a plain structural recursion or a map over the tail would do — it adds a
parameter the reader must track and, done carelessly, scatters "the accumulated value" across
inconsistent argument positions (see the BEFORE above: `w` first in the lambda, `done` second in
the helper). When an accumulator really is warranted:

- **Name it `acc` / `accumulator`**, never a bare `w`/`x`/`r` whose role the reader reconstructs.
- **Keep it in the conventional position** (the fold convention is accumulator-first:
  `f(acc, element)`); don't flip the order between the helper's parameters and the reducer.
- **Don't default it to a mutable literal.** A default `acc=[]`/`acc={}` is shared across calls
  (Python's shared-mutable-default trap, ruff **B006**); use a `None` sentinel (`acc=None` then
  `acc = acc or []`) — or, better, remove the parameter by using the structural shape above.

## Fold direction, and reduce as the last resort

A fold has a **direction**. `foldr` (fold-right) associates from the right and is the natural one
for building a list or respecting a right-leaning structure; `foldl` associates from the left and
is the natural accumulator/iterative one. Pick deliberately — they differ for non-associative
operators and for laziness/stack behavior. Even so, an explicit fold is the last resort among the
named schemes: if the operator is associative with an identity, a *named* fold (sum, product,
all/any, min/max) says more than a bare `reduce`/`fold` call.

## The Python spellings (the scheme is the concept; this is the surface syntax)

The recursion *scheme* is language-independent; its *spelling* is per-language. In Python:

- **map and filter → a comprehension**, not the `map()`/`filter()` builtins — `[f(x) for x in xs]`
  / `[x for x in xs if p(x)]`. (Idiomatic Python; keep them simple — a comprehension doing too
  much wants a loop or a named helper.)
- **fold → the named builtin**: `sum(xs)` / `math.prod(xs)` (pass the correct identity as `start`:
  `sum(xs, start=cls.zero())`, `math.prod(xs, start=cls.one())`), `any` / `all` / `min` / `max`.
  Drop to **`functools.reduce` only for a genuine associative fold the builtins don't cover**, and
  then name its accumulator `acc`. (This is the specific rule the shared `python-coding-standard.md`
  keeps terse — see Cross-links.)
- **running scan (each output depends on the previous accumulation) → `itertools.accumulate`**; a
  true scan is a legitimate fold, so this is correct, not a violation of "prefer map." (Example:
  `frame.py`'s `prefix_blades` builds a running wedge with `accumulate` — exactly right.)
- **adjacent pairs → `itertools.pairwise(xs)`**, the single-pass-safe form of `zip(xs, xs[1:])`
  (works on a one-shot iterator you can't slice). Prefer it to a hand-carried "previous element"
  loop variable.
- **Python has no tail-call optimization and a recursion limit (~1000 frames).** So structural
  recursion is for **bounded** structures (a frame of ≤ *n* vectors, a short AST, a fixed-depth
  tree) where it is clearest; for a deep or unbounded sequence, write the **iterative** form (a
  loop, or a generator) rather than deep recursion. This is the one place the Python spelling
  overrides the scheme: the scheme says "recurse," Python says "but iterate when it's deep."

## References

- **SICP §2.2.3, "Sequences as Conventional Interfaces"** (Abelson & Sussman) — map/filter/
  accumulate as a signal-flow pipeline of independent stages; a direct recursion "fail[s] to
  exhibit this signal-flow structure." <https://sicp.sourceacademy.org/chapters/2.2.3.html>
- **How to Design Programs** (Felleisen, Findler, Flatt, Krishnamurthi) — the design recipe and the
  distinction between **structural** recursion (follow the data definition) and **generative**
  recursion (invent new sub-problems). <https://htdp.org/>
- **John Hughes, "Why Functional Programming Matters"** (1990) — higher-order functions (map, fold)
  as the glue that makes programs modular and composable.
- **Graham Hutton, "A tutorial on the universality and expressiveness of fold"** (J. Functional
  Programming, 1999) — fold as *the* fundamental list recursion scheme (map, filter, sum, … all
  fall out of it), which is why it is the most general and the least specific.
- **Paul Graham, *On Lisp*** — §15.2 "Recursion on Cdrs" (the nil/cons list-recursion idiom) and
  ch. 5 on functional programming / `mapcar`.
  <https://redirect.cs.umbc.edu/courses/331/resources/lisp/onLisp/15macrosReturningFunctions.pdf>
- **Norvig & Pitman, "Tutorial on Good Lisp Programming Style"** (1993) — the maxims *be explicit,
  be specific, be concise, be consistent, be conventional* (use the most specific operator; name
  and shape things as a reader expects). <https://www.cs.umd.edu/~nau/cmsc421/norvig-lisp-style.pdf>
- **Guido van Rossum, "The fate of reduce() in Python 3000"** (2005) — `reduce` demoted from a
  builtin to `functools` because it was "used almost only to implement `sum()`" or to write
  "unreadable code"; `map`/`filter` kept, comprehensions preferred. (Quoted at
  <https://blog.finxter.com/about-guidos-fate-of-reduce-in-python-3000/>.)

## Cross-links

- **`~/.claude/reference/python-coding-standard.md`** — the terse Python *spelling* rule
  ("Reduce with `sum`/`math.prod`, not a hand-rolled accumulator loop"; comprehensions over
  map/filter+loop) points here for the design body.
- The maintainer's `~/.claude/CLAUDE.md` code-shape family — "Prefer total dispatch over an
  open-ended conditional chain", "What earns pulling code into its own function" — of which this
  doc is the recursion-shaping member.
- A project's own additions doc carries its worked examples (e.g. geometricalgebra
  `tasks/reference/conditional-refactoring-rules.md`).
