#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# One command, WITH internet: run Crush against the model on your Mac with the container on the
# host's network (it reaches the model and the internet).
#
#   cd /path/to/the/project/you/want/crush/to/work/on
#   /path/to/runCrushInContainer/client/runCrushWithInternet.sh williamsix@macmini ""
#
#   $1  user@host of the Mac serving the model (any ssh target; ~/.ssh/config aliases work)
#   $2  extra bind mounts for the container, one string of -v flags, "" for none — REQUIRED,
#       e.g. "-v /host/data:/data:z" (use ":z" or no label, never ":Z")
#
# Does everything as one unit: builds the image if needed; SSH-forwards the five model ports to
# 127.0.0.1:808x on this host, blocking until the forward is up (and prompting for your
# password/passphrase if ssh needs one) — "Address already in use" here means another ssh -L
# already holds one of those ports, close it first; runs `make shell` (--network=host) with this
# directory mounted at /work; and on exit — normal, error, or ctrl-C — closes the tunnel and
# removes its temp dir.
# Runs on the Linux HOST only (it drives podman directly); not for NESTED_PODMAN=1.
# Twin: runCrushNoInternet.sh. Shared body: runCrush-common.sh.
RUNCRUSH_LOCALHOST_ONLY=0
# shellcheck source-path=SCRIPTDIR
# shellcheck source=runCrush-common.sh
source "$(dirname "${BASH_SOURCE[0]}")/runCrush-common.sh"
runcrush_main "$@"
