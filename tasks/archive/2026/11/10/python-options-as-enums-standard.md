# Python standard: options and mode parameters are enums, not strings

**Created:** 2026-11-10 (William Emerison Six <billsix@gmail.com>) · **Done:** 2026-11-10

Added the judgment-call section "Options are enums, not strings" to `tasks/reference/python-coding-standard.md`
(right after "Prefer `match` + `case _`"): a parameter selecting one of a fixed set of options takes an
`enum.Enum`, defaulted to a member and dispatched with `match`, whose `case _` raises `TypeError`
naming the enum; labels, titles, file names and library-dictated values stay `str`; converting a
published API is a breaking change. The worked example is github.com/billsix/geometricalgebra
(`frame.InverseMethod`, `functions.MatrixBackend`; its archived task
`tasks/archive/2026/11/10/options-as-enums.md`).

Mirror of github.com/billsix/runClaudeInContainer `tasks/archive/2026/11/10/python-options-as-enums-standard.md`.
The section went into both copies here (`tasks/reference/python-coding-standard.md` and the baked
`client/entrypoint/dotfiles/.config/crush/reference/python-coding-standard.md`), inserted as-is
into each: the copies already differed (144 diff lines from the runClaude canonical, 32 between the
two runCrush copies), and re-syncing them is `tasks/audit-baked-reference-doc-drift.md`.
