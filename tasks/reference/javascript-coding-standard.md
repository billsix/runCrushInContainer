# JavaScript coding standard (shared, cross-project)

**Reference document** — shared cross-project JavaScript standard (vanilla / ES-module JS, no framework),
the sibling of `python-coding-standard.md`, `rust-coding-standard.md`, `c-coding-standard.md`,
`cpp-coding-standard.md`. Read on demand (NOT auto-loaded). Update in place. A project's
`CLAUDE.md`/`README.md` points here and keeps its own repo-specific invariants in its additions doc.
Portable rules only; names no one project's files. (Written 2026-10-25 — William Emerison Six
<billsix@gmail.com>. Revised 2026-10-25 to make **Deno** the default gate over npm/tsc/eslint, to shrink
the npm supply-chain surface to zero for type-checking. Sourced from Deno's `deno check`/`deno lint` docs,
the TypeScript "Type Checking JavaScript Files" guidance, the eslint-plugin-jsdoc docs, and npm/Deno
supply-chain guidance; sources at the end.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep them in sync.**
> Canonical: runClaudeInContainer `tasks/reference/javascript-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted at `~/.claude/reference/javascript-coding-standard.md`.
> Copies in runCrushInContainer (github.com/billsix/runCrushInContainer): its
> `tasks/reference/javascript-coding-standard.md`, and the baked crush-client set
> `client/entrypoint/dotfiles/.config/crush/reference/javascript-coding-standard.md` (delivered to a Crush
> session at `~/.config/crush/reference/javascript-coding-standard.md`). Edit the canonical, re-copy it
> over the other two.

**The central idea:** JavaScript gets the same **"annotate every binding"** discipline as Python — but
via **JSDoc type comments**, checked by a TypeScript-grade checker in `checkJs` mode. Plain JS has no type
syntax, so types live in JSDoc (`@param` / `@returns` / `@type`). **The default gate is Deno** —
`deno check` type-checks, `deno lint` + `deno fmt` lint and format, all from **one signed binary with no
`node_modules`, no lockfile, no transitive dependencies, and npm lifecycle scripts off by default**. That
zeroes the npm supply-chain surface for the gate. npm + `tsc` + ESLint are kept below as the **fallback**
for a repo that is already npm-based. Either way the `.js` ships as-is — no transpile, no build step.

## (a) Enforced by the toolchain — treat a green type-check/lint as authority

### Default: Deno (no npm, no node_modules)

- **`deno check` type-checks the JS** with the same engine behind `tsc`. Turn JS checking on one of three
  ways: the flag **`deno check --check-js <files>`**; a file-level **`// @ts-check`** pragma; or
  project-wide **`compilerOptions.checkJs: true`** in `deno.json`. Run **strict** (`"strict": true`,
  `"noImplicitAny": true`) so an un-annotated opaque binding surfaces as an implicit-`any` error — that is
  the enforcement that makes "annotate everything" real (the JS analogue of Python's
  `check_local_annotations.py`). It emits nothing and exits non-zero on error, so it fits a gate. [Deno:
  check / TS config]
- **`deno.json`** turns it on project-wide and also configures lint + fmt:
  `{"compilerOptions": {"checkJs": true, "strict": true, "noImplicitAny": true},
  "lint": {"include": ["<src globs>"]}, "fmt": {"include": ["<src globs>"]}}`. (`target`/`module` are the
  runtime's; Deno ignores emit options.) [Deno: configuration]
- **`deno lint`** is a built-in linter for JS/TS (no plugins to install); **`deno fmt`** formats JS. Use
  `deno fmt --check` in the gate to fail on unformatted code.
- **`// @ts-expect-error` (preferred) / `// @ts-ignore`** suppress one line, **with a reason**;
  `// @ts-nocheck` opts a file out.
- **The one gap vs ESLint:** `deno lint` does **not** replicate `eslint-plugin-jsdoc`'s "every function
  must *have* a well-formed `@param`/`@returns` tag" nags. That stylistic completeness is covered by **(b)
  below as review discipline**, not a tool. What matters — *type correctness* and no implicit-`any` on an
  opaque binding — **is** fully enforced by `deno check --check-js` in strict mode. So Deno enforces the
  rule that counts; the presence-nags are the only thing traded away, and the house style + review cover
  them.

### Fallback: npm + tsc + ESLint (only when a repo is already on npm)

Use this only when a project already lives in the npm ecosystem (a bundler, an npm-published package). It
reintroduces `node_modules`, so install **safely** — see the target section.

- **`tsc --noEmit`** with `checkJs` type-checks the JS; same strict settings as above. [TS: Type Checking
  JS Files]
- **`jsconfig.json`**: `{"compilerOptions": {"checkJs": true, "strict": true, "noImplicitAny": true,
  "target": "es2022", "module": "esnext", "moduleResolution": "bundler", "noEmit": true},
  "include": ["<src globs>"]}`. (To migrate to TS later: rename to `tsconfig.json`, set `allowJs`.) [VS
  Code: Working with JS]
- **ESLint + `eslint-plugin-jsdoc`** enforces the JSDoc is present/well-formed (the nags Deno lacks). Flat
  config: `import jsdoc from 'eslint-plugin-jsdoc'; export default [jsdoc.configs['flat/recommended'], {
  files: ['**/*.js'], rules: { 'jsdoc/require-param-type':'error', 'jsdoc/require-returns-type':'error',
  'jsdoc/check-types':'error', 'jsdoc/no-undefined-types':'error' } }]`. [eslint-plugin-jsdoc]

Green checker + lint ⇒ the type rules below are satisfied mechanically — don't hand-re-review them.

## (b) Judgment calls — JSDoc types on every binding (house style)

Mirrors `python-coding-standard.md` "annotate every binding": **annotate the type of every binding, not
just function signatures** — LLM-generated JS is reviewed heavily, and plain JS shows no types, so make
them visible. (Tool-agnostic — holds under Deno or the npm fallback.)

- **Functions:** a `/** … */` block with `@param {Type} name` for every parameter and `@returns {Type}`
  (omit only for genuine `void`), plus a sentence on what it does.
- **Variables / locals:** `/** @type {Type} */` on the line above a `const`/`let` whose type the checker
  can't already infer obviously — `/** @type {HTMLButtonElement} */ const btn = document.getElementById('x');`,
  `/** @type {Move[]} */ const moves = [];`. Annotate the obvious ones too in the house style (as in
  Python). The checker infers many locals from the initializer; the ones that MUST be annotated are the
  opaque sources — a DOM lookup, `JSON.parse`, a `fetch`/IPC result, an empty `[]`/`{}` that would
  otherwise be `any[]`/`{}`.
- **Typedefs for shapes:** `@typedef {{from: number, to: number}} Move` (or `@typedef {object} Move` +
  `@property` lines), referenced by name — the JS analogue of a dataclass/struct; define once, reuse.
- **Parameterize generics / element types:** `Move[]` / `Array<Move>`, `Record<string, Recipe>`, never a
  bare `Array`/`object`/`Promise` (they degrade to `any`) — the "no bare generic" rule from Python.
- **Leave correct, obvious inference alone** (`const n = 3` is `3`/number) — "make the type visible where a
  reviewer would otherwise guess," which in JS means anything from a DOM/JSON/IPC/empty-literal source.
  **Don't fight the checker:** a JSDoc the checker rejects is wrong — fix the type, or `@ts-expect-error`
  with a reason; don't contort logic to satisfy an annotation.
- **Scope — how far to apply it:** the same whose-repo rule as every house standard (global CLAUDE.md,
  and `rust-coding-standard.md` "annotate every binding"): sweep the whole file/project only in a repo I
  maintain; in someone else's repo JSDoc-type the code I *add*, and don't restyle the rest.

## The `make type-check` target

A `.PHONY`, `## `-documented `make type-check` run in-container — the JS sibling of the Python `type-check`
target in the Makefile contract (personal overlay). Accumulate exit statuses across steps
(`s=0; cmd || s=1; … exit $s`) so one run reports all the red and fails if any step fails.

### Default (Deno) — the no-`node_modules` gate

- **Install Deno as a single pinned binary at image-build** (a pinned GitHub release / the official
  installer), baked into a committed layer so the gate runs offline — the "all third-party deps fetched at
  image-build, offline thereafter" rule. No `node_modules`, no lockfile, nothing to `npm ci`.
- The target runs **`deno check --check-js <src>`** + **`deno lint <src>`** + **`deno fmt --check <src>`**,
  statuses accumulated. `deno check` of local files needs no network. Deno **skips npm lifecycle scripts by
  default** (the supply-chain vector), so even a stray `npm:` import can't run install-time code.
- This is the recommended gate for a *new* JS surface (e.g. a vanilla, framework-free webview frontend):
  it adds one binary and zero package tree.

### Fallback (npm) — install safely when a repo is already npm-based

The supply-chain hazard: `npm install` runs dependencies' **lifecycle/postinstall scripts**, which recent
attacks (Shai-Hulud, the Nx and event-stream incidents) used to execute arbitrary code at install time. So:

- **`npm ci --ignore-scripts`** installs the pinned devDependencies (typescript, eslint,
  eslint-plugin-jsdoc) from the lockfile **without running any lifecycle script** — the arbitrary-code
  path. [DSO npm security flags; lirantal/npm-security-best-practices] The fleet already runs everything in
  an **ephemeral Fedora+podman image**, so even a defeated flag can't reach the host; pure JS tooling
  (tsc/eslint) needs no native build, so nothing legitimate is lost by skipping scripts. (If a dep ever
  genuinely needs a build, `npm rebuild <pkg>` it selectively.)
- Then **`npx tsc --noEmit`** (checkJs via `jsconfig.json`) **and** **`npx eslint .`**, statuses
  accumulated. Pin devDeps in `package.json` + commit `package-lock.json`; bake `npm ci --ignore-scripts`
  into the image build so it runs offline.
- Note: creating the committed `package-lock.json` the first time needs **one** online `npm install` to
  resolve + pin; `npm ci --ignore-scripts` is offline-only *after* the lock exists and is baked.

## Sources

- Deno — `deno check` (type-checking, `--check-js`): https://docs.deno.com/runtime/reference/cli/check/ ;
  configuration + `compilerOptions`/`checkJs`: https://docs.deno.com/runtime/fundamentals/configuration/
  and https://docs.deno.com/runtime/fundamentals/typescript/ ; `deno lint`:
  https://docs.deno.com/runtime/reference/cli/lint/ ; lifecycle-scripts-off-by-default (supply chain):
  https://docs.deno.com/examples/tutorials/npm_lifecycle_scripts/ and
  https://deno.com/blog/a-more-secure-npm
- TypeScript — "Type Checking JavaScript Files" (`checkJs` / `@ts-check` / JSDoc, the npm fallback):
  https://github.com/microsoft/TypeScript/wiki/Type-Checking-JavaScript-Files ; JSDoc-supported types:
  https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html
- VS Code — "Working with JavaScript" (jsconfig.json, `checkJs`, `@ts-check`):
  https://code.visualstudio.com/docs/nodejs/working-with-javascript
- eslint-plugin-jsdoc (flat config + rules, the npm fallback's presence-nags):
  https://github.com/gajus/eslint-plugin-jsdoc ; https://www.npmjs.com/package/eslint-plugin-jsdoc
- npm supply-chain hardening (`--ignore-scripts`, lifecycle-script risk): DSO npm security flags
  https://p1docs.dso.mil/party-bus/mission-devops/how-tos/requirements/npm-security-flags ;
  lirantal/npm-security-best-practices https://github.com/lirantal/npm-security-best-practices

## Cross-links

- `python-coding-standard.md` "annotate every binding" (the rule this mirrors) and
  `rust-coding-standard.md` "Type annotations — annotate every binding"; the whose-repo/sweep scope in the
  cross-project `CLAUDE.md`. The Makefile `type-check` target contract: the personal overlay
  (`ai-coding-conventions.personal.md`).
- `reimplementing-third-party-libraries.md` — when you'd write a vanilla JS widget (e.g. a menubar) in
  this style instead of taking a runtime dependency, Deno/npm used only to fetch the source to learn from.
