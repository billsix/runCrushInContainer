# One-shot launcher scripts for the Crush client: `runCrushNoInternet.sh` / `runCrushWithInternet.sh`

**Status:** DONE 2026-09-22 — implemented + proven in-sandbox (40/40 harness checks) and run on the
real machines by the maintainer the same day (William Emerison Six <billsix@gmail.com>): "no egress
happened when I ran the script with no internet, and it did when I ran it with internet" — step 5's
egress halves, both modes. Teardown after exit was not separately reported (harness-proven). **Archive
owed** (own commit after the work commit; promote the harness to `tools/check_launchers.sh` then).
Filed 2026-09-22; go-ahead the same day. Absorbs the former
`tasks/verify-localhost-only-network-mode.md` (now `tasks/archive/2026/09/22/…`, superseded): its
end-to-end test is this task's final verification step.
**Priority:** 3 — it is the on-ramp to the mode the README already calls "recommended", and the two
halves it wires together (`LOCALHOST_ONLY=1`, the unix-socket forward) are done but unusable by anyone
who won't run `ssh` and `make` by hand in two terminals.
**Difficulty:** 3 — a few dozen lines of bash, but the ssh/socket/trap lifecycle is easy to get subtly
wrong, and the end-to-end run needs the Mac + a real SSH forward (maintainer's hands-on step).

## BLUF

Add two host-side scripts under `client/`, `runCrushNoInternet.sh` and `runCrushWithInternet.sh`, that
take `<ssh-target>` (e.g. `williamsix@macmini`) and an `EXTRA_MOUNTS` string and do **everything** as
one unit: `make image`, a per-invocation `mktemp -d`, an SSH port-forward that **blocks until it is
up**, the right `make shell` (`LOCALHOST_ONLY=1` with unix sockets + the in-container socat bridge for
the no-internet flavour; plain TCP forward for the with-internet one), and a `trap`-driven cleanup that
tears down the tunnel and the temp dir on normal exit *and* on any error/signal. Zero changes to Crush
or its baked config. "Done" = both scripts work end-to-end on the real machines (model reachable; under
no-internet, nothing else reachable), the README shows them as the one-line way in, and a reference doc
records the two network modes and the launcher design (last step).

## Context (cold-start)

Read first, in order:

1. `tasks/archive/2026/09/20/localhost-only-network-mode.md` — the mode these scripts wrap. It landed
   the `LOCALHOST_ONLY=1` toggle: `client/Makefile:138-157` (`NET_FLAGS`, `MUSE_SOCK_DIR`, the
   `/run/muse` mount) and `client/entrypoint/shell.sh:17-30` (the socat bridge: for each of
   `/run/muse/{8080..8084}.sock` present, `socat TCP-LISTEN:$port,bind=127.0.0.1,reuseaddr,fork
   UNIX-CONNECT:…`). Crush's baked crushrc probes `127.0.0.1:808x` unchanged.
2. `README.md` § "Network modes" (~line 192) — the two modes as documented today, each with the manual
   host `ssh` command the human is expected to run in a second terminal. That manual two-terminal dance
   is what this task removes.
3. `client/Makefile` user-facing knobs the scripts drive: `PROJECT ?= $(CURDIR)` (mounted at `/work`),
   `EXTRA_MOUNTS ?=` (raw `-v …` flags, line 134), `LOCALHOST_ONLY`, `MUSE_SOCK_DIR`, and the `image`
   / `shell` targets. **No Makefile change is expected** — everything the scripts need is already an
   override.
4. `tasks/reference/dependency-network-audit.md` — the enumerated egress surface (D1–D12); the
   correctness gate for the no-internet flavour (under `--network=none` Crush must need nothing but the
   model). Related decision task: `tasks/archive/2026/09/22/decide-egress-verification.md` (a passing no-internet run is
   enforced egress isolation, which partly answers it).
5. Source of the design: the sibling `whitelistnetwork` repo, `tasks/whitelist-only-network-sandbox.md`
   ("Option H": `--network=none` + unix-socket SSH forward + socat).

Current state of the code: the mode works but is **operationally fragile** in exactly the ways the
three ideas below fix — (a) the socket dir is a fixed `~/.cache/runcrush-muse-sockets`, so a socket
left behind by a killed `ssh` makes the next `ssh -L` fail with "Address already in use"; (b) the
human must start the forward *before* `make shell` and remember which `-L` form goes with which mode;
(c) nothing tears the tunnel down afterwards. Verified 2026-09-22 that `client/Makefile` already honours
`MUSE_SOCK_DIR=…`, `PROJECT=…`, `EXTRA_MOUNTS=…`, `LOCALHOST_ONLY=…` as command-line overrides.

## Goal

A person who does not want to know how any of this works runs **one command** from the directory of
the project they want Crush to work on —
`…/client/runCrushNoInternet.sh williamsix@macmini "-v /host/path:/path:z"` — and gets a Crush
session against the Mac's model with the container locked to that model only; the with-internet twin
does the same with the container on the host network. When they exit Crush (or hit ctrl-C, or the
script dies), the SSH tunnel is gone and no temp files remain.

## Design

Harvested into **`tasks/reference/client-network-modes-and-launchers.md`** (the durable copy: the
two modes, the launcher lifecycle, why each choice, gotchas, verification status). What follows is
the design as decided 2026-09-22, kept for the record.

- **Location:** `client/runCrushNoInternet.sh`, `client/runCrushWithInternet.sh`, plus a shared
  `client/runCrush-common.sh` that both `source` (they differ in ~6 lines — the `-L` form and the
  `LOCALHOST_ONLY` toggle — so one copy of the lifecycle avoids drift, same reasoning as the
  Makefile's shared `SHELL_RUN_FLAGS`). These are **host-side** scripts, so they live in `client/`,
  **not** `client/entrypoint/` (that directory is what gets copied into the image).
- **Arguments — exactly two, both required:** `$1` = `<ssh-target>` (`user@host`, passed verbatim to
  `ssh`); `$2` = the `EXTRA_MOUNTS` string, passed straight through to `make shell EXTRA_MOUNTS="$2"`.
  Fewer than two args is a usage error (a caller with nothing to mount passes `""`). No project-dir
  argument: the script passes **`PROJECT="$PWD"`** — the directory it was invoked from — because
  `make -C client` would otherwise default `PROJECT` to `client/` itself.
- **Network mode:** the no-internet flavour keeps **`--network=none`** (what `LOCALHOST_ONLY=1` does
  today). The private-podman-network alternative is logged under "Notes / decisions", not adopted.
- **Per-invocation temp dir:** `tmp=$(mktemp -d)`; the no-internet flavour passes it as
  `MUSE_SOCK_DIR="$tmp"` (the sockets land there, so a stale socket from a previous run can never
  collide — no `StreamLocalBindUnlink` workaround needed); both flavours also use it for the SSH
  control socket (below).
- **Block until the tunnel is up:** `ssh -f -N -o ExitOnForwardFailure=yes -o ControlMaster=yes
  -o ControlPath="$tmp/ctl" <-L …×5> "$target"`. `-f` returns only after authentication *and* after
  every forward is bound, and exits nonzero if any forward fails, so the script blocks exactly as long
  as needed and the password/passphrase prompt happens in the foreground before backgrounding. Then a
  belt-and-braces poll with a timeout: no-internet waits for the five `.sock` files to appear;
  with-internet waits for `127.0.0.1:8080` (or any of the five) to accept a TCP connect. Forward all
  five ports (8080 glimmer, 8081 gemma, 8082 granite, 8083 devstral, 8084 qwen); an `-L` to a port the
  Mac isn't serving still binds (it fails per-connection only), and `shell.sh` bridges only the sockets
  that exist.
- **Order of operations:** parse args → `make -C client image` (idempotent; layer-cached after the
  first build) → `mktemp -d` → install the trap → ssh (blocking) → poll → `make -C client shell …` →
  trap fires.
- **Cleanup:** `cleanup() { ssh -O exit -o ControlPath="$tmp/ctl" "$target" 2>/dev/null; rm -rf
  "$tmp"; }` with `trap cleanup EXIT` plus `INT TERM HUP` (so a signal runs it and then exits with the
  conventional status). Cleanup must be idempotent and must not fail the script if ssh is already gone.
  The `--rm` container and the in-container socat die on their own when `make shell` returns.
- **Not combinable with `NESTED_PODMAN=1`** — the scripts are host-only by construction (they run
  `podman` directly on the host); say so in the header comment.
- **Exit status:** propagate `make shell`'s exit status through the trap (capture `$?` before cleanup).

## Plan

- [x] **1. Write `client/runCrush-common.sh`** — arg parsing + usage, `make image`, `mktemp -d`, trap +
  `cleanup`, the ssh-with-ControlMaster launcher, the poll-with-timeout helper, the `make shell` call.
  Parameterised by two variables the wrapper sets: the forward spec builder (socket vs TCP) and the
  `LOCALHOST_ONLY` value.
- [x] **2. Write the two wrappers** (`runCrushNoInternet.sh`, `runCrushWithInternet.sh`): a header
  comment (what it does, the two args, the one-line example, "host-only, not nested"), set the two
  variables, `source` common, `main "$@"`. `chmod +x` all three and `git add --chmod=+x` (a `Write`
  drops the bit — see the global convention).
- [x] **3. In-sandbox verification (what CAN be proven here):** `bash -n` on all three; `shellcheck`;
  a dry run with `ssh` and `make` shadowed by stub functions/PATH shims that (a) succeed, (b) fail at
  the forward step, (c) get SIGINT mid-session — asserting in each case that the temp dir is removed
  and `ssh -O exit` was attempted; `make -n -C client shell LOCALHOST_ONLY=1 MUSE_SOCK_DIR=/tmp/x
  PROJECT=/p EXTRA_MOUNTS="-v /a:/b:z"` shows `--network=none`, the `/run/muse` mount, `/p:/work`, and
  the extra mount. Save the stub harness under `tasks/adhoc/runcrush-launcher-scripts/`.
- [x] **4. Docs:** README — make the shown `make shell` example the one-line script invocation, keep the
  manual `ssh` + `make shell` form under "Network modes" as the "what the script does" expansion;
  `client/Makefile:148` — fix the stale pointer `tasks/localhost-only-network-mode.md` →
  `tasks/archive/2026/09/20/localhost-only-network-mode.md`; `tasks/reference/architecture.md` — one
  line pointing at the scripts.
- [x] **5. Maintainer end-to-end test — egress halves confirmed 2026-09-22 (see Status) (absorbed from the folded verify task; needs the Mac):**
  1. Mac: `cd server && make serve` (and/or `make serve MODEL=gemma`).
  2. Linux host, from a project dir: `…/client/runCrushNoInternet.sh you@mac-studio.local ""`.
  3. **(a) model reachable:** inside, `curl -s http://127.0.0.1:8080/v1/models` lists the model; `crush`
     starts and generates.
  4. **(b) egress blocked** — each must FAIL inside: `curl -m5 https://example.com`,
     `curl -m5 https://1.1.1.1` (raw IP, proves it isn't just DNS), `getent hosts github.com`.
  5. Exit Crush → on the host, the temp dir is gone and no `ssh -N` to the target remains
     (`pgrep -af "ssh.*-N.*<target>"` is empty); repeat with ctrl-C mid-session and confirm the same.
  6. `…/client/runCrushWithInternet.sh you@mac-studio.local ""` → model reachable AND
     `curl https://example.com` works; same teardown check.
  7. **Fail modes to watch:** model unreachable → the socket files weren't there before `make shell`
     (poll bug) or socat didn't start (check `/run/muse/*.sock` inside); a feature that needs another
     host under `--network=none` → cross-check `tasks/reference/dependency-network-audit.md` and decide
     whether that endpoint gets allowed (then it isn't "localhost only").
- [x] **6. LAST STEP — reference doc (written 2026-09-22):** `tasks/reference/client-network-modes-and-launchers.md` — what
  is TRUE about the two network modes (`--network=host` vs `--network=none` + unix-socket forward +
  socat), the launcher lifecycle (image → mktemp → blocking ssh → shell → trap), why each design choice
  (ControlMaster for teardown, `-f` + `ExitOnForwardFailure` as the "block until up" primitive,
  per-invocation temp dir vs the fixed cache dir), and the logged private-network alternative. Harvest
  this task's Design + Notes into it, slim this task to a work record pointing at it, then archive
  (own commit, after the work commit).

## Work record (2026-09-22)

- Files: `client/runCrush-common.sh`, `client/runCrushNoInternet.sh`, `client/runCrushWithInternet.sh`
  (all `+x`); harness `tools/check_launchers.sh` (run from anywhere:
  `bash tools/check_launchers.sh` → `ALL PASS`, 40 checks); docs:
  README (launchers lead the Client section; "Network modes" points at the reference doc),
  `client/Makefile` + `client/entrypoint/shell.sh` (stale `tasks/localhost-only-network-mode.md`
  pointers → the reference doc), `tasks/reference/architecture.md` (two one-liners), and the new
  `tasks/reference/client-network-modes-and-launchers.md`.
- No Makefile logic change: `PROJECT=`, `EXTRA_MOUNTS=`, `LOCALHOST_ONLY=`, `MUSE_SOCK_DIR=` were
  already command-line overrides.
- Two harness mistakes found and fixed in the same unit: (a) `command make` still resolved to the
  PATH shim (`command` bypasses functions, not PATH) — the `make -n` render now uses the real make
  captured before the shim is prepended; (b) the SIGINT case returned 0 because an `&` child of a
  non-interactive shell has SIGINT ignored (bash's async-child rule; confirmed via
  `/proc/self/status` SigIgn) — the case now launches under `set -m`, and the same launcher exits
  130. Recorded as a gotcha in the reference doc.
- shellcheck: clean with `-x`; the wrappers carry `# shellcheck source-path=SCRIPTDIR` so the
  shared body is followed from any cwd.
- Archive when step 5 passes: own commit after the work commit. The harness is a re-runnable
  regression gate for scripts that will be edited, so it is **promoted to `tools/check_launchers.sh`**
  at archive time rather than `git rm`'d (maintainer left this to discretion, 2026-09-22).
- **Found during the maintainer's run, NOT a launcher defect:** with Gemma served on the Mac, Crush
  pinned Muse Glimmer (8080) and failed to connect — the crushrc probe found no live port and took its
  fallback. Tracked in `tasks/crushrc-startup-failure-and-model-preselect.md` (real-machine run
  FAILED; in-sandbox re-proof of the HEAD crushrc PASSED).

## Notes / decisions

- **2026-09-22 — `--network=none` kept; private podman network logged, not adopted** (maintainer:
  "keep it as network=none for now, but log the idea"). The idea: run the client on a private podman
  network (`podman network create --internal …`) instead of `--network=none`, still reaching the model
  through the unix socket + socat. Why not now: for a single container the socket is a *file*, not a
  network path, so `--network=none` already gives true egress denial with nothing to configure; a
  private network only earns its keep if a second container must talk to the client (or if a TCP path
  to `host.containers.internal` is ever required — the whitelistnetwork writeup's fallback), and a
  non-`--internal` private network still routes out via podman's gateway. Revisit if either need
  appears.
- **2026-09-22 — no project-dir argument; `PROJECT="$PWD"`** (maintainer: "`<ssh-target>` and no
  projectdir"). Rationale in Design.
- **2026-09-22 — `$2` (`EXTRA_MOUNTS`) is required, "for now at least"** (maintainer). Making it
  optional later is a one-line change to the usage check.
- **2026-09-22 — shared `runCrush-common.sh`** rather than two standalone copies (maintainer: "sure").
- **2026-09-22 — folded `tasks/verify-localhost-only-network-mode.md` into Plan step 5** (maintainer:
  "sure"); the old task is archived as superseded, its content lives here.
- **Why `mktemp -d` and not `StreamLocalBindUnlink=yes`:** unlink-on-bind hides the stale socket but
  still leaves the fixed dir shared across concurrent invocations (two sessions would fight over the
  same paths); a fresh dir per run makes concurrent sessions and crash recovery both trivially correct.

## Open questions

None — all four design questions were answered 2026-09-22 (see Notes / decisions).
