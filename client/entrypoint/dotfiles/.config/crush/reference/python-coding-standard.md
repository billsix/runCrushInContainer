# Python coding standard (shared, cross-project)

**Reference document** — shared cross-project Python coding standard; harvested from
geometricalgebra/modelviewprojection CLAUDE.md, 2026-09-13. Read on demand (NOT
auto-loaded). Update in place. A project's `CLAUDE.md`/`README.md` points here and keeps
only its own repo-specific invariants inline.

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/python-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/python-coding-standard.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/python-coding-standard.md`,
> and the baked crush-client set
> `client/entrypoint/dotfiles/.config/crush/reference/python-coding-standard.md` — delivered
> to a Crush session at `~/.config/crush/reference/python-coding-standard.md`, which is how a
> project developed *with Crush* gets this standard. The two sandboxes are parallel
> implementations of the same idea — Claude Code (proprietary) and Crush (open source). Edit
> the canonical, then re-copy it over the other two.

Written for both humans and AI agents: each rule is a statement + a one-line reason. The
worked examples are drawn from geometricalgebra (gacalc) where noted; treat them as
illustrations of the rule, not as gacalc-only policy. **The standard is split in two** —
(a) what **ruff already enforces mechanically** (don't hand-review or re-prose these; if
`make format` is green they're done), and (b) the **judgment calls ruff can't check**
(spend attention here).

## (a) Enforced by ruff — treat green ruff as authority

The `[tool.ruff.lint] select` in `pyproject.toml` (the whole `E`, `F`, `I` categories +
named rules) already gives: PEP 8 layout/whitespace/blank-lines (`E`), the Pyflakes
correctness tier (`F` — unused/undefined/logic bugs, incl. the `== None`→`is None` /
`== True` / bare-`except` idioms E711/E712/E722), import sorting (`I`), modern unions
`X | Y` (UP007/UP035), no mutable/callable default args (B006/B008), no unused loop var
(B007), absolute imports (TID252), no stray `print` (T201), non-crypto `random` /
`shell=True` (S311/S602), **and naming (the `N` / pep8-naming family)**. Treat a green
ruff as authority on all of these.

## Line length is the formatter's job, NOT a design input

`ruff format` (via `make format`, which the maintainer runs) wraps long lines
mechanically, so **never factor the 88-column limit into how you write or refactor code.**
Write the *clearer* form and let the formatter wrap it — in particular, do **not** reject a
ternary, a `match` arm, or a call because the one-liner would exceed 88 cols; that concern
is handled downstream. Length is never the reason to leave a conditional un-refactored —
only *readability* and *outcome shape* are. The rare genuinely-unwrappable case (an aligned
literal, a URL) still gets a scoped `# noqa: E501`, as always. (Bill, 2026-09-05.)

## (b) Judgment calls — prose, because ruff can't check them

### Naming grammar (`N` enforces the *casing*; these are the parts it can't)

snake_case values/functions, CapWords classes/type-vars, exceptions end in `Error`,
UPPER_SNAKE constants, `_internal` (prefer one underscore over `__mangled`), `trailing_`
only to dodge a keyword. **Verbs for functions, nouns for values;** boolean predicates
`is_`/`has_`/`should_`. Descriptive over terse; short names only in tight scopes (loop
index, `except … as e`, `with open() as f`, math). No redundant suffixes (`names` not
`name_list`; `name_by_id` not `id_to_name_dict`), no letter-deleting abbreviations. **A
local bound to a class/type object is named `cls`** (mirrors the classmethod first arg —
e.g. `cls = type(vector)`), never a synonym like `representation`/`klass`.

### Prefer expressions; obey the mutate-vs-return rule

Value-returning forms (`sorted(xs)`, `reversed(xs)`, a comprehension, `s | {x}`) return a
NEW value; in-place methods (`list.sort/append/extend`, `set.add`, `dict.update`, …) mutate
and return `None`. So `top = names.sort()` is a bug, and you must never chain a mutator.
Command–Query Separation: a function either *does* (side effect, returns `None`) or
*computes* (value, no side effect) — not both.

### Reduce with `sum` / `math.prod`, not a hand-rolled accumulator loop

When a loop's only job is to fold an iterable under `+` or `*`, use the builtin: it names
the operation and can't get the accumulator wiring wrong, and it reads as one expression.
Pass the **correct identity** as `start`: `sum(xs)` (implicit `start=0`), `math.prod(xs,
start=1)`; for a non-numeric accumuland pass the type's identity explicitly
(`math.prod(blades, start=cls.one())`, `sum(mvs, start=cls.zero())`). An `int` identity
keeps a float/sympy pipeline intact (`1 * 2.0 == 2.0`). Worked example (gacalc) —
`measure.content_by_rejection` went from `result = 1; for pv in
make_orthogonal_frame(vectors): result = result * pv.magnitude()` to
`math.prod((pv.magnitude() for pv in make_orthogonal_frame(vectors)), start=1)`. **Only
when the loop is a pure fold:** keep the explicit loop if the body also has side effects, an
early exit, or more than one accumulator, or if there is no clean identity element. (Same
spirit: `any` / `all` / `min` / `max`, and `functools.reduce` for other associative folds.)

### Idioms (the full checklist; the ones ruff already enforces are marked)

EAFP over LBYL; truthiness for emptiness `if not seq:` (but compare ints to `0`
explicitly); `is`/`is not` for `None`/singletons *(ruff)*; `isinstance` over `type(x) == T`
*(ruff)*; `enumerate`/`zip` over `range(len(...))`; comprehensions over trivial
map/filter+loop (keep them simple); f-strings over `%`/`.format`; `with` for resources;
`dict.get`/`defaultdict`/`setdefault`; iterable unpacking (`first, *rest = xs`); no
mutable/callable defaults *(ruff)*; `pathlib` over `os.path`; keyword args at call sites for
meaning; flat over nested; no bare `except` *(ruff)*; no stray `print` *(ruff)*; consistent
returns (if any branch returns a value, all do).

### Type annotations — annotate generously

Signatures (params + returns) are the contract → always. **Locals: as much as reasonable —
prefer a declared type over none, including in library code** (`r: Rotor = a * b`); skip
only where it would be pure noise (`n = 3`), and **when in doubt, annotate.**
**Loop/unpack targets** can't be annotated inline — declare the type on the line *above*
(`blade: tuple[int, ...]` / `coef: Coef` above `for blade, coef in
mv.to_blade_dict().items():`; a bare `x: sympy.Symbol` per name above a `symbols(...)`
unpack). Two limits: it does **not** reach a *comprehension*/genexpr loop var (separate
scope — stays inferred), and if a name would be reused across loops of different (sub)types,
**give each loop its own distinctly-named, typed variable** (don't reuse one name for two
types — e.g. `composable_fn: ComposableFunction` in one loop, `invertible_fn:
InvertibleFunction` in the next). **Don't fight the checker:** a locally-correct annotation
that forces edits to unrelated logic or breaks flow-narrowing isn't worth it — leave it
inferred and say why. Read-only container params take the covariant supertype
(`Mapping`/`Sequence`), not invariant `dict`/`list`. Polymorphic values take the abstract
base, never a runtime-picked concrete. (Teaching notebooks especially: name + type the
values.) *(gacalc specifics: the repo-wide sweep landed 2026-09-09, so every remaining
unannotated site is a deliberate exemption catalogued in
`tasks/reference/type-annotation-exemptions.md`; re-run `python tools/check_annotations.py`
after reshaping hand-written Python — a row it reports that is not in that doc is a genuine
gap.)*

### Parameterize generic types — never a bare generic in an annotation

Write `ComposableFunction[MultiVectorBase]` / `InvertibleFunction[g3.Vector]`, not a bare
`ComposableFunction` / `InvertibleFunction` (a bare generic silently degrades its parameter
to implicit `Any`). Where a generic is **invariant** with an **unbounded** parameter, the
parameter must match the value's *exact* type — verify each with the type checker rather
than blanket-annotating a common base. **A *polymorphic* param that accepts *any* instance
of the generic and applies it to the base internally** is `[Any]` — invariance makes a fixed
base-parameter reject concrete-typed arguments, and a bound TypeVar reject the internal
base-application; `Any` is the only thing compatible both ways. Exceptions that stay bare: a
runtime `isinstance(f, SomeGeneric)` (can't take a subscripted generic), and a concrete
`Callable` alias (not a generic). *(gacalc: `ComposableFunction`/`InvertibleFunction` are
invariant with an unbounded `V` because `functions.py` must not import `base`; notebooks
aren't in the `ty` gate — verify their generics with `pyright` in the container, where host
`ty` can't reach. Detail in `tasks/reference/transform-and-composable-function-layer.md` /
`generated-product-typing.md`.)*

### Inline a value used exactly once — unless the name documents an otherwise-opaque expression

This **takes precedence over "annotate generously"**: don't create or keep a single-use
local just to give it a type — inline it (e.g. pass the f-string straight to
`latex_repr=`). Generous typing applies to the locals that *survive* — reused, hoisted out
of a closure so it's computed once, or named to clarify an opaque expression. (Same spirit
as: no local aliases for a value that already has a canonical name — reference the canonical
name directly, never `E1 = Vector.basis_vector(1)`.)

### What earns an extraction: duplication, or naming a phase — not reshaping control flow

Settled 2026-07-18 (gacalc) from what the maintainer accepted and declined:

- **Module-level** when more than one caller needs it. `nbplotutils._to_xy` replaced the
  same 79-char lambda written out **9 times across 5 functions**; `_draw_labelled_triangle`
  replaced three 58-line, 91-93%-identical `draw_*_triangle` helpers with one function plus
  three ~10-line callers (**net -75 lines**, all rendered figures verified pixel-identical).
  A private nested helper in each of the five would have been five copies — worse than the
  duplication it "fixed".
- **Nested** when the extracted part **closes over the enclosing parameters** and names a
  distinct phase of the algorithm. `base.reject`'s `r`/`rejection` close over `away_from`;
  a `_route` splits into `breadth_first_parents` / `walk_back`, both over `a` and `b`.
- **Neither** — leave it alone — when the helper would be used exactly once and exists only
  to reshape control flow or avoid mutating a local. That is the "inline a value used
  exactly once" rule applied to functions.

**"Inner-fn first, guards below" is a consequence of the above, not the goal.** When an
extraction is earned, the guards naturally end up at the bottom calling into it — as in
`base.reject`:

```python
def reject(cls, away_from):
    def r(value):  # the core operation, up top
        return value.wedge(away_from) * away_from.inverse()

    def rejection(blade):  # wraps it with its LaTeX label
        return ComposableFunction(r, latex_repr=..., linearity=Linearity.LINEAR)

    match away_from:  # preconditions / dispatch below, calling in
        case [*sequence]:
            return cls.reject(cls.outer_product_of_vectors(*sequence))
        case MultiVectorBase() as vector if vector.is_vector():
            return rejection(vector)
        case _:
            raise ...
```

Don't chase the shape for its own sake, and **don't churn existing early-return code**; a
cheap top-of-function `raise` on a nonsensical arg is always fine. A related lesson: an
error is best raised by the code that *discovers* it — `_route`'s "no path" moved into the
search itself, which is what let its tail collapse to one line.

### Comments explain *why*, inline at the point they apply

Not a trailing notes block. **Never leave a comment line holding a single word or a sentence
fragment** — when a line runs long, reflow the whole paragraph, not the offending line.

### An externally-defined name overrides the naming rules

Where a name is dictated from outside — a protocol/dunder the interpreter or a library looks
up, a superclass method being overridden — match it **exactly**; renaming unbinds it.
(gacalc examples: `_repr_latex_` — Jupyter looks up that exact name; `__post_init__` /
`__eq__` / `__iter__` / `__matmul__`; and the interchange primitives a concrete
representation must supply — `from_blade_dict` / `to_blade_dict` / `_geometric_product` —
fixed by `MultiVectorBase`, not by taste.) A linter flagging one is the linter being wrong:
suppress it as narrowly as possible with the reason written at the site. The exemption
covers only the fixed name — parameters and locals inside still follow house style.

### Protected terse names — a deliberate exception to "descriptive over terse"

Where a terse name carries a teaching link to a known equation, protect it. gacalc example:
`m` and `b` — `translate(b=...)` and `uniform_scale(m=...)` are named for `f(x) = m*x + b`
(`b` the intercept/shift, `m` the slope/stretch) — so a student meets the transforms through
an equation they already know. **Do not "improve" them to `offset` / `factor`**, and call
them by keyword in teaching code (notebooks, docstrings) so the link is visible at the point
of use. (ruff is fine with both: `N803` only requires lowercase.)

### Prefer `match` + `case _` over an open-ended `if`/`elif` chain, for exhaustiveness

A chain with no final `else` can fall through silently and the hole is invisible; a `match`
makes the default a branch you must look at. **Always write the `case _`** — a `match`
without one has the same hole. It may raise, return a documented fallback, or be an explicit
no-op with a comment. **Caveat:** `match` earns its keep on *structural* patterns; one whose
every case is a boolean guard is an `if`/`elif` in different syntax, justified only by the
exhaustiveness argument — don't convert every two-branch conditional.

### Refactoring a conditional — vary the mechanism (Rules A–E)

Before touching one, ask in order:

- **(A) ternary** — collapse a guard-*value*-return + fall-through-return to `X if cond else
  Y` when both outcomes are single expressions (not multi-statement, no side effect between
  guard and return), there are exactly two outcomes, and it reads at least as clearly
  (length is NOT a criterion — `make format` wraps a long ternary; NOT a top-of-function
  early-exit guard `if bad: raise`/`return None`/`continue` — that's the sanctioned cheap
  guard, don't churn it);
- **(B) dedup** identical branches first (watch for *vestigial* splits kept apart only by
  comments — but verify byte-identical, a `cast`/no-`cast` difference is a live distinction,
  not dead weight);
- **(C) `match`** when the *pattern* does structural work (type/shape/literal/binding) —
  strip the guards, keep the patterns: if they still dispatch → `match`, if all `case _` →
  `if`/`elif`;
- **(D)** turn a boolean/prefix check matchable by extracting a **literal discriminant**
  first (`kind, _, label = name.partition("_")` then `match kind:` with a `case _: raise`
  documenting the invariant);
- **(E)** extract a **long** dispatch's branch-bodies into **named nested functions** that
  **return** their nodes (read the enclosing scope freely, never mutate it) so the dispatch
  is a *table of contents* not interleaved chapters — the memorable framing.

Worked before/after examples + the leave-alones (gacalc):
`tasks/reference/conditional-refactoring-rules.md`.

### Use modern Python, and flag it proactively

Prefer the current-language solution over the historical one, and **when a newer feature
would solve a problem in code you're already touching, say so** rather than silently
preserving the old form. In scope when it fits: `match` (structural pattern matching); `X |
Y` unions and builtin generics over `typing.Optional`/`Union`/`Dict`; PEP 695 `type` aliases
and `class C[T]:` / `def f[T]()` in place of explicit `TypeVar`s (note: an *unbounded* type
parameter must stay unbounded whatever syntax expresses it); `Self`; `@override`;
`typing.TypeIs`; `enum.StrEnum`; `dataclass(slots=True, kw_only=True)`. Don't force one in
where it reads worse; the point is to stop *defaulting* to the old spelling. (gacalc:
`requires-python = ">=3.13"`, and compatibility with older Pythons is explicitly not a
concern.)

## modelviewprojection-specific additions

These are modelviewprojection's own rules and worked examples that specialize or extend the
general standard above. They were collected here from mvp's `CLAUDE.md` (2026-09-13 trim) so
that repo's `CLAUDE.md` can point at this one doc; the file paths and framework names are
mvp's. Other projects can ignore this section.

### Line length is 80, because the book is a PDF

Unlike the 88-column default above, mvp sets **`line-length = 80`** in `pyproject.toml`, which
governs both the formatter and E501 — 80 because the book is built as a PDF, where wider lines
wrap badly or run off the page. Everything else in "Line length is the formatter's job" still
applies: write the clearer form and let `ruff format` wrap it.

### Every `per-file-ignores` entry carries its reason in `pyproject.toml`

Read them before "fixing" a flagged name — most are deliberate.

### An externally-defined name overrides the naming rules — mvp's wx boundary

Applying the general "An externally-defined name overrides the naming rules" rule: here that is
`wxapp.py` / `wxapp2.py` (`OnPaint`, `OnTimer`, `InitGL`, `OnDraw`, `OnInit` — wx looks
up those exact names; exempted from `N802` only) and wx's `attribList=` keyword. The
exemption covers only the fixed name: locals inside those methods follow house style
(hence `VBO` -> `vbo`, `attribList` -> `attrib_list` at the local).

### Python naming wins over the book's mathematical shorthand — everywhere, including the demos

The chapters' Cayley-graph edges are labelled in vector notation
(`\vec{R}_<θ>`, `\vec{T}_<x,y>`, `\vec{S}_<s>`) and the demos used to alias
`translate as T` / `rotate as R` / `uniform_scale as S` to match, with frustum bounds
as `L,R,B,T,N,F` and a light position as `Lx,Ly,Lz,Lw`. **All of that is spelled out
now**: `translate()`, `rotate()`, `uniform_scale()`, `left/right/bottom/top/near/far`,
`light_x…light_w`.
**The graph-to-code mapping is what makes this safe, so keep it.** Each affected demo
carries a short comment above its imports reading the graph labels off against the
function names. When you add a demo whose chapter has a diagram, add the same note —
a student must be able to line the picture up with the source without guessing.
The single remaining naming exemption is `N813` for `import … matrix_stack as ms`,
and it is temporary: the fix is renaming the camelCase *module*
(`tasks/archive/2026/07/19/rename-pymatrixstack-module.md`), which deletes the exemption at the source
rather than suppressing it.

### Composition style: `f @ g` inline, `compose([...])` when it wraps

`f @ g` only when the chain fits on one line; `compose([f, g, ...])` the moment it would
wrap — same order (`f` after `g`, last listed applied first), one function per line, instead
of the formatter's dangling `@` with exploded arguments (maintainer, 2026-09-06). numpy's
matrix `@` (the `mvpvisualization` demos, `test_cayley_scene`) is not composition and keeps `@`.

### Worked example — the `match` + `case _` that was actually bitten

`matrix_stack.get_current_matrix` was five `if`s with no `else`, annotated `-> np.ndarray`,
and fell off the end returning `None` for any unhandled `MatrixStack` member — while every
caller indexed the result. It is now a `match` with `case _: raise`. See also `_route` in
`cayley/cayleygraph.py`, whose tail is a three-case `match`, and `cayleygraph._DfsColor` (an
`enum.IntEnum` that replaced a bare `WHITE, GRAY, BLACK = 0, 1, 2`).

### New code vs existing code

These shapes apply to *new* code; working code is not rewritten to chase them. (The
2026-07-18 sweep that brought the tree into compliance was a deliberate one-time exception,
not the ongoing rule.)

### Duplication across `demos/` is deliberate — "teach once, then share"

A demo may re-inline a helper when its chapter teaches it; `util/clipping.py`,
`util/windowing.py` and `util/cameracontrols.py` document their own cases. Do not DRY the
~20 near-identical `Paddle`/`Camera` dataclasses without reading those notes.

## Cross-links

- `tasks/reference/conditional-refactoring-rules.md` (gacalc) — the Rules A–E worked
  examples.
- `tasks/reference/type-annotation-exemptions.md` (gacalc) — the catalogued
  no-annotation sites and their reasons.
- The maintainer's `~/.claude/CLAUDE.md` — the language-agnostic conventions
  ("Use your discretion", "Never orphan a word on its own comment line", "What earns
  pulling code into its own function", "Prefer total dispatch over an open-ended conditional
  chain", "An externally-defined name always wins over a naming convention") that this
  standard specializes for Python.
