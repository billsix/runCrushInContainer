# Crush wouldn't start: the crushrc `lsp add` syntax bug — and what the client should do at startup with two models

**Status:** complete
**Completed:** 2026-09-22
Started 2026-09-10; created retroactively that day at the maintainer's request (William Emerison Six
<billsix@gmail.com>) after the first real run of the 2026-09-10 image failed.

The crushrc shipped with the language-server work (commit `77e78e8`) passed several values to one
`lsp add` flag, so Crush v0.89.0 refused to start (`lsp add: unknown flag setup.py`). Fixed it by
repeating the flag per value, and made the crushrc probe the loopback model ports at load and
preselect whichever model is served. Confirmed on the real machine 2026-09-22 (maintainer, William
Emerison Six <billsix@gmail.com>: "I just rebuilt the container, it found gemma").

## Root cause

The maintainer's run failed with `Failed to load config … executing shell config
/root/.config/crush/crushrc: lsp add: unknown flag setup.py.` In `internal/shellconfig/flags.go`
(`parseFlagValue`), a `flagString` flag consumes exactly one token, and `opAppend` means the flag may
be **repeated**; the usage text `[--root-markers MARKER ...]` reads as a list but isn't (Crush's own
`load_test.go` uses `--filetypes go --filetypes mod`). Any second bare token is looked up as a flag
name, so the whole config load fails. All six `lsp add` lines were affected.

It shipped because the LSP task (`tasks/archive/2026/09/10/install-language-servers-for-crush.md`)
proved the servers with a handshake in throwaway containers and deferred the image rebuild, so
nothing executed the crushrc through Crush. The cheap gate (build the vendored tree, run
`crush models`) was recorded in `CLAUDE.md` › Conventions.

## Startup behaviour: the maintainer's four questions, answered from the v0.89.0 source

| Question | Stock Crush v0.89.0 | This client (as of 2026-09-10) |
|---|---|---|
| **Autoconfigure if only one model is being served?** | No. A pinned provider is never probed; with `models.large` on a dead port the first message fails with `connection refused`. | **Yes, via the crushrc**, which is executed Bash (30 s load timeout): it `curl -sf -m 2`s each port's `/v1/models` and sets `model large`/`small` to the one that answers. Rule at the time: only Gemma up → Gemma; both, neither, or no `curl` → Glimmer. |
| **Offer both models at the beginning if both are found?** | No startup picker exists once ≥1 provider is configured (`IsConfigured()`); one would need a code patch. | Not built: on the 36 GB Mac the two models don't fit together (~31 GB of weights), so "both up" is rare and resolves to Glimmer with the other one `ctrl+l` away. |
| **Switch between models mid-session?** | **Yes.** `ctrl+l` (also `ctrl+m`) → `handleSelectModel`; refused only while the agent is busy; persists via `UpdatePreferredModel(ScopeGlobal, …)`. | Same. That persistence goes to `~/.local/share/crush/crush.json`, merged **after** the crushrc, so a manual switch outranks the probe for the life of one container (the path is on the `--rm` overlay). |
| **Are all the other providers still disabled?** | The Catwalk catalog loads unless `disable_default_providers` is set. | **Yes.** `option default-providers false` plus the build-time `PATCH_OUT_<X>` patches (`tasks/reference/dependency-network-audit.md` §5). `crush models` listed exactly the two pinned models. |

Superseded: the two-port Glimmer-fallback rule became five-port autodiscovery on 2026-09-20
(`tasks/archive/2026/09/20/country-gated-model-selection.md`); the current mechanism is
`tasks/reference/crush-capabilities.md` § "Which model is active at startup".

**Decisions (maintainer, 2026-09-10):** (1) fix the flag syntax and verify by loading the config through
the vendored build — yes; (2) probe-and-preselect over "Glimmer pinned + `ctrl+l`" — **(b) chosen**;
(3) fix the doc drift found during the same session's read-through now, not at the sweep.

## Work record (2026-09-10)

- `client/entrypoint/crushrc`: the six `lsp add` lines repeat `--filetypes`/`--root-markers` per value
  (with a syntax-gotcha comment); the fixed `model large/small muse-glimmer` pair became the probe
  block, guarded by `command -v curl` so a curl-less image degrades to Glimmer rather than a parse
  error. `client/entrypoint/shell.sh` hint updated.
- `client/entrypoint/00-install-minimal.sh`: added `curl` (a permanent one-package image change; the
  Fedora base already ships it).
- Docs: `tasks/reference/crush-capabilities.md` (startup selection/persistence/precedence),
  `tasks/reference/crush-lsp-integration.md` (table + syntax note), `tasks/reference/architecture.md`,
  `CLAUDE.md`, `README.md`.
- Pre-existing drift fixed in the same session (details in the diff): `tools/sweep_egress_patch_combos.sh`
  gained the untested `crush-shell-history.patch`; patch and slash-command counts corrected across
  docs; the baked/repo doc pairs (`container-file-layout.md`, `nested-podman-design.md`) re-synced;
  serving port no longer called a knob in `README`/`FORKING`; stale "deferred" comments in
  `client/Makefile` and `shell.sh`; `tools/triage_dependency_egress.py` self-path; `.keep` files; and
  task-doc rot in several then-open tasks.
- Left alone on purpose: the archived
  `tasks/archive/2026/08/30/document-container-file-layout-and-manifest.md` still promises a sibling
  `crush.log` that was never committed (archived record); `crush-capabilities.md`'s 29-tool list from
  v0.90.0 (self-flagged there).

## Verification

**In-sandbox (2026-09-10):** built vendored `v0.89.0` (`GOPROXY=off go build -mod=vendor`, no
patches; none touch the config parser) and ran it with the new crushrc:
- `crush models` → exit 0, both models listed (was the `unknown flag` error).
- Neither port answering: `crush --debug run` used `muse-glimmer` and dialed `127.0.0.1:8080`.
- A stand-in `/v1/models` on 8081 only: the run used `gemma-4`.
- `shfmt -d -i 4` clean on the touched scripts; `+x` bits intact.

**Real machine (2026-09-22):** the rebuilt image started with no config error and, with Gemma 4
served, preselected Gemma 4 without `ctrl+l`. The `ctrl+l` listing was not separately reported.

One run earlier on 2026-09-22 had fallen back to Glimmer. An in-sandbox re-proof that day on the
five-port crushrc passed (stub on 8081 only → `crush models` listed only `gemma-4/gemma-4` and the
run dialed 8081, never 8080), so the cause was environmental and never pinned down. Leads, unverified:
llama-server answers `/v1/models` with 503 "Loading model" until loaded (which `curl -f` treats as
failure); podman forwarding a host proxy without `no_proxy=127.0.0.1`; the 2 s timeout on a cold ssh
channel. Making the probe's verdict visible was spun off as `tasks/model-probe-visibility.md`.

## Related
- `tasks/reference/crush-capabilities.md`, `tasks/reference/crush-lsp-integration.md` §4/§6.
- `tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md` — why models are pinned and
  discovery is off.
