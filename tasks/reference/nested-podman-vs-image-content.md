# Nested-podman capability vs. image content — why they must be decoupled

**Reference document** — the design rationale and decision record behind separating
`NESTED_PODMAN` (a run-time capability) from `FULL_TOOLCHAIN` (image content) in the
runCrushInContainer client, and the parallel principle for runClaudeInContainer. Written
2026-09-12 (William Emerison Six <billsix@gmail.com>) after a long diagnosis of "the crush
client has no language servers." Companion tasks:
`tasks/decouple-full-toolchain-from-nested-podman.md` (this repo, the implementation) and
runClaudeInContainer `tasks/scope-lean-image-to-downstream-not-sandboxes.md` (the fleet
rescope). Supersedes the framing in `tasks/reference/architecture.md` §"Two sizes" and
`CLAUDE.md` "Nested = the minimal image, automatically", both of which this decision makes
stale.

## BLUF

`NESTED_PODMAN` legitimately means two *opposite* things depending on who reads it, and the
client's `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)` conflated them — so
typing `make shell NESTED_PODMAN=1` on the host (to get nested capability) silently rebuilt
the **minimal, toolchain-less** image (no language servers), which is the opposite of what
the maintainer wanted. The fix: **image content is chosen explicitly and defaults to the full
toolchain; `NESTED_PODMAN` is purely run-time launch flags.** The minimal image's only
purpose was the *agent's* in-sandbox verification build; that use is dropped (it verifies the
wrong image anyway), so the client is always the full toolchain.

## 1. What the maintainer wants (the vision)

Confirmed from the full history of both repos (READMEs, `CLAUDE.md`, `FORKING.md`, archived
tasks):

- **The two sandboxes — runClaudeInContainer and the runCrushInContainer client — are built
  and run on the host.** They are never built nested in the maintainer's workflow. (The
  client's own docs already say so: run it on the host, not three-deep —
  `tasks/reference/nested-podman-design.md` "The depth caveat".)
- **Each must be able to build and run *other* container-per-project repos nested inside
  it** (podman-in-podman), so the agent can run a project's own `make image`/`run`/`test`.
  This is the whole point of nested support (`client/Makefile` "run podman INSIDE the client
  so Crush can build/run a project's own containers nested"; runClaude
  `tasks/archive/2026/06/07/nested-podman.md` Goal).
- **Nested support must be optional** — some hosts lack `/dev/fuse` etc., where
  `--device` would make `podman run` fail outright; default-off keeps plain `make shell`
  working everywhere (runClaude `nested-podman.md` "Hurts portability of the base command").
- **The full toolchain and nested capability are wanted at the same time.** The client is
  "the full runClaudeInContainer toolchain (~430 packages) plus Crush built from source" — a
  general dev sandbox — *and* it needs nested capability. These are independent wants, not a
  trade-off.

The two repos are deliberately parallel: runCrush "does with Crush what runClaudeInContainer
does with Claude Code." So the design principle here applies to both.

## 2. The two meanings of `NESTED_PODMAN`

The single variable carries two unrelated meanings, distinguished by *who sets it*:

1. **"Launch me nested-capable"** — set by the maintainer *typing* it at a sandbox's
   `make shell` (`make shell NESTED_PODMAN=1`). Correct effect: add `podman run` flags
   (`--device /dev/fuse`, the caps, `--security-opt unmask=ALL`, the `/var/lib/containers`
   tmpfs). Nothing about image content. This is a **run-time** concern, decided at launch.
2. **"I am running inside a nested sandbox"** — read by a *downstream* project's Makefile
   (geometricalgebra, mvp, …) from the *inherited* environment (the sandbox exports
   `-e NESTED_PODMAN=1`). Correct effect: add `--cgroups=disabled` to inner runs
   (`PODMAN_RUN_FLAGS`) and default optional build features lean so a big image fits the
   RAM-backed store. This is a **build-content** concern, and it is legitimate *for downstream
   projects the agent builds nested*.

These never collide for downstream projects, because there `NESTED_PODMAN` is only ever
*inherited*, never typed. They collide for the **sandboxes themselves**, because that is the
one place the maintainer *types* meaning #1 — and the client Makefile wrongly read it as
meaning #2.

## 3. Where the mistake was made

- **The coupling.** `client/Makefile:37`: `FULL_TOOLCHAIN ?= $(if $(filter 1,$(NESTED_PODMAN)),0,1)`.
  This makes *image content* (full vs minimal toolchain) a function of a flag whose meaning,
  when typed at `make shell`, is *run-time capability*. So `NESTED_PODMAN=1` — asked for to
  get nested capability — also flipped the image to minimal.
- **`shell: image` compounded it.** `client/Makefile:281` (`shell: image`), plus
  `shell-exec: image` and `format: image`. Because `make shell` depends on `image`, typing
  `make shell NESTED_PODMAN=1` *rebuilt* the image under `FULL_TOOLCHAIN=0` before running it.
  End result: `make shell NESTED_PODMAN=1` → rebuild minimal → run minimal nested. The
  maintainer got "minimal image + nested," never "full toolchain + nested."
- **The minimal image's real (and only) purpose was the agent's in-sandbox verification
  build**, not anything in the maintainer's workflow. The full client image is ~22.3 GB and
  does not fit the RAM-backed nested store (it failed to *commit* even in a 32 GB store; a
  `remount,size=50g` was needed — `tasks/reference/architecture.md` "Nested-build gotcha").
  So `install-language-servers-for-crush` / `minimal-client-image` (archived 2026-09-10)
  introduced the ~1.65 GB minimal image so the *agent* could build-verify client changes
  nested without a real-machine visit. A repo-wide check found **no other rationale** — not
  faster host builds, not deployment, not airgap size.
- **Why keeping the minimal image is worse than dropping it:** a lean nested build exercises
  a *different package set* than the full image the maintainer ships, so a lean build passing
  says nothing about whether the full image builds. That is exactly how a full image missing
  `ty` (and the other language servers) went unnoticed — the confusion that started this whole
  investigation. It is a false-confidence gate, not a real one.

The symptom chain, for the record: `make shell NESTED_PODMAN=1` (host) → minimal image → the
baked crushrc still `lsp add`s six servers whose binaries aren't installed → every LSP tool
returns `no LSP client handles file`, `command -v ty` empty, and the sidebar shows the
configured servers stuck `unstarted`. (Two *other*, independent LSP bugs surfaced alongside
and are tracked separately: `tasks/lsp-python-server-not-registering.md` and
`tasks/lsp-add-root-markers-gate-startup.md` — those bite even a correct full image.)

## 4. The new design

**Principle: image content is an explicit build-time choice; `NESTED_PODMAN` is run-time
launch capability only. The two sandboxes are always built full; only *downstream* projects
go lean when nested.**

- **runCrush client:** `FULL_TOOLCHAIN ?= 1` — full toolchain always, decoupled from
  `NESTED_PODMAN`. The minimal/lean build is **removed** (its only user, the agent's
  in-sandbox verification, is dropped per §3). `NESTED_PODMAN` keeps only its run-flag block
  and the exported/inherited signal. Drop `shell: image` (and `shell-exec: image`) so
  `make shell` never rebuilds — matching runClaudeInContainer, whose `shell` has no `image`
  prerequisite and never did.
- **Result:** `make image` (full, on host) + `make shell NESTED_PODMAN=1` = full toolchain
  **and** nested capability, simultaneously — the maintainer's goal.
- **runClaudeInContainer:** already the desired shape (no `FULL_TOOLCHAIN`, no `shell: image`).
  The action there is to **not** add a `NESTED_PODMAN`-coupled minimal variant (the proposed
  `minimal-sandbox-image.md` would re-introduce exactly this bug, and reusing the
  `claudecontainer` tag would let a nested build clobber the real image).
- **Downstream projects (geometricalgebra, modelviewprojection, …): unchanged.** There
  `NESTED_PODMAN` is inherited (meaning #2), the agent genuinely builds them nested, and
  lean-when-nested + `PODMAN_RUN_FLAGS` are correct. The scoping the maintainer named — "the
  crux is the sandbox Makefiles, not the other projects" — is exactly right.
- **Fleet convention rescope:** the "optional build flags default lean when `NESTED_PODMAN=1`"
  standard (`port-lean-image-nested-convention.md` + the runClaude umbrella) applies to
  **downstream projects only, never the sandboxes themselves**. Otherwise this bug returns
  fleet-wide.

## 5. Considered and rejected

- **Keep the lean build behind an explicit, non-`NESTED_PODMAN` flag (+ a distinct tag).**
  Rejected 2026-09-12: the maintainer builds sandboxes on the host, and a lean build verifies
  the wrong image (§3). Not worth the flag/tag machinery. Re-add later if a real need appears.
- **Fix only `shell: image` (the maintainer's first instinct), leaving the coupling.**
  Insufficient alone: an explicit `make image NESTED_PODMAN=1` would still build minimal.
  Decoupling `FULL_TOOLCHAIN` is the essential fix; dropping `shell: image` is complementary
  hygiene.
- **Bake `ENV NESTED_PODMAN=1` into the image.** Long-rejected and still rejected: the signal
  must stay coupled to the launch flags, or a plain non-nested `make shell` would falsely
  advertise nested capability (runClaude `nested-podman-design.md`).

## 6. What changes, what doesn't

- **No breakage** to host builds, the airgap/vendoring flow (`make vendor`, `CRUSH_VENDORED`),
  the offline rebuild, or the RHEL-9 `ty` wheel — all are orthogonal to `FULL_TOOLCHAIN`
  (verified against the client Makefile/Dockerfile, 2026-09-12).
- **Docs to update** when the implementation lands: `CLAUDE.md` ("Nested = the minimal image,
  automatically"), `tasks/reference/architecture.md` (§"Two sizes, chosen by where it is
  built" and the nested-build gotcha), and runClaude's `nested-podman-design.md` PODMAN_RUN_FLAGS
  section (which cites the client's `FULL_TOOLCHAIN` line as "the signal can pick a build
  variant" — that generalization is withdrawn for sandboxes).
- **Related, still-open LSP issues** (independent of this): the Python `lsp add` registration
  bug and the `--root-markers` gate — see their tasks.
