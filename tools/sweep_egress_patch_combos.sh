#!/usr/bin/env bash
# Copyright (c) 2026 William Emerison Six
# SPDX-License-Identifier: Apache-2.0
#
# Verification harness for the egress patch/flag system
# (tasks/archive/2026/08/29/implement-egress-patch-flags.md): proves that the patches in
# client/patches/ apply cleanly in ANY flag combination, reverse cleanly, and
# that the key combinations compile.
#
# WHEN TO RUN: on every CRUSH_TAG bump — after regenerating the vendored tree
# (./vendor.sh or client/entrypoint/vendor/vendor-crush.sh) and re-porting the
# patches to the new tag — and after adding or editing any patch in
# client/patches/. Keep the ALL list below in the same canonical order as
# entrypoint/03-build-crush.sh.
#
# Method, per combination:
#   1. forward-apply the selected patches in the canonical order (the same
#      order entrypoint/03-build-crush.sh uses), with `git apply --unidiff-zero`
#      (several patches use zero-context hunks because they edit the same files);
#   2. optionally `GOPROXY=off go build -mod=vendor` (BUILD_COMBOS below);
#   3. reverse-apply in reverse order (`git apply --unidiff-zero -R`);
#   4. assert the tree is byte-identical to the pristine baseline (sha256
#      manifest over every file any patch touches).
# A failure at any step aborts (set -e) — the combination that broke is the
# last one echoed.
#
# Combinations tested: every single patch alone; none; all; the audit-default
# set; the full power set of each group of patches that share files
# (coordinator/config: no-web-tools, no-sourcegraph, no-hyper; fantasy
# anthropic.go: no-google-provider, no-bedrock-aws; cmd/root.go: no-telemetry,
# no-update-providers-cmd); and a fixed set of pseudo-random mixes. Only a
# subset is compiled (builds cost ~30s each; applying is what can conflict, and
# the per-patch builds were done when each patch was authored).
#
# Run from the repo root; needs the vendored tree at client/vendor/crush
# (regenerate with ./vendor.sh or client/entrypoint/vendor/vendor-crush.sh).
set -eu

REPO_ROOT="$(pwd)"
CRUSH=client/vendor/crush
PATCHES="$REPO_ROOT/client/patches"

# Canonical application order — keep identical to entrypoint/03-build-crush.sh.
ALL=(
	crush-at-import.patch
	crush-no-update-check.patch
	no-telemetry.patch
	no-update-providers-cmd.patch
	no-web-tools.patch
	no-sourcegraph.patch
	no-google-provider.patch
	no-bedrock-aws.patch
	no-azure.patch
	no-openrouter.patch
	no-vercel.patch
	no-hyper.patch
	no-copilot.patch
)

# The audit-default set (flags at their defaults: at-import ON via Makefile,
# web-tools + sourcegraph kept, everything else patched out).
DEFAULT="crush-at-import.patch crush-no-update-check.patch no-telemetry.patch no-update-providers-cmd.patch no-google-provider.patch no-bedrock-aws.patch no-azure.patch no-openrouter.patch no-vercel.patch no-hyper.patch no-copilot.patch"

# Combinations that also get compiled.
BUILD_COMBOS=(
	"$DEFAULT"
	"${ALL[*]}"
	""
)

cd "$CRUSH"

# sha256 manifest of every file any patch touches (plus the files patches add,
# which must be ABSENT in the pristine state).
TOUCHED=$(grep -h "^diff --git" "$PATCHES"/*.patch | sed 's|^diff --git a/||; s| b/.*||' | sort -u)
manifest() {
	for f in $TOUCHED; do
		if [ -e "$f" ]; then sha256sum "$f"; else echo "ABSENT  $f"; fi
	done
}
BASELINE=$(manifest)
# Pristine copies of every touched file, for byte-level diff on failure.
SNAP=$(mktemp -d)
for f in $TOUCHED; do
	if [ -e "$f" ]; then mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; fi
done

apply_combo()   { for p in $1; do git apply --unidiff-zero "$PATCHES/$p"; done; }
reverse_combo() { local rev=""; for p in $1; do rev="$p $rev"; done
	for p in $rev; do git apply --unidiff-zero -R "$PATCHES/$p"; done; }
check_clean() {
	local now
	now=$(manifest)
	[ "$now" = "$BASELINE" ] || {
		echo "TREE NOT RESTORED after: $1" >&2
		diff <(echo "$BASELINE") <(echo "$now") >&2 || true
		for f in $TOUCHED; do
			if [ -e "$SNAP/$f" ] && [ -e "$f" ] && ! cmp -s "$SNAP/$f" "$f"; then
				echo "--- byte diff for $f:" >&2
				diff "$SNAP/$f" "$f" >&2 || true
			fi
		done
		exit 1
	}
}

# in_canonical_order <subset...>: echoes the subset sorted into canonical order.
in_order() {
	local out=""
	for p in "${ALL[@]}"; do
		case " $* " in *" $p "*) out="$out $p" ;; esac
	done
	echo "$out"
}

run_combo() { # $1 = combo (canonical order), $2 = build|nobuild
	echo "== combo [$2]: ${1:-<none>}"
	apply_combo "$1"
	if [ "$2" = build ]; then
		GOPROXY=off GOFLAGS= go build -mod=vendor -o /dev/null .
	fi
	reverse_combo "$1"
	check_clean "$1"
}

n=0
# 1. every single patch alone (apply/reverse only — each was compiled when authored)
for p in "${ALL[@]}"; do run_combo "$p" nobuild; n=$((n+1)); done

# 2. build combos: none / default / all
for c in "${BUILD_COMBOS[@]}"; do run_combo "$c" build; n=$((n+1)); done

# 3. power sets of the file-sharing groups (others at the default set), all built —
#    these are the combinations where zero-context hunks could interact.
group_powerset() { # $1..$N group members; others = DEFAULT minus group members
	local members=("$@") base="" p
	for p in $DEFAULT; do
		case " ${members[*]} " in *" $p "*) ;; *) base="$base $p" ;; esac
	done
	local total=$((1 << ${#members[@]})) i j sel
	for ((i = 0; i < total; i++)); do
		sel="$base"
		for ((j = 0; j < ${#members[@]}; j++)); do
			if ((i >> j & 1)); then sel="$sel ${members[$j]}"; fi
		done
		run_combo "$(in_order $sel)" build; n=$((n+1))
	done
}
group_powerset no-web-tools.patch no-sourcegraph.patch no-hyper.patch
group_powerset no-google-provider.patch no-bedrock-aws.patch
group_powerset no-telemetry.patch no-update-providers-cmd.patch

# 4. pseudo-random mixes (fixed seeds -> reproducible), apply/reverse only
for seed in 3 7 11 19 42 57 99 123 200 255; do
	sel=""
	for ((j = 0; j < ${#ALL[@]}; j++)); do
		if (((seed * (j + 3) * 2654435761) >> 7 & 1)); then sel="$sel ${ALL[$j]}"; fi
	done
	run_combo "$(in_order $sel)" nobuild; n=$((n+1))
done

echo "SWEEP OK: $n combinations applied, reversed, and verified byte-identical"
