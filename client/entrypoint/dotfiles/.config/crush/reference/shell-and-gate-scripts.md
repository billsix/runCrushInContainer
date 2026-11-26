# Shell, gate, and format scripts — full rules, incidents, and code shapes

**Reference document** — the detail behind the terse rules in `~/.config/crush/CLAUDE.md`: "A
multi-step check script must propagate every step's failure", "A format-on-exit hook `cd`s to the
repo root first" and "Batch container runs don't take `-it`", plus the executable-bit and
run-anywhere rules for format scripts and the bash naming and scope rules ("Names and scope in
bash"), which apply to every bash script. Read it when writing or reviewing a gate or format script
or any other bash script, a Makefile `podman run` target, or a shell-exit hook, or after editing a
committed script.

Copied from github.com/billsix/runClaudeInContainer `tasks/reference/shell-and-gate-scripts.md`
(William Emerison Six <billsix@gmail.com>, 2026-11-13). Only that doc's portable sections are here,
verbatim; its sections about Claude Code's own Bash tool (zsh quoting, `pkill -f`) do not apply to
Crush, whose bash tool runs an embedded POSIX shell, and its bulk-edit section is
`~/.config/crush/reference/bulk-edit-shell-first.md`. **Keep these sections in sync with that doc.**

## A multi-step check script must propagate every step's failure

**The design intent of `format.sh` (and any `make format` / `lint` / `check` target
that chains tools) is "run EVERY step, so one pass reports ALL the red" — deliberately
not fail-fast.** But a plain command sequence in a shell script exits with the **last
command's status alone**, so `make` reports green whenever the final step passes,
silently masking every earlier failure. This is not hypothetical; it has bitten twice:

- **mvp, 2026-07-09:** 79 `ty` diagnostics in `src/` hid for weeks behind a green
  format gate (the final `ty check` in the sequence happened to pass).
- **gacalc, 2026-07-29:** 3 `ty` errors were printed mid-output, then the last step
  (`ty check tools`) printed its own "All checks passed!" and `make format` exited 0 —
  the error report and the green verdict in the same scroll, and the gate was trusted
  over the scroll.

**The required shape — both properties at once** (every step still runs; any failure
fails the script):

```bash
status=0
ruff check . --fix       || status=1
ruff format              || status=1
ty check src             || status=1
ty check tests           || status=1
exit $status
```

(mvp's variant wraps this in a `run() { "$@" || status=1; }` helper — same thing.)

- **`set -e` is the WRONG fix** — it makes the script fail-*fast*, losing the
  report-everything property the multi-step design exists for. Accumulate, don't abort.
- **Loops need it per-iteration**: `for f in …; do clang-format -i "$f" || status=1;
  done` — a bare loop's exit is its last iteration's (this was gltron's flaw).
- **Safe by shape, no change needed:** a single-command script (its exit *is* the
  gate), and `find … -print0 | xargs -0 tool` (xargs exits 123 if any invocation
  failed — spimulator/texExpToPng's shape).
- **When writing or reviewing ANY gate script, check the exit-code story first:**
  "if step 1 fails and the last step passes, what does `make` see?" And don't trust a
  green gate over an error-bearing scroll — the 2026-07-29 case printed both.
- Audit of all mounted repos (2026-07-29): mvp was already correct; **gacalc, hanoi,
  multivariate-math, gltron fixed**; spimulator/texExpToPng safe by shape; the rest
  have no format script.

## Rewriting a script's contents drops its executable bit — restore it

`Write` (and any full-file rewrite) creates the file at mode 644, so **rewriting a committed
script silently strips its `+x`** — even a content-only pass like adding a license/SPDX header
or reflowing comments. A script **invoked directly** then fails at the point of use, not at edit
time: a Dockerfile `RUN /usr/local/bin/foo.sh`, a `./script.sh`, a Makefile recipe naming the
file by path — all die with `Permission denied`. Scripts invoked as `bash foo.sh` survive, which
is exactly why this is easy to miss: some callers keep working while the build-critical one
breaks, often several commits later.

- **After editing any script — especially a bulk header/format pass over several — check the
  modes and restore the bit in the same change.** `git diff --stat` shows a `mode change 100755
  => 100644` line; `git ls-files -s -- '*.sh'` prints each tracked mode. Restore with `chmod +x
  <paths> && git add --chmod=+x <paths>` (the `--chmod=+x` fixes git's mode even when the
  working-tree bit is already correct).
- **This bit me (runCrushInContainer, 2026-08-25):** an "add Apache SPDX headers" pass rewrote
  six entrypoint scripts `100755 → 100644`; the Dockerfile invokes two directly
  (`01-install-base.sh`, `02-install-vendor-tools.sh`), so the next `make image` failed with
  `Permission denied` — the header edit and the build break were four commits apart.

## Write format/check scripts to run BOTH in the container AND on the host from the repo root

**A `format.sh` (or `lint.sh` / any `make format` gate script) should be PORTABLE — runnable
inside the container *and* on the host from the repo root — so I can format without spinning a
container (William Emerison Six <billsix@gmail.com>, 2026-08-14).** Exactly two things make a format script container-only; avoid
both:

1. **An unguarded `source /venv/bin/activate`.** On the host there is no `/venv`, so the bare
   `source` errors. **Guard it:** `[ -f /venv/bin/activate ] && source /venv/bin/activate` —
   activates the container venv when present, otherwise uses the caller's active env.
2. **Absolute container tool paths** (`ty check /<proj>/src`, `/venv/bin/...`) — they only
   resolve at the container mount path. **Use RELATIVE paths for every step** (`ruff check src`,
   `ty check src`, `ty check tests`) and let the CALLER `cd` to the repo root. Then the script
   runs identically from `cd /<proj> && format.sh` (in-container) and `cd <repo> && format.sh`
   (host). **Trap the mvp exit hook hit:** a per-subdir `cd /<proj>/src && format.sh` makes the
   script's own relative `ruff check src` resolve to `src/src` and fail — the shell-exit hook
   must be a SINGLE `cd /<proj>/ && format.sh` from the root, not one call per subdir. **The hook
   does that `cd` itself, every time:** the user types `exit` from whatever directory they are in,
   so a hook that relies on the shell's current directory formats the wrong tree (or none) as soon
   as they have `cd`'d away. gacalc's hook had the same bug (`cd /gacalc/src/`), fixed 2026-11-13.
3. **A hardcoded `cd /<proj>` INSIDE the script** — some scripts self-`cd` (needed in-container,
   e.g. a C/C++ `find . … | xargs clang-format` that must run from the repo root). **Guard it** so
   it no-ops on the host: `[ -d /<proj> ] && cd /<proj>` — replacing `cd /<proj> || exit 1` (which
   hard-*exits* on the host, dir absent) or a bare `cd /<proj>` (which silently runs in the WRONG
   directory on the host). In-container it `cd`s correctly; on the host it stays at the repo root
   you invoked from. This is the alternative to rule 2's "no `cd`, caller `cd`s": a portable script
   either has **no `cd`** (mvp/gacalc — the caller/exit-hook `cd`s) **or guards its `cd`** (the C/C++
   repos, whose `find .` needs the root).

The host run still needs the package importable in the caller's env for the type-checker step
(editable install + deps); a portable script does not *set that up*, it just does not hardcode
container paths that *fight* it. Worked example + the 2026-08-14 cross-repo sweep that applied all
three rules: mvp `entrypoint/format.sh` (guarded venv + all-relative `ty check` paths, was absolute
`/mvp/...`) and gltron were already portable; **gacalc** got rules 1+2 (guard venv, relative `ty
check src/tests/tools`); **hanoi / multivariate-math / spimulator / texExpToPng** got rule 3 (`[ -d
/<proj> ] && cd /<proj>`), and mvm also needed the venv guard. Pairs with the exit-status rule
above: a good gate script both propagates every step's failure AND runs anywhere from the root.

## Batch container runs don't take `-it`; only interactive ones do

`podman run -it` (or `docker run -it`) allocates a pseudo-terminal and keeps stdin open. Use it
only where a person is at the other end: an interactive shell, a GUI app, a server stopped with
Ctrl-C (the signal reaches the process through the pty), or a tool that prompts (a password, a
token, an interactive spell check). **A batch run — format, lint, type-check, test, build, docs,
any `shell-exec`-style payload — omits it.** With `-t` and no terminal on the caller's side (CI,
cron, an agent's nested `make`), docker refuses with `the input device is not a TTY`; and where it
does run, the pty merges stderr into stdout and turns `\n` into `\r\n`, so logs, pipes and
`grep` see mangled output. If one tool inside an otherwise batch target is interactive, keep `-it`
on that target and say why in a comment next to it. (William Emerison Six <billsix@gmail.com>,
2026-11-13.)

## Names and scope in bash — inline what is used once, `local` at the point of use, no nested helpers

The bash wording of the five naming and scope rules in `python-coding-standard.md` ("Inline a value
used once, and name it in a comment instead of a binding" and "What earns an extraction"). This doc is
the only bash standard there is, so the section lives here; it applies to any bash script, not only to
gate scripts. (William Emerison Six <billsix@gmail.com>, 2026-11-25.)

**How bash scopes names, since the rules depend on it.** A variable is global to the script unless a
function declares it `local`. `local` is dynamically scoped: a function sees the locals of whoever
called it. Every function is global, and one defined inside another function becomes global the first
time the outer one runs. The only scopes that isolate are a subshell (`( … )`, `$( … )`) and each side
of a pipeline.

**1. A variable assigned once and used once is inlined**, with a comment above the expression that names
it (`"$(dirname "${BASH_SOURCE[0]}")"` goes straight into the `cd`). Keep the assignment when it does
something the expression alone cannot:

- **Its value takes several lines.** Inlined, a multi-line expression sits inside another expression
  (a three-line conditional among a call's arguments), which is harder to read than the name was. Rule
  1 is for a value that fits on one source line.
- **The command's failure must stop the script.** `set -e` ignores a command substitution that fails
  inside another command's arguments (`echo "$(false)"` carries on), and so does `local x="$(cmd)"`,
  which returns `local`'s own status (shellcheck SC2155). A command whose failure matters is assigned in
  a statement of its own: `local version` and then `version="$(read_version)"`.
- **It is a regular expression for `[[ … =~ … ]]`**, which has to be an unquoted variable to be read as
  a pattern.
- **It is a table or a setting:** an array of files or cases, a `readonly` constant in the block at the
  top of the script that a reader edits, or a default the environment may override
  (`: "${IMAGE_TAG:=latest}"`).
- **It reads a value before a later command changes its source** (`status=$?` on the line after the
  command, before anything else runs).

**2. Two uses do not automatically earn a name.** "This value, or a fallback" is `${VAR:-default}`; "this
value, or stop" is `${VAR:?message}`; a suffix or prefix removed is `${path%.sh}` or `${path##*/}`.

**3. Assign at the point of use.** Inside a function, write `local` on the line that first assigns the
variable, not in a block at the top. In a script's main body, assign beside the use. The one deliberate
exception is the settings block at the top of the script.

**4. Nesting a helper inside its caller does not apply to bash.** Functions are global, so a function
written inside another is not scoped to it; it only looks as if it were, and it does not exist until the
outer one has run. A function with one caller stays at the top level, defined directly above that
caller, and it earns its place by naming a phase; one that exists only to reshape control flow is
inlined. When the aim is to keep a helper's variables from leaking, give it a subshell body
(`helper() ( … )`), which also discards any `cd` or `set` it does.

**5. Declare every variable in a function `local`, the loop variables included.** That is the bash form
of deliberate shadowing: `local path` inside a function hides the caller's `path`, and without it the
function overwrites the caller's variable (`for i in …` in a function leaves a global `i` behind). The
reverse leak also exists: a function can read its caller's locals. Don't rely on it; pass the value as an
argument.

**What shellcheck reports:** SC2034 (a variable assigned and never used), SC2155 (declare and assign
separately) and SC2154 (a variable read and never assigned). Nothing reports a single-use variable, so
rules 1 to 3 are review rules.
