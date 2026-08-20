# Verify the provider-suppression fix on the airgapped system

**Status:** open — waiting on access to the airgapped machine
**Priority:** 5
**Difficulty:** 2
**Started:** 2026-08-20

## Goal

Confirm, **on the actual airgapped system** where the ~15–20-model symptom was first seen, that the
implemented fix makes Crush offer **only** the local model — no built-in catalog, no onboarding picker
— and that it generates. The fix is implemented and verified at the config level in the sandbox
(`crush models` dropped 1532 → 1), but the real-world, offline confirmation could not be done here (this
sandbox can't reach the host's SSH tunnel). See the archived implementation task:
`tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md`.

## What was implemented (what you're verifying)

- `client/entrypoint/crushrc`: `option default-providers false` + explicit `model add
  muse-glimmer/muse-glimmer --context-window 32768` + `model large|small` selections.
- `server/Makefile`: `MODEL_ALIAS ?= muse-glimmer` + `--alias $(MODEL_ALIAS)` on `serve`.

## Steps (on the airgapped system)

- [ ] **Deploy the new config.** Rebuild the client image so the new crushrc is baked
      (`cd client && make image`), or otherwise get the updated `crushrc` to
      `~/.config/crush/crushrc` on that machine.
- [ ] **Restart the server with the alias** so `/v1/models` reports `muse-glimmer`: re-run `make serve`.
- [ ] **Config check (no picker, no catalog):** with the endpoint reachable, run `crush models` — expect
      **only** `muse-glimmer/muse-glimmer`. Then launch `crush` and confirm it lands directly in a
      session using Muse Glimmer with **no** model picker and **none** of the ~15–20 catalog models.
- [ ] **Offline-robustness check:** launch `crush` **before** the server/tunnel is up. It must still
      show only the local model (the explicit-model pin means no discovery dependency), rather than
      falling into the onboarding catalog. This is the exact case that failed before.
- [ ] **Generation check:** send a prompt; confirm it responds via Muse Glimmer.

## Done when

All boxes checked on the airgapped machine. If any step still shows the catalog, capture the machine's
actual `crush.json`/`crushrc` and `crush models` output and reopen the implementation task — the
mechanism analysis in `tasks/reference/crush-capabilities.md` ("Provider & model selection") lists what
to check (is `disable_default_providers` actually set? does the provider have models?).

## Cross-links

- `tasks/archive/2026/08/20/suppress-embedded-provider-catalog.md` — the implementation + root cause.
- `tasks/reference/crush-capabilities.md` — the durable mechanism (catalog / `disable_default_providers`
  / discovery-deletes-provider).
