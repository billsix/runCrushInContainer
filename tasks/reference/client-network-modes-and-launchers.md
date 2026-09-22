# Client network modes and the one-shot launchers

**Reference document** — what is TRUE about how the Crush client container reaches the model (the
two network modes) and how the two launcher scripts, `client/runCrushNoInternet.sh` and
`client/runCrushWithInternet.sh`, drive a whole session as one unit. Not a task; update in place.
Written 2026-09-22 by William Emerison Six <billsix@gmail.com> (harvested from
`tasks/archive/2026/09/22/runcrush-launcher-scripts.md`; the mode itself landed 2026-09-20,
`tasks/archive/2026/09/20/localhost-only-network-mode.md`, applying "Option H" of the sibling
`whitelistnetwork` repo's `tasks/whitelist-only-network-sandbox.md`).

## The two network modes

Both land the model on `127.0.0.1:808x` *inside* the container, so Crush's baked crushrc (which
probes the five fixed ports at startup — 8080 glimmer, 8081 gemma, 8082 granite, 8083 devstral,
8084 qwen) is identical either way. **Zero Crush changes** is the design constraint both satisfy.

| | with internet (`make shell`, the bare default) | no internet (`make shell LOCALHOST_ONLY=1`) |
|---|---|---|
| podman network | `--network=host` | `--network=none` — only the container's own loopback |
| how the model arrives | the host's TCP forward `ssh -L 808x:127.0.0.1:808x` is visible at the container's `127.0.0.1` because it *is* the host's | unix sockets: host `ssh -L <dir>/808x.sock:127.0.0.1:808x`, `<dir>` bind-mounted at `/run/muse`; `shell.sh` runs one `socat TCP-LISTEN:808x,bind=127.0.0.1,reuseaddr,fork UNIX-CONNECT:/run/muse/808x.sock` per socket present |
| what else the container can reach | everything the host can | **nothing** — no DNS, no raw IP, no other host. A unix socket is a *file*, not a network path, so there is no egress to firewall |
| Makefile knobs | `NET_FLAGS ?= --network=host` | `LOCALHOST_ONLY=1` flips `NET_FLAGS` to `--network=none`, mounts `MUSE_SOCK_DIR` (default `~/.cache/runcrush-muse-sockets`) at `/run/muse`, passes `-e LOCALHOST_ONLY -e MUSE_SOCK_DIR` |

Source: `client/Makefile` (`NET_FLAGS`, `LOCALHOST_ONLY`, `MUSE_SOCK_DIR`, `LOCALHOST_ONLY_MOUNT`
in `SHELL_RUN_FLAGS`) and `client/entrypoint/shell.sh` (the socat loop). The correctness gate for
no-internet mode is that Crush needs *nothing* but the model at runtime — the enumerated egress
surface is `tasks/reference/dependency-network-audit.md` (D1–D12).

Why `--network=none` and not a private podman network: for a single container the socket path
already gives true egress denial with nothing to configure. A private network (`podman network
create --internal …`) only earns its keep if a second container must talk to the client, or if a
TCP path to `host.containers.internal` is ever required (the whitelistnetwork writeup's fallback) —
and a non-`--internal` private network still routes out via podman's gateway. Logged 2026-09-22 as
the alternative to revisit if either need appears; not adopted.

## The launchers — one command, everything as a unit

`client/runCrushNoInternet.sh <ssh-target> <extra-mounts>` and
`client/runCrushWithInternet.sh <ssh-target> <extra-mounts>` are **host-side** scripts (they run
`ssh`, `make` and therefore `podman` on the Linux host — so they live in `client/`, not in
`client/entrypoint/`, which is what gets copied into the image; and they are not for
`NESTED_PODMAN=1`). They differ in ~6 lines — the `-L` form and the `LOCALHOST_ONLY` value — so
both are thin wrappers that set `RUNCRUSH_LOCALHOST_ONLY` and `source` one shared body,
`client/runCrush-common.sh` (one copy of the lifecycle, same anti-drift reasoning as the
Makefile's shared `SHELL_RUN_FLAGS`).

Arguments — exactly two, both required: `$1` the ssh target (`user@host`, passed verbatim, so
`~/.ssh/config` aliases work); `$2` the `EXTRA_MOUNTS` string (`"-v /host/path:/path:z"`, or `""`
for none — a caller has to say so explicitly; use `:z` or no label, never `:Z`, per the
`EXTRA_MOUNTS` comment in `client/Makefile`). There is deliberately **no project-dir argument**:
the launcher passes `PROJECT="$PWD"`, the directory it was run from, because `make -C client`
would otherwise default `PROJECT` to `client/` itself.

Lifecycle (`runcrush_main` in `runCrush-common.sh`):

1. **Traps first** — `trap cleanup EXIT` plus `INT`→130, `TERM`→143, `HUP`→129, installed before
   anything else so an interrupt anywhere exits through cleanup with the conventional status.
2. **`make -C client image`** — idempotent; layer-cached after the first build (the ~22 GB
   toolchain takes a while the first time, seconds after).
3. **`tmp=$(mktemp -d)`** — one private dir per invocation. It holds the SSH control socket and, in
   no-internet mode, the five forwarded `.sock` files (it is passed as `MUSE_SOCK_DIR="$tmp"`, an
   override the Makefile already honoured — no Makefile change was needed).
4. **ssh, blocking** — `ssh -f -N -o ExitOnForwardFailure=yes -o ControlMaster=yes
   -o ControlPath="$tmp/ctl" -L … ×5 "$target"`. All five ports are forwarded regardless of
   which the Mac serves (an `-L` to a port nothing listens on still binds locally — it fails
   per-connection only — and `shell.sh` bridges only the sockets that exist). On failure the
   launcher prints a hint and exits 1.
5. **Poll** — up to 30 s for the forwards to be observable: all five `.sock` files (no-internet) or
   a TCP accept on the first port via bash's `/dev/tcp` (with-internet; this proves ssh is
   listening, nothing about the model — the forward is lazy).
6. **`make -C client shell PROJECT="$PWD" EXTRA_MOUNTS="$2" LOCALHOST_ONLY=<0|1>
   MUSE_SOCK_DIR="$tmp"`** — the interactive session. When it returns, so does the launcher.
7. **`cleanup`** — clears the traps (idempotent), `ssh -q -o ControlPath="$tmp/ctl" -O exit
   "$target"` if the control socket exists (never fails the script), `rm -rf "$tmp"`, then exits
   with the status captured on entry (so `make shell`'s status propagates, and a signal exits
   with its conventional code).

### Why each design choice

- **`ssh -f` + `ExitOnForwardFailure=yes` is the "block until the tunnel is up" primitive.** `-f`
  returns only after authentication *and* after every `-L` forward is bound, and returns nonzero
  if any forward fails; the password/passphrase prompt therefore happens in the foreground before
  ssh backgrounds itself. No sleep-and-hope, no pid to babysit. The poll in step 5 is belt and
  braces.
- **`ControlMaster` is the teardown handle.** `ssh -O exit` closes exactly the tunnel this run
  opened — no `pkill -f 'ssh -fN …'` pattern-matching that could hit someone else's tunnel (the
  README's manual recipe still uses `pkill`, which is fine for a human who knows what's running).
- **`mktemp -d` per invocation, not the fixed `~/.cache/runcrush-muse-sockets`.** A socket file
  left behind by a killed `ssh` makes the next `ssh -L <path>.sock:…` fail with "Address already
  in use". `StreamLocalBindUnlink=yes` would hide that but still share one dir across concurrent
  sessions (two would fight over the same paths); a fresh dir per run makes concurrent sessions
  and crash recovery trivially correct, and cleanup is one `rm -rf`. The fixed-dir default remains
  for hand-run `make shell LOCALHOST_ONLY=1`.
- **The with-internet flavour cannot be made collision-proof the same way**: its forwards are TCP
  ports on the host loopback, so a manual `ssh -L 8080…` already running collides.
  `ExitOnForwardFailure` turns that into a loud failure naming the port, which is the right
  behaviour; the launcher's hint says to close the other tunnel.
- **`$2` required rather than optional** (maintainer decision 2026-09-22, "for now at least"):
  the extra-mounts string is easy to forget and silently getting an unmounted path is worse than a
  usage error. Making it optional later is a one-line change to the `[ "$#" -eq 2 ]` check.

## Gotchas

- **ctrl-C during the session mostly goes to the container, not the launcher.** `make shell` runs
  `podman run -it`, which puts the terminal in raw mode and forwards ctrl-C to the container's
  foreground process as a byte; the launcher's INT trap matters during the image build and ssh
  phases, and for a `kill` from elsewhere. Either way, `make shell` returning is what triggers
  cleanup.
- **Testing the INT trap from a script needs job control.** An `&` child of a *non-interactive*
  shell starts with SIGINT ignored (bash sets `SIG_IGN` on async children when job control is
  off — visible as bit `0x2` in `/proc/<pid>/status` `SigIgn`), which makes a `trap … INT` in the
  child silently inert. The stub harness launches the SIGINT case under `set -m` so the job gets
  its own process group with default dispositions; then a group-INT behaves exactly like ctrl-C
  (launcher exits 130). Verified 2026-09-22; the naive `setsid … &` version returned 0.
- **`:Z` on the socket-dir mount.** `LOCALHOST_ONLY_MOUNT` uses `:Z`, which relabels the mounted
  dir with the container's private SELinux category. Harmless for a throwaway `mktemp -d` (it is
  deleted at exit) but it is why the `EXTRA_MOUNTS` comment says never to use `:Z` on a host
  directory you keep.
- **Not for `NESTED_PODMAN=1`** — nested image builds need network, and the launchers drive the
  host's podman directly.
- **The socket path length limit (108 bytes) is not a concern** for `mktemp -d`'s default
  `/tmp/tmp.XXXXXXXXXX/8080.sock`; it could be if `TMPDIR` points somewhere deep.

## Verification status

- **In-sandbox (2026-09-22): 40/40 checks pass** — `tools/check_launchers.sh` (run from anywhere:
  `bash tools/check_launchers.sh`; promoted from the task's ad-hoc harness at archive time because
  the launchers will be edited again) shadows `ssh` and `make` with PATH
  shims that record argv and mimic the side effects the launcher depends on (the fake ssh creates
  the `.sock` files / a real TCP listener + the ControlMaster socket; `-O exit` tears them down).
  Static: `bash -n`, `shellcheck -x`, and a `make -n` render showing `--network=none`, the
  `/run/muse` mount, `PROJECT` at `/work` and `EXTRA_MOUNTS` threaded. Lifecycle: both happy paths
  (argv exact, five forwards in the right form, tunnel closed, temp dir gone), ssh forward failure
  (exit 1, `make shell` never runs, nothing left behind), SIGINT mid-session (exit 130 + cleanup),
  `make shell` exit 7 propagated, and the three usage errors (exit 2, ssh/make never called).
- **End-to-end on the real machines (2026-09-22, William Emerison Six <billsix@gmail.com>): egress
  confirmed both ways** — "no egress happened when I ran the script with no internet, and it did when
  I ran it with internet". Teardown after exit was not separately reported (it is harness-proven). A
  passing no-internet run is *enforced* egress isolation; that is the basis of the "no standing
  runtime egress check" decision in `tasks/archive/2026/09/22/decide-egress-verification.md`.
- **Seen in the same run, not a launcher defect:** with Gemma served, Crush once pinned Muse Glimmer (the
  crushrc probe's fallback); a rebuilt image found Gemma. Cause undetermined (stale-crushrc image, or
  llama-server still loading — it answers 503 until the weights are in). Record:
  `tasks/archive/2026/09/22/crushrc-startup-failure-and-model-preselect.md`; follow-on that makes the
  probe's verdict visible before `crush` starts: `tasks/model-probe-visibility.md`.

## Related

- Mode implementation: `tasks/archive/2026/09/20/localhost-only-network-mode.md`.
- Launcher task (work record): `tasks/archive/2026/09/22/runcrush-launcher-scripts.md`.
- Egress surface: `tasks/reference/dependency-network-audit.md`; telemetry:
  `tasks/disable-crush-telemetry.md`.
- Big picture: `tasks/reference/architecture.md` § Client, § Connecting.
