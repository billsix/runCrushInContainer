# C++ coding standard (shared, cross-project)

**Reference document** — shared cross-project C++ coding standard, the sibling of
`python-coding-standard.md`. Read on demand (NOT auto-loaded). Update in place. A project's
`CLAUDE.md`/`README.md` points here and keeps its own repo-specific invariants, worked examples,
and file paths in its own additions doc (see Cross-links). Portable rules only: this doc names no
one project's files. (Written 2026-10-15 — William Emerison Six <billsix@gmail.com> — from the
maintainer's own `auto` guidelines plus the C++ Core Guidelines, Herb Sutter's GotW #91/#94, the
Abseil Tips of the Week, the Google C++ Style Guide, Scott Meyers' *Effective C++* (3rd ed.) and
*Effective Modern C++*, and the clang-tidy check catalog; sources at the end. Same day, revised
to add the smart-pointer selection table, the move/forward and lambda rules, the per-standard
feature ladder, and the Meyers items — the maintainer asked for them explicitly.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/cpp-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/cpp-coding-standard.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/cpp-coding-standard.md`, and
> the baked crush-client set `client/entrypoint/dotfiles/.config/crush/reference/cpp-coding-standard.md`
> — delivered to a Crush session at `~/.config/crush/reference/cpp-coding-standard.md`. Edit the
> canonical, then re-copy it over the other two.

Written for both humans and AI agents: each rule is a statement + a one-line reason. **The
standard is split in two** — (a) what **the toolchain already enforces mechanically** (clang-format,
clang-tidy, the compiler's warning level; if `make format` and the build are green, these are done —
don't hand-review or re-prose them), and (b) the **judgment calls no tool can check** (spend
attention here). A C-only project takes tier (a) and the parts of (b) that are not about C++
features (initialization, scope, integer types, naming, comments).

## (a) Enforced by the toolchain — treat a green format/lint/build as authority

- **`clang-format` owns layout.** Every project ships a `.clang-format` (the fleet default is
  `BasedOnStyle: google` with `SortIncludes: Never`; a project may add keys) and a `make format`
  target that runs it in-container. Indentation, brace placement, wrapping, spacing, pointer
  alignment: **never argue about these or hand-format** — write the clearer form and let the
  formatter lay it out. Line length is the formatter's job, NOT a design input: don't reject a
  ternary, an initializer, or a call because the one-liner would exceed the column limit.
  (`SortIncludes: Never` is deliberate — include order can be semantically load-bearing in old
  code; keep it as written.)
- **`clang-tidy` owns the mechanical modernization and the bug-pattern catalog.** Where a project
  has a `.clang-tidy` and a `lint.sh`, a clean run is authority on: `modernize-use-nullptr`,
  `-use-override`, `-use-using`, `-use-equals-default/-delete`, `-use-emplace`, `-loop-convert`,
  `-make-unique/-make-shared`, `-use-bool-literals`, `-avoid-c-arrays`, `-use-string-view`;
  `cppcoreguidelines-init-variables`, `-pro-type-member-init`, `-pro-type-cstyle-cast`,
  `-special-member-functions`, `-virtual-class-destructor`, `-slicing`, `-no-malloc`;
  `bugprone-use-after-move`, `-dangling-handle`, `-narrowing-conversions`, `-integer-division`,
  `-too-small-loop-variable`, `-exception-escape`, `-unique-ptr-array-mismatch`;
  `performance-unnecessary-copy-initialization`, `-for-range-copy`, `-unnecessary-value-param`,
  `-move-const-arg`; `readability-qualified-auto`, `-else-after-return`,
  `-implicit-bool-conversion`, `-redundant-smartptr-get`, `-braces-around-statements`. **On
  2000s-era code several "safe" checks misfire** (`-use-equals-default` on a copy ctor with an init
  list, `-loop-convert`'s container-derived names) — the catalog of warts and the tier-by-tier
  method are in `cpp-ownership-migration.md` and `cpp-build-modernization.md`. Diff and build after
  every `-fix` run; never let it touch vendored code (`-header-filter` scoped to your sources).
- **The compiler's warning level is a gate, not advice.** Pin the standard (`-std=c++23` /
  `cpp_std=c++23` / `CMAKE_CXX_STANDARD 23`; an unpinned build compiles at whatever the installed
  compiler defaults to, which is not reproducible) and build at `-Wall -Wextra -Wpedantic` (Meson
  `warning_level=3`). A new warning in code you touched is yours to fix **at the source**, never with
  a `-Wno-`; `-Wswitch` over `enum class` types, `-Winfinite-recursion`, `-Wparentheses`,
  `-Wignored-qualifiers` each found a real bug in the fleet. Where a project's gate also runs
  sanitizers (`-fsanitize=address,undefined`), a sanitizer report is a failure, not noise.
- **Suppressions are narrow and reasoned.** `// NOLINT(check-name)` / `// NOLINTNEXTLINE(...)`
  with the reason on the same line, or `/* clang-format off */ … /* clang-format on */` around an
  aligned table or ASCII diagram. Never a file-wide or check-wide suppression to make a run green.

## (b) Judgment calls — prose, because no tool can check them

### `auto` — use it with intent, not by reflex

`auto` is one of the most useful compile-time type-deduction features in modern C++ *provided it is
used with discipline*; it is easy to overuse when applied blindly. The rule of thumb:

- **Use `auto` freely when the type is obvious from the right-hand side, redundant, or painfully
  long:** iterators, lambda closures (unnameable), dense template code, and factory/constructor
  calls where the type is already on the right (`auto ptr = std::make_unique<Widget>(…)`,
  `auto it = names.begin()`, `auto parsed = static_cast<Kind>(raw)`). Repeating
  `std::unique_ptr<Widget>` on the left adds visual noise, not safety.
- **Spell the type out when a primitive or domain type carries meaning the reader needs at
  once:** `auto count = get_user_count();` hides whether `count` is `int`, `size_t`, or
  `int64_t`, which matters for signed/unsigned comparisons and overflow; `double`, `float`,
  `std::chrono::milliseconds`, a `Money`/`Angle` domain type, and any value that will be compared,
  divided, or serialized are spelled out. Over-relying on `auto` forces a reader without an IDE to
  hunt down return types.
- **Qualify it.** `auto` strips top-level `const` and references, so `auto x = get_heavy();`
  **silently copies**. Write `const auto&` to observe, `auto&` to mutate in place, `auto*` /
  `const auto*` when the value is a pointer (`readability-qualified-auto` enforces the pointer
  case), and plain `auto` only when you *want* an independent copy (then say so if it isn't
  obvious). Range-`for` over a container of non-trivial elements is `for (const auto& x : xs)`
  by default; over a map use structured bindings, `for (const auto& [key, value] : m)` — a bare
  `std::pair<K, V>` there would copy through an implicit conversion.
- **Use `auto x = Type{init};` to commit to a type and still get the `auto` guarantees** (Herb
  Sutter's GotW #94): the variable cannot be left uninitialized, and a brace-init cannot narrow,
  so `auto n = std::size_t{count};` is both explicit and conversion-safe. The three cases it
  can't express: non-movable types (locks, atomics) — declare them directly; brace lists that
  would deduce `std::initializer_list` — spell the container; multi-word builtins (`long long`)
  — use a fixed-width alias.
- **Two traps:** a proxy type (`std::vector<bool>::reference`, expression templates) deduces to
  the proxy, which may dangle once the temporary dies — spell the value type there; and `auto`
  on a call that returns a reference gives you a *copy*, which may be exactly the surprising
  behaviour change a reader will not expect.
- Why `auto` is *not* overrated: it guarantees initialization at the declaration site, it binds to
  the deduced type and so blocks the unintended implicit conversion an explicit (wrong) type would
  trigger, and it tracks a return-type change during maintenance without a cascade of edits.

### Initialize everything; `const` by default

Every variable is initialized at its declaration (`ES.20`), with braces when a value is given
(`ES.23`: `int n{0};`, `std::vector<int> xs{};` — braces refuse narrowing). Declare locals, members,
and parameters `const` unless they are modified (`ES.25`, `Con.1`), and compile-time constants
`constexpr` (`Con.5`) — `constexpr` over `#define` for numbers and `inline constexpr` for
namespace-scope constants (`ES.31`, `ES.45`: no magic numbers; name them). **One name per
declaration** (`ES.10`) and declare at the point of first use in the smallest scope (`ES.5`,
`ES.21`); a C++17 `if (auto it = m.find(k); it != m.end())` keeps a lookup result scoped to the
branch that needs it. A name's length matches its scope: `i` for a three-line loop, a full noun
phrase for anything a reader must remember across the function.

A raw pointer (or iterator) has **two *independent* `const` opportunities — judge each on its own;
you may want neither, either, or both (they do not imply each other):** **pointee-`const`**
(`const T* p`, when nothing writes `*p` through this pointer) is the high-value one — the classic
const-correctness that documents "input, not modified" and lets the compiler reject an accidental
write, so apply it to every pointer-to-input, *especially* parameters; and **top-level `const`**
(`T* const p`, when the pointer itself is never repointed) is the binding-stability one, exactly
like `const` on a scalar local, so reach for it on a *local* whenever you would `const` a scalar.
Together they read `const T* const p`. **On a function *parameter*, add the pointee-`const` (the
caller-visible contract) but NOT the top-level `const`** — `T* const` on a parameter is a
definition-only detail (not part of the type, no ABI effect) that clutters prototypes; add it in a
definition only if it genuinely helps, and never let a header and its definition disagree. `clang-tidy
misc-const-correctness` finds never-modified locals mechanically; the change is behavior-identical.
(Prefer a borrowing reference or owning container to a raw pointer in the first place per the next
section — but where a raw `T*`/iterator is the right tool, qualify it this way. The same idiom lives
in the C standard, `c-coding-standard.md`.)

### Ownership and lifetime — RAII, `unique_ptr`, raw pointers never own

- **Resources are owned by objects** (`R.1`): memory, files, locks, handles are acquired in a
  constructor and released in a destructor, so no error path can leak. No naked `new`/`delete`
  (`R.11`), no `malloc`/`free` in C++ (`R.10`), no manual `fclose`/`unlock` when a guard type
  exists.
- **Prefer scoped objects to heap allocation** (`R.5`): a local, a member, or a value in a
  container, not a pointer to one. Heap-allocate only for polymorphism, for an object that
  outlives its scope, or for something too large or optional (then `std::optional<T>` beats
  `unique_ptr<T>` for "maybe constructed later").
- **One owner, expressed in the type** (`R.20`/`R.21`): `std::unique_ptr<T>` by default,
  `std::make_unique` to create it (`R.23` — never a bare `new` handed to a smart pointer, except
  wrapping a legacy API that returns an owned raw pointer, with a comment saying so).
  `std::shared_ptr` only when ownership is *genuinely* shared, and then prefer immutable payloads;
  it is not a "don't want to think about it" default.
- **A raw pointer or reference never owns** (`R.3`): `T*`/`T&` parameters and members are
  borrows, and a function taking `T*` promises not to delete it. Query results, "active object"
  aliases, selection lists, back-pointers: raw. **A `unique_ptr` that is never `std::move`d
  should not be a `unique_ptr`** — pass `T&`/`const T&` (or `T*` when null is a valid "none") to
  functions that merely *use* the object (`F.7`, Abseil TotW #187); pass `unique_ptr<T>` **by
  value** only to transfer ownership (`F.26`), and return it by value from factories.
- **Lifetime rules the compiler won't enforce:** never return a pointer or reference to a local
  (`F.43`); never store a `std::string_view`/`std::span` beyond the lifetime of what it views; a
  moved-from object is a zombie — reassign or destroy it, read nothing else from it; `std::move`
  on a `const` object copies (`performance-move-const-arg`) and `std::move` on a return of a local
  pessimizes (`F.48`). Count the names: two names for one datum is a copy, one name is a move,
  zero names is a temporary (Abseil TotW #77).
- Migrating an old codebase from raw owning pointers is its own method with its own traps
  (double-free that compiles clean): `cpp-ownership-migration.md`.

### Smart pointers — which type, and how to pass one

**First ask whether you need a pointer at all** (`R.5`, Meyers EC++ Item 13 / EMC++ Item 18). A
subobject that is constructed unconditionally with its owner, is not polymorphic, and is never
replaced or handed off is a **plain value member** (`cSprite_Manager m_sprites;`), not a
`unique_ptr` — the pointer buys nothing and costs an allocation, an indirection, and a null state.
Reach for a smart pointer only when one of these is true: the type is polymorphic (a base-class
member holding a derived object), the object is optional or created later than its owner
(consider `std::optional<T>` first — it is a value with an empty state), the object is large and
rarely present, it must be moved between owners (a factory result, a container of polymorphic
things), or it outlives a scope (a return value). Then pick by ownership shape:

| Shape | Type | Create with | Notes |
|---|---|---|---|
| exactly one owner, transferable | `std::unique_ptr<T>` | `std::make_unique<T>(…)` | the default; zero overhead over a raw pointer; move-only, so a transfer is visible at the call site (EMC++ 18, 21) |
| one owner, array | `std::unique_ptr<T[]>` | `std::make_unique<T[]>(n)` | only for a C-API buffer; otherwise `std::vector`/`std::array` |
| one owner, non-`delete` cleanup | `std::unique_ptr<T, Deleter>` | the deleter as a stateless functor or lambda | the RAII wrapper for C handles (`FILE*`, `SDL_Surface*`, `Mix_Chunk*`): the deleter is part of the type, so misuse won't compile |
| genuinely shared lifetime (the last user frees) | `std::shared_ptr<T>` | `std::make_shared<T>(…)` | one allocation for object + control block, exception-safe; copies cost an atomic increment, so pass `const shared_ptr&` or `T*` to users that don't take a share (EMC++ 19, 21) |
| observe a shared object without keeping it alive | `std::weak_ptr<T>` | from a `shared_ptr` | caches, observer lists, breaking `shared_ptr` cycles; `lock()` before use (EMC++ 20) |
| a class that must hand out `shared_ptr`s to itself | `std::enable_shared_from_this<T>` | `shared_from_this()` | only valid once the object is already owned by a `shared_ptr` |
| C API that writes a pointer out-parameter | `std::out_ptr`/`std::inout_ptr` (C++23) | `c_api(std::out_ptr(uptr))` | replaces the `T* raw; api(&raw); uptr.reset(raw);` dance |
| non-owning handle | `T*` or `T&` | — | never `std::observer_ptr` (it is not in the standard); a raw pointer *is* the non-owning handle (`R.3`) |
| `std::auto_ptr` | — | — | **removed in C++17** (deprecated since C++11): it "copied" by stealing, which silently emptied the source in a `std::vector` or a by-value call. Every `auto_ptr` is a `unique_ptr` that must be `std::move`d explicitly |

**Passing and returning** (GotW #91, `F.7`, `F.26`, `F.27`): don't put a smart pointer in a
signature unless the function manipulates the *pointer* (takes, gives, or shares ownership).
`unique_ptr<T>` **by value** is "I take it" (a sink); `unique_ptr<T>&` only to reseat the caller's
pointer; `const unique_ptr<T>&` never — write `T*`/`T&`. `shared_ptr<T>` by value is "I will
keep a share"; `const shared_ptr<T>&` only when you *might* keep one; otherwise `T*`/`T&`. A
factory returns `unique_ptr<T>` by value (upgradeable to `shared_ptr` at the caller, never the
reverse). Inside a class, **ownership transfer must go through the API** — an `Add(T*)` that
adopts a raw pointer forces every caller to `.release()` the `unique_ptr` it already holds and
invites a double-adopt; `Add(std::unique_ptr<T>)` makes the hand-off a `std::move` the reader can
see. `.get()` is for *borrowing* a `T*` to store or compare; `.release()` appears only at a
documented hand-off to a raw-owning legacy API, with a comment. `unique_ptr` has the same size and
cost as a raw pointer, so the choice is never a performance question; `shared_ptr` is twice the
size plus the control block and atomic refcounting, which is why it is not the default.
**Pimpl** (EMC++ 22): a `unique_ptr<Impl>` member needs the destructor (and moves) *defined in
the `.cpp`* after `Impl` is complete, or the header's implicit destructor won't compile.

### Function parameters and returns — the conventional four shapes (`F.15`–`F.21`)

| Intent | Spelling | Why |
|---|---|---|
| **in**, cheap to copy (scalars, enums, `std::string_view`, `std::span<const T>`, anything ≤ ~16 bytes and trivially copyable) | `T` by value | passes in registers; a reference would cost a load |
| **in**, everything else | `const T&` | no copy, and a compiler-enforced promise not to modify |
| **in-out** | `T&` | the only case for a non-`const` reference parameter |
| **will-move-from / sink** (the function keeps its own copy) | `T` by value, then `std::move` into the member | one spelling serves both lvalue (copy) and rvalue (move) callers; `T&&` only when a copy must be impossible |
| **forward** (generic wrappers only) | `TP&&` + `std::forward<TP>` | perfect forwarding; never `std::move` a forwarding reference |
| **out** | **a return value**, not an output parameter (`F.20`) | the contract is in the signature, composes in expressions, and C++17 guaranteed elision makes it free |

**Return a struct (or `std::pair`/`std::tuple` with structured bindings at the call site) for
multiple outputs** (`F.21`); reserve output parameters for in-out updates, caller-controlled
allocation, or a measured hot loop that would otherwise reallocate. **Take views, not
containers:** `std::string_view` instead of `const std::string&`/`const char*`, `std::span<const
T>` instead of `const std::vector<T>&`, so callers aren't forced into one container type.
`T*` rather than `T&` only when "no argument" is a valid option (`F.60`); never a smart pointer
as a parameter unless ownership moves. Unused parameters are unnamed (`F.9`), or `/*name*/`.
Prefer default arguments to overloading for the same operation (`F.51`). A function does one
logical thing (`F.2`); past roughly forty lines, ask whether a phase wants its own name (the
language-agnostic "what earns an extraction" rule applies: duplication, or naming a phase — not
reshaping control flow).

### Classes — make the invariant explicit, or use a `struct`

- `struct` for passive aggregates with public members and no invariant; `class` with private
  data the moment an invariant exists (`C.2`, `C.8`). Keep data members private (`C.9`).
- **A constructor establishes the invariant** (`C.41`); prefer in-class member initializers over
  init-list repetition (`C.45`, `C.48`); `explicit` on every single-argument constructor
  (`C.46`) — an implicit conversion you didn't intend is a bug waiting for a reviewer.
- **The rule of zero** (`C.20`): if members are values and smart pointers, write no destructor,
  copy, or move. If you must write one special member, define or `= delete` all five (`C.21`)
  — the compiler-generated rest will be wrong. A polymorphic base gets a `virtual` (or
  `protected` non-virtual) destructor (`C.35`), and is copied only via a virtual `clone()` to
  avoid slicing (`C.67`, `C.130`).
- **`override` on every overrider, never a redundant `virtual`** (`C.128`); `final` only when
  further overriding is a design error, not as a habit. Prefer composition; public inheritance
  only, and only for "is-a" (`C.120`, `C.129`); don't make data members `protected` (`C.133`).
- **`-Woverloaded-virtual` flags a derived function that hides a base `virtual` of the same name —
  but do NOT blanket-`using Base::f;` to un-hide it.** When the base overload has a default argument
  (or an arity) overlapping the derived signature, un-hiding makes the call *ambiguous* and the build
  fails; the hide is often intentional and load-bearing. Decide per method — make the derived a true
  `override` of the base signature, or accept the hide and suppress narrowly with a reason. It is a
  judgment call, not a codemod. (smc's cSprite/cMovingSprite hierarchy, 2026-10-18.)
- Identity by type, not by tag: a runtime `kind`/`m_type` field switched over everywhere is the
  legacy shape of virtual dispatch — when a switch on a type tag appears in new code, ask whether
  a virtual function or `std::variant` + `std::visit` is the design. (Converting an existing
  tag-dispatch codebase is a behavioural refactor; see `cpp-ownership-migration.md`'s method.)
- Operator overloads only for operations whose meaning is obvious and consistent with the builtin
  (`C.160`–`C.168`): arithmetic on a vector type, `<=>` for ordering; never `&&`/`||`/`,`.

### Enums, casts, integers — the silent-conversion cluster

- **`enum class`, never a plain `enum`, in new code** (`Enum.3`): scoped names don't leak
  single-letter enumerators into user scope, and they don't convert to `int` behind your back.
  Specify the underlying type only when it is serialized or must match an ABI (`Enum.7`); don't
  assign values unless they are meaningful (`Enum.8`); `switch` over an `enum class` without a
  `default:` so `-Wswitch` catches a newly added enumerator (where a documented default is the
  design, write it and say why). `using enum E;` (C++20) keeps call sites terse inside the
  implementation without leaking.
- **No C-style or functional casts** (`ES.48`, `ES.49`): `static_cast` for a conversion you mean,
  `dynamic_cast` only when the design needs runtime type recovery, `reinterpret_cast` with a
  comment, `const_cast` almost never (it is undefined behaviour on an object that was defined
  `const`). A cast is a statement that the type system is wrong here; minimise them (`ES.48`).
- **No narrowing** (`ES.46`): brace-init refuses it, `gsl::narrow_cast`/`static_cast` admits it
  deliberately. **Signed by default** for arithmetic (`ES.100`–`ES.107`): don't mix signed and
  unsigned, don't use unsigned to "avoid negatives", use `std::size_t`/`std::ssize` for sizes and
  indices and compare them to other `size_t`s (`std::ssize(v)` or `std::cmp_less` when you must
  compare to a signed count). Fixed-width (`std::int64_t`) when the range is a requirement;
  `int` otherwise. Integer division and `x * y` widening-after-overflow are the two
  `bugprone-` checks worth internalising.
- **Adding `-Wsign-conversion` to a legacy tree is behaviour-preserving by construction:** wrap the
  flagged operand in an explicit `static_cast<DEST>` *at the site* — the cast does exactly what the
  implicit conversion already did, so the runtime result is identical and the warning goes away. Cast
  at the boundary (`vec[static_cast<size_t>(i)]`, `api_taking_int(static_cast<int>(n))`); do NOT retype
  the variable, which is a different and riskier change. (smc, 273 first-party sites made explicit,
  2026-10-18.)
- `nullptr`, never `0`/`NULL` (`ES.47`); `sizeof(x)` over `sizeof(T)`; `++i` over `i++` where the
  result is unused.

### Errors — pick one strategy per project and state it

The language offers three; a project `CLAUDE.md` says which it uses and why:

- **Exceptions** (`E.2`) for errors that can't be handled locally, with RAII making unwinding
  safe. Throw by value, catch by `const&` (`E.15`); never let one escape a destructor, a `noexcept`
  function, or a thread entry; mark a function `noexcept` when it cannot throw (`F.6`) — move
  constructors especially, or containers fall back to copying.
- **`std::expected<T, E>` (C++23) / `std::optional<T>`** when the caller is expected to handle
  the failure inline: the absence or error is in the return type and the compiler forces the
  check. **Never a sentinel value** (`-1`, `nullptr` meaning "closed", an empty string meaning
  "unset") — the type system can't make a caller test it (Abseil TotW #171).
- **Error codes / `std::error_code`** only at a C or OS boundary, converted to one of the above at
  the first opportunity.

`assert`/`[[assume]]`/`gsl::Expects` document preconditions that are *programming* errors, not
input validation; an invariant violation is a bug, a bad input is an error.

### Move, forward, and rvalue references (Meyers EMC++ 23–30, 41–42)

- `std::move` moves nothing: it is a cast to an rvalue; `std::forward` is a *conditional* cast
  that moves only if the caller passed an rvalue. Use `std::move` on an **rvalue reference
  parameter** (`T&&` where `T` is a concrete type) and `std::forward<T>` on a **forwarding
  reference** (`T&&` where `T` is deduced, or `auto&&`); never swap them, and never `std::move`
  a forwarding reference (it steals from an lvalue caller).
- Don't overload on a forwarding reference: it out-matches every other overload, including the
  copy constructor for a non-`const` lvalue. Tag dispatch, a constrained template (concepts),
  or pass-by-value are the alternatives.
- **Assume moves are absent, not cheap, or not used** until you've checked: a type with a
  user-declared destructor or copy operation gets no implicit move; a move that can throw is not
  used by `std::vector` reallocation unless it is `noexcept`; `std::array` and SSO strings move
  by copying. So: `= default` the five special members when you declare any one, and mark move
  constructors/assignments `noexcept`.
- **Pass by value when the parameter is always copied and the type is cheap to move** (a
  constructor storing a `std::string`): one spelling, one move for rvalue callers, one copy for
  lvalue callers. Otherwise the `const T&` / `T&&` overload pair (EMC++ 41).
- Prefer `emplace_back(args…)` to `push_back(T(args…))` when the argument is constructor
  arguments, not an existing object; keep `push_back` for an existing object (EMC++ 42).
  Return a local **by name** (`return result;`) — never `return std::move(local);` (`F.48`): it
  blocks copy elision.
- A moved-from object is valid but unspecified: assign to it or let it die; never read it. Never
  move a `const` object (it copies, silently).

### Lambdas (Meyers EMC++ 31–34, `F.50`–`F.54`)

- **Spell the capture list; avoid `[=]` and `[&]` defaults.** `[&]` dangles the moment the
  lambda outlives the scope (a callback, a thread, a stored `std::function`); `[=]` silently
  captures `this` by pointer (not the members by value) and copies nothing you didn't list, so
  it dangles just as readily. Write `[this]`, `[&x, y]`, or `[self = shared_from_this()]`.
- **Init-capture to move something in** (`[buf = std::move(buf)]`, C++14) — the way to put a
  `unique_ptr` or a large object into a closure.
- Generic lambdas (`auto` parameters, C++14) forward with `std::forward<decltype(x)>(x)`.
- Prefer a lambda to `std::bind` — always; `std::bind` is harder to read, type-erases, and
  inlines worse (EMC++ 34).
- Store a callable as `auto` or a template parameter where you can; `std::function` is the
  type-erased fallback (an allocation and an indirect call) for a heterogeneous container of
  callbacks or an ABI boundary. A lambda used once and locally stays unnamed (`F.11`); one reused
  gets a name. Capture by reference only when the lambda is used before the scope ends
  (`F.52`/`F.53`).

### `const`, `constexpr`, `noexcept` (Meyers EC++ 3, EMC++ 13–16)

- `const` wherever a value is not modified after initialization: locals, members, parameters by
  reference, member functions that don't mutate (EC++ Item 3). A `const` member function on an
  object shared across threads must actually be thread-safe — a mutable cache needs a mutex or
  an atomic (EMC++ 16). Prefer `cbegin`/`cend` and `const_iterator` when you don't mutate
  (EMC++ 13).
- **`constexpr` whenever a value or function *can* be computed at compile time** (EMC++ 15):
  constants (`inline constexpr int kMax = …;` at namespace scope, C++17 inline variables), table
  builders, small math; `consteval` (C++20) when it *must* be. A `constexpr` function is still
  callable at run time, so there is no cost to adding it. Replaces `#define` for every numeric
  or string constant (EC++ Item 2) — the one `#define` that stays is a token used in preprocessor
  string concatenation.
- **`noexcept` when a function will never throw** (EMC++ 14, `F.6`): move operations, swap,
  destructors (implicitly), leaf functions over trivially-copyable data. It is part of the
  interface — callers and `std::vector` optimise on it — so don't add it to a function that
  calls arbitrary user code or allocates. A `noexcept` function that throws terminates.

### Modern C++ — reach for the current spelling, and flag it proactively

Prefer the current-language solution over the historical one, and **when a newer feature would
solve a problem in code you're already touching, say so** rather than silently preserving the old
form. Each project pins its own floor; where it is C++20 or C++23 and backward compatibility is not
a concern, use freely:

- `std::format`/`std::print` over `printf`/`ostringstream` chains — except where the format
  string comes from a translation catalog in printf style, where `std::format`'s `{}` syntax would
  break every existing translation (a real case: keep `snprintf` with `sizeof` there).
- `std::string_view`, `std::span`, structured bindings, `if`/`switch` with initializer,
  `std::optional`/`std::expected`/`std::variant` over tagged unions and sentinels, `constexpr`/
  `consteval` over template metaprogramming for compile-time values, `std::ranges` algorithms and
  views over hand-written loops (`for (auto& x : xs | std::views::filter(pred))`), `<=>` for
  ordering, designated initializers for option structs, `[[nodiscard]]` on any function whose
  return is the point (a factory, a predicate, an `expected`), `[[maybe_unused]]` over a
  commented-out name, `std::chrono` for every duration, `<filesystem>` over `boost::filesystem`,
  `std::jthread`/`std::stop_token` over hand-joined threads, `constinit` for static-storage
  constants, concepts (`template <std::integral T>`) over SFINAE and over unconstrained `auto`
  parameters in a public interface (`T.10`, `T.11`).
- Lambdas: an unnamed lambda for a one-place function object (`F.11`), named when reused;
  capture by reference only for lambdas used locally (`F.52`), by value (or `[this]` explicitly,
  never `[=]`) when stored or passed to another thread (`F.53`, `F.54`).
- **Don't:** `std::auto_ptr`, `std::bind` (a lambda), `typedef` (`using`), `rand()`
  (`<random>`), C arrays (`std::array`/`std::vector`), `std::endl` (`'\n'`; it flushes), `using
  namespace std;` in a header, macros for constants or functions (`ES.30`, `ES.31`), `goto`,
  `va_arg` (`F.55`), `std::list` as a default container (`SL.con.2`: `std::vector` unless measured),
  `shared_ptr` as a default pointer, `volatile` for synchronisation (`CP.8`: `std::atomic`).

### The feature ladder — what each standard added that this doc leans on

A project's pinned `-std` is its floor; this is what becomes available at each rung, so a reader
knows which spellings a C++17 codebase may use and which need the bump. Don't buy a higher
standard than the work uses (`cpp-build-modernization.md`), but when it is already pinned high,
use what it bought.

- **C++11** — the modern baseline: `auto`, range-`for`, lambdas, `nullptr`, `enum class`,
  `override`/`final`, `= default`/`= delete`, `constexpr`, `static_assert`, rvalue references
  and move semantics, `std::unique_ptr`/`shared_ptr`/`weak_ptr`, `std::array`, `std::thread`/
  `std::mutex`/`std::atomic`, `<chrono>`, `<random>`, `using` aliases, variadic templates,
  `noexcept`, brace initialization (and its narrowing check).
- **C++14** — the polish: `std::make_unique` (the one C++11 forgot), generic lambdas (`auto`
  parameters), lambda init-capture, return-type deduction for functions, relaxed `constexpr`
  (loops and locals), variable templates, binary literals and digit separators, `[[deprecated]]`,
  `std::exchange`, heterogeneous lookup in ordered containers.
- **C++17** — the one that changes everyday code: structured bindings, `if`/`switch` with
  initializer, `if constexpr`, inline variables, `std::optional`/`variant`/`any`,
  `std::string_view`, class template argument deduction, fold expressions, guaranteed copy
  elision (so "always auto" becomes safe for non-movable types), `[[nodiscard]]`/`[[maybe_unused]]`/
  `[[fallthrough]]`, `<filesystem>`, parallel algorithms, `std::byte`, `std::size`/`std::data`,
  nested namespaces `a::b::c`; `std::auto_ptr`, `std::bind1st/2nd`, `std::random_shuffle` **removed**.
- **C++20** — the structural one: concepts and `requires`, ranges (`std::ranges::sort`, views),
  `<=>` three-way comparison with `= default`, designated initializers, `std::span`,
  `std::format`, coroutines, modules, `consteval`/`constinit`, `std::jthread` and
  `std::stop_token`, `using enum`, `[[likely]]`/`[[unlikely]]`, `std::erase`/`erase_if`,
  `std::ssize`, `std::cmp_less` and friends, abbreviated function templates (`auto` parameters
  in ordinary functions), `char8_t`, `<bit>`, `<numbers>`.
- **C++23** — the finishing one: `std::expected`, `std::print`/`println`, `std::mdspan`,
  `std::generator`, deducing `this`, `if consteval`, `std::out_ptr`/`inout_ptr`,
  `std::to_underlying`, `std::unreachable`, `[[assume]]`, multidimensional `operator[]`,
  `std::flat_map`/`flat_set`, `std::string::contains`, ranges `to`/`zip`/`enumerate`/`chunk`,
  `std::move_only_function`, `std::stacktrace`, `#warning`, `std::size_t` literals (`uz`).

### Meyers' items that still earn a line (Effective C++, 3rd ed., 2005)

Most of the 55 are now in the Core Guidelines above; these are the ones a reader of a legacy
codebase keeps tripping over, kept with their item numbers so a review can cite them:

- **2** `const`/`enum`/`inline` over `#define`; **3** `const` everywhere it is true; **4**
  initialize before use — members in the initializer list, in declaration order.
- **5–12** know what the compiler writes for you (the special members) and disable what you don't
  want (`= delete`); **7** a polymorphic base has a virtual destructor; **8** destructors never
  throw; **9** never call a virtual function from a constructor or destructor — it dispatches to
  the base; **10** `operator=` returns `*this`; **11** handle self-assignment; **12** copy *all*
  parts (base subobject included) in a hand-written copy.
- **13–17** resources are owned by objects (RAII); **14** think about copying behaviour of a
  resource handle; **16** `new[]` pairs with `delete[]`; **17** store a `new`ed object in a smart
  pointer in a *standalone statement* (the C++11 fix is `make_unique`/`make_shared`).
- **18** make interfaces easy to use correctly and hard to use incorrectly (strong types over
  `int`s, the right default, consistency with the standard library); **20** `const T&` over
  by-value for class types; **21** don't return a reference when you must return an object; **22**
  data members private; **23** prefer non-member non-friend functions; **25** a non-throwing
  `swap`.
- **26** declare variables as late as possible; **27** minimize casting, and never C-style; **28**
  don't return handles (pointers, references, iterators) to internals; **29** strive for
  exception-safe code (the strong guarantee via copy-and-swap); **30** `inline` is a request and
  a cost; **31** minimize compilation dependencies (forward declarations, pimpl).
- **32** public inheritance is "is-a"; **33** don't hide inherited names; **34** separate
  interface inheritance from implementation inheritance; **35** consider alternatives to virtual
  functions (NVI, strategy, `std::function`); **36** never redefine a non-virtual inherited
  function; **37** never redefine a default parameter of a virtual (defaults bind statically);
  **38** has-a is composition; **39** private inheritance is rare; **40** multiple inheritance
  is rarer.
- **41–48** templates: implicit interfaces, `typename` for dependent names, parameterize only
  what varies, traits for compile-time decisions (now `if constexpr`/concepts).
- **49–52** customizing `new`/`delete`: almost never; a custom allocator or an arena is the
  modern spelling.
- **53** heed compiler warnings (this doc's tier (a)); **54** know the standard library; **55**
  know Boost — today: know what the standard *took* from Boost (`filesystem`, `optional`,
  `variant`, `string_view`, `span`, `format`, `ranges`) and use the standard one.

### Headers, includes, and translation units

Every header is self-sufficient and guarded (`#pragma once` or an include guard; follow the
project). Include what you use, and only what you use; forward-declare where a declaration
suffices to cut build coupling. No `using namespace` and no definitions with external linkage in
a header; function-local helpers go in an unnamed namespace in the `.cc`/`.cpp`, not `static`
free functions. A header's include order is what the project's `.clang-format` says
(`SortIncludes: Never` in the fleet, so keep the existing order). Templates and `inline`/`constexpr`
functions live in headers by necessity; everything else in exactly one translation unit.

### Naming — the project's `.clang-format`/`readability-identifier-naming` owns the casing; these are the parts it can't

Follow the surrounding file (an existing codebase's convention beats this list): the Google default
is `PascalCase` types and functions, `snake_case` variables, `kPascalCase` constants, trailing
underscore for private members; a legacy codebase may use `m_member` and `cClassName` — stay
consistent *within* a project. **Verbs for functions, nouns for values; boolean predicates read as
questions** (`is_empty`, `has_parent`, `should_retry`). Descriptive over terse, with short names
only in tight scopes. A loop/handle variable is named for the **element type**, not the container
word (`sprite`, not `obj`; never a singularised container name). No Hungarian prefixes beyond
what the project already uses; no letter-deleting abbreviations. **An externally-defined name
always wins** — an override's signature, a callback, a C API symbol, a serialized field name —
match it exactly and suppress the linter at the site with the reason (the language-agnostic rule).

### Comments — `why`, inline, present tense; doxygen for the public surface

Comments explain *why* and the non-obvious *what* (an invariant, a unit, an ownership promise,
a citation), at the point they apply, never in a trailing notes block, and never the history ("was
X, changed to Y" belongs in the commit). Public headers get structured doc-comments (`///` or
`/** */` with `@param`/`@return`/`@throws`, the C++ analogue of the Python Google-docstring rule);
a one-line `///` on anything a reader will hover. Never leave a comment line holding a single word
or a fragment — reflow the paragraph. Commented-out code is deleted, not kept.

### Tests — doctests by default, beside the code

A unit test documenting an API is a **doctest beside the code**, same as the Python/Rust rule
(`doctests-by-default.md`). C++ has no built-in doctest, so use the **`doctest` framework**
(github.com/doctest/doctest — single header, vendored by source): `#include <doctest/doctest.h>`
once per header, then a `TEST_CASE` **right after** the function it tests (or after the class — a
`TEST_CASE` can't sit inside a class body), inside the code's namespace. Compile the cases out of
production/GUI binaries with **`-DDOCTEST_CONFIG_DISABLE`** set per-target (each becomes an
uninstantiated no-op, so no `#ifndef` guards), build one runner TU with
`DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN`, and run it under `ctest` from `make test`. Keep as a plain
(non-doc) test the same cases the other languages do — fixtures/parametrization, property/loop
checks, multi-step stateful sequences, and anything needing a debugger. Full mechanics (include-path
and formatter-exclusion gotchas): `doctests-by-default.md` `## C++`.

### Concurrency — the one-paragraph floor

Prefer no shared mutable state (pass values, return values). Where state is shared, a `std::mutex`
guarded by `std::lock_guard`/`std::scoped_lock` (never a bare `lock()`), `std::atomic` for a flag or
counter, `std::jthread` so a thread is joined on every exit path. Document which thread may call a
function when it matters (a mixer/audio callback, a GUI thread). Data races are undefined behaviour,
not "a timing issue"; run the project's gate under ThreadSanitizer when threads are in play.

## Cross-links

- **Each project's own additions doc** — the repo-specific invariants, the chosen error strategy,
  the worked examples (e.g. a game's `tasks/reference/refactoring-to-modern-cpp.md`, a library's
  modernization record).
- `cpp-ownership-migration.md` — the method and idioms for raw-pointer → `unique_ptr`
  migration, and the clang-tidy warts on old code.
- `cpp-build-modernization.md` — Meson port, pinning `-std`, `enum class` migration, raising the
  warning level, the tree-wide reformat commit.
- `cpp-python-bindings.md` — nanobind/pybind11 over an existing C++ core.
- `porting-with-an-output-oracle.md` — proving a modernization changed no output.
- `code-style-conventions.md` — the language-agnostic rules (comment reflow, line-length changes,
  externally-defined names, what earns an extraction, total dispatch) this standard specializes.
- `python-coding-standard.md` — the Python sibling; the two docs share one shape on purpose.

## Sources

- C++ Core Guidelines (Stroustrup, Sutter, eds.) — github.com/isocpp/CppCoreGuidelines; rule
  numbers cited inline.
- Herb Sutter, *GotW #91: Smart Pointer Parameters*,
  herbsutter.com/2013/06/05/gotw-91-solution-smart-pointer-parameters/, and *GotW #94: AAA
  Style (Almost Always Auto)*,
  herbsutter.com/2013/08/12/gotw-94-solution-aaa-style-almost-always-auto/.
- Scott Meyers, *Effective C++*, 3rd ed. (Addison-Wesley, 2005; 55 items) and *Effective Modern
  C++* (O'Reilly, 2014; 42 items on C++11/14) — cited inline as "EC++ Item N" / "EMC++ N".
- cppreference, *Dynamic memory management* — en.cppreference.com/w/cpp/memory (the smart-pointer
  inventory, `auto_ptr`'s deprecation in C++11 and removal in C++17, `out_ptr` in C++23).
- Abseil *Tips of the Week* — abseil.io/tips: #77 (temporaries, moves, copies), #126
  (`make_unique` is the new `new`), #161 (good locals and bad locals), #165 (`if`/`switch` with
  initializers), #171 (avoid sentinel values), #176 (prefer return values to output parameters),
  #187 (`unique_ptr` must be moved), #232 (when to use `auto`), #234 (pass by value, pointer, or
  reference).
- Google C++ Style Guide — google.github.io/styleguide/cppguide.html (the `BasedOnStyle: google`
  the fleet formats to; its no-exceptions rule is Google's, not this standard's).
- clang-tidy check list — clang.llvm.org/extra/clang-tidy/checks/list.html.
