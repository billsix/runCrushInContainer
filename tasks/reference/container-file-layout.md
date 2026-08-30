# Container file layout — baked files, mounts, and final runtime paths

**What this is:** the single source of truth for where every file in the client
container comes from — what `client/Dockerfile` bakes, what `client/Makefile`
mounts over it, and where each file ends up at run time. Written for the agent
running INSIDE the container ("where do my files live?") as much as for a human
editing the build. Print it on the host with `make -C client manifest`.

**Two synced copies, deliberately:** the repo copy
`tasks/reference/container-file-layout.md` and the baked copy
`~/.config/crush/reference/container-file-layout.md` (in-repo source:
`client/entrypoint/dotfiles/.config/crush/reference/container-file-layout.md`).
Edit both together — the baked one is the only one the agent can reach when the
runCrushInContainer repo is not mounted.

**Re-sync check:** compare `client/Dockerfile`'s `COPY` lines and the
`client/Makefile` `SHELL_RUN_FLAGS` block against the tables below; a `COPY` or
`-v` flag not listed here means this doc has rotted. Last verified 2026-08-30
against the Crush `v0.89.0` build.

**Origin:** an agent session inside the container was asked how it was built and
had to reverse-engineer this layout from the Dockerfile + Makefile, hitting
exactly the ambiguities the tables below resolve (work record:
`tasks/archive/2026/08/30/document-container-file-layout-and-manifest.md`, with
the session log alongside it).

## Where am I? (orientation for the agent in the container)

- **The project you were pointed at is mounted at `/work`**
  (`-v $(PROJECT):/work`; `PROJECT` defaults to the directory `make shell` ran
  from). `shell.sh` cd's there at launch.
- **Any other repo path you find yourself in came from `EXTRA_MOUNTS`** —
  user-supplied, and invisible to these docs and the Makefile conventions. If
  your cwd is not under `/work`, that is why; nothing else about the layout
  changes.
- Your own config and conventions live under `~/.config/crush/`
  (= `/root/.config/crush/`); the tables below say which of those files are
  baked and which are mounted from the host.

## Baked files (Dockerfile `COPY`, in build order)

| Repo source (under `client/`) | Container path | Shadowed at run time? |
| --- | --- | --- |
| `entrypoint/00-install-minimal.sh` | `/usr/local/bin/00-install-minimal.sh` | no (always run at build) |
| `entrypoint/01-install-base.sh` | `/usr/local/bin/01-install-base.sh` | no (run iff `FULL_TOOLCHAIN=1`) |
| `entrypoint/02-install-vendor-tools.sh` | `/usr/local/bin/02-install-vendor-tools.sh` | no (run iff `VENDOR_TOOLS=1`) |
| `patches/` | `/patches/` | no |
| `entrypoint/vendor/` | `/usr/local/bin/vendor/` (`chmod +x`) | no |
| `entrypoint/03-build-crush.sh` | `/usr/local/bin/03-build-crush.sh` | no |
| — (built by `03-build-crush.sh`) | `/usr/local/bin/crush` (via `GOBIN`) | no |
| `entrypoint/dotfiles/.extrabashrc` | `/root/.extrabashrc` | no |
| `entrypoint/dotfiles/.config/containers/storage.conf` | `/root/.config/containers/storage.conf` | no (nested-podman fuse-overlayfs) |
| `entrypoint/dotfiles/.config/crush/CLAUDE.md` | `/root/.config/crush/CLAUDE.md` | no (always-loaded conventions) |
| `entrypoint/dotfiles/.config/crush/commands/` (7 files) | `/root/.config/crush/commands/` | no (slash commands) |
| `entrypoint/dotfiles/.config/crush/reference/` (6 files) | `/root/.config/crush/reference/` | no (see doc mapping below) |
| `entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.md` (blank default) | `/root/.config/crush/ai-coding-conventions.personal.md` | **YES — host overlay mounted over it** |
| `entrypoint/dotfiles/.config/crush/ai-coding-conventions.personal.example.md` | `/root/.config/crush/ai-coding-conventions.personal.example.md` | no |
| `entrypoint/crushrc` | `/root/.config/crush/crushrc` | no (model pin, catalog off, file-tool auto-allow) |
| `entrypoint/shell.sh` | `/shell.sh` | **YES — bind-mounted over by `make shell`** |

Build-generated state that is not a `COPY`: the `~/.bashrc` line
`source ~/.extrabashrc`; `/usr/share/containers/mounts.conf` emptied (only when
the full toolchain installed it); `ENV CRUSH_DISABLE_METRICS=1 DO_NOT_TRACK=1
GOBIN=/usr/local/bin GOFLAGS=-trimpath`.

## Run-time mounts (`SHELL_RUN_FLAGS`, shared by `make shell` and `make shell-exec`)

| Host path | Container path | When |
| --- | --- | --- |
| `client/entrypoint/shell.sh` | `/shell.sh` | always — **overrides the baked copy**, so a `shell.sh` edit is live with no `make image` |
| `$(PROJECT)` (default: dir `make` ran from) | `/work` | always (no `:Z` on purpose — see the SELinux note in `architecture.md`) |
| `~/.tmux.conf` | `/root/.tmux.conf` | only if it exists on the host |
| `~/.gnupg` | `/root/.gnupg` | only if it exists on the host |
| `~/.gitconfig` | `/root/.gitconfig` | only if it exists on the host |
| `~/.ai-coding-conventions.personal.md` | `/root/.config/crush/ai-coding-conventions.personal.md` | always (`touch`ed blank if absent) — **overrides the baked blank**; note the dotted host name → un-dotted container name |
| `~/.config/crush/stack.md` | `/root/.config/crush/stack.md` | always (`mkdir`+`touch`) — the diversion stack survives `--rm` |
| `EXTRA_MOUNTS` | user-chosen | user-supplied; no doc covers these paths |

Non-mount run flags that also shape the environment: `--network=host`
(`NET_FLAGS`), `--security-opt label=disable` (`SELINUX_OPT`),
`-e NESTED_PODMAN=0|1`, and under `NESTED_PODMAN=1` the device/cap flags plus
the tmpfs image store at `/var/lib/containers` — see `nested-podman-design.md`.

## Reference-doc mapping (repo ↔ baked)

The citation rule (from the project `CLAUDE.md`): **inside the container cite
the baked `~/.config/crush/reference/…` path**; in repo docs cite
`tasks/reference/…`. The baked copies' in-repo source directory is
`client/entrypoint/dotfiles/.config/crush/reference/`.

| Doc | Repo `tasks/reference/` | Baked `~/.config/crush/reference/` |
| --- | --- | --- |
| `architecture.md` | yes | no (repo-only) |
| `crush-capabilities.md` | yes | no (repo-only) |
| `dependency-network-audit.md` | yes | no (repo-only) |
| `glimmer-models-and-airgap-quant-selection.md` | yes | no (repo-only) |
| `nested-podman-design.md` | yes | yes — **keep the two copies in sync** |
| `container-file-layout.md` (this doc) | yes | yes — **keep the two copies in sync** |
| `bluf-bottom-line-up-front.md` | no | yes (copied from runClaudeInContainer) |
| `llm-overused-phrases.md` | no | yes (copied from runClaudeInContainer) |
| `print-debugging.md` | no | yes (copied from runClaudeInContainer) |
| `sandbox-capability-map.md` | no | yes (copied from runClaudeInContainer) |

Caveat: when the mounted project is runCrushInContainer itself, a filename
search finds up to THREE copies of a baked doc (the baked one, the
`tasks/reference/` twin, and the `client/entrypoint/dotfiles/...` source). The
dotfiles copy is the baked one's source; the `tasks/reference/` copy, where one
exists, is the repo-facing twin.

## Notes

- `make -C client manifest` prints this doc. Static on purpose — it `cat`s the
  repo copy rather than generating from the Makefile/Dockerfile (decision:
  William Emerison Six <billsix@gmail.com>, 2026-08-30 — start static, add
  dynamic generation only if drift becomes a real problem).
- `server/` is native macOS, not containerized, and is deliberately out of
  scope here (decision: William Emerison Six <billsix@gmail.com>, 2026-08-30).
- The `CRUSH_AT_IMPORT` patch is what makes the baked `CLAUDE.md`'s `@`-import
  of the personal overlay work; `crushrc` registers that `CLAUDE.md` as a
  `global-context-path`.
