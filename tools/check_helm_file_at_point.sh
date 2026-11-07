#!/bin/bash
# Check that an Emacs config's C-x C-f (helm-find-files) prefills a
# repo-root-relative file name at point with the real file: the
# helm-ff-guess-ffap-filenames setting every vendored helm.el carries.
# Runs the ERT suite in check_helm_file_at_point.el headless, loading helm from
# the config's vendored elpa/ and then the config's helm.el.
#
#   bash tools/check_helm_file_at_point.sh <path to a .emacs.d with elpa/ and helm.el>
#
# Exit status: 0 when all cases pass. Needs `emacs` and `git` on PATH.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "$#" -eq 1 ] || { echo "usage: $0 <path to .emacs.d>" >&2; exit 2; }
emacsd="$(cd "$1" && pwd)"
[ -f "$emacsd/helm.el" ] || { echo "no helm.el in $emacsd" >&2; exit 2; }
ls -d "$emacsd"/elpa/helm-[0-9]* >/dev/null 2>&1 || { echo "no vendored helm in $emacsd/elpa" >&2; exit 2; }
exec emacs --batch -Q \
    --eval "(setq bill/test-elpa \"$emacsd/elpa\" bill/test-subject \"$emacsd/helm.el\")" \
    -l "$here/check_helm_file_at_point.el" -f ert-run-tests-batch-and-exit
