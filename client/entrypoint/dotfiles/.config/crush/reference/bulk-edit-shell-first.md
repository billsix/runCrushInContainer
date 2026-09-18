# Bulk edits, shell-first: discover → log → iterate → fix

Read this before a **bulk operation** — *find every instance of X across the tree, then fix each*.
The terse rule is in `~/.config/crush/CLAUDE.md` ("Ad-hoc scripts", the bulk-op paragraph); this doc
carries the command idioms and gotchas. (William Emerison Six <billsix@gmail.com>, 2026-09-18;
command idioms verified against the tool docs that day.)

## Why shell-first

Lead with a **shell discovery command**, not a Python file-walk. One `rg` call returns just the
matches, so the model is not reading every file front-to-back to work out what to fix next — which
matters most here, where the local model has a **small context window** (see `CLAUDE.md` intro). The
discovery output becomes a **worklog**: a list to iterate over, so the job proceeds like a human
doing a bulk change (grep for the instances, then handle them one by one) instead of re-reading the
tree.

The workflow is four phases, and the ad-hoc-script rules apply (`CLAUDE.md` "Ad-hoc scripts"): save
the discovery command as `tasks/adhoc/<slug>/discover.sh` and its output as a committed *snapshot*
worklog under `tasks/adhoc/<slug>/data/` (git-rm'd with the slug dir at archive). A bulk discovery
command IS substantive — its output drove the diff — so it is **exempt from "skip one-liners"**; only
an *exploratory* one-liner with no downstream artifact stays unsaved.

## Portability first (this environment)

- **Crush runs commands through an embedded POSIX-sh interpreter** (`internal/shellconfig/load.go`),
  not zsh or bash. Keep discovery/fix commands **POSIX-sh-portable**: avoid bashisms (`[[ … ]]`,
  arrays, `<(…)` process substitution). A plain `while … | …`, `$(…)`, and `for` are fine.
- **Paths repo-root- / `/work`-relative, never container-absolute.** The project is mounted at
  `/work` (`container-file-layout.md`); any `/foo/opt/…` path came from `EXTRA_MOUNTS` and is dead on
  the next launch. In a saved script derive the root: `REPO="$(cd "$(dirname "$0")/../../.." && pwd)"`
  or `git rev-parse --show-toplevel`, and address reads AND writes (the data file included) from there.
- **These images are Linux/GNU only** — GNU `sed`/`grep`/`gawk` idioms below apply as written.

## 1. Discover (machine-readable)

`rg` is present in this image (Crush's own grep tool shells out to it) and is the default: fast,
skips binaries and `.gitignore`.
- `rg -n --column 'PAT' src/` → `file:line:col:text`. `rg --vimgrep 'PAT' src/` forces exactly one
  row per match (multi-match lines otherwise collapse). `rg -l 'PAT'` = filenames only;
  `rg --json 'PAT'` = structured (per-match `line_number`, byte `start`/`end`).
- `git grep -n 'PAT' -- '*.py'` for *every tracked file* — respects the git index, so no
  `.gitignore` blind spot (rg can skip a tracked-but-ignored file).
- Spaces/newlines in names: NUL-delimit — `rg -0 -l 'PAT'`, `grep -rlZ 'PAT' . | xargs -0 …`,
  `find . -name '*.py' -print0 | xargs -0 …`.
- A *reusable* script (rg not guaranteed elsewhere) guards:
  `command -v rg >/dev/null 2>&1 || { …grep -R fallback… }`.

## 2. Log

Write the matches to `tasks/adhoc/<slug>/data/matches.txt` — the audit record and the worklist.
It is a **snapshot, not a replay driver**: its line numbers are true only at discovery time (phase 3).

## 3. Iterate & fix — never trust the saved line numbers

Saved offsets rot the instant an edit shifts a line, so:
- **Preferred — match by content, re-derived live**: `sed -i 's/exact_old/new/' f`, or context-scoped
  `sed -i '/anchor/s/old/new/' f`. No stored offset to go stale; re-running is naturally a no-op.
- **When you must use offsets** (match text ambiguous) or the edit changes a file's line count,
  process each file **bottom-up** so earlier edits don't shift not-yet-applied lines:
  `grep -n 'PAT' f | sort -t: -k1,1 -rn | while IFS=: read -r n _; do sed -i "${n}s/old/new/" f; done`
  (`tac` is the base primitive).
- **In-place tools**: `sed -i` (GNU here — BSD would need `-i ''`; moot on Linux). Multi-line /
  lookaround → `perl -0777 -pi -e 's/old/new/gs' f` (slurps the file so `.` spans newlines).
  Field/column edits → `gawk -i inplace '{…}' f`.
- **Greedy trap**: `sed`/ERE have no `.*?`; use a negated class `[^>]*` (not `.*`) to stop at the
  first delimiter.
- **Idempotent when cheap** (welcome, **not required** — the point is the worklog): anchor to a field
  that stops matching once fixed (`sed -i 's/^\(version:\).*/\1 2/' f`); guard with
  `grep -q 'PAT' f && sed -i …` so an absent pattern fails loud; beware `s/foo/foobar/g` re-matching.
  Content-matching and bottom-up are kept here as plain **correctness** measures (don't edit the
  wrong line via a stale offset), independent of whether the fix is idempotent.

## 4. Iterate the worklist safely, and verify

- Read loop: `while IFS= read -r line; do …; done < matches.txt` — `IFS=` keeps leading whitespace,
  `-r` keeps backslashes, and **redirect from the file** (not `cat … | while`), or a counter set in
  the loop vanishes in the pipeline subshell. Add `|| [ -n "$line" ]` to catch a final unterminated
  line. Resumable: move done rows into `matches.done.txt`, remaining =
  `grep -vFf matches.done.txt matches.txt`.
- **Verify by re-discovery**: the phase-1 command must now report zero matches — `rg -l 'PAT' src/`
  empty = clean; or `rg -c 'PAT' src/` before/after + `diff` to catch a partial fix. `git diff -U0`
  reviews many one-line changes tightly and makes a greedy over-match obvious.

## Gotchas

- `grep -r` prints "Binary file … matches" — use `grep -I` to skip binaries (rg does by default).
- Prefer plain `find` over `find -L` for a source sweep — `-L` follows symlinks and is slow / loops
  on symlink farms.
- `LC_ALL=C` makes grep/sed byte-wise (faster, safe on pure-ASCII source; **wrong** for a
  Unicode-sensitive substitution — `.` then matches a byte, not a character).
- Never edit a file you are reading in the same pipeline (`grep … f | sed -i … f`) — the two-phase
  discover-to-file-then-edit shape exists to avoid exactly that.

## Lifecycle (per `CLAUDE.md` "Ad-hoc scripts")

`discover.sh` + `data/` + the fix script ride the **work commit** together and are `git rm`'d in the
**archive commit** (commit 3) with the slug dir. If the fix script is promoted to `tools/`, the
one-shot data file is **not** promoted — delete it (it is a record, not a tool).
