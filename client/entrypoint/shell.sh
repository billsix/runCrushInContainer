#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# What `make shell` runs. Barebones: land in the mounted project and remind the user how to
# reach the model. No auth (keyless local server); the conventions layering is baked into the
# image and loaded by the crushrc, not by this script.
# Fail-fast setup (there's no heavy setup here, but this is the template convention;
# the final `exec bash` is a fresh bash not under -e). NOTE: the Dockerfile bakes this
# file at /shell.sh as a fallback, but `make shell` bind-mounts the repo copy over it
# (SHELL_RUN_FLAGS), so an edit here is live on the next launch — no `make image` needed.
# Full baked-vs-mounted map: tasks/reference/container-file-layout.md.
set -e
cd /work 2>/dev/null || cd /

# Localhost-only mode (make LOCALHOST_ONLY=1): the container runs --network=none, so it has
# ONLY its own loopback and NO route off the box. The model is bind-mounted in as unix sockets
# at /run/muse (from the host's unix-socket SSH forward); bridge each to the 127.0.0.1 port
# Crush's crushrc probes, so the model still works while the container reaches nothing else.
# socat backgrounds (the `&` returns 0, so `set -e` is fine) and dies with the --rm container.
# Set the forward up on the host BEFORE launching (the sockets must exist for the bridge). See
# tasks/localhost-only-network-mode.md.
if [ "${LOCALHOST_ONLY:-0}" = "1" ]; then
    for port in 8080 8081; do
        if [ -S "/run/muse/$port.sock" ]; then
            socat "TCP-LISTEN:$port,bind=127.0.0.1,reuseaddr,fork" \
                  "UNIX-CONNECT:/run/muse/$port.sock" &
        fi
    done
fi

# The Crush/tunnel hint is interactive-only: skip it when `make shell-exec` passes a
# script/command (args present).
if [ "$#" -eq 0 ]; then
    printf '\n\033[36m[runCrushInContainer]\033[0m Crush is on your PATH. Before starting it, make\n'
    printf '  sure the SSH tunnel to the Mac is up \033[33mon the host\033[0m:\n'
    if [ "${LOCALHOST_ONLY:-0}" = "1" ]; then
        sd="${MUSE_SOCK_DIR:-\$HOME/.cache/runcrush-muse-sockets}"
        printf '  \033[33mlocalhost-only mode\033[0m (--network=none; the container reaches ONLY the model).\n'
        printf '  Forward the model to UNIX SOCKETS on the host (not TCP):\n'
        printf '    \033[36mssh -N -L %s/8080.sock:127.0.0.1:8080 -L %s/8081.sock:127.0.0.1:8081 you@mac-studio\033[0m\n' "$sd" "$sd"
    else
        printf '    \033[36mssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 you@mac-studio\033[0m\n'
    fi
    printf '  (8080 = Muse Glimmer, 8081 = Gemma 4; forward both, serve whichever you like)\n'
    printf '  then run:  \033[36mcrush\033[0m   (it starts on whichever model answers; ctrl+l switches)\n\n'
fi

# No args -> interactive shell (as before). Args (a `-c '...'` payload from
# `make shell-exec`) -> run them after setup, in a fresh bash not under -e.
exec bash "$@"
