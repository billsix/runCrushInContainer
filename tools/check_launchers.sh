#!/usr/bin/env bash
# Regression gate for client/runCrush{NoInternet,WithInternet}.sh — proves the launcher LIFECYCLE
# (image → mktemp → blocking ssh → poll → make shell → cleanup) without a Mac, an sshd, or
# podman: `ssh` and `make` are shadowed by PATH shims that record their argv and mimic the
# observable side effects the launcher depends on (ssh creates the forwarded unix sockets / a
# TCP listener + the ControlMaster socket; `ssh -O exit` tears them down). Cases:
#   1  no-internet, happy path      → exit 0; make argv right; sockets forwarded; tunnel closed;
#                                     temp dir gone
#   2  with-internet, happy path    → same, TCP -L form, LOCALHOST_ONLY=0
#   3  ssh forward fails            → exit 1; make shell never ran; no temp dir left behind
#   4  SIGINT mid-session           → exit 130; tunnel closed; temp dir gone
#   5  make shell exits 7           → exit 7 propagated; tunnel closed; temp dir gone
#   6  usage errors (0 args, 1 arg) → exit 2, ssh/make never called
# Plus `bash -n` + shellcheck on the three scripts and a `make -n` render of the shell target.
# Paths are relative to this script / the repo root — nothing container-absolute.
# Run from anywhere:  bash tools/check_launchers.sh   (promoted from tasks/adhoc/runcrush-launcher-scripts/ 2026-09-22)
set -u

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
client="$repo_root/client"
work=$(mktemp -d)
shim="$work/shim"
log="$work/log"
mkdir -p "$shim" "$log"
export HARNESS_LOG="$log"

status=0
pass() { echo "  ok   $*"; }
fail() { echo "  FAIL $*"; status=1; }
check() { # check <description> <command...>
    local desc=$1; shift
    if "$@"; then pass "$desc"; else fail "$desc"; fi
}

harness_cleanup() {
    # kill any listener a fake ssh left behind, then the work dir
    if [ -s "$log/listeners" ]; then
        # shellcheck disable=SC2046
        kill $(cat "$log/listeners") 2>/dev/null || true
    fi
    rm -rf "$work"
}
trap harness_cleanup EXIT

# ---- the shims ------------------------------------------------------------------------------
cat >"$shim/ssh" <<'EOF'
#!/usr/bin/env bash
# fake ssh: records argv; `-O exit` tears down; otherwise mimics `-f -N -L ...` side effects.
printf '%s\n' "$*" >>"$HARNESS_LOG/ssh.args"
ctl=""
for a in "$@"; do case "$a" in ControlPath=*) ctl=${a#ControlPath=} ;; esac; done
if printf '%s\n' "$@" | grep -qx -- '-O'; then
    echo EXIT >>"$HARNESS_LOG/ssh.events"
    if [ -s "$HARNESS_LOG/listeners" ]; then kill $(cat "$HARNESS_LOG/listeners") 2>/dev/null; : >"$HARNESS_LOG/listeners"; fi
    rm -f "$ctl"
    exit 0
fi
if [ "${FAKE_SSH_FAIL:-0}" = 1 ]; then
    echo "bind [127.0.0.1]:8080: Address already in use" >&2
    exit 255
fi
dirname "$ctl" >"$HARNESS_LOG/tmpdir"
python3 - "$ctl" <<'PY'
import socket, sys
socket.socket(socket.AF_UNIX).bind(sys.argv[1])
PY
prev=""
for a in "$@"; do
    if [ "$prev" = "-L" ]; then
        case "$a" in
            /*.sock:*)   # unix-socket forward: create the socket file
                python3 - "${a%%:*}" <<'PY'
import socket, sys
socket.socket(socket.AF_UNIX).bind(sys.argv[1])
PY
                ;;
            127.0.0.1:*) # TCP forward: a real accepting listener on that port
                port=${a#127.0.0.1:}; port=${port%%:*}
                python3 - "$port" <<'PY' &
import socket, sys
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", int(sys.argv[1]))); s.listen()
except OSError:
    sys.exit(0)   # port busy on this box: skip it (the launcher probes only the first port)
while True:
    c, _ = s.accept(); c.close()
PY
                echo $! >>"$HARNESS_LOG/listeners"
                ;;
        esac
    fi
    prev=$a
done
sleep 0.2   # let the listeners bind before the launcher polls
exit 0
EOF
cat >"$shim/make" <<'EOF'
#!/usr/bin/env bash
# fake make: records argv; `shell` optionally sleeps (for the SIGINT case) and exits as told.
printf '%s\n' "$*" >>"$HARNESS_LOG/make.args"
for a in "$@"; do
    if [ "$a" = shell ]; then
        [ -n "${FAKE_MAKE_SHELL_SLEEP:-}" ] && sleep "$FAKE_MAKE_SHELL_SLEEP"
        exit "${FAKE_MAKE_SHELL_STATUS:-0}"
    fi
done
exit 0
EOF
chmod +x "$shim/ssh" "$shim/make"
real_make=$(command -v make)   # resolved BEFORE the shim shadows it (`command` does not bypass PATH)
export PATH="$shim:$PATH"

reset_log() { rm -f "$log"/*; }
tmpdir_gone() { [ -f "$log/tmpdir" ] && [ ! -e "$(cat "$log/tmpdir")" ]; }
tunnel_closed() { grep -qx EXIT "$log/ssh.events" 2>/dev/null; }
make_shell_line() { grep -m1 ' shell ' "$log/make.args"; }

# ---- static checks ----------------------------------------------------------------------------
echo "== static"
for f in runCrush-common.sh runCrushNoInternet.sh runCrushWithInternet.sh; do
    check "bash -n $f" bash -n "$client/$f"
done
check "shellcheck (3 scripts)" shellcheck -x "$client/runCrushNoInternet.sh" "$client/runCrushWithInternet.sh" "$client/runCrush-common.sh"
render=$("$real_make" -n -C "$client" shell LOCALHOST_ONLY=1 MUSE_SOCK_DIR=/tmp/x PROJECT=/p EXTRA_MOUNTS="-v /a:/b:z" 2>&1)
check "make -n: --network=none"        grep -q -- '--network=none' <<<"$render"
check "make -n: socket dir mounted"    grep -q -- '-v /tmp/x:/run/muse' <<<"$render"
check "make -n: PROJECT at /work"      grep -q -- '-v /p:/work' <<<"$render"
check "make -n: EXTRA_MOUNTS threaded" grep -q -- '-v /a:/b:z' <<<"$render"

# ---- case 1: no-internet happy path ----------------------------------------------------------
echo "== 1 no-internet happy path"
reset_log
proj=$(mktemp -d); cd "$proj"
"$client/runCrushNoInternet.sh" fake@mac "-v /a:/b:z" >/dev/null 2>&1; rc=$?
check "exit 0 (got $rc)" [ "$rc" -eq 0 ]
check "make image called first"          bash -c 'head -1 "$1" | grep -q " image$"' _ "$log/make.args"
line=$(make_shell_line)
check "PROJECT=\$PWD"                    grep -q "PROJECT=$proj " <<<"$line"
check "EXTRA_MOUNTS passed verbatim"     grep -q -- 'EXTRA_MOUNTS=-v /a:/b:z ' <<<"$line"
check "LOCALHOST_ONLY=1"                 grep -q 'LOCALHOST_ONLY=1 ' <<<"$line"
check "MUSE_SOCK_DIR = the mktemp dir"   grep -q "MUSE_SOCK_DIR=$(cat "$log/tmpdir")\$" <<<"$line"
check "ssh: -f -N ExitOnForwardFailure ControlMaster" grep -q -- '-f -N -o ExitOnForwardFailure=yes -o ControlMaster=yes' "$log/ssh.args"
check "ssh: five unix-socket -L forwards" [ "$(grep -o -- '-L [^ ]*/808[0-4]\.sock:127.0.0.1:808[0-4]' "$log/ssh.args" | wc -l)" -eq 5 ]
check "tunnel closed (ssh -O exit)"      tunnel_closed
check "temp dir removed"                 tmpdir_gone
cd "$repo_root"; rm -rf "$proj"

# ---- case 2: with-internet happy path --------------------------------------------------------
echo "== 2 with-internet happy path"
reset_log
proj=$(mktemp -d); cd "$proj"
"$client/runCrushWithInternet.sh" fake@mac "" >/dev/null 2>&1; rc=$?
check "exit 0 (got $rc)" [ "$rc" -eq 0 ]
line=$(make_shell_line)
check "LOCALHOST_ONLY=0"                 grep -q 'LOCALHOST_ONLY=0 ' <<<"$line"
check "EXTRA_MOUNTS empty"               grep -q 'EXTRA_MOUNTS= ' <<<"$line"
check "ssh: five TCP -L forwards"        [ "$(grep -o -- '-L 127.0.0.1:808[0-4]:127.0.0.1:808[0-4]' "$log/ssh.args" | wc -l)" -eq 5 ]
check "tunnel closed"                    tunnel_closed
check "temp dir removed"                 tmpdir_gone
cd "$repo_root"; rm -rf "$proj"

# ---- case 3: ssh forward fails ----------------------------------------------------------------
echo "== 3 ssh forward fails"
reset_log
before=$(find "${TMPDIR:-/tmp}" -maxdepth 1 -name 'tmp.*' 2>/dev/null | sort)
FAKE_SSH_FAIL=1 "$client/runCrushNoInternet.sh" fake@mac "" >/dev/null 2>"$log/stderr"; rc=$?
after=$(find "${TMPDIR:-/tmp}" -maxdepth 1 -name 'tmp.*' 2>/dev/null | sort)
check "exit 1 (got $rc)"                 [ "$rc" -eq 1 ]
check "hint printed"                     grep -q 'could not open the tunnel' "$log/stderr"
check "make shell never ran"             bash -c '! grep -q " shell " "$1"' _ "$log/make.args"
check "no temp dir left behind"          [ "$before" = "$after" ]

# ---- case 4: SIGINT mid-session ---------------------------------------------------------------
echo "== 4 SIGINT mid-session"
reset_log
# Gotcha: an `&` child of a NON-interactive shell starts with SIGINT ignored (bash sets SIG_IGN
# on async children when job control is off), which makes the launcher's INT trap inert — a
# harness artifact, not a launcher bug (from a terminal, ctrl-C is a normal SIGINT to the
# foreground group). `set -m` turns job control on: the job gets its own process group and
# default signal dispositions, so the group-INT below reaches the launcher, its make, and the
# make's sleep, exactly like ctrl-C.
set -m
FAKE_MAKE_SHELL_SLEEP=30 bash "$client/runCrushNoInternet.sh" fake@mac "" >/dev/null 2>&1 &
pid=$!
set +m
for _ in $(seq 1 50); do grep -q ' shell ' "$log/make.args" 2>/dev/null && break; sleep 0.1; done
kill -INT -- "-$pid"
wait "$pid"; rc=$?
check "exit 130 (got $rc)"               [ "$rc" -eq 130 ]
check "tunnel closed"                    tunnel_closed
check "temp dir removed"                 tmpdir_gone

# ---- case 5: make shell's exit status propagates ---------------------------------------------
echo "== 5 make shell exits 7"
reset_log
FAKE_MAKE_SHELL_STATUS=7 "$client/runCrushWithInternet.sh" fake@mac "" >/dev/null 2>&1; rc=$?
check "exit 7 (got $rc)"                 [ "$rc" -eq 7 ]
check "tunnel closed"                    tunnel_closed
check "temp dir removed"                 tmpdir_gone

# ---- case 6: usage --------------------------------------------------------------------------
echo "== 6 usage"
reset_log
"$client/runCrushNoInternet.sh" >/dev/null 2>&1; rc=$?
check "no args → exit 2 (got $rc)"       [ "$rc" -eq 2 ]
"$client/runCrushNoInternet.sh" fake@mac >/dev/null 2>&1; rc=$?
check "one arg → exit 2 (got $rc)"       [ "$rc" -eq 2 ]
"$client/runCrushNoInternet.sh" -h "" >/dev/null 2>&1; rc=$?
check "-h as target → exit 2 (got $rc)"  [ "$rc" -eq 2 ]
check "ssh/make never called"            bash -c '[ ! -e "$1/ssh.args" ] && [ ! -e "$1/make.args" ]' _ "$log"

echo
[ "$status" -eq 0 ] && echo "ALL PASS" || echo "FAILURES"
exit "$status"
