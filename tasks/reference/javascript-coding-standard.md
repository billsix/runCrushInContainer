# JavaScript coding standard (shared, cross-project)

**Reference document** — shared cross-project JavaScript standard (vanilla / ES-module JS, no framework),
the sibling of `python-coding-standard.md`, `rust-coding-standard.md`, `c-coding-standard.md`,
`cpp-coding-standard.md`. Read on demand (NOT auto-loaded). Update in place. A project's
`CLAUDE.md`/`README.md` points here and keeps its own repo-specific invariants in its additions doc.
Portable rules only; names no one project's files. (Written 2026-10-25 — William Emerison Six
<billsix@gmail.com> — from the TypeScript "Type Checking JavaScript Files" guidance, the VS Code "Working
with JavaScript" docs, the eslint-plugin-jsdoc docs, and npm supply-chain-hardening guidance; sources at
the end.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep them in sync.**
> Canonical: runClaudeInContainer `tasks/reference/javascript-coding-standard.md`
> (github.com/billsix/runClaudeInContainer), mounted at `~/.claude/reference/javascript-coding-standard.md`.
> Copies in runCrushInContainer (github.com/billsix/runCrushInContainer): its
> `tasks/reference/javascript-coding-standard.md`, and the baked crush-client set
> `client/entrypoint/dotfiles/.config/crush/reference/javascript-coding-standard.md` (delivered to a Crush
> session at `~/.config/crush/reference/javascript-coding-standard.md`). Edit the canonical, re-copy it
> over the other two.

**The central idea:** JavaScript gets the same **"annotate every binding"** discipline as Python — but
via **JSDoc type comments**, checked by the TypeScript compiler in `checkJs` mode. Plain JS has no type
syntax, so types live in JSDoc (`@param` / `@returns` / `@type`), and **`tsc --noEmit` (with `checkJs`) +
ESLint (`eslint-plugin-jsdoc`)** are the gate — no transpile, no build step, the `.js` ships as-is.

## (a) Enforced by the toolchain — treat a green type-check/lint as authority

- **`tsc --noEmit` type-checks the JS** when `checkJs` is on. It emits nothing (`--noEmit`) — it only
  checks; the `.js` ships unchanged. TypeScript reads JSDoc types exactly as it reads `.ts` annotations.
  Run it in **strict** mode (`strict: true`, `noImplicitAny: true`) so an un-annotated opaque binding
  surfaces as an implicit-`any` error — that is the enforcement that makes "annotate everything" real (the
  JS analogue of Python's `check_local_annotations.py`, free from `tsc`). [TS: Type Checking JS Files]
- **`jsconfig.json`** turns the check on project-wide:
  `{"compilerOptions": {"checkJs": true, "strict": true, "noImplicitAny": true, "target": "es2022",
  "module": "esnext", "moduleResolution": "bundler", "noEmit": true}, "include": ["<src globs>"]}`. A
  `jsconfig.json` is a `tsconfig.json` with JS-friendly defaults; `include`/`exclude` scope which files are
  checked. (To later migrate to TS: rename to `tsconfig.json`, set `allowJs`.) [VS Code: Working with JS]
- **`// @ts-check`** at the top of a file opts a single file in without a project config; `// @ts-nocheck`
  opts one out; `// @ts-expect-error` (preferred) / `// @ts-ignore` suppress one line, **with a reason**.
- **ESLint + `eslint-plugin-jsdoc`** enforces the JSDoc is present, well-formed, and typed. Flat config:
  `import jsdoc from 'eslint-plugin-jsdoc'; export default [jsdoc.configs['flat/recommended'], { files:
  ['**/*.js'], rules: { 'jsdoc/require-param-type':'error', 'jsdoc/require-returns-type':'error',
  'jsdoc/check-types':'error', 'jsdoc/no-undefined-types':'error' } }]`. Green `tsc` + `eslint` ⇒ the
  type rules below are satisfied mechanically — don't hand-re-review them. [eslint-plugin-jsdoc]

## (b) Judgment calls — JSDoc types on every binding (house style)

Mirrors `python-coding-standard.md` "annotate every binding": **annotate the type of every binding, not
just function signatures** — LLM-generated JS is reviewed heavily, and plain JS shows no types, so make
them visible.

- **Functions:** a `/** … */` block with `@param {Type} name` for every parameter and `@returns {Type}`
  (omit only for genuine `void`), plus a sentence on what it does.
- **Variables / locals:** `/** @type {Type} */` on the line above a `const`/`let` whose type `tsc` can't
  already infer obviously — `/** @type {HTMLButtonElement} */ const btn = document.getElementById('x');`,
  `/** @type {Move[]} */ const moves = [];`. Annotate the obvious ones too in the house style (as in
  Python). TS infers many locals from the initializer; the ones that MUST be annotated are the opaque
  sources — a DOM lookup, `JSON.parse`, a `fetch`/IPC result, an empty `[]`/`{}` that would otherwise be
  `any[]`/`{}`.
- **Typedefs for shapes:** `@typedef {{from: number, to: number}} Move` (or `@typedef {object} Move` +
  `@property` lines), referenced by name — the JS analogue of a dataclass/struct; define once, reuse.
- **Parameterize generics / element types:** `Move[]` / `Array<Move>`, `Record<string, Recipe>`, never a
  bare `Array`/`object`/`Promise` (they degrade to `any`) — the "no bare generic" rule from Python.
- **Leave correct, obvious inference alone** (`const n = 3` is `3`/number) — "make the type visible where a
  reviewer would otherwise guess," which in JS means anything from a DOM/JSON/IPC/empty-literal source.
  **Don't fight the checker:** a JSDoc `tsc` rejects is wrong — fix the type, or `@ts-expect-error` with a
  reason; don't contort logic to satisfy an annotation.
- **Scope — how far to apply it:** the same whose-repo rule as every house standard (global CLAUDE.md,
  and `rust-coding-standard.md` "annotate every binding"): sweep the whole file/project only in a repo I
  maintain; in someone else's repo JSDoc-type the code I *add*, and don't restyle the rest.

## The `make type-check` target — install npm + tsc + ESLint SAFELY

The supply-chain hazard: `npm install` runs dependencies' **lifecycle/postinstall scripts**, which recent
attacks (Shai-Hulud, the Nx and event-stream incidents) used to execute arbitrary code at install time.
So install with scripts disabled:

- **`npm ci --ignore-scripts`** installs the pinned devDependencies (typescript, eslint,
  eslint-plugin-jsdoc) from the lockfile **without running any lifecycle script** — the arbitrary-code
  path. [DSO npm security flags; lirantal/npm-security-best-practices] The fleet already runs everything
  in an **ephemeral Fedora+podman image**, so even a defeated flag can't reach the host; and pure JS
  tooling (tsc/eslint) needs no native build, so nothing legitimate is lost by skipping scripts. (If a dep
  ever genuinely needs a build, `npm rebuild <pkg>` it selectively.)
- Then **`npx tsc --noEmit`** (checkJs via `jsconfig.json`) **and** **`npx eslint .`** (flat config with
  `eslint-plugin-jsdoc`). **Accumulate both exit statuses** so one run reports all the red and fails if
  either fails (the gate-script shape: `s=0; cmd || s=1; … exit $s`).
- Pin the devDependencies in `package.json` + commit `package-lock.json`; bake `npm ci --ignore-scripts`
  into the **image build** (the "all third-party deps fetched at image-build, offline thereafter" rule) so
  the type-check runs offline. The target is a `.PHONY`, `## `-documented `make type-check` run
  in-container — the JS sibling of the Python `type-check` target in the Makefile contract (personal
  overlay).

## Sources

- TypeScript — "Type Checking JavaScript Files" (the `checkJs` / `@ts-check` / JSDoc authority):
  https://github.com/microsoft/TypeScript/wiki/Type-Checking-JavaScript-Files ; JSDoc-supported types:
  https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html
- VS Code — "Working with JavaScript" (jsconfig.json, `checkJs`, `@ts-check`):
  https://code.visualstudio.com/docs/nodejs/working-with-javascript
- eslint-plugin-jsdoc (flat config + rules): https://github.com/gajus/eslint-plugin-jsdoc ;
  https://www.npmjs.com/package/eslint-plugin-jsdoc
- npm supply-chain hardening (`--ignore-scripts`, lifecycle-script risk): DSO npm security flags
  https://p1docs.dso.mil/party-bus/mission-devops/how-tos/requirements/npm-security-flags ;
  lirantal/npm-security-best-practices https://github.com/lirantal/npm-security-best-practices ;
  OpenReplay "npm supply chain defense" https://blog.openreplay.com/npm-supply-chain-defense/

## Cross-links

- `python-coding-standard.md` "annotate every binding" (the rule this mirrors) and
  `rust-coding-standard.md` "Type annotations — annotate every binding"; the whose-repo/sweep scope in the
  cross-project `CLAUDE.md`. The Makefile `type-check` target contract: the personal overlay
  (`ai-coding-conventions.personal.md`).
