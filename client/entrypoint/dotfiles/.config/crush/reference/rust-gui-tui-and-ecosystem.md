# Rust in practice: GUI (wxDragon), TUI (ratatui), and the sandbox toolchain

**Reference document** — the practical companion to `rust-coding-standard.md`: hard-won facts for
writing Rust **GUIs** (wxDragon / wxWidgets), **TUIs** (ratatui / crossterm), and CLI line-editing,
plus how the Rust toolchain behaves in these sandboxes. Read on demand (NOT auto-loaded). Update in
place. States what is **true now**, agent-facing. (Written 2026-10-23 — William Emerison Six
<billsix@gmail.com> — from porting github.com/billsix/towersofhanoi to Rust: a `rust/` Cargo
workspace of one library crate + four front-ends, built and verified in the sandbox. Versions below
are what resolved at that time; re-check with `cargo add`/docs.rs before pinning.)

> **Shared across both sandboxes — three byte-identical copies (this banner included); keep
> them in sync.** Canonical: runClaudeInContainer `tasks/reference/rust-gui-tui-and-ecosystem.md`
> (github.com/billsix/runClaudeInContainer), mounted in a Claude Code session at
> `~/.claude/reference/rust-gui-tui-and-ecosystem.md`. Copies in runCrushInContainer
> (github.com/billsix/runCrushInContainer): its `tasks/reference/rust-gui-tui-and-ecosystem.md`, and
> the baked crush-client set
> `client/entrypoint/dotfiles/.config/crush/reference/rust-gui-tui-and-ecosystem.md` — delivered to a
> Crush session at `~/.config/crush/reference/rust-gui-tui-and-ecosystem.md`. Edit the canonical,
> then re-copy it over the other two.

## The Rust toolchain in the sandbox

- **Present in both sandbox base lists** (`entrypoint/01-install-base.sh`): `rust`, `cargo`,
  `rustfmt`, `rust-analyzer` (the LSP). `cargo`/`rustc` were 1.99.0 (Fedora). **`clippy` is NOT
  installed by default** — the standard's lint gate (`cargo clippy -- -D warnings`) needs the
  `clippy` package added to the base list(s); until then `cargo build`/`cargo test`/`cargo fmt` are
  the gates you can run.
- **Network:** `cargo` can reach crates.io here (crate fetches succeed). A **std-only crate builds
  fully offline** — add no dependency and `cargo build`/`test` need no network, which is the cheapest
  way to land a verified first milestone before pulling heavy crates.
- **Pinning:** `cargo add` writes a caret range to `Cargo.toml`; the **committed `Cargo.lock` is the
  real pin** (exact resolved versions). Commit `Cargo.lock` for binaries/workspaces.
- **Headless GUI/TUI verification** (no display in the sandbox): build, then run under
  **`xvfb-run -a timeout -s KILL <seconds> ./target/debug/<bin>`**. Exit **137** (SIGKILL after the
  timeout) means it launched and ran — a crash exits 0/1 quickly instead. Grep the captured log for
  `panic`/`abort`, and `pgrep -x <bin>` afterward to confirm no leaked process (hard-kill + audit —
  leaked GUI processes have swapped a host before). A `ratatui` TUI also has `TestBackend` for a true
  unit-test of the rendered frame (see below), which needs no display at all.

## wxDragon (wxWidgets GUI bindings)

The `wxdragon` crate (0.9.x; with `wxdragon-sys` + `wxdragon-macros`) gives safe Rust bindings over
wxWidgets. **`wxdragon-sys`'s `build.rs` downloads the wxWidgets source (3.3.4) over HTTPS and builds
it statically** — it does NOT use the system wxGTK. (`cargo tree -i openssl-sys` reveals the download
path: a `reqwest`/`native-tls` *build*-dependency.) So the build needs:

- **`openssl-devel`** (+ `pkg-config`, in the base toolchain) — so `openssl-sys`/`reqwest` compile
  for the wxWidgets-source download. **Without it the build fails** with `Package 'openssl' not found`
  / `could not find openssl via pkg-config` — the first thing to install when you hit it.
- **`wxGTK-devel`** — not for its own wx (wxDragon builds 3.3.4), but it reliably pulls in
  **`gtk3-devel`** and the GTK/X11/cairo/pango headers the from-source wxWidgets GTK build compiles
  against.
- **`libSM-devel`** and **`libICE-devel`** — the X11 session libraries the static wxWidgets links.
  Without their `-devel` `.so` symlinks the final link fails with `cannot find -lSM` /
  `cannot find -lICE` (the runtime `.so.N` are present; only the dev symlinks were missing).
- A full native toolchain — **`gcc`/`gcc-c++`, `make`, `cmake`, `ninja-build`** (wxdragon-sys
  cmake-builds wxWidgets from source) and **`clang-devel`** (`libclang.so`, because wxdragon-sys runs
  `bindgen` over its C++ header; without it the build panics `Unable to find libclang`).
- **System image libraries' `-devel`** — wxWidgets links them (it does NOT vendor its own): `png`
  and `zlib` arrive via `gtk3-devel`, but **`libjpeg-turbo-devel`, `libtiff-devel`, `expat-devel`**
  must be added, or a binary's final link fails `cannot find -ljpeg / -lexpat / -ltiff`. (A lean,
  Python-only image like hanoi's has *none* of the toolchain or these libs — the whole stack goes in
  the Rust install group; a full dev sandbox already has them.)

**The first build is very heavy** (it downloads and compiles all of wxWidgets) — cache the Cargo
target dir so it is not repeated every run. **Offline caveat:** because wxWidgets is fetched at build
time, a wxDragon build needs network and is not offline-reproducible as-is; point
`WXDRAGON_SYS_BUILD_DIR` at a pre-vendored wx source to make it offline.

### API shape (programmatic; what the hanoi GUI uses)

- **Entry:** `wxdragon::main(|_| { … });` with `use wxdragon::prelude::*;`.
- **Builders:** `Frame::builder().with_title(..).with_size(Size::new(w,h)).build()`;
  `Panel::builder(&parent).build()`; `Button::builder(&parent).with_label(..).build()`;
  `TextCtrl::builder(&parent).with_style(TextCtrlStyle::MultiLine | TextCtrlStyle::ReadOnly).build()`;
  `ListBox::builder(&parent).build()`.
- **Menus:** `Menu::builder().append_item(id, "&Label\tCtrl+X", "help").append_separator()
  .append_check_item(id, ..).build()`; `MenuBar::builder().append(menu, "&Title").build()`;
  `frame.set_menu_bar(menu_bar)`.
- **Sizers:** `BoxSizer::builder(Orientation::Vertical).build()`; `sizer.add(&widget, proportion,
  SizerFlag::Expand | SizerFlag::All, border)`; **`sizer.add_sizer(&child_sizer, …)`** for a nested
  sizer; `panel.set_sizer(sizer, true)`.
- **Events** (all take `'static` closures): `button.on_click(move |_| …)`;
  `frame.on_menu_selected(move |ev: MenuEventData| match ev.get_id() { … })` — route menu items by
  their id; `listbox.on_item_double_clicked(move |_| …)`; `panel.on_paint(move |_| …)`;
  `panel.on_size(move |_| panel.refresh(true, None))`.
- **Dialogs:** `MessageDialog::builder(&parent, message, caption).build().show_modal()`;
  `TextEntryDialog::builder(&parent, message, caption).with_default_value(v).build()` then
  `show_modal()` compared to **`ID_OK`** and `get_value() -> Option<String>`. `Dialog::builder(&parent,
  title).with_size(w,h).build()` for a custom dialog.
- **Status bar:** `frame.create_status_bar(2, 0, ID_ANY as i32, "")` then
  `frame.set_status_text(text, field_index)`.
- **State queries/mutation:** `widget.enable(bool)`, `widget.show(bool)`, `widget.set_label(..)`,
  `frame.layout()`, `frame.get_menu_bar() -> Option<MenuBar>`, `menu_bar.find_item(id) ->
  Option<MenuItem>`, `menu_item.set_label(..)` / `menu_item.check(bool)`, `menu_bar.check_item(id, b)`.
- **XRC** is available (`include_xrc!` generates a typed UI struct), but for a small UI **building it
  programmatically is simpler and type-safe**; reserve XRC for large hand-designed layouts.

### Drawing: the wxDC model only (no GraphicsContext)

wxDragon exposes the **wxDC** drawing model, **not** `wxGraphicsContext`. In a `panel.on_paint`:
`let dc = AutoBufferedPaintDC::new(&panel);` then `dc.set_background(Colour::rgb(..))`,
`dc.set_background_mode(BackgroundMode::Solid)`, `dc.clear()`, `dc.get_size() -> (i32, i32)`,
`dc.set_pen(Colour, width, PenStyle::Solid)`, `dc.set_brush(Colour, BrushStyle::Solid)`,
`dc.draw_rectangle/draw_rounded_rectangle(x,y,w,h,[radius])/draw_circle(x,y,r)/draw_line/draw_text/
draw_ellipse`, `dc.set_text_foreground(Colour)`. Set `panel.set_background_style(BackgroundStyle::Paint)`
at construction.

**Consequence:** there are **no gradient or alpha brushes**. Ports of wxPython drawing that used
`wxGraphicsContext` linear gradients and translucent shadows degrade to **solid fills** (and no
drop-shadows) — a cosmetic downgrade, not a functional one. If true AA/gradients are ever required,
`wxdragon-sys` would need to bind `wxGraphicsContext` (out of scope so far).

### Gotchas (cost real time; check these first)

- **Event closures are `'static`**, so they cannot borrow local state. Share mutable GUI state via
  **`Rc<RefCell<GuiState>>`**: build the widgets, move them into the state, wrap in `Rc<RefCell<…>>`,
  then set each handler by **cloning the widget handle out of the state** and capturing an `Rc`
  clone. wxDragon widgets are cheap **`Clone`** handles (a pointer), so this is fine.
- **`MenuBar` is NOT `Clone`** (most widgets are). Don't store/clone it — fetch it on demand with
  `frame.get_menu_bar()` and call `find_item`/`check_item` on that.
- **`ID_ANY` is an `i64` constant**; APIs taking an `Id` want `i32` — write `ID_ANY as i32`.
- The builder method is **`with_default_value`**, not `with_value`, on `TextEntryDialog`.
- A GUI's shared-state model clashes with the engine's `&mut`-borrowed design: the hanoi GUI keeps
  the cross-game registry + the game pieces in `GuiState` and, per command, **moves the
  game/labelling/recorder into a transient `GameSession` that borrows the registry, then moves them
  back out** (`std::mem::replace`/`take`), so one owned struct serves the `'static` closures.

## ratatui + crossterm (terminal UI)

`ratatui` (0.30.x) + `crossterm` (0.29.x) replace curses. `ratatui::init()` / `ratatui::restore()`
set up/tear down the terminal; the model is **immediate-mode** — `terminal.draw(|frame| …)` each
iteration. `let [a, b, c]: [Rect; N] = Layout::vertical([Constraint::Length(1), Constraint::Min(1),
…]).areas(frame.area());`; render `Paragraph::new(lines).alignment(..).style(..)` with
`Line`/`Span`/`Style`/`Color`. Input is `crossterm::event::read()` → `Event::Key` (classify
`KeyCode`; Ctrl-C via `KeyModifiers::CONTROL`), replacing curses `getch`.

- **`ratatui::backend::TestBackend`** renders to an in-memory buffer with no display — a real
  **headless unit test**: `Terminal::new(TestBackend::new(w,h))`, `terminal.draw(|f| draw_fn(f))`,
  then read `terminal.backend().buffer().content()`. Keep the frame-drawing functions pure (take
  state, render) so they are testable; the event loop (needing a real terminal) is not.
- **A lazy generator that mutates shared state between steps does not map to a Rust `Iterator`** —
  an `Iterator` holding `&mut state` forbids the caller observing the state between `next()` calls.
  Use an explicit **stepper**: `fn step(&mut self, state: &mut State) -> Option<Item>`.

## rustyline (CLI line editing / tab-completion)

`rustyline` gives readline-style editing + completion at a real terminal. Keep the **completion
logic pure** (`fn completions(buffer, word, &registry) -> Vec<String>`) so it is unit-testable; the
`rustyline` wiring (a `Completer` impl + the edit loop) is terminal-only and not unit-tested. For
scripted/piped I/O, read lines from a generic `BufRead`/`Write` and skip readline entirely — that
path stays byte-for-byte testable.

## Worked example

github.com/billsix/towersofhanoi `rust/` — a Cargo workspace: a `hanoigame` **library crate** (model,
command parser, engine/dispatcher, presenter, recipes, solvers; ~51 unit tests mirroring the Python
suite) plus four binaries — `hanoi-cli` (stdin/stdout, 19 I/O tests), `hanoi` (ratatui TUI, 5
`TestBackend` tests), `hanoi-gui` (wxDragon), all over the one shared library, kept in sync with the
Python package feature-for-feature.

## Cross-links

- `rust-coding-standard.md` — the (a)/(b) standard this doc is the practical companion to.
- `nested-run-and-gates.md` — running a project's own containers nested + the headless Xvfb recipe.
- `print-debugging.md` — the compiler/`cargo test`/`RUST_BACKTRACE`/`dbg!` instrumentation method.

## Sources

- The hanoi Rust port (github.com/billsix/towersofhanoi), 2026-10-23 — the API facts above were read
  from the wxDragon source and confirmed by building.
- wxDragon — github.com/AllenDang/wxDragon, docs.rs/wxdragon; `ratatui` — ratatui.rs,
  docs.rs/ratatui; `crossterm` — docs.rs/crossterm; `rustyline` — docs.rs/rustyline.
