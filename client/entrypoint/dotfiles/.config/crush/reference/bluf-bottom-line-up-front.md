# BLUF — Bottom Line Up Front

**Reference document** — what BLUF is, where it comes from, why it works, and how to write a good one.
States what is true; not a task. Created 2026-08-29 (William Emerison Six <billsix@gmail.com>). Backs
the `## BLUF` task-doc convention in the baked `CLAUDE.md` ("Task documents"). Baked into the image at
`~/.config/crush/reference/`; ported from runClaudeInContainer (`github.com/billsix/runClaudeInContainer`).

## What it is

**BLUF = Bottom Line Up Front.** State the **main point / conclusion / required action in the very
first sentence(s)**, *before* the background, reasoning, or supporting detail. The reader gets the
essential message immediately and can decide whether — and how closely — to read the rest. It inverts
the instinct to "build up" to a conclusion: the conclusion comes first, the build-up follows for
whoever needs it.

It answers, up front: **what is this, and what do you need from me / what happens next?**

## Where it comes from

BLUF is a **US Army writing standard**, formalized in **Army Regulation 25-50** (*Information
Management: Records Management: Preparing and Managing Correspondence*) — the ~100-page regulation that
governs Army correspondence. Its roots are mid-20th-century military communication protocols, where a
commander must grasp a message's essence in seconds under time pressure. AR 25-50's rationale, in its
own words: *"the greatest weakness in ineffective writing is that it doesn't quickly transmit a focused
message."* BLUF is the fix — lead with the focused message.

From the military it spread into **corporate communication, legal writing, and government filings**,
wherever readers are busy and decisions are time-sensitive (email subject/first-line, exec summaries,
memos, PR descriptions, incident reports).

## Why it works

- **Decisions get made faster.** The reader knows the ask/outcome before investing in the detail, so
  they can act or triage immediately.
- **It respects the reader's time and attention.** No hunting through paragraphs for "so what?"; the
  point isn't buried at the end where a skimming reader never reaches it.
- **It forces the writer to actually know their point.** You can't write a good BLUF until you've
  decided what the single most important thing is — which improves the whole document.
- **It degrades gracefully.** A reader who stops after the BLUF still leaves with the essential message;
  one who continues gets the support. Either way they're served.

## How to write a good one

1. **Lead with the conclusion / recommendation / required action** — the "so what," not the setup.
2. **Keep it short** — one to a few sentences. If it needs a paragraph, it isn't a *bottom line* yet.
3. **Say what it IS and what "done"/the ask is.** For a proposal: the recommendation + the decision you
   need. For a task: what the task is and what "done" means. For a report: the finding + its
   consequence.
4. **Front-load the specifics** — the number, the file, the outcome, the deadline — not vague framing.
5. **Then stop.** Put the background, options, and reasoning *below* the BLUF, for the reader who wants
   them. Don't re-litigate the point in the BLUF.

### Bad vs. good

- **Bad (bottom line buried):** *"Over the last quarter we evaluated three caching strategies against
  our latency SLOs, weighing memory cost, eviction behavior, and operational complexity, and after
  considering the trade-offs…"* — the reader still doesn't know the recommendation.
- **Good (BLUF):** *"Recommendation: adopt Redis with an LRU policy — it's the only option that meets
  the 50 ms p99 SLO within our memory budget. Rationale and the rejected alternatives follow."*

- **Bad (task, no bottom line):** *"There's some inconsistency in how projects mount their shell
  script…"* — what's the task?
- **Good (task BLUF):** *"Add a `make shell-exec` target (batch twin of `make shell`) to every project
  that has `make shell`. Done = the target runs a script in the same container env, verified nested."*

## How we use it (task docs)

Every non-trivial task doc leads with a **`## BLUF`** section — **1–4 sentences: what the task IS and
what "done" means** — directly under the header, before `## Context` and the body. It pairs with the
cold-execution default (see "Task documents" in `CLAUDE.md`): a fresh reader (a new session, you months
later, a colleague) should grasp the whole point of the task from the BLUF alone, then use `## Context`
to orient and the body to act — with none of the conversation that produced the task.

The same habit is worth applying beyond task docs: PR descriptions, status updates, reference-doc
openings, and any message where a busy reader needs the point first.

## Sources

- [BLUF (communication) — Wikipedia](https://en.wikipedia.org/wiki/BLUF_(communication))
- [Army Regulation 25-50 — *Preparing and Managing Correspondence*](https://netsuite.blog/army-writing-regulation-ar-25-50-guide) (the regulation that formalizes BLUF for Army writing)
- [Bottom Line Up Front: write to make decisions faster — Matt Ström-Awn](https://mattstromawn.com/writing/bluf/)
- [Bottom Line Up Front (BLUF): What It Is and How to Use It — LegalClarity](https://legalclarity.org/bottom-line-up-front-bluf-what-it-is-and-how-to-use-it/)
