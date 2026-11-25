# Code-style conventions — rationale, examples, and worked cases

**Reference document** — the full rationale and worked examples behind several
language-agnostic code-style rules kept terse in the cross-project `CLAUDE.md`. Read on demand
when the matching trigger fires. For the
Python-specific standard (ruff tiers + naming/idiom judgment calls) see
`~/.claude/reference/python-coding-standard.md`.

## Worked example — "use your discretion" enforcing an 80-column limit

(The worked example from the `CLAUDE.md` "Use your discretion" section, relocated here
2026-09-14 because it turns on line-length reflow; the rule itself stays inline in `CLAUDE.md`.)

**Enforcing an 80-column limit (mvp, Python/ruff, 2026-07-18).** 78
over-long lines, one instruction ("80 is good, I make a PDF of it; fix as much as
possible with your discretion"):

- **70 were prose** — comments and docstrings. Rewrapped automatically, no questions.
  Handled RST bullet continuation indent and Sphinx `#:` markers so the rewrap didn't
  corrupt structure.
- **2 were `import a.b.c as name`** at 88 chars. Rewrote as `from a.b import name` —
  identical binding, 71 chars. A different mechanism than wrapping, because wrapping an
  import is ugly and this is just better.
- **1 was an f-string.** Split with implicit concatenation, which cannot change the
  runtime value.
- **1 was a `//` comment inside a GLSL shader string.** Wrapping it would have pushed
  half a comment onto a new line as *invalid GLSL* — the linter can't see that it's
  shader source. Shortened the comment text instead.
- **4 were a hand-aligned 4×4 matrix literal** in a book *about matrices*, already
  carrying `# fmt: off` — the alignment IS the documentation. Left long with
  `# noqa: E501` and a comment saying why. Reflowing would have been technically
  compliant and actively worse.

## Never orphan a word on its own comment line

**Reflow the whole paragraph, not the offending line.** When a comment or docstring line
is over the limit, re-wrap the entire contiguous paragraph as a unit. Fixing the single
long line in isolation produces this, which I don't want:

```python
# stored ``steps`` field stay typed tuple[Step, ...] for readers while
# the
# constructor accepts the broader input.
```

A comment line holding one word or a short sentence fragment is always wrong. **This
applies to every comment syntax I use** — `#`, `//`, `/* … */`, `;;`, `--`, `%`, `!` —
and to doc comments (docstrings, doxygen `/** … */`, javadoc, `///` Rust doc comments)
just the same.

### Changing a line-length limit without causing that

Language-agnostic; the tool names are examples.

1. **Set the limit in config, in one place**, so the formatter and the linter agree.
   `[tool.ruff] line-length` (governs both `ruff format` and E501), `ColumnLimit` in
   `.clang-format`, `max_width` in `rustfmt.toml`, `printWidth` for prettier,
   `max_line_length` in `.editorconfig`. Then **remove any per-invocation
   `--line-length`-style flags** from format scripts so there's a single source of truth
   — a formatter at 80 with a linter at 88 quietly lets new long lines land.
2. **Run the formatter first.** It reflows *code* for free. Whatever survives is prose
   and unbreakable tokens — that's the real work-list, and it's much smaller. Note which
   side of the line your formatter sits on: `ruff format`/`black`/`gofmt` won't touch
   comment prose at all, while `clang-format` *will* if `ReflowComments` is on — and if
   it is, let it do the bulk and only hand-check what it leaves.
3. **Fix the residue paragraph-wise, and do NOT try to automate it.** I tried; it doesn't
   generalize. A "reflow every ragged paragraph" pass matched 87 paragraphs — mostly the
   author's own deliberate line breaks in files the change never touched. Tightening the
   heuristic still matched content that must never be joined into a paragraph. Use an
   **explicit allowlist of paragraphs you have read**, and print before/after for each.
4. **Things that look like prose but must not be reflowed** — check for every one before
   touching a comment block. Language-independent: bulleted/numbered lists, key/controls
   lists, section banner comments, **commented-out code**, license headers, ASCII diagrams
   and tables, aligned literals (matrices, register/bitfield tables, enum value columns),
   and math notation whose spacing carries meaning. Toolchain-specific: doc-extraction
   markers that drive a build (`doc-region-begin/end`, doxygen `\brief`/`\param`, javadoc
   tags, `//!` sections), literate/cell markers (jupytext `# %%`, org-mode `#+begin_src`),
   and anything a preprocessor reads.
5. **Watch for line structure that is syntactically load-bearing, not stylistic** — where
   re-wrapping changes meaning rather than looks. C/C++ multi-line macros continued with
   trailing `\` (moving the backslash breaks the macro); shell and Make line
   continuations; Make recipe lines (leading TAB is significant); assembly, one
   instruction per line; a `//` comment inside a string literal that is *source for
   another language* (embedded GLSL/SQL/regex) — wrapping emits invalid code in that
   inner language, and the linter can't see it. In these, shorten the text or restructure;
   never just insert a newline.
6. **Re-verify after**: linter clean, formatter idempotent (`--check` reports no changes),
   and the code still builds — compile, don't just re-lint.

The shape to copy: bulk-fix silently, vary the mechanism, protect what matters, and
surface only the judgment calls.

## Comments and docstrings describe the present, not the history

**A comment/docstring documents the code's CURRENT behavior — not what it used to do, or why it
changed.** When you fix or change behavior, the temptation is to narrate the change in the docstring
("this replaces the old `cos θ == 1` test, which was wrong for anti-parallel vectors …"). Don't: a
docstring is re-read by every future reader, none of whom cares what the code *used to* be, and the few
who do want the history will look in the **`CHANGELOG`** (consumer-facing changes) or the **commit
message** (always) — the two places built for it. A docstring that recounts its own history is stale
the moment the next change lands and buries the one thing the reader needs (what it does now).

- **Write:** the current behavior, the contract, the math/spec it implements, a pointer to a proof or
  equation if it aids understanding. (`is_parallel_to`: *"True iff `A ∧ B = 0` — so same-direction and
  anti-parallel both count; verified in `Predicates.lean`."*)
- **Don't write (in a comment/docstring):** "replaces the old X", "previously did Y", "was wrong
  because …", "changed from Z", "new in vN", "fixed the bug where …". That's changelog/commit text.
- **Where the history goes:** `CHANGELOG.md` `[Unreleased]` for anything a consumer would notice; the
  commit message for the rest. Both are discoverable (`git log -p`, `git blame`) without polluting the
  source.
- **One nuance:** a `# TODO`/`# NOTE` about *current* known limitations or a *future* plan is fine
  (it's present-tense state). The ban is specifically on narrating the *past* — "what this used to be."

Language-agnostic — every comment and doc-comment syntax. Same spirit as the open-issues-list rule
(docs carry the current state; git carries the history). Worked example: gacalc `is_parallel_to`
(2026-10-02) — the first fix narrated the old `cos θ == 1` behavior in the docstring; it was rewritten
to state only the current wedge-zero criterion, with the change recorded in `CHANGELOG.md`.

## An externally-defined name always wins over a naming convention

**If a name is dictated by something outside the code — a framework superclass method
you're overriding, an interface/protocol member you're implementing, a callback
signature, a magic name a library looks up — then the naming rules do not apply to it.**
Renaming it doesn't make it tidier; it *unbinds* it and silently breaks the code. This
is not a judgment call and it needs no case-by-case discussion: match the external name
exactly, however ugly it is by house style.

Language-agnostic. Examples: wxPython's `OnPaint` / `InitGL` / `OnInit`, Qt's
`paintEvent`, `unittest`'s `setUp` / `tearDown`, Python dunders and protocol names
(`__enter__`, `_repr_latex_`, `__post_init__`), a C callback whose signature is fixed by
the API taking it, JNI's `Java_pkg_Class_method`, a serialization field that must match
a wire format, an env var or CLI flag someone else specifies.

Consequences:

- **A linter flagging one of these is the linter being wrong, not the code.** Suppress
  it — scoped as narrowly as the tool allows (a `per-file-ignores` entry for a
  framework-boundary file, an inline `noqa`/`NOLINT`) — and **write the reason at the
  suppression site**: which framework, and that the name is externally fixed.
- **Say so in the project's own conventions doc**, so the exemption is discoverable and
  the next person doesn't "fix" it.
- The exemption covers *only* the externally-fixed name itself. Parameters, locals, and
  helpers inside such a method still follow house style.

## Name an iteration variable for what it holds; keep a shared generic collection generic

**A loop/iteration handle should say its element type, not `obj`/`item`/`x`/`p`.** A reader
scanning `for (const auto& obj_ptr : objects)` learns nothing; `for (auto& sprite : ...)` says the
loop body operates on sprites. Language-agnostic — Python `for waypoint in waypoints`, not
`for w in ...`; the same for a `.get()`/unwrap alias inside the loop. This matters most after a
mechanical pass that mints generic names (a `unique_ptr` ownership flip, clang-tidy
`modernize-loop-convert`, a codemod), which is where the meaningless handles pile up.

**But a *shared generic collection* keeps a generic name — put the type at the use site.** When a
container is genuinely polymorphic in type — a base-class/template member reused across many
concrete subclasses, a `List<T>` field, a heterogeneous queue — do **not** rename it to one
concrete element type: that name is a lie everywhere else it is used. The canonical case (smc,
2026-09-24): `cObject_Manager<T>::objects` is one public member of a base template inherited by
~12 managers, holding sprites in one, overworlds/sounds/levels/surfaces in others. Renaming the
member to `sprites` would misname it in eleven managers. The fix is to anchor the type at each
**loop variable** (`for (auto& sprite : m_sprite_manager->objects)`) — the reader learns the
element type from the handle, and the collection name stays honest about being generic. Renaming
the collection per-context would need per-subclass typed accessors (`Get_Sprites()`) — a larger,
separate refactor, not a rename pass.

Mechanics when doing this in bulk: it is a **pure rename**, so a codemod can *generate* the diff,
but the *choice* of name is per-site judgment — a human eyeballs each hunk. Scope each rename to
the variable's block and collision-guard it (skip if the target name already names a param/local
in that block, or you shadow it). **Key the rename on the container expression or the enclosing
scope, not a per-file-uniform assumption** — a single file often has loops over different
containers, and "all this file's loops are X" mislabels the odd one out (that mistake happened and
had to be redone container-keyed). See the `modernize-loop-convert` note in
`cpp-ownership-migration.md` for the clang-tidy-specific version.

## What earns pulling code into its own function

**Duplication, or naming a distinct phase. Not reshaping control flow.** Language-
agnostic; the examples are Python because that is where it came up.

- **Lift to shared/module scope when more than one caller needs it.** Two real cases
  (gacalc, 2026-07-18): one helper replaced the same expression written out 9 times
  across 5 functions; one shared function replaced three ~58-line, 91-93%-identical
  plot helpers, net **-75 lines**. Giving each caller its own private copy of the helper
  would have been *more* duplication, not less — so "extract a local helper" was the
  wrong instinct even though something clearly needed extracting.
- **Nest it when it closes over the enclosing function's parameters, or when it has exactly one
  caller,** and names a real phase of the algorithm (`nest_one_caller.py`, in this directory,
  does the one-caller case mechanically; a helper with a doctest or one another file imports
  stays at module level). A BFS routine split into `breadth_first_parents` /
  `walk_back`, both capturing the endpoints, reads as the algorithm; its tail collapsed
  to one line.
- **Do neither when the helper would be used exactly once** and exists only to reshape
  control flow or avoid mutating a local. That is the "inline a value used once" rule
  applied to functions. I proposed exactly this once and the user declined it — the two
  helpers were single-use and existed only to fill a constructor call.

**A corollary worth its own line: raise an error from the code that discovers it.** The
BFS above got clean not by relocating guards but by moving its "no path" failure *into
the search*, which is the only place that knows the target is unreachable.

**Don't chase a shape for its own sake, and don't churn existing early-return code.** A
cheap top-of-function guard is fine and usually right. When I swept a codebase looking
for functions that "should" be restructured this way, the honest answer for nearly all of
them was: leave them alone.

## Names: inline what is used once, declare at the point of use, nest and shadow

Language-agnostic (the examples are Python; the rules hold for C, C++, Rust, shell, Lisp). Decided by
William Emerison Six <billsix@gmail.com>, 2026-11-06, while refactoring gacalc's
`Frame.to_invertible_function`; the Python wording and worked example are in
`python-coding-standard.md` ("Inline a value used once, and name it in a comment instead of a binding").
Each rule is reworded for its language, with the bindings that language must keep, in
`rust-coding-standard.md`, `cpp-coding-standard.md`, `c-coding-standard.md`,
`haskell-coding-standard.md` and `javascript-coding-standard.md` ("Locals and helpers") and, for bash,
in `shell-and-gate-scripts.md` ("Names and scope in bash") (2026-11-25).

- **A name bound once and used once is inlined, even if it was there to explain the expression.** A
  reader who meets a declaration scans ahead to see how far it is used, and a single-use binding makes
  that scan pointless; the longer the function, the worse. Put a comment above the inlined
  subexpression that describes it and gives it its name instead.
- **Two uses do not automatically earn a name.** Check whether one expression absorbs them: "this value,
  or a fallback if it is absent" is usually a library call with a default argument (`getattr(obj,
  name, fallback)`, `dict.get(key, default)`, `next(it, default)`, `std::optional::value_or`,
  `Option::unwrap_or_else`, `${VAR:-default}`); a cheap, clear expression can simply be repeated. Keep
  the name when repeating the expression would read worse or recompute something expensive.
- **Declare a name at the point of use**, not many lines before it.
- **A helper with one caller is nested inside that caller** where the language has a nested function (a
  nested `def` in Python, a nested function in JavaScript, a `where` helper in Haskell, a
  `let`/`flet`/`labels` in Lisp, in Rust an inner `fn` or, when it captures a local, a closure). Where
  it does not, keep it private and directly
  above its caller: `static` in C, an anonymous-namespace or `detail` function in C++ (a lambda only
  when it captures local state), a top-level function in bash, where every function is global.
- **When nesting, shadow deliberately and verify it.** Give the helper's parameter the caller's name when
  it holds the same kind of value, so the reader knows the outer binding is out of play inside the
  helper. Correct shadowing means the helper never needs the outer value, and none of its other names
  hide an enclosing binding it does need. A linter that warns on shadowing (`-Wshadow`, clippy's
  `shadow_*`, pylint `redefined-outer-name`) gets a narrow suppression with the reason at the site.
  C, C++, Haskell and bash differ: a C or C++ helper is a separate function, so its parameters reuse
  the caller's names with no shadowing; Haskell's `-Wall -Werror` build rejects shadowing, so a `where`
  helper reads the caller's arguments and takes no parameter for them; and in bash the rule becomes
  "declare every function variable `local`".

## Prefer total dispatch over an open-ended conditional chain

**A chain of `if` / `else if` with no final `else` can fall through silently, and the
hole is invisible** — nothing in the code marks the case nobody handled. A construct with
a mandatory-feeling default (`match`/`case _`, `switch`/`default`, a sealed-type match)
makes that branch something you have to look at and decide about.

This is not a style preference; it is a bug class I have actually hit. In mvp,
`pyMatrixStack.get_current_matrix` was five `if`s with no `else`:

```python
def get_current_matrix(matrix_stack) -> np.ndarray:   # annotated -> ndarray
    if matrix_stack == MatrixStack.model:
        return __model_stack__[-1]
    ...                                    # four more `if`s, no else
    # falls off the end -> returns None, and every caller indexes the result
```

Every real case was handled, so it looked fine; the hole only opens when someone adds an
enum member. Rewritten as a `match` with `case _: raise ValueError(...)`, the omission
becomes impossible to add by accident.

**The discipline is the pairing, not the keyword: always write the default branch.** A
`match` without a `case _` has exactly the same hole. The default may raise, return a
documented fallback, or be an explicit no-op with a comment saying why — but it must be
written.

Language notes: Python `match` + `case _`; C/C++ `switch` + `default` (and turn on
`-Wswitch`, which catches an unhandled enum for you); Rust/ML-family matches are
exhaustive by compiler and need no discipline. Where the language gives you a compiler
check, prefer letting it check rather than adding a catch-all that defeats it.

**Caveat, so this doesn't get over-applied:** `match` earns its keep on *structural*
patterns (destructuring, type dispatch). A `match` whose every case is a boolean guard —
`case (a, b) if a == b:` — is an `if`/`elif` chain in different syntax, justified only by
the exhaustiveness argument above. Don't convert every two-branch conditional.

## C++: migrating raw owning pointers to `unique_ptr`

Turning a pre-C++11 codebase that owns through raw `T*` / `vector<T*>` + hand `delete` into one
that owns through `std::unique_ptr` is a recurring, hazardous job with its own playbook — the
recon → codemod → compiler-drive → runtime-verify method, the raw→`unique_ptr` idiom table, the
double-free-that-compiles trap, and the clang-tidy checks that misfire on old code. It lives in its
own doc: **`cpp-ownership-migration.md`** (read it before starting such a migration). The
compiler/runtime "oracle" method it relies on is in `print-debugging.md`.

## A tree-wide reformat is its own commit, listed in `.git-blame-ignore-revs`

When a formatter is first applied tree-wide (`clang-format`, `ruff format`, a line-length change),
commit **only the reformat** — no doc edits, no config tweaks, no fixes riding along — so the
commit can be hidden from `git blame` without hiding real history. Then add the SHA to a root
`.git-blame-ignore-revs` (GitHub reads it automatically; a clone needs
`git config blame.ignoreRevsFile .git-blame-ignore-revs`, so the project `CLAUDE.md` says so). The
negative example: ePiX's 2026-06-09 reformat commit also carried `Makefile`, `format.sh`,
`pyproject.toml` and task-doc edits, so ignoring it costs the blame on those lines (accepted, noted
in the file's comment). Reformatting upstream-authored sources in a *mirror* is a maintainer
decision to record next to the mirror rule. Related C++ modernization notes (Meson port, `-std`,
`enum class`): `cpp-build-modernization.md`.
