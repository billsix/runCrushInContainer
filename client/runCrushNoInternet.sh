#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# One command, NO internet: run Crush against the model on your Mac with the container able to
# reach nothing but that model.
#
#   cd /path/to/the/project/you/want/crush/to/work/on
#   /path/to/runCrushInContainer/client/runCrushNoInternet.sh williamsix@macmini ""
#
#   $1  user@host of the Mac serving the model (any ssh target; ~/.ssh/config aliases work)
#   $2  extra bind mounts for the container, one string of -v flags, "" for none — REQUIRED,
#       e.g. "-v /host/data:/data:z" (use ":z" or no label, never ":Z")
#
# Does everything as one unit: builds the image if needed; SSH-forwards the five model ports to
# unix sockets in a fresh temp dir, blocking until the forward is up (and prompting for your
# password/passphrase if ssh needs one); runs `make shell LOCALHOST_ONLY=1` with this directory
# mounted at /work — the container is --network=none and reaches the model only through those
# sockets (a socat bridge inside re-exposes them as 127.0.0.1:808x, so Crush is unchanged); and
# on exit — normal, error, or ctrl-C — closes the tunnel and removes the temp dir.
# Runs on the Linux HOST only (it drives podman directly); not for NESTED_PODMAN=1.
# Twin: runCrushWithInternet.sh. Shared body: runCrush-common.sh.
RUNCRUSH_LOCALHOST_ONLY=1
# shellcheck source-path=SCRIPTDIR
# shellcheck source=runCrush-common.sh
source "$(dirname "${BASH_SOURCE[0]}")/runCrush-common.sh"
runcrush_main "$@"
