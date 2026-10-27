# Rust coding standard (shared, cross-project)

**Reference document** — shared cross-project Rust coding standard, the sibling of
`c-coding-standard.md`, `cpp-coding-standard.md`, and `python-coding-standard.md`. Read on demand
(NOT auto-loaded). Update in place. A project's `CLAUDE.md`/`README.md` points here and keeps its
own repo-specific invariants, worked examples, and file paths in its own additions doc (see
Cross-links). Portable rules only: this doc names no one project's files. (Written 2026-10-23 —
William Emerison Six <billsix@gmail.com> — primarily from Google's Rust style guide
(google.github.io/styleguide/rustguide.html), rounded out with the official Rust Style Guide, the
Rust API Guidelines, and the rustfmt/clippy/rustc tool catalogs; sources at the end. Where this doc
states a rule drawn from the Google guide, that guide is the citation.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/rust-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/rust-coding-standard.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/rust-coding-standard.md`, and
> the baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/rust-coding-standard.md`
> — delivered to a Crush session at `~/.config/crush/reference/rust-coding-standard.md`. Edit the
> canonical, then re-copy it over the other two.

Written for both humans and AI agents: each rule is a statement + a one-line reason. **The
standard is split in two** — (a) what **the toolchain already enforces mechanically** (rustfmt,
clippy, the compiler's warnings and `deny` lints; if `cargo fmt --check` and `cargo clippy` are
green and the build is warning-clean, these are done — don't hand-review or re-prose them), and
(b) the **judgment calls no tool can check** (spend attention here). Rust's great advantage is that
tier (a) is unusually wide: the borrow checker, the type system, exhaustiveness checking, and the
default rustc lints decide, at compile time, matters that are style debates in C/C++. So tier (b)
is mostly about *API shape* and *which tool to reach for* rather than safety.

## (a) Enforced by the toolchain — treat a green format/lint/build as authority

- **`rustfmt` owns layout.** Every project ships a `rustfmt.toml` and a `make format` (or
  `cargo fmt`) target. Indentation, block-vs-visual indent, brace placement, wrapping, trailing
  commas, spacing: **never argue about these or hand-format** — write the clearer form and let
  rustfmt lay it out. Line length is the formatter's job, not a design input. The Google-guide
  rustfmt keys worth setting: `max_width = 100` (the fleet width; drop it only if a stable
  toolchain lacks the option), `hex_literal_case = "Lower"` (lowercase hex digits,
  `0xab123cdef`), `format_macro_matchers = true`, and `imports_granularity = "Module"` (one
  `use` per module — see imports below). `#[rustfmt::skip]` is allowed **only** for deliberate
  manual alignment or generated code, **never** for a personal style preference.
- **`clippy` owns the lint and bug-pattern catalog.** The gate is `cargo clippy --all-targets
  -- -D warnings` (a clippy warning fails the build). A clean run is authority on the checks it
  covers, among them the ones the Google guide calls out by name: `borrowed_box` / `ptr_arg`
  (take `&T` / `&[T]`, not `&Box<T>` / `&Vec<T>`), `should_implement_trait` /
  `wrong_self_convention` (use the standard trait and the right `self`), `new_without_default`,
  `len_without_is_empty`, and `exhaustive_enums`. Suppress a false positive **narrowly at the
  site** (`#[allow(clippy::rule)]`) with the reason in a comment, never crate-wide.
- **The compiler's warnings and lints are gates, not advice.** Build warning-clean; promote the
  categories a project cares about with `#![deny(...)]` (commonly `unsafe_op_in_unsafe_fn`,
  `missing_docs` on a public library, `rust_2018_idioms`). Rust's default lints already enforce
  what are naming *conventions* elsewhere — `non_snake_case` (functions, variables, modules),
  `non_camel_case_types` (types, traits, enum variants), `non_upper_case_globals` (consts,
  statics) — so **casing is mechanical here**; don't re-review it. `unused_*`, `unreachable_*`,
  and non-exhaustive-match are hard errors or default-deny. **Pin the edition** (`edition =
  "2021"` or `"2024"` in `Cargo.toml`) and the MSRV (`rust-version`) — an unpinned edition
  changes idioms and macro hygiene between toolchains.
- **The borrow checker and type system settle what C/C++ argue about.** Lifetimes, aliasing,
  move-vs-copy, exhaustiveness, and null (there is none — `Option`) are compile-time facts, not
  review topics. If it compiles, those are done; spend review on the API, not on memory safety.

## (b) Judgment calls — prose, because no tool can check them

### Type annotations — annotate every binding (house style, over Rust's inference)

**House rule, deliberately stronger than idiomatic Rust** (the sibling of
`python-coding-standard.md` "annotate every binding"). Rust infers local types and the Google guide
leaves `let` bindings inferred; the maintainer overrides that — because LLM-generated code is reviewed
heavily, **every binding carries an explicit type so the reviewer reads it at the binding, not by
inferring it** (William Emerison Six <billsix@gmail.com>, 2026-10-25). Concretely:

- **`let` bindings get an explicit type**, even the obvious ones: `let total: u32 = 0;`,
  `let moves: Vec<Move> = recorder.default_moves();`, `let name: String = dlg.value();` — not
  `let total = 0;`. This is the main deviation from idiomatic/Google Rust (which prefers inference).
- **`fn` signatures are already mandatory** (params + returns; the compiler enforces them) — nothing to
  add. The one place Rust *would* infer is a **closure**: annotate its params/return where a reader
  can't see the type at a glance (`|m: &Move| -> bool { … }`); leave trivial ones (`|x| x + 1`) bare.
- **`const`/`static` already require types** — nothing to add.
- **Prefer the annotation over turbofish** so the type reads at the binding: `let v: Vec<u8> =
  xs.collect();`, not `let v = xs.collect::<Vec<u8>>();` — same information, placed where a reviewer
  scans. Turbofish stays only where there's no binding (`xs.sum::<u32>()` used inline).
- **Pattern bindings that can't carry an inline type — leave inferred by default** (the Rust analogue of
  Python's loop/unpack/`except as` targets): a `for x in …` loop variable, an `if let Some(x) = …` /
  `while let` / `match`-arm binding. Stable Rust can't annotate these in place; **don't contort** them
  (no extra `let` just to add a type). Annotate the scrutinee, or add a typed `let` in the body, only
  where it genuinely aids clarity (an opaque iterator item). A destructuring `let` CAN be annotated and
  should be: `let (fp, tp): (usize, usize) = pair;`.
- **Don't fight the compiler/clippy.** An annotation that breaks needed inference, or that clippy's
  `redundant_type_annotations` flags (a restriction lint, off by default — a project that turns it on
  opts out of this rule and says so), isn't worth a contortion: leave it inferred and say why. Fully
  parameterize generics (`Vec<Move>`, never a stray `_` a reader must resolve).
- **No automated checker** (unlike Python's `check_local_annotations.py`): the compiler enforces
  signatures, nothing enforces local annotations — so this is a **review-discipline** rule, not a gate.

**Scope — how far to apply it (general: same for Python / C / C++ / any house standard), keyed on whose
repo it is:**

- **A repo I maintain, or a file I mainly control:** sweeping the whole file or project to annotate every
  binding is welcome — do it.
- **Someone else's repo:** apply this (my) style to **the code I add** — a new function I write gets
  types on everything in it — but **do NOT sweep the rest of the file/project**: a whole-file type sweep
  buries what I actually changed and isn't my call. Use my style for my additions, or the project's own
  documented style where it has a conflicting one.

### Imports and `use` — unqualified types, module-qualified functions, no globs

- **Import types and traits and use them unqualified** — `use regex::Regex;` then `Regex`, not
  `regex::Regex` at each site. Exceptions: an ambiguous name (`io::Error`, or rename with `as`),
  a large group of types, macros/generated code, and heavy-dependency code.
- **Call free functions through their module** — `mem::transmute(y)`, not an unqualified
  `transmute` — so the reader sees where it comes from.
- **Import a trait locally** (inside the function body) unless it is used throughout the file —
  it keeps a trait-method import next to its use.
- **Glob imports (`use x::*`) are discouraged.** The permitted cases: `use super::*;` in an
  inline module, `use Enum::*;` inside that enum's own method bodies, and `pub use submodule::*;`
  in a non-leaf module that re-exports.
- **One module per `use`** (matches `imports_granularity = "Module"`); don't avoid defining a
  **prelude** module — avoid preludes.

### Module and file organization — small crates, name the file after its item

- **Prefer small crates, ideally one file each**; a larger crate is justified by trait coherence
  or a foundational library. **Name a leaf module and its file after its primary item** (`struct
  Foo` → `foo.rs` / `mod foo`). **A non-leaf module holds only `mod` declarations and
  re-exports**, plus a little "ties things together" glue. Test modules (`mod tests`) and
  cross-language binding modules are fine as leaf modules.

### Naming — follow the standard library's method vocabulary

- **Conversions carry their cost in the prefix and the `self`:** `as_` (cheap borrow, `&self`),
  `to_` (expensive/owned, `&self`), `into_` (consuming, `self`). Match the std convention exactly
  — clippy's `wrong_self_convention` checks it.
- **Getters/setters:** `foo()` returns by value, `foo_mut()` returns `&mut`, `set_foo()` takes by
  value, `take_foo()` clears and returns the old value, `replace_foo()` sets and returns the old,
  `with_foo()` takes a closure. No `get_` prefix (std doesn't use one).
- **Constructors:** `new()`, or `new_with_foo()` when there are several; a fallible one is
  `try_new()`. **A value conversion `from_foo()` is paired with a `From`/`TryFrom` impl**, not an
  ad-hoc free function.
- **Extension traits end in `Ext`** (`ForeignTypeExt`).
- **Lifetimes get descriptive names** for type lifetimes; the exceptions are very generic types
  (`Cow`), the anonymous `'_` where it works, and up to two single-letter lifetimes for a plain
  input→output relationship.
- **Generic parameters are short and hint at the bound** (`T`, `U` for broad APIs; a letter from
  the key trait otherwise). **Avoid obscure abbreviations** and don't shorten a word by dropping
  letters; well-known ones (`IpAddr`) are fine.

### Comments and documentation — `///` items, `//!` modules, document the sharp edges

- **Document public APIs.** Use `///` for items and `//!` at the top of a module/crate file;
  Markdown, with capitalization and punctuation. Include a runnable example somewhere in the
  crate. **Always document the panics** a function can raise on malformed input, and **document
  the invariants of every `unsafe` fn/trait**.
- **Comment only to add what the code doesn't convey** — don't restate the name, don't explain
  basic language features; a self-explanatory enum variant may go undocumented. Use `//` for
  implementation notes, `TODO`s, and commented-out code. Prefer a hand-written doc comment over
  macro-generated docs.
- **`// SAFETY:` is required at every `unsafe { … }`** and `unsafe` impl, stating why the
  invariants hold.

### Derives, traits, and attributes — derive it, implement the standard trait

- **`#[derive(...)]` whenever possible** — don't hand-write what a derive expresses. **Implement
  the matching standard trait** rather than an ad-hoc method (`FromStr`, not a bespoke
  `from_str`; `Display`, not `to_string`).
- **Prefer the weaker bound unless you need the stronger:** `PartialEq` over `Eq`, `PartialOrd`
  over `Ord`. Derive `Clone` for most types (not ones owning an external resource), `Copy` only
  for a type that will stay `Copy` (error types included where possible), `Default` when there is
  a `new()` or a natural empty state, `Hash + Eq` for a map key (`Ord` too if it has a total
  order).
- **`#[non_exhaustive]`** on a public enum/struct used **across team boundaries** (so adding a
  variant/field isn't a breaking change); skip it for a fixed ontology or a genuinely two-state
  enum. **`#[must_use]`** on a function whose result it is a bug to ignore (pure functions,
  error/critical returns) and on types that are errors or lazy computations. **`const fn`** on a
  public function only if it will *stay* const. **`#[doc(hidden)]` is private** — don't call into
  someone else's hidden items.

### Generics, trait objects, and parameters — accept the borrowed form

- **In libraries, prefer generics (`T: Trait`, `impl Trait`) over `dyn Trait`**, except where
  code size matters. **Accept the flexible borrowed type:** `&[T]` over `&Vec<T>`, `&str` over
  `&String`, `&T` over `&Box<T>`, `Option<&T>` over `&Option<T>`. Reach for `impl Into<T>` only
  when call-site ergonomics clearly justify it (application code almost never should). **Define a
  trait only for generic programming, `impl`/`dyn` use, or an extension trait** — not to organize
  code.

### Matching and control flow — exhaustive, and the right narrowing tool

- **One variant of interest → `if let` / `let … else`**, not a `match` with a throwaway arm
  (a `match` is fine when it reads cleaner). **Prefer pattern matching over `x.is_some()` then
  `x.unwrap()`.** On a `#[non_exhaustive]` enum, list every variant or add a wildcard arm (and
  consider the `non_exhaustive_omitted_patterns` lint). **Prefer `expect("reason")` over
  `unwrap()`** when a panic is truly justified — the message says why.

### Iterators and combinators — short chains, named when long

- **Avoid long or complex combinator chains.** Don't put a chain in a `for` loop header — bind it
  to a named variable first. Avoid `for_each` (use a `for` loop) unless there's a strong reason.
  A short chain, or one that replaces real logic (`any()`, `all()`), is the good use.

### Ownership and error handling — borrow first, one error strategy per project

- **Prefer unique ownership and borrowing over `Rc`/`Arc`; prefer borrowing over `.clone()`.**
  Clone when a deep copy is genuinely needed or borrowing gets too tangled; cloning an `Rc`/`Arc`
  (a refcount bump) is fine. **Return an iterator over a `Vec<T>` in reusable library code**
  (application code may return `Vec<T>` for simplicity).
- **The reporting split:** `Option` for a simple, obvious absence; `Result` for a recoverable
  failure where the caller needs context; `panic!`/`assert!` for a bug or violated invariant.
  Developer-facing binaries and tests may panic freely. **State the project's error strategy in
  its `CLAUDE.md`** (same rule as the C doc): the ecosystem default is **`thiserror` for a
  library** (typed, `#[non_exhaustive]` error enums) and **`anyhow` for an application/binary**
  (one `anyhow::Result` with context) — don't mix the two in a public API. Attach context with
  `.context(...)` / `?`, not by stringly-typing.

### Unsafe, macros, and startup — avoid, isolate, justify

- **Avoid `unsafe`** unless safe code can't do it; **isolate it behind a safe abstraction** (a
  separate crate where it's substantial), and **justify it** in a comment — why safe code won't
  work, with a benchmark if the reason is performance. Every `unsafe` block carries its
  `// SAFETY:` (tier-b comment rule above).
- **Macro preference order:** ordinary Rust first, then `macro_rules!`, then other code
  generation, then a `proc_macro` as the last resort. **Don't run code before `main()`** (no
  `ctor`-crate static initializers).

### Miscellaneous style points worth stating

- **`format!` / `write!`** to concatenate more than two strings or to interpolate — not a chain
  of `+`. **Prefer an `enum` to a `bool` parameter** when the meaning isn't obvious at the call
  site (a bare `true` is unreadable); if a `bool` stays, add an inline `/* name: */` comment. Use
  an **`assert!` message** to explain the invariant and log the values.
- **A newtype over a type alias** when the semantics differ or the types could be mixed up (an
  alias is only a rename; a newtype is a real type). **Named struct fields over a tuple struct**,
  except a single-field newtype or a very local tuple. **Implement `is_empty()` alongside
  `len()`** (clippy's `len_without_is_empty`). **Don't overload an operator** for a
  non-mathematical purpose. **Never reach into a poisoned `Mutex`** (handle or propagate the
  poison).

## Cross-links

- `cpp-coding-standard.md`, `c-coding-standard.md`, `python-coding-standard.md` — the sibling
  standards; same (a)/(b) split and voice. The C doc's "one error strategy per project, stated in
  its `CLAUDE.md`" rule is the model for Rust's `thiserror`-vs-`anyhow` choice above.
- `code-style-conventions.md` — the language-agnostic rules (comment reflow, line-length changes,
  externally-defined names that override naming, what earns an extraction, prefer total dispatch)
  this standard specializes. Rust's exhaustive `match` is the total-dispatch rule enforced by the
  compiler.
- `cpp-build-modernization.md` — pinning a language standard / raising the lint level / a
  tree-wide reformat commit; the same mechanics apply to pinning a Rust edition and a
  `cargo clippy -D warnings` gate.
- `print-debugging.md` — the instrumentation-driven method (compiler, clippy, `cargo test`,
  `RUST_BACKTRACE`, `dbg!`, Miri for `unsafe`) that tier (a) relies on.
- `doctests-by-default.md` — **prefer a ` ```rust ` doc-comment example (a doctest) over a plain
  `#[test]` by default**; `cargo test` runs them for free (`cargo test --doc`). Its `## Rust` section
  plus the language-agnostic core (keep-as-`#[test]` exceptions, migration/consolidation hazards,
  doctest-authoring traps) — read before migrating tests to doctests or wiring `cargo test` into a
  `make test`/`make check` gate.
- `rust-gui-tui-and-ecosystem.md` — the practical companion: writing Rust **GUIs** (wxDragon /
  wxWidgets, incl. the `wxGTK-devel` + `libSM/libICE-devel` build deps and the DC-not-GraphicsContext
  limitation), **TUIs** (ratatui / crossterm), CLI line-editing (rustyline), the `Rc<RefCell>`
  event-state pattern, and how the Rust toolchain behaves in the sandbox. Read before a Rust
  GUI/TUI/bindings task.

## Sources

- **Google Rust Style Guide** — google.github.io/styleguide/rustguide.html (the primary source;
  most tier-(b) rules above are its guidance, with its codebase-specific `[chrome]`/`[Fuchsia]`
  tags omitted as not portable).
- **The Rust Style Guide** (official, rustfmt's basis) — doc.rust-lang.org/style-guide/ — applies
  wherever it doesn't conflict with the above.
- **Rust API Guidelines** — rust-lang.github.io/api-guidelines/ — naming and API-design checklist
  the method/trait rules draw on.
- **rustfmt** configuration — rust-lang.github.io/rustfmt/ (the tier-(a) keys); **Clippy** lint
  list — rust-lang.github.io/rust-clippy/ (the named lints).
- **The Rust Reference** and **The Rust Programming Language** (the book) —
  doc.rust-lang.org/reference/, doc.rust-lang.org/book/ — for the default rustc lints and the
  language facts tier (a) leans on.
- **`thiserror`** / **`anyhow`** (dtolnay) — the library/application error-handling split.
