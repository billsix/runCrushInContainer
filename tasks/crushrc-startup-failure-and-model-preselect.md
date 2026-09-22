# Crush wouldn't start: the crushrc `lsp add` syntax bug — and what the client should do at startup with two models

**Status:** REOPENED 2026-09-22 — **the real-machine check FAILED**: with Gemma 4 served on the Mac
(`make serve MODEL=gemma`) and Crush launched via `client/runCrushNoInternet.sh` /
`runCrushWithInternet.sh` on a freshly rebuilt image, Crush "failed to connect, it was still trying
the glimmer port" and `ctrl+l` showed Glimmer (maintainer, William Emerison Six <billsix@gmail.com>).
That is the crushrc's *fallback* branch (no port answered the probe → pin Glimmer), so the probe's
`curl` failed on the machine. **In-sandbox re-proof the same day PASSED** on the HEAD (five-port,
`try_model`-function) crushrc: vendored `v0.89.0` rebuilt offline, stub `/v1/models` on 8081 only →
`crush models` lists exactly `gemma-4/gemma-4`, `crush --debug run` dials `127.0.0.1:8081` (9×) and
never 8080. `curl` IS in the image (`00-install-minimal.sh:47`). So the crushrc + interpreter are
cleared; the cause is environmental. Leads, unverified: (1) llama-server answers `/v1/models` with
**503 "Loading model"** until the weights are loaded — `curl -f` treats that as failure, so starting
`crush` before `make probe MODEL=gemma` answers on the Mac reproduces the symptom exactly; (2) podman
forwards host `http_proxy`/`https_proxy` into the container by default (`--http-proxy=true`), and a
proxy without `no_proxy=127.0.0.1` breaks a loopback `curl` (Crush's own Go client would misbehave
too); (3) the 2 s `-m` timeout on a cold ssh channel. **Next:** instrument the probe (log each port's
curl exit + HTTP code, warn loudly on fallback) so the machine says which — proposed 2026-09-22,
awaiting go-ahead. Earlier status: implemented and proven in-sandbox 2026-09-10; **awaiting the maintainer's host rebuild** (`make -C client image`, then `crush` starts and `ctrl+l` lists two models). Created retroactively 2026-09-10 at the maintainer's request (William Emerison Six <billsix@gmail.com>) after the first real run of the 2026-09-10 image failed.
**Priority:** 2
**Difficulty:** 2
**Started:** 2026-09-10

## BLUF

The crushrc that shipped with the language-server work (commit `77e78e8`, 2026-09-10) passed several
values to one `lsp add` flag (`--root-markers pyproject.toml setup.py .git`); Crush v0.89.0 parses the
second value as a flag name and aborts config loading, so **`crush` refused to start** with
`Failed to load config … lsp add: unknown flag setup.py`. Fixed by repeating the flag per value. While
here, the maintainer's expectation for a two-model client was written down and implemented: the crushrc
now **probes both loopback ports at load and preselects whichever model is being served**. Done means
the rebuilt image starts, lands on the served model, and `ctrl+l` still offers both.

## Context — read first

- `client/entrypoint/crushrc` — the file in question (six `lsp add` lines; the probe/preselect block).
- `tasks/reference/crush-capabilities.md` § "Provider & model selection" → "Which model is active at
  startup, and what a `ctrl+l` switch does" — the v0.89.0 mechanism this task relies on (no startup
  probe, no picker with ≥1 provider, `UpdatePreferredModel` writes to the data dir, config precedence).
- `tasks/reference/crush-lsp-integration.md` §4 (the six lines, corrected) and §6 (flag syntax note).
- `tasks/archive/2026/09/10/install-language-servers-for-crush.md` — the work that introduced the bug;
  its verification tested the *servers* in throwaway containers but never loaded the crushrc through
  Crush.
- `tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md` — why models are pinned explicitly
  and discovery is off (discovery *deletes* an unreachable provider and falls into the catalog).
- Vendored source studied: `client/vendor/crush` at `v0.89.0` (`git describe --exact-match`), the same
  tag `CRUSH_TAG` pins — `internal/shellconfig/{lsp,flags,load}.go`, `internal/config/{load,store,config}.go`,
  `internal/ui/model/{ui,keys}.go`.

## What happened

1. The maintainer built the 2026-09-10 image, served a model on the Mac (server side fine), ran
   `crush` in the container, and got:
   `Failed to load config from paths [/etc/crush/crush.json /root/.config/crush/crush.json
   /root/.config/crush/crushrc /root/.local/share/crush/crush.json]: failed to load shell config
   /root/.config/crush/crushrc: executing shell config /root/.config/crush/crushrc: lsp add: unknown
   flag setup.py.`
2. Root cause, read from `internal/shellconfig/flags.go` (`parseFlagValue`): a `flagString` flag consumes
   **exactly one** token (`return v, i + 2`); `opAppend` means the flag may be **repeated** to append.
   The usage text `[--root-markers MARKER ...]` reads as a list but isn't. Crush's own test
   (`internal/shellconfig/load_test.go:145`) uses `--filetypes go --filetypes mod`. Any second bare
   token is looked up as a flag name → `unknown flag` → the whole config load fails → no Crush.
3. All six lines were affected (multiple `--filetypes` and/or `--root-markers` values); `--args server`
   / `--args start` were fine (single value).
4. Why it shipped: the LSP task proved the servers with an LSP handshake in throwaway containers
   (`tasks/adhoc/verify-language-servers-on-rhel9/`) and deferred the image rebuild to a human-gated task
   — nothing ever executed the crushrc through Crush. The cheap gate that would have caught it (build
   the vendored tree, `crush models`) is now recorded in `CLAUDE.md` › Conventions.

## What the client should do at startup — the maintainer's four questions, answered from the source

| Question | Stock Crush v0.89.0 | This client (as of 2026-09-10) |
|---|---|---|
| **Autoconfigure if only one model is being served?** | No. A pinned provider is never probed; there is no health check. With `models.large` pointing at a dead port the first message fails with `connection refused`. | **Yes, via the crushrc.** It is executed Bash (`internal/shellconfig/load.go`, same interpreter as the bash tool, 30 s `loadTimeout`), so it `curl -sf -m 2`s `127.0.0.1:8080` and `:8081/v1/models` and sets `model large`/`small` to the one that answers. Rule: **only Gemma up → Gemma; both, neither, or no `curl` → Glimmer.** |
| **Offer both models at the beginning if both are found?** | No startup picker exists once ≥1 provider is configured (`IsConfigured()` = `len(EnabledProviders()) > 0`, `config.go:720`; onboarding only when false, `ui.go:491`). A picker would have to be a code patch. | Not built; on a 36 GB Mac the two models don't fit together (~31 GB of weights), so "both up" is the rare case, and it resolves to Glimmer with the other one `ctrl+l` away. Revisit only if a bigger box serves both routinely. |
| **Switch between models mid-session?** | **Yes.** `ctrl+l` (also `ctrl+m`, `keys.go:89`) → `handleSelectModel` (`ui.go:2241`); refused only while the agent is busy; persists with `UpdatePreferredModel(ScopeGlobal, …)` and refreshes the agents in place. | Same. Caveat: that persistence goes to `~/.local/share/crush/crush.json`, which `lookupConfigs` (`load.go:917-947`) merges **after** the crushrc, so a manual switch outranks the probe — for the life of one container only (the path is on the `--rm` overlay); the next `make shell` probes again. |
| **Are all the other providers still disabled?** | The Catwalk catalog loads unless `disable_default_providers` is set. | **Yes.** `option default-providers false` is unchanged, and the build-time `PATCH_OUT_<X>` patches still remove/guard Google/Vertex, Bedrock, Azure, OpenRouter, Vercel, Hyper and Copilot (`tasks/reference/dependency-network-audit.md` §5). `crush models` lists exactly `gemma-4/gemma-4` and `muse-glimmer/muse-glimmer`. |

**Decisions (maintainer, 2026-09-10):** (1) fix the flag syntax and verify by loading the config through
the vendored build — yes; (2) probe-and-preselect over "Glimmer pinned + `ctrl+l`" — **(b) chosen**;
(3) fix the doc drift found during the same session's read-through now, not at the sweep.

## Work record (2026-09-10)

- `client/entrypoint/crushrc`: the six `lsp add` lines now repeat `--filetypes`/`--root-markers` per
  value (with a syntax-gotcha comment); the fixed `model large/small muse-glimmer` pair became the
  probe block (guarded by `command -v curl`, so a curl-less image degrades to Glimmer, never to a
  parse error); header comment updated. `client/entrypoint/shell.sh` hint updated.
- `client/entrypoint/00-install-minimal.sh`: `curl` added (the full toolchain already had it; the
  Fedora base ships it, so dnf no-ops) — a permanent, one-package image change, called out here.
- Docs: `crush-capabilities.md` (new subsection on startup selection/persistence/precedence),
  `crush-lsp-integration.md` (table + syntax note), `architecture.md` (client config bullet),
  `CLAUDE.md` (two new Conventions bullets + refreshed in-flight list), `README.md` (client paragraph).
- Drift fixed in the same session (found by the read-through, predates this task; details in the diff):
  `tools/sweep_egress_patch_combos.sh` now includes `crush-shell-history.patch` (it was the 14th
  patch and untested by the sweep); "thirteen patches" → fourteen in `architecture.md`,
  `crush-capabilities.md`, `dependency-network-audit.md` (+ its §5 row); "7 slash commands" → 8 in
  `CLAUDE.md`/`README`/`FORKING`/`container-file-layout.md`; the two baked/repo doc pairs
  (`container-file-layout.md`, `nested-podman-design.md`) re-synced byte-identical; `README`/`FORKING`
  no longer call the serving port a swappable knob and `FORKING` step 1 names the model-table
  variables; `dependency-network-audit.md` says 8080 *and* 8081; stale "deferred" comments in
  `client/Makefile` and `shell.sh`; `tools/triage_dependency_egress.py` self-path; `.keep` files in
  `tasks/adhoc`, `tasks/archive`, `tasks/reference`, `tools`; task-doc rot in
  `port-runclaude-conventions-systems.md` (archived path, real dotfiles paths, command count),
  `force-read-diversion-stack-on-session-load.md` (outdated mounted-stack premise flagged),
  `bump-crush-to-v0.90.0.md` (`Blocked on:`/`Recheck:` shape), `standardize-project-container-template.md`
  (contradictory "no items open"), `glimmer-models-and-airgap-quant-selection.md` §6 and
  `gemma-4-alongside-glimmer.md` §3 (pre-decision text flagged), `new-hardware-bringup.md` (alias per
  model).
- Left alone on purpose: the archived `2026/08/30/document-container-file-layout-and-manifest.md`
  still promises a sibling `crush.log` that was never committed (an archived record; not rewriting
  history); `crush-capabilities.md`'s 29-tool list enumerated from v0.90.0 (self-flagged there).

## Verification / done-state

**Done in the sandbox (2026-09-10):** built the vendored `v0.89.0` tree
(`GOPROXY=off go build -mod=vendor`, no patches — none touch the config parser) and ran it with the
new crushrc at a scratch `$HOME/.config/crush/crushrc`:

- `crush models` → exit 0, lists `gemma-4/gemma-4` and `muse-glimmer/muse-glimmer` (was: the
  `unknown flag setup.py` error).
- Neither port answering: `crush --debug run "Reply OK"` logged `"provider":"muse-glimmer"` and dialed
  `127.0.0.1:8080` (connection refused, as expected with no server).
- A stand-in on 8081 only (`python3 -m http.server` serving a `v1/models` file): the same run logged
  `"provider":"gemma-4"` / `"model":"gemma-4"` — the probe picked Gemma.
- `shfmt -d -i 4` clean on the touched `entrypoint/*.sh`; `+x` bits intact.

**Owed to the maintainer (human-gated):**

- [ ] `[LINUX HOST]` `make -C client image` (full image), `make -C client shell`, `crush` starts with no
      config error while the Mac serves either model.
- [ ] `[CONTAINER]` with only Gemma served: the status bar shows Gemma 4 without touching `ctrl+l`; with
      only Glimmer served: Glimmer. `ctrl+l` lists exactly the two.
- [ ] Record which model was served and the observed preselect here, then archive (this task's
      durable content already lives in `crush-capabilities.md` and `crush-lsp-integration.md`).

## Open questions

None — the three decisions above were taken by the maintainer on 2026-09-10.
