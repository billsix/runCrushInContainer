# Upgrade the container base from Fedora 44 to Fedora 45 (done)

Bumped `client/Dockerfile` to `fedora:45` and rebuilt the Crush client sandbox
image nested. Fleet-wide Fedora 44 → 45 bump (William Emerison Six
<billsix@gmail.com>, 2026-11-05). The client reuses runClaudeInContainer's
~430-package toolchain (`client/entrypoint/01-install-base.sh`), so the F45
package changes are identical to that sandbox's.

## What broke and how it was fixed
`01-install-base.sh` failed to resolve five packages on F45:

- **`dotnet-sdk-8.0`** → **`dotnet-sdk-10.0`** (F45 dropped the 8.0 SDK; ships 10.0
  LTS and 11.0 preview).
- **`libgit2-devel`** → **`libgit2_1.9-devel`** (F45 versioned the package name).
- **`pcre-devel`** → **dropped** (PCRE1 removed from F45; `pcre2-devel` was already
  in the list).
- **`shfmt`** and **`procs`** → **dropped from the dnf list**, now installed from
  their upstream release binaries by a new `client/entrypoint/01b-install-binary-tools.sh`
  (shfmt mvdan/sh v3.14.1; procs dalance/procs v0.14.12, pinned, x86_64). Both were
  removed from Fedora 45; `01-install-base.sh` stays a single pure `dnf install`
  and the binary fetch lives in its own host-runnable script + Dockerfile layer.

## Verification
`make image` nested (from `client/`): **EXIT=0**, tagged `crushcontainer:latest`.
The dnf step resolved, Crush built from source (v0.89.0), and all later layers
(including Lean) completed. (A first attempt hit the 50-min `timeout` at the Lean
layer; the fix itself was already proven — a longer timeout built clean.)

## Mirror
These base-list edits are the canonical set; the identical fixes were applied to
`runClaudeInContainer` (`01-install-base.sh` + its own `01b-install-binary-tools.sh`).
