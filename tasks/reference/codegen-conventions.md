# Generating source code (any target language) — rationale and worked study

**Reference document** — the durable rationale and the gacalc A/B/C study behind the
"Generating source code" rule in the cross-project `CLAUDE.md`. Read on demand when you are
writing or reviewing a **code generator**.

These are the durable, language-agnostic lessons — distilled from gacalc's
`tools/gen_specialized.py`, (`github.com/billsix/geometricalgebra`), which moved from string
concatenation to hand-built Python `ast` nodes → `ast.unparse` (2026-06-07; the A/B/C study is
archived there at `tasks/archive/2026/06/07/codegen-via-python-ast.md`).

- **Prefer building STRUCTURED output over concatenating strings, when the target language
  gives you the tools.** Python has `ast` + `ast.unparse`; many languages have an AST +
  pretty-printer, a builder API, or at least a formatter. Structured emission is
  **correct-by-construction**: the unparser cannot emit syntactically invalid code, and node
  construction is validated (Python ≥3.13) — so a whole bug class disappears (mismatched
  parens, bad indentation, trailing-comma slips). Concrete gacalc win: a fragile
  regex-on-source rename *and* a real indentation/dedent bug both became **impossible** —
  nodes carry structure, not whitespace, and the formatter owns layout.
- **The spectrum, with the ergonomic sweet spot in the middle:** raw string concatenation →
  **template-splice / quasiquote** (parse a code *snippet* with holes, fill them
  programmatically — Python `ast.parse("self.X")` + a `NodeTransformer`; Lisp backquote; a
  templating layer elsewhere) → **hand-built nodes** (no source text at all). Template-splice
  reads like *writing code with holes* and is usually the best effort/clarity trade. Hand-built
  nodes are maximal code-as-data purity but **verbose** (gacalc's Scalar class was ~260
  node-lines vs ~140 as a template) with an AST-API learning curve — pick them only when
  explicit code-as-data genuinely pays (a Lisp/metaprogramming mindset) or the structure earns
  its keep. **Tell:** if your node-builder helper set starts to look like a quasiquote,
  template-splice was the natural abstraction.
- **Define "the output is the same" as EQUIVALENCE, not byte-identity.** An unparser/formatter
  emits *canonical* form (its own parens, wrapping, no comments), so a rewrite is never
  textually identical to hand-tuned output. Verify two ways instead: **(a) structural
  equivalence** (e.g. `ast.dump` per file — same statements/expressions, formatting aside;
  watch operand *order*, which IS part of the tree) and **(b) behavioural parity** (the full
  test suite stays green). If someone insists on byte-identical, the only honest path is a
  **one-time re-baseline** — regenerate, format, adopt *that* as canonical.
- **Build a parity harness FIRST, then convert one emitter at a time.** Before touching the
  generator, write the harness that runs old-vs-new into temp dirs, asserts equivalence, and
  runs the suite — it is the safety net the whole rewrite leans on. Migrate incrementally (one
  method/class emitter per step), re-running the harness each step, so a regression localizes
  to the last change.
- **Guard run-to-run determinism** (regenerate twice, assert byte-stable) as a permanent
  make/CI gate — dict/set iteration order, timestamps, or `Math.random`-style nondeterminism
  in a generator is a silent drift source.
- **Comments and license headers can't live in an AST** — keep the file header (copyright +
  imports + banner comments) as raw text prepended to the unparsed body; docstrings survive
  (they're ordinary string statements).
- **Not every layer benefits equally.** gacalc's *math* layer was already generated (sympy ran
  the symbolic products); the AST rewrite barely helped it — only swapping a regex for a
  NodeTransformer. The payoff was the *scaffolding* (classes, methods, dispatch). Spend the
  effort where the string bookkeeping actually lives.
- **Understandability ≠ line count.** The pure-node version was more verbose but *not* less
  understandable for a metaprogramming mindset — explicit code-as-data, named/testable
  builders, no two-language whitespace fragility. Judge a codegen style by whether a maintainer
  can follow and safely edit it, not by how few lines it is.

## Generated files in a repo: edit the source, never the output

The consumer side of the rule above. Anything a build step produces — an umbrella header
concatenated from a curated list, driver scripts and man pages from `*.in` templates, a
`configure_file` output, a jupytext `.ipynb` from a `.py` — is **never hand-edited**: change the
list / template / generator and regenerate. Two practices make this stick: (1) the project
`CLAUDE.md` carries a short **"Generated files — do NOT hand-edit"** table mapping each output to
its source and generator (ePiX: `epix.h` ← `make_header`'s list; `epix`/`elaps`/`flix`/`laps`/
`epix.1`/`epix.el` ← the `*.in` templates via Meson `configure_file`); (2) generated outputs that
are *not* committed are gitignored, and those that *are* committed (so an optional heavy target
can build without its toolchain) are named as such. Build-system porting notes for this:
`cpp-build-modernization.md`.
