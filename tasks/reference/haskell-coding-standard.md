# Haskell coding standard (shared, cross-project)

**Reference document** — shared cross-project Haskell coding standard, the sibling of
`python-coding-standard.md`, `rust-coding-standard.md`, `c-coding-standard.md` and
`cpp-coding-standard.md`. Read on demand (NOT auto-loaded), **before writing or reviewing Haskell**,
including a throwaway `tasks/adhoc/` program or a `tools/` tool. Update in place. A project's
`CLAUDE.md`/`README.md` points here and keeps its own repo-specific invariants and worked examples
in its own additions doc. Portable rules only. (Written 2026-11-11 — William Emerison Six
<billsix@gmail.com> — from what typing every binding of a 7,600-line GHC program taught: the
Haskell engine port of github.com/billsix/spimulator, `port/haskell/`, the worked example cited
below.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/haskell-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/haskell-coding-standard.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/haskell-coding-standard.md`, and
> the baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/haskell-coding-standard.md`
> — delivered to a Crush session at `~/.config/crush/reference/haskell-coding-standard.md`. Edit the
> canonical, then re-copy it over the other two.

Written for both humans and AI agents: each rule is a statement and a one-line reason. **The
standard is split in two:**
- **(a) What the toolchain enforces mechanically:** GHC's warnings under `-Wall -Werror`, plus
  `hlint` and `ormolu` where a project adopts them. Don't hand-review these.
- **(b) The judgment calls those tools cannot check.**

## (a) Enforced by the toolchain — treat a clean `-Wall -Werror` build as authority

- **Build with `-Wall -Werror`**, under GHC's default language (GHC2021 since GHC 9.2). `-Wall`
  already gives:
  - a signature on every top-level binding (`-Wmissing-signatures`);
  - unused imports, bindings and matches;
  - incomplete patterns (`-Wincomplete-patterns`, `-Wincomplete-uni-patterns`) and name shadowing;
  - the partial-function warning on `head`/`tail` (`-Wx-partial`, GHC 9.8+).
- **`hlint`** (Fedora `hlint`; both sandboxes install it) flags simplifications and idioms. Its
  suggestions are advice, not a gate, unless a project wires `hlint` into its gate; then a
  suppression needs a reason at the site (`{- HLINT ignore "..." -}`).
- **`ormolu`** (Fedora `ormolu`; both sandboxes install it) formats. Adopt it per project. Running
  it over an existing code base is a whole-tree reformat, so make it its own commit, like any
  formatter sweep. Where a project runs it, layout is its call.
- GHC does **not** check local bindings for signatures. `-Wmissing-local-signatures` covers only
  polymorphic ones, and nothing checks do-binds. The rule in (b) needs a project checker
  (below).

## (b) Judgment calls

### Type annotations — annotate every binding

Write the type of **every** named binding, not just the top-level signatures GHC requires. This is
the house rule the Python standard states for Python ("annotate every binding", William Emerison Six
<billsix@gmail.com>, 2026-09-28): the reader should never have to infer a name's type. Haskell can
write a type on almost every binding; GHC2021 includes `ScopedTypeVariables`, so no pragma is
needed. Use this form for each kind:

| Binding | Form |
|---|---|
| top-level (GHC enforces) | `parse :: String -> Either Error Ast` above it |
| do-bind | `s :: Spim <- newSpim` |
| do-bind, tuple pattern | `(lo, hi) :: (Int, Int) <- getBounds arr`: one signature for the whole pattern |
| do-bind, other patterns | parenthesize: `(Just x :: Maybe Int) <- lookupThing` |
| `let` / `where`, function or value | a signature line above: `closeListing :: IO ()` |
| `let` / `where`, tuple pattern | one signature line per variable, above the binding |

**Exempt by default.** In these cases the type is fixed by something right next to the binding,
so leave it inferred. This is the analog of the Python standard's exemption for loop and unpack
targets. Write the type only where it actually helps a reader. A project's checker does not ask
for these.
- Lambda parameters. The function the lambda is passed to fixes their type.
- Variables bound by a `case` alternative. The constructor fixes their type.
- Variables bound by a function's argument patterns. The function's own signature types them.
- Pattern-guard binds, `| Just x <- lookup k m`. The guarded expression fixes the type.
- List-comprehension generators. The list fixes the type.

**Getting the types right:**
- **An outer type variable needs an explicit `forall`.** A local signature that names the enclosing
  function's type variable (`e` in `bsearchBy :: (e -> Ordering) -> Array Int e -> Maybe e`)
  refers to it only when the enclosing signature binds it: `bsearchBy :: forall e. ...`. Without
  the `forall`, the local `e` is a fresh variable and GHC reports a rigid-type-variable mismatch.
- **Give a local the concrete type it is used at.** Write a polymorphic signature, with all its
  constraints, only when the binding really is used at several types.
  - GHC generalizes local functions, so a helper used only at `Int` infers as
    `Integral a => a -> a`. `go :: Int -> Int` says what the code does.
  - A local in a do block over an `IOUArray` is in `IO`, not "some `f`".
- **Write a polymorphic signature with all its constraints.** GHC's error ("add (Num a) to the
  context of the type signature for `apply`") names a missing one. Drop the redundant ones:
  `Integral a` already implies `Eq a` and `Num a`.
- **A pattern signature can bind a fresh type variable, silently.** `n :: a <- act` compiles with
  no `a` in scope and means "some type". It says nothing, so write the concrete type
  (`n :: CInt <- act`).
- **Use the module's own vocabulary.** Write `String`, not `[Char]`. Use the project's type
  synonyms where the code uses them (`InstRef`, not `IORef Instruction`). Use the qualifier the
  module imports with (`B.ByteString` under `import qualified Data.ByteString.Char8 as B`).
  - Types copied from tools (`.hie` files, ghci, GHC errors) expand synonyms and drop
    qualifiers, so rewrite them before pasting.
  - Expect new imports: a written type can name a type the module never mentioned (`Word64`,
    `IORef`, `CSize`).
- **Split a one-line `let` with several bindings** (`let a = 1; b = 2`) into one binding per line,
  each with its signature, because a signature cannot go between `;`-separated bindings on one line.
- **Generated code follows the rule too.** The generator emits the signatures; never hand-edit a
  generated module to add them.

**Enforce it with a checker.** GHC writes each module's identifiers, their binding kinds, source
spans and types to `.hie` files with `-fwrite-ide-info`. A small GHC API program can read those
and list each binding of the required kinds that lacks a type.
- Worked example: github.com/billsix/spimulator `port/haskell/tools/BindingTypes.hs`, run by
  `port/haskell/tests/check-annotations.sh`.
- Type-check with `-fno-code -fwrite-ide-info` into a separate output directory. It is quick and
  never races a concurrent build.
- **Do not trust a `.hie` type as a source signature for a polymorphic binding.** It omits class
  constraints, and it can print two distinct type variables with the same name. Use it for
  monomorphic types; for polymorphic ones, read the code or take GHC's own error advice.

### Totality

- **No partial functions where a total one exists.** Use pattern matching, `listToMaybe`,
  `Data.List.NonEmpty` or `maybe`/`either` instead of `head`, `tail`, `!!`, `fromJust`, `read`.
  `-Wx-partial` catches only some of these.
- **Every `case` has a deliberate last branch.** `-Wincomplete-patterns` makes a missing
  constructor an error. Where a wildcard is the default, write it with a comment saying why it is
  safe. A guard chain ends in `otherwise`. This is the Haskell form of "prefer total dispatch"
  (`~/.claude/CLAUDE.md`).
- **Mutually exclusive conditions are one guard chain** (`| a = …`, `| b = …`, `| otherwise = …`),
  not nested `if`s: the reader sees one decision. This mirrors the Python standard's
  `if`/`elif`/`else` rule.

### Data, names and modules

- **Options and states are algebraic data types, not strings or `Int` codes.** Derive what the
  code needs (`Eq`, `Show`, `Enum`, `Bounded`) and `case` on the constructors. A mistyped string is
  a run-time bug; a mistyped constructor does not compile.
- **Naming:** `camelCase` for values and functions, `CapWords` for types and constructors. Use
  `is`/`has` for predicates, and descriptive names except in tight scopes (`x`, `xs`, `acc`, `i`).
  **A name dictated from outside wins**: an FFI binding, or a constructor that mirrors another
  language's identifier so two sources can be read side by side (`TOK_ADD_OPCODE`). Say why where
  the type is defined.
- **Imports are explicit or qualified:** `import Data.Word (Word32)`, or
  `import qualified Data.Map.Strict as Map`. A reader can then find where every name comes from,
  and `-Wall` keeps the lists honest.
- **Strict where state accumulates:** use `Data.Map.Strict`, `foldl'`, and strict fields (`!`) on
  long-lived records and loop state. Lazy accumulation leaks space without any warning.
- **Haddock every top-level binding and type:** `-- |` above it, and `-- ^` after a constructor or
  field. Describe what it does now; history goes in the commit message.

### Structure

- **Name a recursion scheme rather than hand-writing it.** Use `map`, `filter`, a fold (`foldl'`
  for a strict left fold), `traverse`, `mapM_`, `forM_`. Recurse by hand only when none fits, and
  then follow the data's shape (`~/.claude/reference/recursive-design.md`).
- **A `where` helper earns its name** by being used more than once, or by naming a phase of the
  function. That is the same test as the shared "what earns pulling code into its own function"
  rule. A `where` binding used once that only renames an expression is inlined, with a comment.
- **IO at the edges:** keep pure logic in pure functions and the `IO` in a thin layer that calls
  them. It is easier to test and to read.

## Cross-links

- `~/.claude/reference/python-coding-standard.md`: the annotate-every-binding rule this one
  mirrors, and its exemption for targets that cannot be annotated.
- `~/.claude/reference/recursive-design.md`: recursion schemes.
- github.com/billsix/spimulator `tasks/archive/2026/11/11/haskell-port-annotate-every-binding.md`: the
  typing work this doc's rules come from, and the checker.
