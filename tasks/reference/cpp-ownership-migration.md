# Migrating a C++ codebase from raw owning pointers to `unique_ptr`

Durable, cross-project notes on turning a 2000s-era C++ codebase that owns everything through raw
pointers and hand `delete` into one that owns through `std::unique_ptr` — the method, the idioms,
and the traps. Distilled from the Secret Maryo Chronicles (SMC) modernization (2026-09-24), but
the shape is general to any pre-C++11 game/engine/tool with manager classes over `vector<T*>`.
Companion to `print-debugging.md` ("flip the definition and let the compiler enumerate the work").

## The method (recon → codemod → compiler → runtime)

1. **Recon first — find what the compiler can't see.** A read-only survey (grep + read) of every
   use of the container/owner you're about to change. You are hunting the **ownership hazards**,
   not the mechanical breaks: double-ownership (the same pointer held by two owners), aliasing (a
   raw pointer squirreled away and freed elsewhere), container-to-container transfers, reorder-in-
   place, and any "remove without free" path. The compiler will never flag these — they compile
   fine and free twice at runtime. Write them down before you touch code.
2. **Do the structural/hazard fixes deliberately, by hand.** These carry the design decisions
   (e.g. "who owns X" — make the borrower non-owning). One per commit where it stands alone.
3. **Codemod the mechanical majority.** The bulk is `for (auto x : c)` → `for (auto& x : c)` (a
   by-value loop can't copy a `unique_ptr`) and is safe for both raw and owning vectors, so a
   regex codemod handles it. Idempotent, scoped, collision-guarded.
4. **Flip the definition; let the compiler drive the residue.** `make` stops at the first failing
   TU, so errors come in waves — fix a wave, rebuild, repeat. The residue after the codemod is
   only the context-dependent `.get()` / `.release()` sites.
5. **Runtime-verify — a compile-clean ownership migration is NOT correct.** The types can line up
   while something is freed twice. Run the smoke/gate; on a `double free`/`SIGABRT`, get the
   backtrace under gdb (`gdb -batch -ex run -ex bt`) — it points straight at the bad free.

The migration is **atomic per shared type**: if N subclasses share one templated `objects` member,
you cannot flip it for some and not others — the flip + all its site fixes are one commit. Shrink
that commit by landing the separable prep first (below).

## Idioms — raw owner → `unique_ptr` owner

Given a manager whose storage becomes `vector<unique_ptr<T>>`:

| raw pattern | unique_ptr replacement |
|---|---|
| `objects.push_back(raw)` (Add adopts) | `objects.emplace_back(raw)` (constructs `unique_ptr<T>(raw)`) |
| `find + erase; delete obj` (Delete, frees) | `erase(it)` frees via the `unique_ptr`; if it's a *remove-without-free*, `it->release()` **before** `erase` |
| `for(...) delete *it; clear()` (Delete_All) | `objects.clear()` — the `unique_ptr`s free themselves |
| `return objects[i]` / `return obj` (Get returns borrowed) | `return objects[i].get()` / `return obj.get()` — return a **borrowed** `T*` |
| `std::find(b,e,raw)` | `std::find_if(b,e,[raw](const std::unique_ptr<T>& p){return p.get()==raw;})` |
| `for (auto x : objects) x->f()` | `for (auto& x : objects) x->f()` (operator-> works); `x.get()` only where a raw `T*` is needed (cast, compare, pass-by-`T*`, assign) |
| reorder in place: `first=front(); erase(it); front()=x; insert(begin()+1,first)` | move ownership: `auto owned=std::move(*it); erase(it); insert(begin(), std::move(owned))` — never hold a raw copy across the `erase` (it frees) |
| replace a slot: `*it = newraw; delete old` | `it->reset(newraw)` (frees old, adopts new) |
| move a whole vector's elements to another owner: `dst.insert(dst.end(), src.begin(), src.end()); src.clear()` | `dst.insert(dst.end(), std::make_move_iterator(src.begin()), std::make_move_iterator(src.end())); src.clear()` |
| alias the owning vector: `Foo* p = &mgr->objects` where `Foo=vector<T*>` | can't — the types differ. Iterate directly, or lift the loop body into a lambda called from both the borrowed-list loop and the owning-vector loop (`x.get()`) |

**Non-owning views stay raw.** Query results, "colliding objects", selection lists, the "active"
alias pointers — these borrow. Keep them `vector<T*>` and feed them `.get()`. Only the *one* real
owner becomes `unique_ptr`.

## The double-free trap that compiles fine

The signature bug: code that **moved** ownership between two owners by exploiting that a raw
`vector<T*>::clear()` frees nothing. Example (SMC `Add_Collisions`): push each `col_list` pointer
into a second raw-owning list, then `col_list.clear()` — ownership transferred, because `clear()`
on raw pointers doesn't delete. After the source vector becomes `vector<unique_ptr>`, the naive
port keeps `.get()` (borrow into the second owner) but now `clear()` **frees** — so the object is
owned by both and freed twice. Fix: `release()` the source `unique_ptr` at the hand-off so the
`clear()` frees nothing. **Rule: any transfer that leaned on "clear/erase of a raw pointer vector
doesn't free" must become an explicit `release()`/`std::move` once the source is owning.**

## Splitting the atomic flip into landable commits

- **Un-derive/borrow-ify the double owners first** (own commit, behavior-identical): if a class
  held the same pointers a real owner also holds, make it a plain non-owning `vector<T*>` (it was
  already relying on a clear-only teardown to avoid a double free — you're just making that
  explicit). Now only the real owner flips.
- **Range-for the read loops first** (own commit): they compile against both `T*` and
  `unique_ptr<T>`, so they land before the flip and shrink it.
- **Then the flip** (one commit): base type + subclass semantics + the compiler-driven `.get()`
  residue.

## clang-tidy on old code — useful but warty (verify each check)

`clang-tidy` (run per-file with the flags after `--`, `-header-filter` scoped to your source so it
never rewrites vendored deps) is the right tool for the mechanical modernization *around* the
ownership change, but on 2000s code several "safe" checks misfire — always diff and build:

- `modernize-loop-convert` names each range-for variable after its **container**, so a member
  container `m_foos` yields a local `m_foo` — which violates the `m_` = member convention, and an
  awkward singular (`m_properties` → `propertie`). Fix the generated names (a scoped,
  collision-guarded rename codemod), or skip the check on `m_`-prefixed containers. When you do the
  rename pass, name the handle for the **element type**, not the container word — `sprite`, not
  `obj`/`propertie`; but leave a **shared generic collection** (a base-template member like
  `cObject_Manager<T>::objects`, inherited by 12 managers each with a different `T`) named
  generically — it is a different type in each context, so anchor the type at the loop *variable*,
  not the collection. **Two codemod-mechanics lessons from doing this at scale (smc,
  2026-09-24):** (a) **key the rename on the container expression (or the enclosing class/scope), not
  a per-file-uniform assumption** — a file with heterogeneous loops (one over a particle list, one
  over an overworld list) will get one mislabeled if you assume "this file's loops are all X"; the
  smc pass misfired exactly there and had to be redone container-keyed. (b) The codemod only
  **generates** the diff — a human picks each name and eyeballs each hunk, because the *choice* is
  judgment, not mechanical (the collision guard catches shadowing a param/local, but not a wrong-
  but-legal name).
- `modernize-use-equals-default` will **botch** an empty copy constructor with a member-init list
  (emits `: , = default;`, won't compile) and will rewrite a hand-written `operator=` to
  `= default` — a copy/assign **semantics** change. Keep its destructor/default-ctor conversions;
  revert the copy/move/assignment ones.
- `modernize-use-emplace`, `-use-nullptr`, `-use-using`, `-use-bool-literals`, `-use-override` are
  reliably safe on such code.
- Skip `-use-auto` and `-redundant-void-arg` unless the maintainer wants that style churn.

## See also

- `print-debugging.md` — the oracle-driven method this is an instance of (the compiler + the
  runtime smoke are the two oracles).
- `code-style-conventions.md` — the surrounding C++ style rules.
