# Lean 4 / Mathlib proof methodology — coordinates first, then leaf constructs

**What this is:** cross-project methodology for machine-checking mathematics in **Lean 4 + Mathlib**,
distilled from a from-scratch geometric-algebra proof development (github.com/billsix/geometricalgebra,
the `proofs/` Lean layer). It is the Lean analogue of `python-coding-standard.md` and
`cpp-ownership-migration.md` in this repo — the transferable "how to work" lessons, not any one
project's theorems. Read it before starting or extending a Lean formalization.

**Status:** first draft, 2026-09-29 (William Emerison Six <billsix@gmail.com>), distilled from the
gacalc versor / projection / algebra-law session.

## The core workflow: coordinates first, then generalize to leaf constructs

The workflow that worked, and the one to repeat:

1. **Prove it concretely, in coordinates, first.** Model each object as a coordinate structure (one
   field per component, `@[ext]`), define the operations by their explicit formulas, and prove the
   first theorems by `simp only [defs]; ext <;> ring` (or `field_simp; ring`). This gets a **green,
   trusted result fast** — you are certain the math is right before investing in abstraction. It is the
   Lean form of "make it work, then make it clean."
2. **Then lift the recurring coordinate facts into named "leaf" lemmas**, and re-prove the higher
   results *structurally* on top of them (`rw`/`exact` chains, no coordinates). The coordinate proofs
   become the **bridge**, isolated in a few named lemmas; everything above reads as algebra.

This two-phase rhythm is deliberate: the coordinate phase de-risks the mathematics; the leaf phase
makes the development legible, general, and maintainable. Do **not** try to be abstract from the start
— you will fight the prover about facts you have not yet confirmed are true.

## Leaf vs. structural — the architecture

- **Leaf lemmas** connect a definition to its coordinate representation. Proved **once** by
  `ext <;> ring` / `field_simp`: the operation tables, bilinearity/symmetry/antisymmetry of the
  bilinear forms, "magnitude-squared of a basis object = sum of squares," a fundamental split
  (`product = innerpart + outerpart`), etc. There is nothing below them; they are *meant* to touch
  coordinates.
- **Structural layer** — everything built on the leaves — should be **coordinate-free**: `rw` chains
  over the leaf lemmas and prior results. If a high-level theorem is still doing `ext <;> ring`, ask
  whether a leaf + a structural rewrite would say it better.

**The named-leaf discipline (important):** when you find yourself re-deriving the same coordinate fact
inline in proof after proof (`have h : normSq (vec a) = a₁²+… := by simp; ring`), stop and **make it a
named leaf lemma** (`normSq_vec`), then reuse it. Duplicated inline coordinate derivations are the
Lean smell equivalent of copy-pasted code. Periodically **index the leaves** in a reference doc and
sweep the proofs to replace inline re-derivations with the named lemma.

**Don't invent redundant leaves.** Before adding a leaf, check it is not the *same primitive* under a
different name — e.g. "a vector dotted with itself" is just its *squared magnitude*; add the
magnitude-squared leaf and route the self-dot through it, rather than two lemmas with the same RHS.
Prefer phrasing nondegeneracy hypotheses in the primitive that is actually the concept (`|a|² ≠ 0`),
not an equivalent-but-different expression (`a·a ≠ 0`).

## Correct-by-construction from an oracle

If the project already has a trusted reference implementation (a test oracle, a slow-but-obvious
version), **derive the Lean definitions mechanically from it** rather than hand-transcribing formulas:
run the oracle on fully-symbolic inputs, print each output coordinate, and transcribe verbatim. Then
prove small "confirmation" lemmas (the multiplication table, `I² = −1`, …) that independently check the
transcription. This makes the Lean layer correct-by-construction against the oracle — the same
principle as `codegen-conventions.md` (structured output, parity harness). Keep the derivation script
as a promoted tool, not a throwaway, if it generalizes (e.g. parameterized by dimension/size).

## Representation choice

Model the carrier as a **coordinate structure with `@[ext]`**, and expose distinguished elements as
**genuine elements of the type**, not as raw scalars — e.g. a basis vector is a value of the algebra,
matching how Mathlib's `CliffordAlgebra` maps `ι Q : M →ₗ CliffordAlgebra Q`. Do the standalone
construction yourself and map to the Mathlib general theory only for the **equivalence** direction; a
from-scratch proof plus a pointer to the general result is more instructive than citing the library
theorem as the proof.

## `field_simp` / `ring` / `simp` gotchas (all hit in practice)

- **Denominator matching.** `field_simp` needs the nonzero fact in the form it normalizes to (usually
  `^2` sums). Provide `h : … ^ 2 + … ≠ 0` (not the raw `a*a` form). If two *different* denominators
  appear, **unify them first** (prove they are equal, rewrite one to the other) — otherwise
  `field_simp` cross-multiplies and the degree blows up (seen: a degree-8 `ring` timeout).
- **Degree blow-up → prove for a literal, then instantiate.** A coordinate identity about a *derived*
  object (e.g. one whose entries are themselves products) can blow up. Prove it for a **fresh literal**
  (free low-degree variables), then instantiate at the derived object — the proof is done once at low
  degree and instantiation is free.
- **`reverse`/negation emits `-0`.** `simp` won't reduce `√(… - 0 …) = √(… 0 …)`; peel with
  `congr 1; ring`.
- **Name clashes with Mathlib.** Your algebra-law lemmas (`mul_assoc`, `mul_one`, `smul_smul`,
  `one_smul`, `mul_smul`, …) share names with Mathlib's ℝ/general versions. **Fully-qualify** yours
  (`MyNamespace.mul_smul`) in `rw` chains, or `rw` picks the wrong one / errors ambiguous.
- **`first | t1 | t2` after `<;>` needs parentheses:** `ext <;> (first | ring | linear_combination h)`
  — without them the trailing alternative mis-groups.
- **Squared vs. `√` magnitude.** Keep proofs in the **squared** form (`⟨AÃ⟩`, no `√`) as long as
  possible — that is where the concise, `ring`-closable identities live. Introduce the `√` magnitude
  only to *state* a magnitude result; it does not help proofs.
- **Build gate: `sorry` only warns.** `lake build` treats an incomplete proof as a warning, so a bare
  build can pass with holes. Gate on a `#print axioms` / grep-for-`sorryAx` check (or scan sources for
  `sorry`/`admit`) so a hole fails the build like a red test. Pin `lean-toolchain` and the Mathlib rev;
  bake Mathlib into the image so `make lean` runs offline.

## The payoff, and its limits

Refactoring to leaves buys **legibility and generality**, not fewer *total* lines — the leaves still
cost their one coordinate proof each. Convert a proof to structural only when it is *both*
coordinate-free *and* no longer than the `ext <;> ring` it replaces; a one-line coordinate leaf is fine
as-is. The real win is that high-level theorems (isometry, angle/orientation preservation, projection
decompositions) become short `rw` chains a reader can follow, instead of opaque coordinate bashes.
