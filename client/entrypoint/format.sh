#!/usr/bin/env bash
# Format the client's shell scripts with shfmt.
#
# Portable: runs from the client/ dir either in the built image (`make format`) or on the host
# (`cd client && ./entrypoint/format.sh`, needs shfmt on PATH). shfmt formats in place. Accumulate
# status so the gate reports ALL problems yet still fails if ANY step failed — never fail-fast
# (`set -e` would lose the report-everything property).
set -uo pipefail

status=0
shfmt -w -i 4 entrypoint/*.sh || status=1
exit $status
