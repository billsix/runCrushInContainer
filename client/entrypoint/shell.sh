#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
# What `make shell` runs. Barebones: land in the mounted project and remind the user how to
# reach the model. No auth, no conventions layering — that's deferred (see the task docs).
cd /work 2>/dev/null || cd /

printf '\n\033[36m[runCrushInContainer]\033[0m Crush is on your PATH. Before starting it, make\n'
printf '  sure the SSH tunnel to the Mac is up \033[33mon the host\033[0m:\n'
printf '    \033[36mssh -N -L 8080:127.0.0.1:8080 you@mac-studio\033[0m\n'
printf '  then run:  \033[36mcrush\033[0m   (it auto-discovers the served model)\n\n'

exec bash
