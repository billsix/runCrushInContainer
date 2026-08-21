#!/usr/bin/env bash
#
# run-live-test.sh -- prove the patched Crush recursively splices `@path` imports.
#
# RUN THIS ON THE HOST (outside the sandbox), with the model server + SSH tunnel up.
# It mounts this directory at /work in the `crushcontainer` image and runs one
# non-interactive `crush run`. This dir has a CLAUDE.md that Crush auto-loads; that
# file's only `@secret.md` line is the sole place the secret code appears, so if the
# model can state the code, the `@`-import spliced secret.md's contents in.
#
# Usage:   ./run-live-test.sh
#   Override the image or endpoint if needed:
#          IMAGE=crushcontainer HOSTNET=--network=host ./run-live-test.sh
#
# Expected: crush --version prints "v0.89.0+dirty" (the +dirty = your patch is baked in),
# and the run prints PURPLE-HeXaGON-7788 -> PASS.
set -uo pipefail

# Directory this script lives in = the fixture dir mounted at /work (CLAUDE.md + secret.md).
DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${IMAGE:-crushcontainer}"
# --network=host so 127.0.0.1:8080 in the container is the host's SSH-forwarded port.
HOSTNET="${HOSTNET:---network=host}"
# label=disable matches how `make shell` runs the container (unconfined).
SELINUX="${SELINUX:---security-opt label=disable}"
SECRET="PURPLE-HeXaGON-7788"

echo "== 1. Confirm the patched binary =="
# --entrypoint crush makes the container run `crush --version` instead of the shell.
ver="$(podman run --rm --entrypoint crush "$IMAGE" --version 2>&1)"
echo "   crush version: $ver"
case "$ver" in
    *+dirty*) echo "   OK: +dirty -> patched build is baked in." ;;
    *)        echo "   WARNING: no +dirty -> this looks like the STOCK build; the test will FAIL." ;;
esac
echo

echo "== 2. Ask the model for the secret (only present via @secret.md) =="
# -w /work sets the working dir so Crush auto-loads /work/CLAUDE.md; `run <prompt>` is
# Crush's non-interactive one-shot. No -it (not interactive), no TTY needed.
# `crush run` is non-interactive and AUTO-APPROVES all tool permissions (no --yolo needed;
# --yolo is a bare-`crush`-only flag and is rejected here). `-q` hides the spinner so the
# captured output is just the answer. `timeout 300` caps a slow/stuck run (the local model
# is ~21 tok/s and the agent may take a few steps, so allow generous time).
out="$(timeout 300 podman run --rm $HOSTNET $SELINUX \
        -v "$DIR":/work -w /work \
        --entrypoint crush "$IMAGE" \
        run -q "What is the project's secret build code? Reply with only the code." 2>&1)"
rc=$?
[ $rc -eq 124 ] && out="(timed out after 300s -- likely stuck; see notes)"
echo "   crush answered: $out"
echo

echo "== 3. Verdict =="
if printf '%s' "$out" | grep -q "$SECRET"; then
    echo "   PASS: @-import works -- secret.md was spliced in via the @secret.md line."
    exit 0
else
    echo "   FAIL: secret not found. Either the patch isn't active (see step 1), the"
    echo "         server/tunnel is down, or the context file wasn't loaded."
    exit 1
fi
