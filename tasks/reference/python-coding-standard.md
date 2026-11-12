# Python coding standard (shared, cross-project)

**Reference document** — shared cross-project Python coding standard. Read on demand (NOT
auto-loaded). Update in place. A project's `CLAUDE.md`/`README.md` points here and keeps its
own repo-specific invariants, worked examples, and file paths in its own additions doc
(see Cross-links). Portable rules only: this doc names no one project's files. (Originally
harvested from two projects' CLAUDE.md 2026-09-13; project specifics split back out
2026-10-12 — William Emerison Six <billsix@gmail.com>.)

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

Written for both humans and AI agents: each rule is a statement + a one-line reason.
**Worked examples and any repo-specific detail live in each project's own additions doc**
— e.g. modelviewprojection's `tasks/reference/python-coding-standard-mvp.md` and
geometricalgebra's `tasks/reference/python-coding-standard-gacalc.md` — so this shared doc
stays portable and names no one project's files. A rule here points to "your project's
additions doc" for the worked example. **The standard is split in two** —
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

## Excluding a file from the gate takes TWO settings — ruff and ty don't share excludes

`ty` does **not** honor ruff's `extend-exclude`, so a file you need out of the gate (e.g. one
whose filename is an invalid Python module name, or generated/vendored code) must be listed in
**both** places in `pyproject.toml`: `[tool.ruff]` `extend-exclude = [...]` **and**
`[tool.ty.src]` `exclude = [...]`. Set only the ruff entry and `make type-check` still
type-checks the file; set only the ty entry and `ruff` / `make format` still lints it — a silent
half-exclusion. The worked example lives in your project's additions doc. (William Emerison Six
<billsix@gmail.com>, 2026-11-02.)

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
(`math.prod(xs, start=cls.one())`, `sum(xs, start=cls.zero())`). A non-float identity
element keeps a float/sympy pipeline intact (`1 * 2.0 == 2.0`). **Only
when the loop is a pure fold:** keep the explicit loop if the body also has side effects, an
early exit, or more than one accumulator, or if there is no clean identity element. (Same
spirit: `any` / `all` / `min` / `max`, and `functools.reduce` for other associative folds.)
More broadly, prefer the **most specific** scheme: **map/filter → a comprehension**, fold → the
named builtin above, and **`functools.reduce` only for a genuine associative fold the builtins
can't cover** — and then **name its accumulator `acc`/`accumulator`** (not a bare `w`/`x`) in the
conventional accumulator-first position. For how to *shape* a recursion itself — nil/cons
structural recursion, mapping over the tail instead of threading an accumulator, when an
accumulator is actually warranted, and the Python no-TCO caveat — see
`~/.claude/reference/recursive-design.md`.

### Idioms (the full checklist; the ones ruff already enforces are marked)

EAFP over LBYL; truthiness for emptiness `if not seq:` (but compare ints to `0`
explicitly); `is`/`is not` for `None`/singletons *(ruff)*; `isinstance` over `type(x) == T`
*(ruff)*; `enumerate`/`zip` over `range(len(...))`; comprehensions over trivial
map/filter+loop (keep them simple; `recursive-design.md` for the why and for shaping a
recursion); `itertools.pairwise` over a hand-carried "previous element"; f-strings over
`%`/`.format`; `with` for resources;
`dict.get`/`defaultdict`/`setdefault`; iterable unpacking (`first, *rest = xs`); no
mutable/callable defaults *(ruff)*; `pathlib` over `os.path`; keyword args at call sites for
meaning; flat over nested; no bare `except` *(ruff)*; no stray `print` *(ruff)*; consistent
returns (if any branch returns a value, all do).

### Type annotations — annotate every binding

Annotate the type of **every** variable — every module-level/global AND every local — not
just function signatures. Signatures (params + returns) are the contract → always; **and
every assignment binding carries its own explicit type too**, including obvious ones once
waved through as noise (`n: int = 3`, `total: float = 0.0`) — do NOT skip a binding
(William Emerison Six <billsix@gmail.com>, 2026-09-28). Holds in library code
(`r: Versor = a * b`) AND in throwaway `tasks/adhoc/` scripts.
**Loop/unpack / `with as` / `except as` targets** can't carry an inline annotation, and a
project's completeness checker deliberately **exempts** them — so by default **leave them
inferred**, matching what the project's existing code does. Add a type on the line *above*
(`key: str` / `count: int` above `for key, count in counts.items():`; a bare
`x: sympy.Symbol` per name above a `symbols(...)` unpack) **only where it genuinely aids
clarity** — an opaque unpack, or a `ty` error the annotation resolves. When you *do*
annotate above, it still does **not** reach a *comprehension*/genexpr loop var (separate
scope — stays inferred), and if a name would be reused across loops of different (sub)types,
**give each loop its own distinctly-named, typed variable**. (Leave-inferred-by-default
reflects the checker's exemption and established practice — William Emerison Six
<billsix@gmail.com>, 2026-10-19.) **Don't fight the
checker:** a locally-correct annotation
that forces edits to unrelated logic or breaks flow-narrowing isn't worth it — leave it
inferred and say why. Read-only container params take the covariant supertype
(`Mapping`/`Sequence`), not invariant `dict`/`list`. Polymorphic values take the abstract
base, never a runtime-picked concrete. (Teaching notebooks especially: name + type the
values.) A project that has run a repo-wide annotation sweep may catalogue its remaining
deliberate exemptions and provide a checker — see your project's additions doc.

### Parameterize generic types — never a bare generic in an annotation

Write `Stack[int]` / `Mapping[str, Node]`, not a bare `Stack` / `Mapping` (a bare generic
silently degrades its parameter to implicit `Any`). **When the exact parameters are not readily knowable, parameterize with `Any` rather than leaving the generic bare** — `list[Any]` / `dict[str, Any]` beats bare `list` / `dict`: a bare generic *already* means implicit `Any`, but silently — invisible to a reader, and it slips past the checker — whereas an explicit `Any` documents that the element type is intentionally unconstrained. Prefer the exact type where it is clear, fall back to `Any` where it is not, and **never leave it bare** (William Emerison Six <billsix@gmail.com>, 2026-10-29). Where a generic is **invariant** with an **unbounded** parameter, the
parameter must match the value's *exact* type — verify each with the type checker rather
than blanket-annotating a common base. **A *polymorphic* param that accepts *any* instance
of the generic and applies it to the base internally** is `[Any]` — invariance makes a fixed
base-parameter reject concrete-typed arguments, and a bound TypeVar reject the internal
base-application; `Any` is the only thing compatible both ways. Exceptions that stay bare: a
runtime `isinstance(f, SomeGeneric)` (can't take a subscripted generic), and a concrete
`Callable` alias (not a generic). A project whose generics are invariant with an unbounded
parameter, or whose notebooks fall outside the type gate, documents the specifics and the
`[Any]`-vs-exact-type calls in its own additions doc.

### Inline a value used once, and name it in a comment instead of a binding

This **takes precedence over "annotate generously"**: don't create or keep a single-use
local just to give it a type — inline it (e.g. pass the f-string straight to
`latex_repr=`). Generous typing applies to the locals that *survive* — reused, or hoisted out
of a closure so it's computed once. (Same spirit as: no local aliases for a value that already
has a canonical name — reference the canonical name directly, never
`E1 = Vector.basis_vector(1)`.)

**A name bound once and used once is inlined, even when the name was there to explain the
expression.** A reader who meets a declaration scans ahead to see how far it is used; a
single-use binding makes them do that scan for nothing, and the cost grows with the length of
the function. Inline the expression and put a **comment above it that quotes or describes the
subexpression and gives it its name** ("`pairs`: each orthogonal vector with the frame vector
it came from, in frame order"), so the reader still gets the name without a binding to track.
Keep a binding only when it is reused or hoisted so it is computed once. (Decided by William
Emerison Six <billsix@gmail.com>, 2026-11-06; this replaced an earlier exception that kept a
single-use name when it documented an opaque expression.)

**"Used twice" does not by itself earn a name either.** Before keeping a multi-use local, check
whether one expression absorbs the uses. `d = getattr(cls, "DIMENSION", None)` followed by
`n = d if d is not None else fallback` is exactly `getattr(cls, "DIMENSION", fallback)` (the
fallback is now always evaluated, which is fine when it is cheap); `dict.get(key, default)` and
`next(iterator, default)` collapse the same shape. A cheap, clear expression such as `len(xs)`
can simply be repeated. Keep the name when repeating its expression would be longer or harder
to read than the name, or would compute something expensive twice; an example is a three-line
dimension computation used in a check and again in that check's error message.

**Declare a name at the point of use.** A binding built many lines before its only use makes
the reader carry it across everything in between. Move it down to where it is used, or, if it is
used once, inline it there.

Worked example: gacalc's `Frame.to_invertible_function` refactor, 2026-11-06 (that project's
additions doc). Earlier examples, 2026-10-29: `rest_orthogonal_to_v` in
`frame.make_orthogonal_frame` and the `prepended` blade in `Gn._geometric_product`, each inlined
into the recursive call it fed.

### What earns an extraction: duplication, or naming a phase — not reshaping control flow

Settled 2026-07-18 from what the maintainer accepted and declined:

- **Module-level** when more than one caller needs it: replacing one expression written out
  many times across several functions, or collapsing near-identical sibling helpers into one
  parametrized function plus thin callers. A private nested helper copied into each caller
  would be worse than the duplication it "fixed".
- **Nested** when the extracted part **closes over the enclosing parameters** and names a
  distinct phase of the algorithm.
- **Neither** — leave it alone — when the helper would be used exactly once and exists only
  to reshape control flow or avoid mutating a local. That is the "inline a value used
  once" rule applied to functions.
- **A helper with one caller is nested inside that caller**, not defined beside it at the outer
  level. This applies to a helper that earns its existence (a recursion, a step reused within
  the caller) but has only one caller. Nesting shows its scope at a glance; the only cost is
  creating a function object per call of the caller, negligible unless that caller runs in a
  tight loop.
- **When nesting, shadow deliberately, and verify the shadowing.** Give the nested helper's
  parameter the caller's name when it holds the same kind of value (`peel(remaining, y)`
  inside `backward(y)`), so the reader knows the outer binding is out of play inside the
  helper. Check that this is correct: the helper must never need the outer value, and none of
  its other names (parameters, pattern captures, locals) may hide an enclosing binding it does
  need. (William Emerison Six <billsix@gmail.com>, 2026-11-06.)

**"Inner-fn first, guards below" is a consequence of the above, not the goal.** When an
extraction is earned, the inner function(s) carrying the core operation go up top (closing
over the enclosing parameters) and the preconditions / dispatch — typically a `match` — land
at the bottom, calling in. Don't chase the shape for its own sake, and **don't churn existing
early-return code**; a cheap top-of-function `raise` on a nonsensical arg is always fine. A
related lesson: an error is best raised by the code that *discovers* it — pushing a "not
found" into the search itself is often what lets a function's tail collapse to one line.
Worked examples live in each project's additions doc.

### Guard application code with `if __name__ == "__main__":` — separate functional from script

**A module should be safe to import without *doing* anything** — defining functions, classes and
constants, not running them. Any code that *acts* when the file is run as a script (a demo, a CLI
entry point, opening a window, `sys.exit()`, printing, wiring up `argparse`) goes under an
`if __name__ == "__main__":` guard at the bottom, calling a `main()` that is itself just another
defined function. Treat this as **standard practice**, not an afterthought: a bare module that runs
work at import is the thing to fix.

- **Restructure to make it true when it isn't.** If a module mixes a reusable function with
  work it does at import, split them — lift the reusable part to a plain function/class, and move
  the "run it" part under the guard. The separation of *functional* (importable, testable) from
  *application* (the script's entry) is the point; the guard is how Python spells it.
- **It is what makes a module doctest-safe.** `pytest --doctest-modules` *imports* every module it
  collects, so an unguarded script crashes collection; guarding it project-wide lets the doctest
  gate collect everything with no per-module exclusion list (see
  `~/.claude/reference/doctests-by-default.md`). (hanoi, 2026-10-27: all 11 modules were already
  guarded, so the gate's `testpaths = tests src` needed no allowlist.)
- **The reach has a limit:** don't contort a module whose *only* purpose is to be run (a thin
  `__main__.py`, a genuine one-shot script) — but even there, a `main()` under the guard beats
  top-level statements, because it stays importable for a test.

### Comments explain *why*, inline at the point they apply

Not a trailing notes block. **Never leave a comment line holding a single word or a sentence
fragment** — when a line runs long, reflow the whole paragraph, not the offending line.

### An externally-defined name overrides the naming rules

Where a name is dictated from outside — a protocol/dunder the interpreter or a library looks
up, a superclass method being overridden — match it **exactly**; renaming unbinds it.
(Examples: `_repr_latex_` — Jupyter looks up that exact name; `__post_init__` / `__eq__` /
`__iter__` / `__matmul__`; and any interchange primitive a base class or protocol fixes by
contract, not by taste.) A linter flagging one is the linter being wrong:
suppress it as narrowly as possible with the reason written at the site. The exemption
covers only the fixed name — parameters and locals inside still follow house style.

### Protected terse names — a deliberate exception to "descriptive over terse"

Where a terse name carries a teaching link to a known equation, protect it: a single-letter
or very short name a reader already knows from the math it encodes, matched to the equation,
is clearer than a "descriptive" rename. **Do not "improve" such a name** to a generic word,
and call it by keyword in teaching code (notebooks, docstrings) so the link is visible at the
point of use. (ruff is fine: `N803` only requires lowercase.) The concrete protected names
live in each project's additions doc.

### Prefer `match` + `case _` over an open-ended `if`/`elif` chain, for exhaustiveness

A chain with no final `else` can fall through silently and the hole is invisible; a `match`
makes the default a branch you must look at. **Always write the `case _`** — a `match`
without one has the same hole. It may raise, return a documented fallback, or be an explicit
no-op with a comment. **Caveat:** `match` earns its keep on *structural* patterns; one whose
every case is a boolean guard is an `if`/`elif` in different syntax, justified only by the
exhaustiveness argument — don't convert every two-branch conditional.

### Options are enums, not strings

A parameter that selects one of a fixed set of options (a mode, a method, a backend) takes an
`enum.Enum`, never a string or a `Literal["a", "b"]` of strings. Define the enum next to the
function that takes it (or in the lowest module that names it in a signature), export it, give it a
docstring listing what each member means, and default the parameter to a member
(`backend: MatrixBackend = MatrixBackend.NUMPY`). Dispatch with `match` on the members, and keep the
`case _` (rule above): there it raises `TypeError` naming the enum, which is what a caller still
passing the old string sees. Why: a typo in a string option is a runtime error at best and a silent
wrong branch at worst; an enum member is checked by the type checker and the editor completes it.
Not options: labels, titles, file names, LaTeX, and values a library dictates (matplotlib colours) stay
`str`. Converting a published API this way is a breaking change (changelog + version bump). Worked
example: github.com/billsix/geometricalgebra (`frame.InverseMethod`, `functions.MatrixBackend`,
2026-11-10).

### Mutually exclusive branches are one `if`/`elif`/`else` chain

When two or more conditions pick among the outcomes of **one decision**, write them as a single chain,
`if` … `elif` … `else`, with the last outcome in the `else`. That includes a run of early-exit guards in
front of a result: each guard is a branch of the same decision, so it is an `elif`, and the result is the
`else`.

```python
# Not this: three separate ifs, then a fall-through. They exit, so they are exclusive,
# but the reader has to check that.
if along == zero:
    raise ValueError("the zero vector spans no line")
if vector == zero:
    return 0
if not vector.is_parallel_to(along):
    raise ValueError("not on the line")
return (vector / along).scalar_part()

# This: one decision, read top to bottom, and the else is the default.
if along == zero:
    raise ValueError("the zero vector spans no line")
elif vector == zero:
    return 0
elif not vector.is_parallel_to(along):
    raise ValueError("not on the line")
else:
    return (vector / along).scalar_part()
```

The chain's `else` is the total default, which is what the `match` rule above asks for, so an
all-guard `match` (`case _ if …:` in every arm) is written as this chain instead. Two things stay as
they are: **a single guard** before the function's main body (`if bad: raise`, then the body; there is
no second branch to chain), and **independent checks** that can each fire (accumulating errors, a
cleanup step), which are separate `if`s on purpose. Don't let a linter talk you out of the `else`:
ruff's `RET505`/`RET506` ("unnecessary `else` after `return`/`raise`") contradict this rule, so leave
them off. (William Emerison Six <billsix@gmail.com>, 2026-11-07: "I want to see that they are mutually
exclusive.")

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

Worked before/after examples + the leave-alones live in the project additions docs.

### Use modern Python, and flag it proactively

Prefer the current-language solution over the historical one, and **when a newer feature
would solve a problem in code you're already touching, say so** rather than silently
preserving the old form. In scope when it fits: `match` (structural pattern matching); `X |
Y` unions and builtin generics over `typing.Optional`/`Union`/`Dict`; PEP 695 `type` aliases
and `class C[T]:` / `def f[T]()` in place of explicit `TypeVar`s (note: an *unbounded* type
parameter must stay unbounded whatever syntax expresses it); `Self`; `@override`;
`typing.TypeIs`; `enum.StrEnum`; `dataclass(slots=True, kw_only=True)`. Don't force one in
where it reads worse; the point is to stop *defaulting* to the old spelling. (Each project
states its own `requires-python` floor; where it is recent and backward-compat is not a
concern, reach for the modern spelling freely.)

**Enum member values: default to `enum.auto()`.** When a member's *value* carries no
external meaning — it is just a distinct tag compared by identity — use `enum.auto()` rather
than hand-numbering `0, 1, 2…`, which invites a reader to assume the number matters and
breaks silently if a member is reordered or inserted. Hand-assign a value only for an
**articulated reason**, stated at the enum: it mirrors a wire/DB/protocol constant, indexes a
parallel structure, is persisted, or is otherwise observed outside the program. (`auto()`
composes with `StrEnum`/`IntEnum` when you need a string/int backing but not a *specific*
one.) **Corollary:** never write logic that depends on an `auto()` value — iterate or compare
the members themselves (cycle with `list(E).index(x)`, not `x.value`).

### Tests: parametrize over the variants, don't copy the test

When several tests differ only in **data** (a dimension, a representation/type, an algorithm
choice, a sample input), write **one** test with `@pytest.mark.parametrize`, not one copy per
variant. A loop over the variants *inside* a test is the same smell: the first failing case hides
the rest, and the report doesn't say which one failed. (William Emerison Six <billsix@gmail.com>,
2026-11-07.)

- **Name the variant list once, at module level**, typed, and pass it to every test that runs over
  it (`INVERSE_METHODS: list[str] = ["reciprocal", "peel"]`, `FRAMES: list[list[Vector]] = […]`). A
  new variant is then one line, and every test picks it up.
- **Give readable `ids=`** (`ids=["2d", "3d"]`, `ids=["gn-2d-symbolic", "g3-concrete"]`) so a failure
  names its case. Keep a parallel `*_IDS: list[str]` beside the data list; typing the list of
  `pytest.param(...)` objects would need pytest's private `ParameterSet`.
- **Write the expected value into the case, not into the test**, when it differs per variant:
  parametrize over `(input, expected)` pairs. Don't recompute the expected value with the code under
  test's own algorithm (a fold, a formula). That restates the implementation, and the test can't
  fail.
- **Stack two `parametrize` decorators for a cross product** (2 frames × 2 methods = 4 cases) instead
  of listing every combination by hand.
- **Share an expensive object through a module-scoped fixture, and parametrize over fixture names**
  (`request.getfixturevalue(name)`) when the variants are costly to build (a symbolic object that
  takes seconds to minutes). Plain data is cheap; put it straight in the parametrize list.
- **Mind list invariance in the type checker:** a list literal mixing two element types (a symbolic
  list next to a graded-type list) is not a `list[Base]` unless each element list is annotated
  `list[Base]` too.

**Keep tests apart when:**
- the assertions differ, not only the data (merging would need an `if` on the parameter);
- the test compares two variants with each other (parametrize the *pair*, not each variant);
- the test checks the **static** type per variant (`typing.assert_type`, or a binding annotated with
  each variant's own return type). A parameter erases that static type;
- each copy spells out its own formula on purpose, as a readable worked example (an explicit
  `a_1 * b_1 + a_2 * b_2` in 2D next to its 3D version).

Count collected cases (`pytest --collect-only -q`) before and after a fold. The count should stay
the same or grow; no assertion should disappear.

### Docstrings — Google / napoleon style

**Write docstrings in Google style (parsed by `sphinx.ext.napoleon`), and on any symbol a
Sphinx book renders via autodoc, put the full field set — `Args:`, `Returns:`, `Raises:`,
`Example:` — on EVERY documented method, including trivial ones.** This is the maintainer's
standard (chosen 2026-09-26; NumPy style rejected). Shape:

```
def zero(cls) -> Self:
    """The additive identity 0.

    Returns:
        Self: the value that leaves any other unchanged under ``+``.
    """
```

- The **summary line + extended description** carry the real prose (and any citations, e.g.
  a source text and page); the field lists come after. Keep the project's math /
  domain voice — Google structure is a *frame*, not a flattening.
- `self` / `cls` are **not** listed in `Args:` (napoleon convention). Document the rest with
  types + meaning.
- An existing doctest moves under an `Example:` header (napoleon renders it; it still runs
  under `pytest --doctest-modules`).
- **Prefer a doctest over a plain `pytest` test by default** — an `example → output` belongs in the
  docstring next to the code, collected by `--doctest-modules`. The rule, the keep-as-pytest
  exceptions, the migration/consolidation hazards (dangling `pinned by tests/…` references, book
  doc-region sources, generator-authored doctests for codegen), and the doctest-authoring/lint traps
  are in **`doctests-by-default.md`** (its `## Python` section) — read it before migrating tests to
  doctests or wiring `--doctest-modules` into `make test`.
- When the book sets `autodoc_typehints = "none"` (recommended — see the sphinx-book doc),
  the types you write in `Args:`/`Returns:` ARE the rendered type info, so get them right.
- The book must enable `sphinx.ext.napoleon`. The **rendering/config** side of a Sphinx book
  (autodoc typehints, `api.rst` coverage, fonts/glyphs, reading real build warnings) is its
  own topic: `sphinx-book-conventions.md`.

The non-Python analog (C/C++, …): the same "structured doc-comment with parameter/return
sections" discipline via doxygen/javadoc; the language changes the marker, not the habit.

## Pin direct dependencies — an unpinned dep can silently backtrack to an ancient major

Pin every direct third-party dependency to an exact version in `requirements.txt` /
`pyproject.toml` (then bake it per the "Self-contained images + live source" rule). An
**unpinned** dep is a trap: when a newer Python or a conflicting pin makes its current
release unsatisfiable, the resolver does **not** fail — it backtracks to the newest version
that *does* resolve, which can be years old with a different API. The build stays green; the
code breaks later at import or type-check.

- **Treat a pin that "installs" a *different* (older) version than requested as a conflict to
  surface, not accept.** It means the exact version can't be satisfied in this environment
  (a transitive cap, a missing wheel for this Python); find out why and resolve it — override
  the stale cap, pin a version that resolves, or drop the dep — rather than shipping a pin
  that lies about what runs.
- **Run the type-checker against the project's own venv.** The gate does `source
  /venv/bin/activate` before `ty check`, so `ty` sees the baked deps; a bare `ty check` outside
  the venv resolves against the system interpreter and reports phantom import/attribute errors.
- **In an image, every Python package lives in the venv, and the venv copy wins** — install them
  all with `uv pip install` into `/venv`, even ones the distro also ships as `python3-*`. Do **not**
  try to reuse the distro copies through `--system-site-packages` by pinning to the distro version
  and installing with plain `pip`: pip then reports "already satisfied" and writes **no**
  `/venv/bin` console script, so `pytest` / `sphinx-build` / `jupyter` resolve to the distro's
  `/usr/bin` scripts, which run as `#!/usr/bin/python3`, cannot see `/venv`, and fail to import the
  venv's packages (bare `pytest` dies on its first import; a book's autodoc and executed notebooks
  break; `python -m pytest` would work, but nobody types that). uv does not count system packages
  as installed, so it gives `/venv` its own copy and its own scripts — which is what you want.
  Only a package with **no** usable wheel stays distro-only (`dnf install` it, filter it out of the
  pip step).
- **Lock the whole resolved set, not just the direct deps.** Generate a `constraints.txt` with
  `uv pip compile` for the image's own Python (direct deps + build prereqs like setuptools/wheel +
  every transitive dependency), install with `-c constraints.txt`, and regenerate it from a
  `make update-pins` target (needs the network) — never by hand. Direct pins alone leave the
  transitive deps free to drift, and a drifted transitive dep breaks things far from its cause.
  The image/packaging mechanics are the container-template contract (the personal overlay's
  "Self-contained images" + "Python deps" sections), not this code-style doc.
- Worked incident (modelviewprojection, 2026-11-06): unpinned `moviepy` + `Pillow==13.0.0` (the
  only pillow with a cp315 wheel on Python 3.15) → uv backtracked `moviepy` to the 6-year-old
  `1.0.3` (no top-level `ImageSequenceClip`), surfacing as a `ty` `unresolved-attribute` **and**
  a latent runtime `AttributeError`. The "unpinned" dep had passed every build until the new
  Python + a conflicting pin met. Fix: pin `moviepy==2.1.1` and override its overly-conservative
  `pillow<12` cap at install.
- Worked incident (modelviewprojection, 2026-11-12): the image `uv pip install`ed `requirements.txt`
  into a `--system-site-packages` venv expecting distro-matching pins to be "already satisfied" —
  but uv ignores system packages, so all 15 distro-provided packages were installed twice, and a
  venv `mpmath` broke the distro `sympy`'s import. Switching to plain `pip` removed the duplicates
  but left `/venv/bin` with no `pytest` or `sphinx-build`, so `make test` and the book failed.
  Fix: venv wins (uv installs everything) plus a `constraints.txt` lock — the layout
  github.com/billsix/geometricalgebra already used.

## Cross-links

- **`~/.claude/reference/recursive-design.md`** — the language-agnostic companion: map/filter/fold
  as named recursion schemes, structural (nil/cons) recursion, the accumulator-passing discipline,
  and the Python no-TCO caveat. This doc holds the Python *spelling* (comprehension / `sum` /
  `functools.reduce`); that one holds the *design*.
- **Each project's own additions doc** — worked examples, repo-specific invariants, and
  project-local cross-links (e.g. a conditional-refactoring Rules A–E example, a
  no-annotation-exemptions catalogue): modelviewprojection
  `tasks/reference/python-coding-standard-mvp.md`, geometricalgebra
  `tasks/reference/python-coding-standard-gacalc.md`.
- The maintainer's `~/.claude/CLAUDE.md` — the language-agnostic conventions
  ("Use your discretion", "Never orphan a word on its own comment line", "What earns
  pulling code into its own function", "Prefer total dispatch over an open-ended conditional
  chain", "An externally-defined name always wins over a naming convention") that this
  standard specializes for Python.
