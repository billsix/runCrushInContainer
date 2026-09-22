#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# Shared body of the two one-shot Crush launchers, runCrushNoInternet.sh and
# runCrushWithInternet.sh. SOURCED by them, never run directly. Host-side: it runs `ssh`, `make`
# and therefore `podman` on the Linux host, so it is not for use inside a container and not
# combinable with NESTED_PODMAN=1. The wrapper sets RUNCRUSH_LOCALHOST_ONLY (1 = no internet,
# 0 = with internet) before sourcing this, then calls runcrush_main "$@".
#
# Lifecycle, in order (design + rationale: tasks/reference/client-network-modes-and-launchers.md):
#   1. `make image`   — idempotent: layer-cached after the first build (the first build of the
#                       ~22 GB toolchain takes a while; later runs return in seconds).
#   2. `mktemp -d`    — one private dir per invocation for the SSH control socket and, in
#                       no-internet mode, the forwarded model sockets. A fresh dir each run is what
#                       makes a stale socket from a crashed session impossible (the fixed ~/.cache
#                       dir that `make shell LOCALHOST_ONLY=1` defaults to fails with "Address
#                       already in use" after an unclean exit).
#   3. ssh, BLOCKING  — `ssh -f -N -o ExitOnForwardFailure=yes`: `-f` returns only after
#                       authentication AND after every -L forward is bound, nonzero if any forward
#                       fails, so it is the "block until the tunnel is up" primitive, and the
#                       password/passphrase prompt happens here in the foreground before ssh
#                       backgrounds itself. ControlMaster gives the tunnel a handle ($tmp/ctl) that
#                       cleanup closes with `ssh -O exit` — no pid hunting.
#   4. poll           — belt and braces: wait up to CONNECT_TIMEOUT s for the forwards to be
#                       observable (the .sock files in no-internet mode; a TCP accept on the first
#                       port in with-internet mode).
#   5. `make shell`   — PROJECT=$PWD (the dir the launcher was run from — NOT client/, which is
#                       what `make -C client` would default to), EXTRA_MOUNTS from $2, and the
#                       mode's LOCALHOST_ONLY / MUSE_SOCK_DIR.
#   6. trap → cleanup — on normal exit, on `make shell` failing, and on INT/TERM/HUP: close the
#                       tunnel (`ssh -O exit`), remove the temp dir, exit with the failing step's
#                       status. The --rm container and its in-container socat bridge die on their
#                       own when `make shell` returns.
set -eu

# One port per model (server/Makefile MODEL_PORT_<m>): 8080 glimmer, 8081 gemma, 8082 granite,
# 8083 devstral, 8084 qwen. All five are forwarded regardless of which the Mac serves: an -L to a
# port nothing listens on still binds locally (it only fails per-connection), and shell.sh
# bridges only the sockets that exist.
MODEL_PORTS="8080 8081 8082 8083 8084"
CONNECT_TIMEOUT=30

client_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
tmp=""
target=""
fwd=()

usage() {
    cat >&2 <<EOF
usage: $(basename "$0") <ssh-target> <extra-mounts>

  <ssh-target>    user@host of the machine serving the model(s), e.g. williamsix@macmini;
                  passed verbatim to ssh, so ~/.ssh/config aliases work.
  <extra-mounts>  REQUIRED: extra podman bind mounts for the container, as one string of
                  -v flags, e.g. "-v /host/path:/path:z"; pass "" for none. Use ":z" or no
                  label, never ":Z" (see EXTRA_MOUNTS in client/Makefile).

The directory you run this from is mounted at /work (the project Crush works on).
EOF
    exit 2
}

# Runs once, on every exit path. Idempotent (the trap is cleared first), and never fails the
# script itself: a tunnel that is already gone is fine.
cleanup() {
    local status=$?
    trap - EXIT INT TERM HUP
    if [ -n "$tmp" ]; then
        if [ -S "$tmp/ctl" ]; then
            echo "[runCrush] closing the SSH tunnel to $target" >&2
            ssh -q -o ControlPath="$tmp/ctl" -O exit "$target" 2>/dev/null || true
        fi
        rm -rf "$tmp"
    fi
    exit "$status"
}

# Fills the global array `fwd` with the five -L flags in the mode's form.
build_forward_flags() {
    local port
    fwd=()
    for port in $MODEL_PORTS; do
        if [ "$RUNCRUSH_LOCALHOST_ONLY" = 1 ]; then
            fwd+=(-L "$tmp/$port.sock:127.0.0.1:$port")
        else
            fwd+=(-L "127.0.0.1:$port:127.0.0.1:$port")
        fi
    done
}

tunnel_is_up() {
    local port
    if [ "$RUNCRUSH_LOCALHOST_ONLY" = 1 ]; then
        for port in $MODEL_PORTS; do
            [ -S "$tmp/$port.sock" ] || return 1
        done
        return 0
    fi
    # bash's /dev/tcp: a connect proves ssh is listening on the first port (the forward itself
    # is lazy — ssh reaches the Mac per client connection — so this says nothing about the model).
    port=${MODEL_PORTS%% *}
    (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null
}

wait_for_tunnel() {
    local deadline=$((SECONDS + CONNECT_TIMEOUT))
    until tunnel_is_up; do
        [ "$SECONDS" -lt "$deadline" ] || return 1
        sleep 1
    done
}

runcrush_main() {
    [ "$#" -eq 2 ] || usage
    target=$1
    local extra_mounts=$2
    case "$target" in ""|-*) usage ;; esac

    # Traps first, so an interrupt anywhere below (even during `make image`, when there is
    # nothing to clean yet) still exits through cleanup with the conventional status.
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    trap 'exit 129' HUP

    echo "[runCrush] 1/3  make image (cached after the first build)" >&2
    make -C "$client_dir" image

    tmp=$(mktemp -d)
    build_forward_flags
    echo "[runCrush] 2/3  SSH tunnel to $target (returns once every forward is bound)" >&2
    if ! ssh -f -N \
            -o ExitOnForwardFailure=yes \
            -o ControlMaster=yes -o ControlPath="$tmp/ctl" \
            "${fwd[@]}" "$target"; then
        echo "[runCrush] ssh could not open the tunnel. Is $target reachable? In with-internet" >&2
        echo "[runCrush] mode, 'Address already in use' means another ssh -L already holds one" >&2
        echo "[runCrush] of ports $MODEL_PORTS on this host — close it first." >&2
        exit 1
    fi
    if ! wait_for_tunnel; then
        echo "[runCrush] the tunnel did not become reachable within ${CONNECT_TIMEOUT}s" >&2
        exit 1
    fi

    if [ "$RUNCRUSH_LOCALHOST_ONLY" = 1 ]; then
        echo "[runCrush] 3/3  make shell LOCALHOST_ONLY=1 (--network=none: the model only)" >&2
    else
        echo "[runCrush] 3/3  make shell (--network=host: the model + the internet)" >&2
    fi
    make -C "$client_dir" shell \
        PROJECT="$PWD" \
        EXTRA_MOUNTS="$extra_mounts" \
        LOCALHOST_ONLY="$RUNCRUSH_LOCALHOST_ONLY" \
        MUSE_SOCK_DIR="$tmp"
}
