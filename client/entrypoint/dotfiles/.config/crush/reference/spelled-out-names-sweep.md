# Spelling out abbreviated names — a rename sweep for code people learn from

**Reference document** — how to plan and run a sweep that replaces a codebase's abbreviated and
acronym names (`gpr`, `inst`, `xmalloc`, `ExcCode::AdEL`) with spelled-out ones
(`general_purpose_registers`, `instruction`, `allocate_or_exit`, `ExceptionCode::AddressErrorLoad`),
without changing behaviour. Read it **before** writing such a task, or when the `/spell-out-names`
command runs. Portable rules only; the one worked example is cited by URL at the end. (Written
2026-11-14 — William Emerison Six <billsix@gmail.com> — from the sweep of a C simulator core and its
Python, Haskell and Rust ports, about 1,500 names.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep them in
> sync.** Canonical: runClaudeInContainer `tasks/reference/spelled-out-names-sweep.md`
> (github.com/billsix/runClaudeInContainer), delivered to a Claude session at
> `~/.claude/reference/spelled-out-names-sweep.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/spelled-out-names-sweep.md`, and the
> baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/spelled-out-names-sweep.md`
> — delivered to a Crush session at `~/.config/crush/reference/spelled-out-names-sweep.md`. Edit the
> canonical, then re-copy.

## Why

Short names were a typing economy. With completion and an assistant writing much of the code, that
economy is gone, and the cost stays with the reader: a student meeting `gpr` has to learn a code
before reading the line. The sweep pays that cost once.

## How the maintainer asks for it

One line: `/spell-out-names <scope>` (for example `/spell-out-names src include`, or
`/spell-out-names` for the whole repo). The command **writes task docs and stops**; it renames
nothing. The tasks then follow the normal lifecycle: open questions answered, go-ahead, work,
done-record, archive.

## Step 1 — check the repo's situation before planning

Each check below is either a recorded fact in the task's `## Context` ("this repo takes no upstream
merges: its remotes are …") or a numbered open question. Several can rule the sweep out, or shrink
it, so they come first.

1. **Upstream merges.** Is the repo a fork that still takes merges from an upstream (an
   `upstream` remote, a vendor branch, a "sync with upstream" task)? Every renamed line conflicts
   with every later upstream change to it. If it does, the default is not to sweep, or to sweep only
   code the fork owns; ask. A repo whose remotes all point elsewhere is an upstream-only checkout and
   is out of scope entirely.
2. **Patches meant for upstream.** Code carried as patches someone will send upstream follows the
   upstream's names. Leave it alone.
3. **Consumers.** Is any renamed name public API of a library others pin? Then the rename is a
   breaking change: a version bump and a `CHANGELOG.md` entry, or a deprecated alias. An application
   nobody links against has no such cost.
4. **Generated code.** Rename the generator's **input** (its tables, templates, column names),
   never the output, then regenerate. List everything else the generator feeds (other languages'
   tables, editor grammars), because those change in the same commit. Take care that the generator's
   data columns that hold *user-facing text* (mnemonics, keywords) are not renamed with the
   identifier columns.
5. **Mirrors.** Ports, bindings or reimplementations that share the names. Each gets its own task,
   after the primary one, reusing its rename table so the same concept has the same name everywhere.
6. **Code the build does not compile.** `#if` branches, other platforms' files, optional features
   off by default, examples outside the build. List them; each needs its own compile check, or a
   hand review if it cannot be built.
7. **Other contracts on the code.** A teaching subset (code a course compiler must parse), a coding
   standard with its own naming rules, or a project rule against style sweeps. Respect them.
8. **What must not change** (the exemption list):
   - names defined outside the code (a library's functions, a protocol's fields, an overridden
     framework method, POSIX `fd`);
   - text the program prints or reads, so test goldens stay byte-identical (an enum's printed
     name, a format string's text, a JSON key);
   - what the user types (assembler mnemonics, register names, command words);
   - names quoted from a manual or standard, which keep the manual's spelling in a comment.

## Step 2 — build the vocabulary, and settle the policy questions

1. **List every name** the scope declares, from the language's own tools rather than by regex
   (see the per-language notes below), with kind and location.
2. **Split each name into words** and collect the distinct words. The abbreviations are a few
   hundred words, not thousands of names, so decide per word, then derive the names.
3. **Find each word's meaning** from context, and from the domain's sources when it is jargon (a
   processor manual, an RFC, a standard). **Record the sources in the task**: the reader of the
   glossary needs to check a meaning without redoing the research.
4. **Ask the maintainer the policy questions** before any rename, as numbered questions with a
   recommendation each. The ones that came up:
   - domain acronyms (`CP0` → `coprocessor_0`?);
   - name by meaning or by the manual's name (`STACK_POINTER_REGISTER /* $sp */`, or `REG_SP`?);
   - the keep-list of acronyms every reader knows (AST, ASCII, EOF, IO, JSON, REPL, ms, the
     language's own `syscall`);
   - idiomatic library-habit names (`xmalloc`): rename, with the habit name in a comment?
   - mathematical names in numeric code (`a`, `b`, `q`, `r` in a long-hand multiply), which are
     usually clearer short.
5. **Write the glossary as a reference doc** in the repo (`tasks/reference/<…>-glossary.md`):
   the vocabulary, the conventions, and per-language notes. It outlives the task; new code follows
   it, and a one-line convention in the project `CLAUDE.md` points at it.

Watch for one spelling with two meanings (`reg` holding a register number in one function and a
register's value in another, `le` as little-endian versus less-or-equal). A rename table keyed by
spelling alone cannot split them; key those rows by declaration (`path:line`) or rename them in a
targeted pass.

## Step 3 — rename by the language's own view of the code

Never a blind text substitution: it renames strings, comments it should not, and other scopes'
names. Use what the compiler or an LSP knows, then a token pass for what that misses.

- **C.** clang's JSON AST (`clang -Xclang -ast-dump=json -fsyntax-only`) gives each declaration an
  id and each use a `referencedDecl` id, so a rename follows references, not spellings. Its
  locations are delta-encoded and in **bytes**, not characters (UTF-8 text breaks character
  offsets). Macros, macro parameters, struct designators (`.field =`), array sizes and enum
  constants used in them need a token pass that skips string literals. The AST must match the tree,
  so regenerate or revert generated files before dumping it.
- **Python.** `ast` to find the module's own declarations; `tokenize` to rename, which leaves
  strings alone while still reaching f-string expressions. Never rename dunders or builtins; check
  `__slots__` and `__all__` strings and string-quoted forward references by hand.
- **Haskell.** The port's own names are every identifier **minus** what the libraries export (ghci
  `:browse` of each imported module), keywords and module names. Rename to camelCase, keep primes,
  and watch for Prelude shadowing (`length`, `error`) under `-Wall -Werror`.
- **Rust.** Declaration patterns, minus std's prelude, every name a `use` imports from outside the
  crate, `macro_rules!` fragment specifiers (`expr`, `ident`) and module (file) names. After a single
  `.`, rename only names the crate declares as a function or field, so std's `.len()` stays; `..`
  is a range, not member access. Inline format arguments (`"{fd}"`) follow their variables.
- **An LSP rename** (clangd, rust-analyzer, pyright, HLS) is a fine alternative for a few dozen
  names; a table-driven codemod scales better past that and can be re-run.

Keep the codemod and its tables under `tasks/adhoc/<task-slug>/` (a `data/` worklog of names,
words and renames, a manual-rows file for the decisions), make it idempotent, and re-run it from a
clean tree after each change to it.

## Step 4 — batch, build, prove

1. **Batch by declaration kind** (types, functions, globals, fields, locals, macros), one commit
   each when committing is authorized, building and testing after every batch.
2. **Let the compiler find collisions.** `-Werror -Wshadow` (C), `-Wall -Werror` (Haskell),
   `clippy -D warnings` (Rust), the type checker (Python). Two names that become one spelling fail
   the build; resolve each with a manual row.
3. **Prove a pure rename by comparing code bytes.** For C, compare each object file's `.text` and
   `.rodata` sections before and after (`objcopy -O binary --only-section=…`); debug info and symbol
   names differ, code must not. For the other languages the proof is the test suite plus
   byte-identical golden outputs.
4. **Check the residue.** Grep the old spellings after each batch; what remains is either a
   reasoned exemption or a miss, often in code the build skipped (Step 1, item 6).
5. **Run the full containerized gate** with the repo's default flags at the end.

## Step 5 — finish

- **Format once**, at the end, as its own commit, so the rename commits stay reviewable.
- **Fix comments by hand**: renamed names lengthen lines, and the formatter leaves orphaned words
  on comment lines; reflow the paragraph.
- **Add manual-name comments** where the reader will meet the manual's name elsewhere
  (`/* $sp */`, `/* AdEL: Address error on a load */`).
- **Update docs and tests that quote names**: task and reference docs, the README, error-message
  tests.
- **List the rename commits in `.git-blame-ignore-revs`** once they exist (the maintainer's commits
  in the stage-only default), so `git blame` skips them.
- **Archive** with a done-record that keeps the decisions, the sources and the exemptions; the
  `tasks/adhoc/` scripts are `git rm`'d by the last task that reads their tables.

## Lessons from the worked example

- Check what the output prints from names: Python's `Enum.name`, Rust's `Debug` output and format
  arguments. A rename there changes golden files; map the printed text explicitly.
- Exclude names generated from the generator's data when listing a port's own names, and rename
  them through the generator.
- Short words leak from comments and prose into word lists (possessives, articles); skip names under
  three letters unless they are known abbreviations.
- Enum members whose spelling is shared with another name (`Int` both an exception code and a
  scanner token) belong in a targeted pass, not the whole-tree table.
- Location counters (`current_data_pc`) are not program counters even when the original code calls
  them `pc`; spell out what a thing is, not what its abbreviation suggests.

## Worked example

github.com/billsix/spimulator, 2026-11-14:

- `tasks/archive/2026/11/14/spelled-out-names-c-core.md` — the C core: decisions, sources and
  exemptions;
- `tasks/archive/2026/11/14/spelled-out-names-python-port.md`, `…-haskell-port.md`,
  `…-rust-port.md` — the ports;
- `tasks/reference/spelled-out-names-glossary.md` — the resulting glossary;
- the codemods (`list_names.py`, `split_words.py`, `classify_words.py`, `apply_renames.py`,
  `compare_code.sh`, `port_names.py`) are in history at commit `ced3497`, under
  `tasks/adhoc/spelled-out-names-c-core/` and `tasks/adhoc/spelled-out-names-python-port/`. They
  are project-specific; read them for the shape, don't vendor them.
