# Tauri desktop apps in Rust (v2): backend, webview frontend, Linux build

**Reference document** — hard-won facts for building a **Tauri v2** desktop app whose Rust backend
reuses an existing library crate and whose UI is a static webview frontend: the project shape, the
IPC boundary, the Linux (Fedora) build dependencies, and how it wires into the container template.
The companion to `rust-coding-standard.md` and `rust-gui-tui-and-ecosystem.md` (Tauri is a *webview*
GUI, a different stack from wxDragon/ratatui, so it gets its own file). Read on demand (NOT
auto-loaded). Update in place. States what is **true now**, agent-facing. (Written 2026-10-23 —
William Emerison Six <billsix@gmail.com> — from adding a Tauri front-end to
github.com/billsix/towersofhanoi, a fifth UI over the same `hanoigame` Rust core. Versions below are
what resolved then; re-check with `cargo add`/docs before pinning.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/tauri-desktop-apps.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/tauri-desktop-apps.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/tauri-desktop-apps.md`, and
> the baked crush-client set
> `client/entrypoint/dotfiles/.config/crush/reference/tauri-desktop-apps.md` — delivered to a
> Crush session at `~/.config/crush/reference/tauri-desktop-apps.md`. Edit the canonical,
> then re-copy it over the other two.

## What Tauri is, and the one decision to make first

A Tauri app is a **native Rust backend** (`src-tauri/`) that owns the state and logic, plus a **web
UI rendered in the OS webview** (WebKitGTK on Linux, WebView2 on Windows, WKWebView on macOS). The
two talk over Tauri's IPC: the frontend calls `invoke("command_name", args)` and the backend answers
with a serde-serializable value. **Use v2** (`tauri` 2.12.x, `tauri-build` 2.7.x as of 2026-10-23);
v1 docs are not interchangeable.

**The decision that shapes everything: Tauri is a front-end, not a rewrite.** If you already have a
Rust library crate with the model/logic, the Tauri backend **depends on that crate** (a path
dependency) and wraps its operations as commands — do not reimplement the logic in `src-tauri`. The
backend is thin glue + a view-model; the crate is the engine. (In the hanoi port the backend is one
`main.rs` over the `hanoigame` crate, exactly as the CLI/TUI/wx front-ends are.)

## Project shape

A standalone `tauri/` dir (see "Workspace isolation" for why it is *not* a member of the core Cargo
workspace):

```
tauri/
├── src-tauri/
│   ├── Cargo.toml        # bin crate: tauri (features=["…"]), tauri-build (build-dep),
│   │                     #   serde + serde_json, and a path-dep on ../../rust/<corecrate>
│   ├── build.rs          # fn main() { tauri_build::build(); }
│   ├── tauri.conf.json   # the app config (below)
│   ├── icons/            # PNGs referenced by bundle.icon (must be VALID PNGs — see gotchas)
│   └── src/main.rs       # #[tauri::command]s + the managed state + tauri::Builder
└── frontend/             # the static web UI (index.html + main.js + style.css)
```

`tauri.conf.json` essentials for a **no-bundler, static** frontend:

```jsonc
{
  "$schema": "https://schema.tauri.app/config/2",
  "build":  { "frontendDist": "../frontend" },      // static dir, embedded at compile time
  "app":    { "withGlobalTauri": true,              // → window.__TAURI__ in the page (no npm import)
              "windows": [{ "title": "…", "width": 920, "height": 680 }],
              "security": { "csp": null } },
  "bundle": { "active": false,                      // skip installer packaging; `cargo run` just launches
              "icon": ["icons/32x32.png", "icons/128x128.png", "icons/icon.png"] }
}
```

`generate_context!()` (called in `main`) **embeds `frontendDist` into the binary at compile time**, so
there is no dev server and no separate frontend build step — `cargo run` compiles the Rust and serves
the baked HTML. Good for a small app and a Rust-only toolchain.

## The IPC boundary (the part that is Tauri-specific)

- **Commands** are `#[tauri::command] fn name(...) -> T where T: Serialize`, registered with
  `.invoke_handler(tauri::generate_handler![a, b, c])`. The frontend calls them by name with a
  camelCase-keyed args object; a Rust param `discs: u32` arrives as `invoke("new_game", { discs })`.
- **Shared state** is registered with `.manage(Mutex::new(AppState::new()))` and read in a command via
  a parameter `state: State<'_, Mutex<AppState>>`, then `state.lock().unwrap()`. **Do not try to alias
  the state type** — `type Shared = State<'_, Mutex<AppState>>` does not work (the elided lifetime has
  no home in a type alias); write the full `State<'_, Mutex<AppState>>` in each command signature.
- **One view-model per response (recommended).** Have every command return the *same* struct — a
  `#[derive(Serialize)] struct Snapshot { … }` capturing the whole view (board, status, legal moves,
  flags, lists). The frontend then has one `render(snapshot)` that repaints from it, no matter which
  command was called. Keep this struct a **projection for display**, not the raw model: expose exactly
  what the UI draws (e.g. add a structured `towers: [Vec<u32>; 3]` when the UI needs shapes a text
  rendering can't be re-parsed into). `serde` serializes fixed arrays and `Vec` fine.
- **The `&mut`-engine vs shared-state clash** (same issue the wxDragon GUI hits, see
  `rust-gui-tui-and-ecosystem.md`): if the core engine wants an owned/`&mut`-borrowed session, hold the
  pieces in `AppState` and, per command, **move them into a transient session that borrows the registry,
  then move them back** with `std::mem::replace`/`std::mem::take`. One `Mutex<AppState>` then serves
  every command.

## Frontend without a bundler (plain HTML + vanilla JS)

`withGlobalTauri: true` puts the API on the page as `window.__TAURI__`, so `const { invoke } =
window.__TAURI__.core;` with **no** `import`/npm. That is the cheapest UI for a newcomer and a
Rust-only image: three static files (`index.html`, `main.js`, `style.css`) under `frontend/`, each
driving play via `await invoke(...)` and re-rendering from the returned view-model. A `<canvas>`
graphics board is ordinary 2-D canvas (`ctx.roundRect`/`arc`/`fillText`; WebKitGTK 2.5x supports
`roundRect`); mirror a native renderer's palette/layout math directly in JS. TypeScript + a bundler
(Vite) stays an option if the UI grows, at the cost of a Node toolchain in the image.

## Linux build dependencies (Fedora) — read the `-sys` crates' needs UP FRONT

Tauri's Linux backend links **WebKitGTK**, pulled in by a chain of `-sys` crates whose `build.rs`
scripts run `pkg-config`. On a box without the dev packages, each fails with `Package '<lib>' not
found` **one at a time** — do not discover them reactively. For Tauri v2 on Fedora 44 the two that
are not already present from a GTK3 stack are:

- **`webkit2gtk4.1-devel`** — provides `webkit2gtk-4.1.pc` (and the javascriptcoregtk headers the
  `javascriptcore-rs-sys` / `webkit2gtk-sys` crates need).
- **`libsoup3-devel`** — provides `libsoup-3.0.pc` (the `soup3-sys` crate; the error is
  `Package 'libsoup-3.0' was not found in the pkg-config search path`).

The rest of the chain (gtk3, glib/gio/gobject, cairo/pango/gdk-pixbuf/atk, gdk-x11) resolves against
the **gtk3 headers** a GUI stack already carries (e.g. `wxGTK-devel` pulls `gtk3-devel`; a full dev
sandbox has them). **Verify a package actually provides the `.pc` a crate wants** before adding it, so
the rebuild is one round, not several:

```sh
dnf repoquery --whatprovides '*/libsoup-3.0.pc'     # → libsoup3-devel
dnf repoquery --whatprovides '*/webkit2gtk-4.1.pc'  # → webkit2gtk4.1-devel
```

These go in the project's Rust install group (`entrypoint/04-install-rust.sh` for hanoi), alongside
the toolchain. A lean/Python-only image has none of the GTK stack, so the whole set lands there.

## Config & build gotchas (cost real time)

- **`bundle.icon` must list VALID PNGs.** `tauri-build`/`generate_context!` validate the icon files at
  compile time; a missing or non-PNG icon fails the build (`failed to read icon …` / not a PNG). For a
  placeholder, generate real RGBA PNGs at the listed sizes (32, 128, 128@2x, plus `icon.png`) rather
  than empty/renamed files. `bundle.active: false` skips *packaging* but the icons are still read.
- **`src-tauri/gen/`** (generated ACL/capability schemas, regenerated by `tauri-build` each build) is
  **gitignore it** — along with `src-tauri/target/`.
- **Headless / software rendering:** a webview under Xvfb (or a VM with no GPU) needs
  **`WEBKIT_DISABLE_DMABUF_RENDERER=1`** in the environment or WebKitGTK crashes/blank-screens trying
  DMA-BUF. Set it where the app launches (the Makefile run target). Even then, **a full webview launch
  is best verified on a real display** — a headless smoke risks leaked `WebKitWebProcess`/
  `WebKitNetworkProcess` (hard-kill + `pgrep` audit; leaked GUI processes have swapped a host). A
  `cargo check` + `cargo fmt --check` + the frontend JS parsing clean is the cheap gate; the visual
  check is the maintainer's on host.

## Workspace isolation (keep the heavy webview deps off the core build)

Put the `tauri/` crate **outside** the core library's Cargo workspace, with a path-dep reaching into
it (`../rust/<corecrate>`), rather than adding it as a workspace member. Reason: the core workspace's
build stays clean, fast, and offline-buildable (std-only crates, quick `cargo test`); folding Tauri in
would couple every `cargo build` there to the WebKitGTK `-sys` stack and its system deps. The path-dep
gives code reuse without build coupling. (`tauri/.gitignore` then carries `src-tauri/target/`,
`src-tauri/gen/`, and the container's `.container-target/`.)

## Container wiring (the template)

- A `make rust-tauri` run target: `cd tauri/src-tauri` → set a per-crate `CARGO_TARGET_DIR` (a
  bind-mounted `.container-target`, so artifacts persist across `--rm` runs) and `CARGO_HOME` (a shared
  bind-mounted `.container-cargo`, so crate downloads persist) → `WEBKIT_DISABLE_DMABUF_RENDERER=1` →
  `cargo run`, under the same X11/Wayland passthrough the other GUI targets use. The two cache dirs are
  the dnf/pip-download-cache analog for cargo; see `rust-gui-tui-and-ecosystem.md` for the toolchain
  detail and the `CARGO_HOME`/`CARGO_TARGET_DIR` persistence pattern.
- **Self-contained-image caveat:** the WebKitGTK deps are system packages (fine, they bake into the
  image), but like any crate-fetching build the first `cargo run` needs network; a `--mount=type=cache`
  (or the bind-mount cargo caches) speeds rebuilds but does **not** make the image ship the deps — see
  the self-contained-images rule in the personal overlay if an offline-export guarantee matters.

## Cross-links

- `rust-coding-standard.md` — the Rust (a)/(b) standard the backend follows.
- `rust-gui-tui-and-ecosystem.md` — the sibling: wxDragon/ratatui/rustyline, the sandbox toolchain,
  headless-Xvfb verify, and the `CARGO_HOME`/`CARGO_TARGET_DIR` cache pattern.
- `nested-run-and-gates.md` — running a project's own containers nested.

## Sources

- The hanoi Tauri port (github.com/billsix/towersofhanoi, `tauri/`), 2026-10-23 — the facts above were
  read from building it in the sandbox: backend `cargo check`/`cargo fmt` clean, play-verified on host.
- Tauri — tauri.app (v2 docs), `tauri`/`tauri-build` on crates.io; the `-sys` chain —
  `webkit2gtk-sys`, `soup3-sys`, `javascriptcore-rs-sys` on docs.rs.
