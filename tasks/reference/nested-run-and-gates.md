# Running projects in a nested container, and verification gates — full detail

**Reference document** — the full detail behind the terse "Running projects in a nested
container" and "Verification gates in nested containers" rules in the cross-project
`CLAUDE.md`. Read on demand **before** building or running a project's containers nested,
before calling a code change verified, or when a nested run errors. (Relocated verbatim from
`CLAUDE.md`, 2026-09-14.) For the flag *design* and operating lore see
`~/.claude/reference/nested-podman-design.md`; for the RAM-store / lean-image scope,
`~/.claude/reference/minimal-nested-images.md`; for what the sandbox ships,
`~/.claude/reference/sandbox-capability-map.md`.

## Running projects in a nested container

I run inside a Podman sandbox (the `runClaudeInContainer` / `claudecontainer` image). Most of my projects build and run *themselves* in a container — usually via a `Makefile` target (`make run`, `make shell`, `make test`, `make image`) wrapping a `podman run` / `docker run`. I can run those **nested** inside this sandbox, but there are two things to get right. Don't assume a project's container command works as-is; apply these.

**1. Assume nested support is present — act on it, verify only if a run errors.** Nested podman needs `make shell NESTED_PODMAN=1` at launch, but **default to assuming it's on and just run the nested command** (the PODMAN_RUN_FLAGS convention, point 2, handles the cgroups flag) rather than pre-checking every time — the pre-check is noise, and the run itself is the real test. The `NESTED_PODMAN=1` set at that outermost launch is exported into the session and inherited by every nested `make` through its `NESTED_PODMAN ?= 0` (make's `?=` respects an env value), so you run **plain** `make image` / `make test` / `make shell` for a nested project — **never pass `NESTED_PODMAN=1` on a downstream command**; that flag belongs only on the outermost host launch, which is the user's to run. **Only if a nested run actually fails** do you diagnose:

```sh
test -e /dev/fuse && podman info >/dev/null 2>&1 && echo "nested OK" || echo "no nested — relaunch with NESTED_PODMAN=1"
```

`/dev/fuse` is the tell: absent ⇒ plain `make shell`, nested won't work — then tell the user to relaunch the sandbox from the `runClaudeInContainer` repo with **`make shell NESTED_PODMAN=1`** (I can't add those flags from inside an already-running container).

**2. `--cgroups=disabled` on inner runs — now handled by the `PODMAN_RUN_FLAGS` convention (2026-08-29).** Historically the sandbox's `/sys/fs/cgroup` was read-only and every inner `podman run` died without `--cgroups=disabled`; on the current host stack cgroup2 mounts rw and flagless inner runs work, but the flag stays as harmless belt-and-braces. The standing convention: a `NESTED_PODMAN=1` sandbox **exports `NESTED_PODMAN=1` into the session**, and each converted project Makefile carries `PODMAN_RUN_FLAGS ?= $(if $(filter 1,$(NESTED_PODMAN)),--cgroups=disabled)` threaded into every `$(CONTAINER_CMD) run` line (never `build` — podman build rejects the flag and doesn't need it) — so `make test`/`make run` Just Work nested, and on the host (env var absent) behave byte-identically. **Converting an unconverted project's Makefile to this pattern is pre-authorized** (it is the permanent-passthrough idiom the personal overlay already blesses); for one-off runs in unconverted projects, appending the flag to a hand-run `podman run` remains fine. Full design + rollout status: runClaudeInContainer `tasks/reference/nested-podman-design.md` ("The PODMAN_RUN_FLAGS convention").

**3. A DOWNSTREAM project's lean image is an opt-in (`MINIMAL_IMAGE=1`), never inferred from being nested, and never the sandbox's.** A downstream project Makefile may drop an optional *build* flag when `MINIMAL_IMAGE=1` (`FLAG ?= $(if $(filter 1,$(MINIMAL_IMAGE)),0,1)`) to build a small export/airgap image. The sandbox does **not** set `MINIMAL_IMAGE`, so a nested `make image` builds FULL by default — the inner store is disk-backed now (2026-09-27), so a full image fits nested and lean is a deliberate choice, not a necessity. Image content keys off `MINIMAL_IMAGE`, **never** `NESTED_PODMAN` (that signal was renamed for build content 2026-09-27; the old overload silently downgraded the runCrush client, reverted 2026-09-12 — runCrushInContainer `tasks/reference/nested-podman-vs-image-content.md`; standard: `tasks/reference/minimal-nested-images.md`). **Never apply `MINIMAL_IMAGE` to runClaudeInContainer or the runCrushInContainer client themselves**: they are built on the host and merely *launched* nested.

**Any standing authorizations for nested runs are personal — see `ai-coding-conventions.personal.md`** (e.g. a
blanket pre-approval to add `--cgroups=disabled` transiently, or to make temporary
build-file additions a task needs). Absent such a grant, the default holds: propose the
edit and wait for the go-ahead, per point 2 above.

**Other specifics:**
- **GUI apps CAN be run and screenshotted headlessly — without touching the project's Dockerfile.** The sandbox already ships `Xvfb` (`xorg-x11-server-Xvfb`, explicit in `runClaudeInContainer`'s `entrypoint/01-install-base.sh`) plus ImageMagick (`import`/`convert`) and Mesa's software GL. **Run the X server in the sandbox and share its socket into the nested container** — do NOT add xvfb to the project's image (William Emerison Six <billsix@gmail.com>, 2026-07-18: "can you not change the Dockerfile for mvp?"). The recipe, verified on mvp's OpenGL demos:
  ```sh
  Xvfb :99 -screen 0 1280x800x24 &
  podman run --rm --cgroups=disabled -e DISPLAY=:99 \
      -v /tmp/.X11-unix:/tmp/.X11-unix -v "$(pwd)":/proj:Z <image> …
  ```
  Software GL works through this (glfw reports `4.6 (Compatibility Profile) Mesa`), so real GL demos render. Then **verify pixels, not just exit codes**: a GUI app that doesn't crash may still be drawing nothing. `import -display :99 -window root shot.png`, then check unique-colour count / non-black fraction, and *look at the PNG*. A long-running demo has no exit code worth reading — wrap it in `timeout N` and treat rc=124 as "ran the full duration", with a screenshot as the actual evidence.
- **If a project's editable install is broken, `-e PYTHONPATH=/proj/src` gets you running anyway** — don't let a packaging bug block behavioural verification. (mvp's `loadpackages.sh` currently fails on a missing `setuptools` build dep; the demos still run fine with PYTHONPATH set.)
- **`:Z` on EXTRA_PODMAN_FLAGS poisons repos for host-side `make shell`.** The sandbox runs `--security-opt label=disable`, so a `:Z` project mount at sandbox launch relabels the whole repo to `container_file_t:s0:c1022,c1023` — which a normal *confined* container (the project's own `make shell`) cannot read, and its `:Z` won't relabel away. Symptom: `cd /<project>: Permission denied` inside the project container while the sandbox is (or was) up. Host-side fix: `sudo restorecon -R <repo>`; prevention: use `:z` or no label flag on EXTRA_PODMAN_FLAGS entries (the label-disabled sandbox doesn't need `:Z` at all). Diagnosed 2026-07-07 (spimulator).
- **Networking just works** — default bridged/netavark networking is verified (an inner `apt update` / package pull reaches the network). No `--network` flag needed. If a run ever dies on `netavark: set sysctl ... Read-only file system`, `--network=host` is a working fallback. **Gotcha — `podman build` is different (observed 2026-11-06, geometricalgebra `make image`):** a
  nested build's `RUN` step died with `setup network: pasta failed with exit code 1: Couldn't open network
  namespace /proc/<pid>/ns/net: Permission denied` (Error 125), while a nested `podman run` of the same base
  had working default networking. **Cause (diagnosed 2026-11-07, Fedora 45 sandbox: podman 6.1.3, buildah
  1.45.1):** the sandbox is a rootless container on the host (`/proc/self/uid_map` maps uid 0 to the host
  user), so the inner podman runs rootful with netavark for `podman run`, but buildah's `RUN` steps see the
  user namespace and take the rootless pasta path, which cannot open a network namespace there. The
  Fedora 44-based sandbox's older podman/buildah did not hit this. Tested on a one-line `RUN getent hosts
  github.com`: the default and `--network=bridge` fail; `--network=host`, `--isolation=chroot` and the
  environment variable `BUILDAH_ISOLATION=chroot` all work. **Fix:** launch the sandbox with
  `-e BUILDAH_ISOLATION=chroot` (the example launcher `exampleRunClaude.sh` passes it through
  `EXTRA_PODMAN_FLAGS`, which goes straight into `podman run`); then every nested `podman build` works unchanged.
  Without it, add `--network=host` to the one `podman build` command (run the `make -n image` line by
  hand rather than editing the Makefile).
- **Inside the sandbox an inner run's `:Z` is fine** (it relabels the sandbox's own view, under `label=disable`); on the host, never `:Z` a host tree (see the `:Z` note above).
- **Inner image store is ephemeral** — pulled/built images don't survive the session; expect re-pulls. (Disk-backed dir by default since 2026-09-27; RAM tmpfs is opt-in via `NESTED_PODMAN_STORE=tmpfs`.)
- **Manage inner images by RAM pressure only in the opt-in tmpfs mode.** With the default on-disk store this juggling is mostly moot (disk is plentiful). In `NESTED_PODMAN_STORE=tmpfs` mode the store is a small **RAM-backed** tmpfs (`/var/lib/containers`, sized by `NESTED_PODMAN_TMPFS_SIZE`, **default 8g**), so every pulled/built image costs real memory. **Don't** `rmi` an image the moment you're done with it — keeping it avoids an expensive rebuild if you need it again this session. Instead, **before building or pulling a new image**, estimate its size (a Fedora/full-toolchain image is multiple GB; a slim base is hundreds of MB) and check headroom with `df -h /var/lib/containers`. Only if there isn't enough room, **evict** — `podman rmi` an existing image that seems unlikely to be needed again soon (and `podman image prune -f` for dangling layers) to make space. (`--rm` removes the *container*; the *image* persists until you `rmi` it.) The goal is fewest rebuilds within the RAM budget, not a clean store. Also: when validating in a throwaway image, install the baseline tools your check depends on first — a minimal base (e.g. `ubuntu:24.04`) ships no `python3`, which can make a check *silently pass*.
- **Storage is native kernel overlay**; `podman info --format '{{index .Store.GraphStatus "Native Overlay Diff"}}'` reports `true` (see "Storage speed").
- The host Podman stays **rootless** — nested runs never gain privilege on the real host. Full rationale lives in the `runClaudeInContainer` repo's `CLAUDE.md` / `README.md` and `tasks/archive/2026/06/07/nested-podman.md`.

## Verification gates in nested containers

When nested podman is available, "done" for a code change means **the project's own containerized gate passed** — the `make image` / `make test` / `make dist` target that repo's CLAUDE.md names as its gate — not merely an in-sandbox build and unit-test run. Build the nested container and run the real gate before calling a change verified.

- **Flag coverage is part of the gate.** Trimming feature flags (`BUILD_DOCS=0`, `BUILD_TREE_SITTER=0`, `USE_EMACS=0`, …) to speed a gate up is legitimate **only when the diff cannot affect the trimmed paths**. If a change touches any input that a flag-gated feature consumes — a shared header, a codegen/table source, docs sources — that flag must be ON in the gate; a green gate with the consuming feature compiled out verifies nothing about it. (Learned 2026-07-07 in spimulator: an `opcodes.h` tag rename sailed through three `BUILD_TREE_SITTER=0` image gates, then broke the user's plain `make image` inside the tree-sitter keyword pipeline.)
- **Before ending a work session, run one gate with the repo's default flags** (a plain `make image`) — the defaults are what the user actually runs — or, if that's genuinely not possible, say explicitly in the summary which flag-gated paths went unexercised.
- **A local lint/type-check pass is not the image's: the image installs its tools fresh.** A tool from `dnf install` in the image (`ty`, `ruff`, `hlint`, clippy) can be newer than the sandbox's copy, and a newer checker can reject code the older one passed. Before trusting an in-sandbox lint run as a preview of the gate, `dnf upgrade` that tool in the sandbox (or compare `<tool> --version` with the image's build log). (Learned 2026-11-11 in github.com/billsix/spimulator: `port-python-lint` passed with the sandbox's `ty` 0.0.91 and failed the image build under `ty` 0.0.99.)

## Headless GUI runs in the sandbox — process hygiene (William Emerison Six <billsix@gmail.com>, 2026-09-22)

The sandbox shares the host kernel: every GUI process a headless test leaves behind is host RAM.
On 2026-09-22 overnight PaperBoat runs (Xvfb + software GL) leaked instances that **ignore
SIGTERM**; two forgotten copies — renamed to `Paperboat.pristine`, so `pkill -x Paperboat` never
matched — grew to ~19 GB RSS each and swapped the host into a ten-minute stall. Rules, now also in
the imps harness (`tasks/reference/imps/headless-gui-port-testing.md` there has the full method):

- `timeout -s KILL <secs>` on **every** launch of a GUI binary; never plain `timeout`, never a bare `&`.
- `trap 'pkill -9 -x <binary>' EXIT` in every harness and ad-hoc launch command.
- Never run a renamed copy of a binary; use a second build directory instead.
- Audit before moving on and before ending the session — `ps -eo pid,rss,etime,comm | grep -i
  <binary>` — kill leftovers, and state the audit result in the report.
- Gotchas that cost time: under Xvfb + llvmpipe a GL window's contents are not capturable
  (screenshots are black, `xdotool` cannot aim), and libultraship ports swallow stdout —
  instrument to stderr; drive ImGui popups with an env-gated auto-click hook on a throwaway branch.


## A gate target that depends on `image` rebuilds the image when run nested (2026-10-04)

Observed in geometricalgebra: `make lean` is declared `lean: image`, so a nested `make lean` ran the whole
`podman build` (a 16 GB Mathlib image) for 19 minutes before I noticed. On the host the same prerequisite is a
no-op.

**Cause, revised 2026-11-12.** The host store's layers *do* serve as build cache. A nested `make image`
of github.com/billsix/spimulator, whose image the host had built the day before, hit the cache on
42 of 43 steps and finished in seconds. Two things defeat that cache:
- **The store being ignored.** containers-common 0.69's vendor drop-in did this (see
  `tasks/reference/nested-podman-design.md`, "Which storage config the nested podman reads"); the
  `entrypoint/shell.sh` warning now flags it.
- **A shadowing base image.** If the sandbox's own store holds a newer `fedora:45` (pulled by an
  earlier nested build), `FROM registry.fedoraproject.org/fedora:45` resolves to it, not to the
  host's, so every step misses. `podman images` shows the name twice, once with R/O false. Untagging
  the inner copy (`podman untag <inner-id> registry.fedoraproject.org/fedora:45`) restores the hits.

So the advice below still holds whenever either condition might apply. **Nested, run the gate's own `podman run` line directly
against the existing image** (`podman images` lists it read-only), e.g.
`podman run --cgroups=disabled --rm -v $PWD:/<proj>:Z --entrypoint /bin/bash localhost/<image> /<proj>/<gate>.sh`,
or only accept the rebuild when the image genuinely changed. Check `ps` for a `podman build` before
assuming a slow gate is the gate.

**The same holds for run targets, not only gates** (William Emerison Six <billsix@gmail.com>, 2026-11-09): never invoke a `: image` target
just to see a guard message or test a recipe. In geometricalgebra, `make spyder` (to check its
`USE_SPYDER` guard) started a full nested rebuild, Lean and TeX layers included, that ran for well
over an hour. Use `make -n <target>` to see the recipe, or run the guard line by hand.

**Watching a long build:** a `podman build` log is full of carriage-return progress bars, so
`tail` on it can dump tens of KB into context. Ask for the step instead:
`grep -a -o "STEP [0-9]*/[0-9]*: [A-Z]*" <log> | tail -1`, plus the log's mtime to see whether it
is still moving.

## Storage speed: native overlay, and the warning that says when you don't have it (William Emerison Six <billsix@gmail.com>, 2026-11-15)

**The nested podman uses the kernel's native overlay, so a layer commit tars only the new layer.**
`podman info --format '{{index .Store.GraphStatus "Native Overlay Diff"}}'` prints `true`. This works
because the inner store, `/var/lib/containers`, is a real filesystem (the host disk dir, or the
tmpfs), never the sandbox's own overlay root; buildah's temp files sit on the same volume
(`image_copy_tmp_dir`), because a build-context overlay mount on `/var/tmp` fails. Measured
2026-11-15 on the 3.1 GB spimulator image: a two-step build (`RUN echo`, `RUN dnf install cowsay`)
took 13 s native, 9 s native on tmpfs, and 62 s under the fuse-overlayfs setup it replaced.

**Without native diff, every commit walks the whole image.** fuse-overlayfs has no native diff, so
containers/storage's `NaiveDiffDriver` finds each layer's changes by walking the merged tree of the
layer and its parent, one `Lstat` per file through FUSE. The cost grows with the whole image, not
with what the step changed: on a TeX-sized image a one-line `RUN` took 4 minutes to commit, and one
commit ran over 40 minutes and looked like a hang (the log stops after a `STEP n: RUN …` line, `ps`
shows nothing running the step, and `podman build` sits in `futex` wait). A sandbox image built
before the switch still has `mount_program = /usr/bin/fuse-overlayfs`; `entrypoint/shell.sh` then
prints a `[nested podman] … no native overlay diff` warning at start. Rebuild that image on the host
(`[HOST] make image`) and relaunch before a large nested build.

**Requirements, if the setup is ever moved:** the store on a non-overlay filesystem; `CAP_SYS_ADMIN`
in the sandbox's user namespace (`--cap-add=sys_admin`); no `metacopy` in `mountopt` (the kernel
rejects it in a user namespace, and containers-common's vendor drop-in turns it on, so ours
overrides it); a fresh store (an old one's `.has-mount-program` flag pins fuse until reset; the
per-session store is always fresh).

## Concurrent nested builds share one storage lock — time builds alone (William Emerison Six <billsix@gmail.com>, 2026-11-08)

Several `podman build`s can run at once in the sandbox, but committing a layer takes the store's lock, and
a big layer (a TeX install, a large `COPY`) holds it for as long as the commit takes (minutes under the
old fuse-overlayfs setup). Two things follow:

- **A build that copies a huge context into a layer stalls every other build.** A probe
  `COPY . /ctx` of geometricalgebra's 7.5 GB tree left two unrelated image builds idle for 8 minutes;
  they resumed seconds after the probe was stopped. Copy only what you need to measure (the same paths
  the real `Dockerfile` copies).
- **Never time a build while another runs.** A fully cached hanoi build measured 99 s while a
  spimulator build was committing layers, then 2.6 s after a change while spimulator was compiling, which
  looked like a 38x win for a `.dockerignore`. Alone it was 2.0 s either way. Measure with `ps` showing no
  other `podman build`, and repeat each timing.

Running independent builds in parallel is still fine for throughput; only the timings are unreliable.

