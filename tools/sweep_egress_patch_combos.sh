#!/usr/bin/env bash
# Thin shim: the logic lives in sweep_egress_patch_combos.py (ported from this bash
# 2026-10-29; the combination sequence is byte-identical). Callers (CRUSH_TAG-bump
# checklists, the reference docs) keep using tools/sweep_egress_patch_combos.sh.
exec python3 "$(dirname "$0")/sweep_egress_patch_combos.py" "$@"
