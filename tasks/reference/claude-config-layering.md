# The layered `~/.claude` — what persists, what's tracked, and why

**What this is:** the standing description of how the sandbox assembles
`/root/.claude` from the host's private state, this repo's tracked config, and a
per-user personal overlay — plus the persistence rationale and the alternatives that
were rejected. Read this before touching `CLAUDE_CONFIG_MOUNT`,
`CLAUDE_DOTFILES_MOUNT`, `CLAUDE_PERSONAL_MOUNT`, or the
`entrypoint/dotfiles/.claude/` layout.
Consolidated 2026-07-30 from the root `CLAUDE.md`, `Makefile` comments, and the
archived incident task
(`tasks/archive/2026/07/09/persist-claude-login-across-containers.md`).

## The five mounts, in stacking order

The `shell` target mounts, in order (later mounts shadow earlier paths):

1. **Host `~/.claude` → `/root/.claude`** (`CLAUDE_CONFIG_MOUNT`) — the private,
   *unversioned* layer: OAuth credentials (`.credentials.json`), session
   history and resumable transcripts, per-project **agent memory**
   (`projects/<project>/memory/`), settings, plugins, file-history.
2. **Host `~/.claude.json` → `/root/.claude.json`** (`CLAUDE_JSON_MOUNT`, added
   2026-08-16) — Claude Code's **onboarding / login-menu state**
   (`hasCompletedOnboarding`, `oauthAccount`, `userID`), which it keeps **separate** from
   the credentials in mount 1. Critically, `~/.claude.json` is a *sibling* of `~/.claude`,
   **not** inside it, so `CLAUDE_CONFIG_MOUNT` does **not** cover it — and unmounted it lives
   on the ephemeral `--rm` overlay and dies each launch. Result: Claude sees no onboarding
   record and shows the "Select login method" menu **every session even with valid
   credentials mounted**. Seeded to `{}` if absent, then bind-mounted — same `touch`-at-parse
   idiom as `CLAUDE_PERSONAL_MOUNT`. **This ephemeral-`~/.claude.json`, not OAuth *session*
   token expiry, was the true root cause of "I log in via the web every session"** (diagnosed
   2026-08-16; the token-env-var task had mis-attributed it to expiry / a "stale sandbox" —
   see `tasks/archive/2026/08/16/long-lived-auth-token-env-var.md`). The `CLAUDE_CODE_OAUTH_TOKEN` env var can't
   fix it because the menu is gated on this onboarding state, not on API auth.
3. **`entrypoint/dotfiles/.claude/CLAUDE.md` → `/root/.claude/CLAUDE.md`** and
   **`.../commands/ → /root/.claude/commands/`** (`CLAUDE_DOTFILES_MOUNT`) —
   the *tracked* layer: cross-project conventions and slash commands,
   version-controlled in this repo. Edits made in a live session flow straight
   back to the git working tree.
4. **`tasks/reference/ → /root/.claude/reference/`** (same variable) — this
   repo's reference docs, mounted so that pointers in the tracked `CLAUDE.md`
   ("read `~/.claude/reference/llm-overused-phrases.md` at session start")
   resolve in **every** session. The docs stay in their conventional
   `tasks/reference/` home; the mount is just an alias. The `tasks/reference/` mount
   exists because the mounted `CLAUDE.md` **references the reference docs by their
   `~/.claude/reference/…` path and reads them on demand at a trigger** (e.g. "before
   hand-instrumenting a bug, read `print-debugging.md`"), so those paths must resolve in the
   container. (History: the five were `@`-imported — auto-loaded every session — from
   2026-08-02/08-13 until **2026-09-14**, when the measured ~18K-tok/session cost led to
   demoting them to triggered read-on-demand; only `stack.md` and the personal overlay stay
   `@`-imported. See the conventions' "Reference docs — read-on-demand at a trigger" section.)
5. **Host `~/.ai-coding-conventions.personal.md` → `/root/.claude/ai-coding-conventions.personal.md`**
   (`CLAUDE_PERSONAL_MOUNT`, added 2026-08-14) — the *personal overlay*. The tracked
   `CLAUDE.md` ends with `@~/.claude/ai-coding-conventions.personal.md`; the repo ships a **blank** default
   (`entrypoint/dotfiles/.claude/ai-coding-conventions.personal.md`, baked by the Dockerfile `COPY`) so a bare
   `podman run` resolves the import instead of dangling, and `make shell` shadows it with
   the host's `~/.ai-coding-conventions.personal.md` — **`touch`ed if absent at parse time,
   the same idiom as `CLAUDE_CONFIG_MOUNT`'s `mkdir -p` below, and unconditional because
   the `@`-import target must always exist**. This keeps the *tracked* conventions
   maintainer-agnostic while each user's specifics (identity, repo→URL mapping, project
   template, standing authorizations) live only on their host file, never committed. **The
   host and container basenames differ on purpose** — the host file is a hidden dotfile (out
   of the way among the user's dotfiles), while the repo/container copy is un-dotted so the
   baked default and the `.example` template stay visible in `ls`; the bind mount bridges the
   two names. See
   the root `CLAUDE.md` "personal overlay" note, `FORKING.md`,
   `entrypoint/dotfiles/.claude/ai-coding-conventions.personal.example.md`, and
   `tasks/archive/2026/11/08/separate-general-and-personal-conventions.md`. (Harvested verbatim from the
   root `CLAUDE.md` during the 2026-09-13 trim:) The mounted `CLAUDE.md`'s opening
   section (**"This is the SHARED layer…"**) instructs the agent to route any
   maintainer-specific content to this overlay, never to the shared file, so the
   separation stays self-maintaining. **Worked examples** stamped with one of the maintainer's
   projects stay in the shared file with the lesson generalized; one moves to the overlay only when
   its lesson cannot be stated without that repo (decided 2026-08-14, when the split was made). Dated
   decision stamps (`Name <email>, date`) are not personal content: the stamp convention requires them
   in the shared file too.

Auth and sessions never live in git; conventions never live only in a container; personal
specifics never live in the tracked repo. That split is the whole design.

**Gotcha: a single-file bind mount shows the file as it was at launch once git replaces it.** The
personal overlay (`~/.ai-coding-conventions.personal.md`) and the tracked `CLAUDE.md` are mounted as
single files, which binds the host file's inode. An in-place edit (an editor, `Edit`, Python
`write_text`) keeps the inode and shows through. A `git merge`, `checkout`, `rebase` or `stash` writes a
new file and unlinks the old one, so the running sandbox keeps the stale copy until it is relaunched.
Found 2026-11-15: after the maintainer merged a dotfiles branch, the sandbox's
`~/.claude/ai-coding-conventions.personal.md` still held the pre-merge Python-deps rule, and a repo
review reported a contradiction that no longer existed. When the current text matters (an audit, a
comparison), read the overlay from its working copy, github.com/billsix/dotfiles
`.ai-coding-conventions.personal.md`, if that repo is mounted, and `cmp` it against the mounted copy.

## If the login menu returns despite the mounts

The onboarding persistence (mount 2) only works if `~/.claude.json` is actually bind-mounted
*and* carries a completed-onboarding record. If a **second** fresh sandbox still shows
"Select login method", diagnose in order:

1. **[CONTAINER]** `ls -la ~/.claude.json` — expect a real file, not an empty `{}`. If it's
   `{}`-only or missing, the mount didn't attach → check step 2.
2. **[HOST]** `make -n shell | grep -- '/root/.claude.json'` — expect one
   `-v …:/root/.claude.json:Z` line. Empty means an old `Makefile` without `CLAUDE_JSON_MOUNT`.
3. **[CONTAINER]** `grep -o 'hasCompletedOnboarding[^,]*' ~/.claude.json` — expect
   `hasCompletedOnboarding":true`. `false`/absent means no browser login has completed yet;
   run `claude`, log in once, and it sticks.

Also: `/logout` deliberately resets onboarding (log in once more), and ~28 days of disuse
lapses the mounted refresh token (a single browser login renews it).

## Why the host mount is `mkdir -p`, not an existence check

The other host mounts (`~/.tmux.conf`, `~/.gitconfig`, `~/.gnupg`) are
*conditional* — skipped if absent, correctly, because they're optional
conveniences. `~/.claude` is different: **if the mount silently no-ops, the
whole private layer is written to the container's overlay and dies with the
container.** That actually happened (diagnosed 2026-07-09): the host had no
`~/.claude` (Claude Code had only ever run inside the sandbox), the
`$(shell if [ -d ... ])` evaluated to empty with no warning, and the cost was a
re-sign-in every launch **plus silent loss of agent memory and resumable
sessions** — memory notes written in good faith each session, discarded at exit.

Hence (`Makefile`):

```make
CLAUDE_CONFIG_MOUNT := $(shell mkdir -p $(CLAUDE_CONFIG_DIR); echo "-v $(CLAUDE_CONFIG_DIR):/root/.claude:Z")
```

Two details that matter and are easy to "clean up" into a regression:

- **The `mkdir -p` must live inside the `$(shell …)`.** The variable is
  `:=`-expanded at Makefile *parse* time; a `mkdir` recipe line in the `shell:`
  target would run after the flag was already computed. And `make` runs on the
  host, so this creates the host-side directory itself — no manual step.
- **Do not revert it to an existence check** because it "matches the other
  mounts." The asymmetry is the point: optional mounts may skip; this one must
  never skip.

Caveat: `:Z` relabels host `~/.claude` with a container SELinux type —
harmless to the (unconfined) host user's own processes; `:z`/no flag would also
work since the sandbox runs `label=disable`.

## Auth beyond the mount — a long-lived token env var (2026-08-15)

**This token is for headless/CI/`-p` use only — it does *not* silence the interactive login
menu.** That menu is gated on onboarding state and is fixed by `CLAUDE_JSON_MOUNT` (mount 2
above); the token authenticates API calls, not the menu. See
`tasks/archive/2026/08/16/long-lived-auth-token-env-var.md`.

The `~/.claude` mount persists `.credentials.json`, whose access token auto-refreshes via a
~28-day refresh token (persisted, since it's in the mount) — so interactive login already
survives across runs once mounts 1–2 are in place. For **non-interactive** use where you want
auth independent of the mounted login entirely, use a **long-lived token passed through from
the host env**, never stored in the repo (so it honors the 2026-07-09 "don't put
`.credentials.json` in git" decision):

- The Makefile var **`CLAUDE_AUTH_ENV`** adds `-e CLAUDE_CODE_OAUTH_TOKEN` (and `-e
  ANTHROPIC_API_KEY`) to the `shell:` `podman run` **only when the host var is set** — computed
  via `$(shell [ -n "$$VAR" ] && printf …)` at parse time, so an *unset* var never shadows the
  mounted credentials with an empty value.
- **`CLAUDE_CODE_OAUTH_TOKEN`** (recommended, subscription-friendly) is a ~1-year token from
  `claude setup-token`; export it on the host (`~/.bashrc`/`~/.zshrc`). `ANTHROPIC_API_KEY` also
  works but bills per-token on a separate API account — for forks, not the subscription path.
- **`entrypoint/shell.sh`** prints a one-time setup hint at container start while no token is set.

Precedence: an env-var token **overrides** the mounted session login — per the
[auth docs](https://code.claude.com/docs/en/authentication.md), `CLAUDE_CODE_OAUTH_TOKEN`
(rank 5) is read before the stored `/login` credentials (rank 7), so it authenticates even with
valid mounted creds present. The image must be Claude Code **≥ 2.1.225** (a pre-2.1.225 bug
replaces the env token mid-session with a short-lived stored token, 401-ing later); this repo's
Dockerfile runs `claude update` at build, so a rebuilt image is current.

**Gotcha that bit the maintainer (2026-08-15) — "set" must mean *exported*.** `CLAUDE_AUTH_ENV`
is a `$(shell …)` evaluated at Makefile-parse time, and that subshell inherits only **exported**
host vars. A var that is merely *set* — `echo ${#VAR}` prints a length but `declare -p VAR` shows
`--`, not `-x` — is invisible to make, so no `-e` flag is added and the container never sees it.
And a **running container predates a newly-added export**: only a fresh `make shell` picks it up.
Both were the whole of a "still prompts for web auth" report where the wiring was already correct.
Confirm on the host with `declare -p CLAUDE_CODE_OAUTH_TOKEN` (want `-x`) and
`make -n shell | grep -- '-e CLAUDE_CODE_OAUTH_TOKEN'` (want the flag emitted), then relaunch.

See `README.md` ("Auth"), the root `CLAUDE.md` ("The layered Claude config" and "Host shell vs
container shell"), and `tasks/archive/2026/08/16/long-lived-auth-token-env-var.md`.

## Why the container stays ephemeral (`--rm`)

Rejected alternatives from the 2026-07-09 incident, kept rejected on purpose:

- **A long-lived / named container** (`podman start` reuse): would persist login
  but sacrifices the fresh-state guarantee, delays image upgrades, and diverges
  from the ephemeral-container template every other project follows.
- **A named volume for `/root/.claude`:** persists but hides state from the
  host filesystem. A plain host directory is inspectable, backupable, and is
  what the layered design already reaches for.

Persistence belongs in *host directories mounted in*, never in the container.

## Editing workflow

- **Conventions / slash commands:** edit `entrypoint/dotfiles/.claude/` (in
  this repo). In a live session the bind mounts make the edit take effect on
  the next read *and* land in the working tree for commit. **Gotcha (2026-10-15):
  `CLAUDE.md` is a single-FILE bind mount, and an editor that saves by
  write-temp-then-rename (the agent's Edit/Write tools, Emacs by default) replaces
  the inode, so the mounted `/root/.claude/CLAUDE.md` keeps showing the OLD content
  while the repo file is already updated** — verify with `stat -c %i` on both paths
  or a `diff`. The repo copy is the truth and is what gets staged; the live view
  catches up at the next `make shell`. The `commands/` and `reference/` mounts are
  DIRECTORY mounts and do not have this problem (a new or rewritten file appears at
  once).
- **Reference docs:** edit `tasks/reference/` as usual; same live-mount effect.
- The Dockerfile's `COPY entrypoint/dotfiles/ /root/` matters **only** for
  containers run without the host `~/.claude` mount (e.g. someone else's bare
  `podman run`); in normal `make shell` use, the mounts shadow the baked copy,
  so an image rebuild is *not* needed for config changes.
- Never route secrets through the repo: `.credentials.json` is host-layer only
  (the 2026-07-09 task explicitly declined shuttling it through git — sign in
  fresh instead).

## Related

- `tasks/reference/nested-podman-design.md` — the other big Makefile subsystem.
- Root `CLAUDE.md` "The layered Claude config" — the short operational
  summary of this doc.
