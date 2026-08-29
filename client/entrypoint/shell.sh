#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# What `make shell` runs. Barebones: land in the mounted project and remind the user how to
# reach the model. No auth, no conventions layering — that's deferred (see the task docs).
# Fail-fast setup (there's no heavy setup here, but this is the template convention;
# the final `exec bash` is a fresh bash not under -e). NOTE: this shell.sh is BAKED
# into the image (COPY), not bind-mounted, so this edit takes effect after `make image`.
set -e
cd /work 2>/dev/null || cd /

# The Crush/tunnel hint is interactive-only: skip it when `make shell-exec` passes a
# script/command (args present).
if [ "$#" -eq 0 ]; then
    printf '\n\033[36m[runCrushInContainer]\033[0m Crush is on your PATH. Before starting it, make\n'
    printf '  sure the SSH tunnel to the Mac is up \033[33mon the host\033[0m:\n'
    printf '    \033[36mssh -N -L 8080:127.0.0.1:8080 you@mac-studio\033[0m\n'
    printf '  then run:  \033[36mcrush\033[0m   (it auto-discovers the served model)\n\n'
fi

# No args -> interactive shell (as before). Args (a `-c '...'` payload from
# `make shell-exec`) -> run them after setup, in a fresh bash not under -e.
exec bash "$@"
