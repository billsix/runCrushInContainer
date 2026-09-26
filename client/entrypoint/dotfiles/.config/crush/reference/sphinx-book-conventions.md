# Sphinx book conventions (autodoc rendering, LaTeX/PDF, fonts)

**Reference doc** — how to make a project's Sphinx book (`book/docs/`, HTML + lualatex PDF over
an autodoc'd Python package) render *cleanly*. The config/rendering companion to the **docstring
STYLE** rule, which lives in `python-coding-standard.md` ("Docstrings — Google / napoleon style").
Read before touching a book's `conf.py`/`api.rst` or chasing a docs-build warning. Distilled from
the geometricalgebra book work, 2026-09-26 (William Emerison Six <billsix@gmail.com>); the
per-project build mechanics stay in that project's own `book-and-docs-pipeline.md`.

## Build first, then read the REAL warnings — don't guess

The single most important habit: **run `make docs` (or the project's build) and read the actual
warnings before "fixing" anything.** Predicted problems are often already fine (e.g. `|A|` inside
a `` `` `` code-span or a `::` literal block is NOT parsed as RST, so it does not warn), and the
real ones are elsewhere. Fix exactly what the build reports, then rebuild to confirm zero.

## The recurring fixes

- **`autodoc_typehints = "none"`** in `conf.py`. Otherwise autodoc turns every type annotation
  into a cross-reference, and any name with no documented target (a `TypeVar`, a re-exported
  class, a helper in an un-documented module) becomes an "undefined Hyper reference" in the PDF —
  easily 100+. With it off, the types live in the Google `Args:`/`Returns:` prose instead (so
  write them accurately — see the docstring-style rule).
- **`api.rst` must `.. automodule::` EVERY package module** that anything cross-references, not
  just the "main" ones. An explicit `:func:`other.module.thing`` in a docstring has no target
  unless `other.module` is documented somewhere in the doc set.
- **Enable `sphinx.ext.napoleon`** (Google-style docstrings) and, for Unicode math in docstrings,
  `latex_engine = "lualatex"` (pdflatex errors on literal Unicode; lualatex renders it).
- **docutils syntax warnings** ("Inline substitution_reference / literal start-string without
  end-string", "Undefined substitution referenced") come from an unbalanced `|` or `` ` `` in a
  docstring parsed as prose. Fix by wrapping the token in the `` `` `` code-role, or make an ASCII
  math/equation block a proper `::` literal block (then its `|`s aren't parsed). A trailing suffix
  on a literal (`` ``Foo``s ``) also breaks it — reword.
- **Missing glyph** (lualatex logs `Missing character: There is no <c> in font [Main.otf]`, and it
  DROPS from the PDF): add a luaotfload **fallback** in `conf.py` `latex_elements['preamble']` to a
  font that has the glyph, keeping the main font. Reference the fallback font **by file**
  (`file:DejaVuSans.ttf:mode=harf;`) so it needs no luaotfload name database; name only fonts that
  are actually installed (naming an absent font crashes the build). Do NOT swap the whole main
  font if it has other glyphs you need (e.g. the script capitals).
  ```
  \directlua{luaotfload.add_fallback("fb", {"file:DejaVuSans.ttf:mode=harf;"})}
  \setmainfont{FreeSerif}[RawFeature={fallback=fb}]
  \setsansfont{FreeSans}[RawFeature={fallback=fb}]
  \setmonofont{FreeMono}[RawFeature={fallback=fb}]
  ```

## Measuring warnings from the build log — gotchas

- **Undefined hyperrefs:** `grep -c 'Hyper reference.*undefined'` **undercounts** — LaTeX wraps the
  warning across lines so "undefined" often lands on the next line. Count with
  `grep -oE "Hyper reference .api:[^' ]+"`, or isolate the *final* latexmk pass (the log accumulates
  every pass, and early-pass "undefined" is stale — latexmk reruns to resolve refs). A residual
  count whose labels are already in `*.aux` is just a convergence tail; a clean rebuild
  (`rm -rf book/docs/_build && make docs`) converges it.
- **Cheap per-docstring RST check without a full build:**
  `docutils.core.publish_doctree(doc, settings_overrides={"warning_stream": …, "report_level": 2})`.
  CAVEAT: `:func:`/`:meth:`/`:class:`/`:attr:` "unknown interpreted text role" errors there are
  **false positives** — Sphinx defines those roles, bare docutils doesn't. Only "start-string
  without end-string" / "undefined substitution" are real.
- A `Font shape ... undefined` warning (e.g. small-caps-italic a text font lacks) is cosmetic —
  LaTeX auto-substitutes a shape, nothing is lost; not worth a fragile `\DeclareFontShape` hack.

## Verify

`make docs` exits 0 with **0** substitution warnings and no `Missing character`; a clean rebuild
shows the undefined-hyperref count converge to ~0. Docstring `Example:` blocks still pass
`pytest --doctest-modules`. If the package's docstrings are copied elsewhere (e.g. a code
generator copying base docstrings into generated modules), the copy path's gates stay green too.

## Cross-links

- `python-coding-standard.md` › "Docstrings — Google / napoleon style" — the docstring STYLE rule.
- A project's own `tasks/reference/book-and-docs-pipeline.md` — its build mechanics + package set.
