Drop a stack entry we have decided **not** to do. This is deliberately separate from
`/stack-pop`, which means "finished".

The stack file is `~/.config/crush/stack.md`.

Steps:

1. Identify the entry: `$ENTRY` is its number from `/stack`; empty means the top.
   Show me the entry and **confirm before removing it** — dropping is the one stack
   operation that discards work, so it always asks.

2. **Ask why, and record it.** If the entry has a task doc, do not silently delete the
   doc: mark it parked/closed with the reason, then archive it. The reason matters more
   than the removal — a dropped item with no recorded reason gets re-proposed later and
   re-investigated from scratch.

3. Remove the entry and confirm what remains on the stack.

4. **Never treat "we decided against it" as done.** If work was completed, that is
   `/stack-pop`. If it turned out to be unnecessary, or was based on a premise that proved
   wrong, that is this command, and the write-up should say which — including when the
   premise was wrong, because that is the most useful thing to know later.
