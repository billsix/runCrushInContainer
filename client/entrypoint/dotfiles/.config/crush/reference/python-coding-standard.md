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

### Idioms (the full checklist; the ones ruff already enforces are marked)

EAFP over LBYL; truthiness for emptiness `if not seq:` (but compare ints to `0`
explicitly); `is`/`is not` for `None`/singletons *(ruff)*; `isinstance` over `type(x) == T`
*(ruff)*; `enumerate`/`zip` over `range(len(...))`; comprehensions over trivial
map/filter+loop (keep them simple); f-strings over `%`/`.format`; `with` for resources;
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
silently degrades its parameter to implicit `Any`). Where a generic is **invariant** with an **unbounded** parameter, the
parameter must match the value's *exact* type — verify each with the type checker rather
than blanket-annotating a common base. **A *polymorphic* param that accepts *any* instance
of the generic and applies it to the base internally** is `[Any]` — invariance makes a fixed
base-parameter reject concrete-typed arguments, and a bound TypeVar reject the internal
base-application; `Any` is the only thing compatible both ways. Exceptions that stay bare: a
runtime `isinstance(f, SomeGeneric)` (can't take a subscripted generic), and a concrete
`Callable` alias (not a generic). A project whose generics are invariant with an unbounded
parameter, or whose notebooks fall outside the type gate, documents the specifics and the
`[Any]`-vs-exact-type calls in its own additions doc.

### Inline a value used exactly once — unless the name documents an otherwise-opaque expression

This **takes precedence over "annotate generously"**: don't create or keep a single-use
local just to give it a type — inline it (e.g. pass the f-string straight to
`latex_repr=`). Generous typing applies to the locals that *survive* — reused, hoisted out
of a closure so it's computed once, or named to clarify an opaque expression. (Same spirit
as: no local aliases for a value that already has a canonical name — reference the canonical
name directly, never `E1 = Vector.basis_vector(1)`.)

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
  exactly once" rule applied to functions.

**"Inner-fn first, guards below" is a consequence of the above, not the goal.** When an
extraction is earned, the inner function(s) carrying the core operation go up top (closing
over the enclosing parameters) and the preconditions / dispatch — typically a `match` — land
at the bottom, calling in. Don't chase the shape for its own sake, and **don't churn existing
early-return code**; a cheap top-of-function `raise` on a nonsensical arg is always fine. A
related lesson: an error is best raised by the code that *discovers* it — pushing a "not
found" into the search itself is often what lets a function's tail collapse to one line.
Worked examples live in each project's additions doc.

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
- When the book sets `autodoc_typehints = "none"` (recommended — see the sphinx-book doc),
  the types you write in `Args:`/`Returns:` ARE the rendered type info, so get them right.
- The book must enable `sphinx.ext.napoleon`. The **rendering/config** side of a Sphinx book
  (autodoc typehints, `api.rst` coverage, fonts/glyphs, reading real build warnings) is its
  own topic: `sphinx-book-conventions.md`.

The non-Python analog (C/C++, …): the same "structured doc-comment with parameter/return
sections" discipline via doxygen/javadoc; the language changes the marker, not the habit.

## Cross-links

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
