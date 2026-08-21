# Words and phrases overused by Claude Code and LLMs — catalog, alternatives, verdicts

**Created:** 2026-07-29 (work record: `tasks/archive/2026/07/29/llm-overused-phrases.md`)
**What this is:** a research-backed catalog of the words and multi-word phrases that
Claude Code and LLMs generally overuse; for each: what it means, ~15 alternatives, and
a verdict on which alternatives are worth remembering. The distilled, actionable form
lives in `entrypoint/dotfiles/.claude/CLAUDE.md` ("Words and phrases you overuse");
this file is the full catalog behind it.

**Why (Bill, 2026-07-29):** this is *not* about hiding that an LLM wrote the text —
Bill isn't concealing that. The goal is that the output be **less annoying, more
varied, and more interesting to read**. The sources below are mostly framed as
"AI-detection tells" because that's the literature that exists; read them here as a
map of *monotony* — where the prose falls into the same rut every time — not as a
disguise kit. That framing also drives the verdicts: deletion, specificity, and plain
words are preferred because they read better, not because they evade detection.

## Cross-cutting findings (read these first — they shape every verdict)

1. **Every LLM-ism is a pre-existing, legitimate word or idiom, mechanically overused
   until it reads as a cliché.** (HN consensus.) None of these are wrong in a single
   use; *frequency* is the tell. A ban-list overcorrects — the goal is rationing, not
   prohibition.
2. **Synonym rotation just mints the next cliché.** Several "alternatives" that
   circulate (unpack, foundational, dive into, utilize, frictionless, elegant) are
   themselves on overuse lists. The durable fixes, in order:
   **(a) delete** the word/phrase (it's usually filler);
   **(b) be specific** — name the file, number, version, consequence, or dependency the
   vague word was standing in for;
   **(c) use the plainest word** (use, show, is, careful, complex, required).
3. **The vocabulary drifts by model generation.** Wikipedia's guide tracks eras:
   GPT-4-era (delve, tapestry, testament, intricate, boasts), GPT-4o-era (fostering,
   showcasing, pivotal, vibrant), GPT-5-era (emphasizing, highlighting, enhance).
   Academic-corpus studies found "delve" *declined* after being publicly called out in
   2024 while "significant" kept climbing — so treat any fixed list as a snapshot.
4. **Scale of the evidence:** a Science Advances study of 15M PubMed abstracts found
   ~280 excess "style words" in 2024 (top markers: *delves* at 25× expected frequency,
   *showcasing* 9.2×, *underscores* 9.1×), estimating ≥13.5% of 2024 abstracts were
   LLM-processed. The Claude-specific tics below are documented in Claude Code GitHub
   issues (48 open issues citing "You're absolutely right!") and HN threads devoted to
   individual phrases ("How to stop Claude from saying load-bearing").

Within each entry, alternatives **worth remembering are bold**; the rest are listed to
show they were considered (and often why they fail).

---

## A. Claude-Code conversational tics

### 1. "You're absolutely right!" (also "Exactly right", "Perfect!", "Great question!", "I got the issue!")

Reflexive validation openers. A documented byproduct of RLHF: human raters score
agreeable responses higher, so the model leads with enthusiastic agreement regardless
of whether it verified the claim — one user counted twelve "You're absolutely right!"
in a single conversation. The damage isn't just style: it signals agreement the model
hasn't earned, so real confirmations become indistinguishable from tics.

Alternatives considered: **"Correct."**, **"Right — <restate the point>."**,
**"Good catch."** (when the user found a real bug), **"Confirmed — <what was
verified>."**, **"That matches what I found."**, "Agreed.", "Fair point.", "That's
true.", "Yes, and …", **"Partly — X holds, but Y doesn't."**, **"No — actually …"**
(when they're wrong), "Verified:", "Fair enough.", "You have a point.", opening with
the substance and no agreement marker at all.

**Verdict:** this one can't be fixed by synonym rotation — fifteen ways to say "you're
right" are the same disease. The keepers are the *calibrated* forms: plain "Correct"
when checked, "Good catch" when they truly caught something, "Partly — …" and "No —
actually …" when warranted, and most often **no opener at all**: start with the
substance. "Perfect!" after your own edit is self-praise; report what the edit did
instead.

### 2. "load-bearing" (Bill's seed example)

Borrowed from construction: a wall that carries the weight of the structure above it,
so removing it causes collapse. Claude applies it figuratively to any comment, test,
config line, or convention whose removal would break something ("that comment is
load-bearing"). It earned its own HN thread; the consensus explanation is that one
model's mild lexical bias, multiplied by billions of generated tokens, turns a vivid
phrase into an instant tell. Notably it's a *good* term — vivid, precise — and Bill's
own conventions use it ("line structure that is syntactically load-bearing"). The
problem is reflexive reuse.

Alternatives considered: **"removal breaks X"** (name the X), **"N call sites depend
on this"**, **"the build/tests rely on it"**, **"does real work — not decorative"**,
**"required for correctness"**, "essential", "critical", "relied-upon", "structural",
"foundational" (itself an AI-ism), "indispensable", "semantically significant",
"actually used", "important", "the tests would catch its removal".

**Verdict:** the specific forms win — say *what* depends on the thing and *what breaks*
without it; that's more informative than any adjective. "Essential"/"critical" are
fine generic fallbacks. Keep "load-bearing" itself for the occasional case where the
structural metaphor genuinely fits, at most once per document.

### 3. "The key insight (is)"

Labels one fact as the pivotal understanding that makes everything click. Flagged on
HN as repetitive filler — partly because the model uses it for observations that are
neither key nor insights.

Alternatives considered: **"the crux (is)"**, **"the trick (is)"** (for techniques),
**"the upshot (is)"** (for consequences), **"in short"**, "the point is", "what
matters here", "the heart of it", "put simply", "the reason is", "the core idea",
"what makes this work", "the observation that …", "the essential fact", "what changed
my mind", stating the fact with no label.

**Verdict:** usually just state the insight — if it's key, the reader will notice.
"The crux", "the trick", and "the upshot" are worth remembering because they carry
distinct meanings (the hard part / the technique / the consequence) rather than
generic emphasis. Ration all of them.

### 4. "battle-tested" / "production-ready"

Maturity-inflation claims: "battle-tested" = proven by long adversarial real-world
use; "production-ready" = safe to deploy as-is. LLMs apply both to code that merely
compiled or passed a first test run, which makes them actively misleading, not just
stylistic.

Alternatives considered: **"passes the test suite"**, **"widely used (by X and Y)"**,
**"stable since <version>"**, **"handles the edge cases we know about"**, **"works on
the inputs tested"**, "proven", "mature", "reliable", "hardened", "vetted",
"field-tested", "well-tested", "deployed", "solid", "dependable".

**Verdict:** the evidence-shaped alternatives are the only good ones — they state what
was actually verified and are checkable. The adjective-shaped ones ("proven",
"hardened", "vetted") are the same inflation in different clothes. Never claim either
original phrase for code you just wrote.

### 5. "push back (on)"

To resist or challenge a proposal or claim ("let me push back on that"). Real
workplace idiom; the model reaches for it every time it disagrees, which turns
disagreement into a ritual phrase.

Alternatives considered: **"disagree"**, **"I don't think that's right, because …"**,
**"object (to)"**, **"question"**, "challenge", "dispute", "counter", "contest",
"take issue with", "rebut", "resist", "demur", "argue the other side", "raise a
concern", "I'd argue against".

**Verdict:** "disagree" and the explicit "I don't think that's right, because …" are
better in nearly every case — they commit to a position instead of gesturing at
resistance. "Object" and "question" are precise when those are what's meant. Keep
"push back" for occasional variety only.

### 6. "honest" / "genuinely" / "to be honest" / "honestly"

Sincerity markers. The tell (noted on HN, where someone counted "honest" 57 times in
Claude's constitution): flagging one statement as honest implies the others weren't,
and the model sprinkles these as filler intensifiers ("genuinely impressive").

Alternatives considered: **deletion** (the answer ~90% of the time), **"frankly"** /
**"bluntly"** (only before genuinely unwelcome news), "candidly", "plainly", "in
practice", "realistically", "my actual view is", "truthfully", "for what it's worth",
"speaking plainly", "no sugar-coating:", "sincerely", "straightforwardly", "if I'm
being direct", the bare statement.

**Verdict:** delete. Everything you say should be honest, so the marker carries no
information. The one survivor: "frankly"/"bluntly" as a one-word warning that bad news
follows — and only there.

### 7. "synthesize"

To combine multiple sources or ideas into a coherent whole. Legitimate academic term;
LLMs deploy it mechanically for any act of summarizing or merging ("let me synthesize
the findings").

Alternatives considered: **"combine"**, **"merge"**, **"sum up"**, **"consolidate"**,
**"boil down"**, "distill" (drifting AI-ward itself), "summarize", "integrate",
"compile", "unify", "condense", "pull together", "assemble", "aggregate",
"reconcile".

**Verdict:** "combine", "merge", and "sum up" cover almost every real use plainly.
"Consolidate" when many things become one; "reconcile" when they conflicted. Watch
"distill" — it's becoming the replacement cliché.

### 8. "land" (verb, of changes)

Engineering jargon for a change reaching the main branch or shipping ("once this
lands"). Genuine usage from Chromium/Mozilla culture; one HN commenter realized
they'd absorbed it from Claude, which is the tell that it's over-frequent.

Alternatives considered: **"merge"**, **"commit"**, **"ship"**, **"finish"**,
"apply", "integrate", "goes in", "deliver", "check in", "push", "wrap up",
"complete", "is in", "arrives", "done".

**Verdict:** "merge" and "commit" are precise git verbs — prefer them because they
say *which* event happened. "Ship" for user-visible release, "finish" for plain
completion. "Land" is fine occasionally; it's real jargon, just rationed.

---

## B. Dress-up vocabulary (the "delve" class)

### 9. "delve (into)" (also "dive into", "dig into")

To examine deeply. THE canonical LLM word — 25× its expected frequency in 2024 PubMed
abstracts, and so notorious that its usage measurably *declined* after being called
out publicly in 2024.

Alternatives considered: **"examine"**, **"look at"**, **"go through"**, **"walk
through"** (for code/steps), **"trace"** (for execution/data flow), "investigate",
"study", "analyze", "inspect", "read through", "cover", "review", "probe", "get into
the details of", "unpack" (equally flagged — avoid), "explore" (borderline, also
inflated).

**Verdict:** "examine", "look at", and "go through" are the plain workhorses; "walk
through" and "trace" earn their place by being concrete about *how* the examining
happens. Avoid trading delve for "unpack" or "dive into" — same class, same tell.

### 10. "leverage" / "harness" (as verbs)

To use something to advantage ("leverage the existing cache"). Business-speak
inflation of "use"; "harness" adds an energy metaphor ("harness the power of").

Alternatives considered: **"use"**, **"build on"**, **"rely on"**, **"reuse"**,
**"draw on"**, "apply", "employ", "exploit" (good in technical contexts: "exploit
sortedness"), "make use of", "take advantage of", "capitalize on", "work with",
"benefit from", "put to work", "utilize" (strictly worse — same inflation, uglier).

**Verdict:** "use" wins almost every time; this entry is the clearest demonstration
that the plain word is the cure. "Build on"/"rely on"/"reuse" are keepers because
they say *how* the thing is used. "Exploit" is precise for algorithms. Never
"utilize".

### 11. "robust"

Resilient to errors, bad input, and edge cases. A legitimate engineering term diluted
into empty praise — LLMs call any working code "robust" without naming what it
survives.

Alternatives considered: **"handles malformed input"** (or whatever it actually
handles), **"fails gracefully"**, **"reliable"**, **"fault-tolerant"**, **"solid"**,
"resilient", "sturdy", "dependable", "hardened", "stable", "well-tested",
"error-tolerant", "durable", "sound", "defensive".

**Verdict:** keep "robust" only in its technical sense *with evidence* ("robust to
empty input — tested"). Otherwise name the property: "handles malformed input",
"fails gracefully". "Reliable"/"solid" for casual use. Unevidenced "robust" is the
new "very good".

### 12. "comprehensive"

Covering everything relevant. LLMs use it to inflate coverage claims ("comprehensive
test suite") with no denominator, making it unverifiable puffery. Also one of the
ten marker words in the PubMed excess-vocabulary study.

Alternatives considered: **"complete"**, **"thorough"**, **"covers X, Y, and Z"**
(the enumeration), **"all N cases"**, "exhaustive" (only when literally so), "full",
"end-to-end", "detailed", "extensive", "in-depth", "wide-ranging", "total",
"systematic", "broad", "all-inclusive".

**Verdict:** the enumeration beats every adjective — "covers all 12 opcodes" is
checkable, "comprehensive" is not. "Thorough" and "complete" are honest when true;
"exhaustive" only when you can prove exhaustion.

### 13. "seamless(ly)"

Without visible joins — integration with no friction, breakage, or manual steps.
Marketing vocabulary; in LLM output it decorates any integration regardless of how
many seams it actually has.

Alternatives considered: **"drop-in"**, **"no API change"**, **"no migration
needed"**, **"works unchanged"**, **"without breaking existing callers"**, "smooth",
"invisible to callers", "compatible", "clean", "transparent" (overloaded in CS —
careful), "unobtrusive", "painless", "frictionless" (same disease), "effortless"
(same disease), "integrated".

**Verdict:** the testable claims win: "drop-in", "no API change", "no migration
needed" all assert something a reader can verify. "Smooth" for casual use. Skip the
marketing synonyms — frictionless/effortless are seamless with a different coat.

### 14. "crucial" / "pivotal" / "vital" (importance adjectives)

All assert high importance: crucial = decisive, pivotal = a turning point, vital =
life-sustaining/necessary. Top-tier academic-corpus markers; LLMs attach them to
everything, which deflates them to "somewhat relevant".

Alternatives considered: **"required"** / **"necessary"** (when literally true — the
best, because testable), **"important"** (the honest generic), **"central"** /
**"main"**, **"the build fails without it"** (state the consequence), "essential",
"critical" (also inflated), "key" (also inflated), "significant" (still climbing on
LLM-overuse charts), "decisive", "indispensable", "mandatory", "core",
"fundamental" (AI-flavored), "load-bearing" (see entry 2 — circular!).

**Verdict:** prefer stating what happens without the thing; "required"/"necessary"
when true; plain "important" otherwise. Note the trap this entry demonstrates: half
the candidate synonyms (key, critical, significant, fundamental) are on overuse lists
themselves — rotation is not the cure, calibration is.

### 15. "intricate" / "nuanced" / "multifaceted"

Complexity-admiration words: intricate = many interlocking parts, nuanced = fine
distinctions, multifaceted = many aspects. LLM prose uses them to *admire* complexity
as praise; engineers mostly need to *warn* about it.

Alternatives considered: **"complex"** (plain), **"subtle"** (for
surprising behavior), **"tricky"**, **"fiddly"**, **"easy to get wrong"**,
"complicated", "involved", "elaborate", "hairy", "tangled", "convoluted" (when
criticism is intended), "delicate", "layered", "detailed", "has many interacting
parts".

**Verdict:** the honest engineer-speak wins: "tricky", "fiddly", "subtle", "easy to
get wrong" — these warn rather than admire. "Convoluted" when you mean it as
criticism. Plain "complex" otherwise.

### 16. "meticulous(ly)"

With extreme, painstaking care and precision. In LLM output it's usually
*self*-praise ("I meticulously verified…") — asserting care instead of demonstrating
it. A top GPT-4-era marker word.

Alternatives considered: **"careful(ly)"**, **"systematic(ally)"**, **"line by
line"**, **"checked each case"** (show the care), "thorough(ly)", "precise(ly)",
"rigorous(ly)", "exact", "painstaking", "scrupulous", "diligent", "methodical",
"attentive", "deliberate", "detailed".

**Verdict:** "careful" and "systematic" cover the honest uses; better still, list
what was actually checked and let the reader conclude the care. Adverbial self-praise
("meticulously") is precisely the tell — cut it.

### 17. "foster" / "bolster" / "cultivate" (vague enable-verbs)

Foster = help develop, bolster = strengthen/support, cultivate = grow deliberately.
In technical prose they're almost always vapor — code doesn't foster things, and the
sentence usually can't say what concretely improved.

Alternatives considered: **"support"**, **"enable"**, **"strengthen"**, **"make X
easier"** (name the X), **deletion of the whole clause**, "encourage", "promote",
"help", "improve", "reinforce", "increase", "aid", "back", "sustain", "nurture"
(worse).

**Verdict:** if you can name what concretely improves, use "enable"/"support"/
"strengthen" with that object; if you can't, the clause was decorative — delete it.
This family mostly signals a sentence that says nothing.

### 18. "underscore" / "highlight" / "showcase" (emphasis verbs)

All mean "make prominent": underscore = emphasize the importance of, highlight = draw
attention to, showcase = display admiringly. "Underscores" ran 9.1× and "showcasing"
9.2× expected frequency in 2024 abstracts; the construction "this underscores the
importance of X" is a signature LLM sentence.

Alternatives considered: **"show"**, **"demonstrate"**, **"confirm"**,
**"indicate"**, **"suggest"** (these three grade evidence strength honestly),
"prove", "reveal", "illustrate", "point to", "mean", "make clear", "stress",
"emphasize" (plain but now GPT-5-era-flagged), "is evidence that", "exhibit".

**Verdict:** "show" is almost always the right verb. "Confirm"/"indicate"/"suggest"
are keepers because they encode *how strong* the evidence is — a real distinction.
"Showcase" is promotional; drop it entirely.

### 19. "enhance" / "elevate" / "streamline" / "empower" (metric-free improvement verbs)

All claim improvement without naming the axis: enhance = make better, elevate = raise
in quality, streamline = make more efficient, empower = give capability. "Enhancing"
is a marker word in the academic corpus and a GPT-5-era favorite.

Alternatives considered: **"improve"** (the honest generic), **"speed up"**,
**"simplify"**, **"shorten"**, **"cut from X to Y"** (numbers!), "clarify", "reduce
<memory/latency/lines>", "clean up", "tighten", "fix", "refine", "optimize" (only
with a measurement), "ease", "polish", "strengthen".

**Verdict:** name the axis and the number: "cut startup from 4s to 300ms" beats every
verb on this list. "Speed up"/"simplify"/"shorten" when the axis is clear; "improve"
as the plain fallback. "Elevate" and "empower" never belong in technical prose.

### 20. "realm" / "landscape" / "tapestry" / "ecosystem" / "journey" (figurative nouns)

Metaphorical place/fabric/travel words dressing up "field", "situation", "set of
tools", "process". "Tapestry" is the single strongest tell — a Forbes editor: "I no
longer believe there's a way to innocently use the word 'tapestry' in an essay."
"Realm" and "landscape" (figurative) are top academic markers.

Alternatives considered: **naming the actual thing** ("the Python packaging tools",
not "the Python packaging landscape"), **"area"**, **"field"**, **"domain"**,
"space" (trendy — careful), "world", "category", "topic", "discipline", "industry",
"environment", "context", "setting", "the set of X", "the state of X".

**Verdict:** name the thing; "field"/"area"/"domain" when a generic is genuinely
needed. "Ecosystem" is acceptable in its established technical sense (package
ecosystem) but rationed. "Tapestry": never. "Journey": never in technical writing.

### 21. "testament" ("a testament to")

Evidence or proof of a quality ("its stability is a testament to its test suite") —
significance inflation that asserts a causal link while dodging the causal claim. A
top GPT-4-era marker.

Alternatives considered: **recasting around the cause** ("X is stable *because* its
tests catch regressions"), **"shows"**, **"evidence of"**, **"because of"**,
**"thanks to"**, "proof of", "reflects", "demonstrates", "result of", "sign of",
"indicates", "confirms", "credit to", "consequence of", "speaks to" (same disease).

**Verdict:** recast the sentence to make the causal claim directly — "because" is the
word "testament" is avoiding. "Shows"/"evidence of" for the evidential reading. Drop
"testament" from the vocabulary entirely.

---

## C. Phrase-level tells

### 22. "It's important to note that" / "It's worth noting that"

Throat-clearing before a point: announces significance instead of demonstrating it.
On every AI-tell list; the test is that deleting it never loses information — if it
weren't worth noting, you wouldn't note it.

Alternatives considered: **"Note:"**, **"Caveat:"**, **"Careful:"**, **"Gotcha:"**,
**"One catch:"**, **deletion** (just state the point), "NB:", "Beware:", "Warning:",
"Heads-up:", "Keep in mind" (borderline filler), "Also:", "But:", "Don't miss:",
"A wrinkle:".

**Verdict:** delete, or use the compact classifying markers — "Caveat:", "Careful:",
"Gotcha:" tell the reader *what kind* of note follows in one word, which pairs well
with the house rule that caveats attach inline to the step they affect.

### 23. "In today's fast-paced / ever-evolving world|landscape" (scene-setting openers)

Pure filler establishing that the present exists. The signature LLM essay opener;
"in today's digital landscape" and kin appear on every detection list.

Alternatives considered: **starting with the subject** (deletion), **a concrete
anchor**: "Since Python 3.13, …", "Now that X exists, …", "With the 2025 release of
X, …", "Because X changed, …", "X used to require Y; now …", a specific date, a
specific version, the specific event driving relevance, "Recently" (weak),
"Currently" (weak), "Today," (weak), "As of <date>", "Nowadays" (weak), the claim
itself with no preamble.

**Verdict:** deletion is the alternative. When context genuinely matters, make it
concrete — a version, date, or event. Every generic rotation of the opener is equally
bad; only specificity survives. (All the "weak" entries above are the same filler,
shorter.)

### 24. "It's not just X, it's Y" (negative parallelism — also "This isn't about X. It's about Y.", "No X. No Y. Just Z.")

A contrast frame that manufactures a strawman (X) so the real point (Y) sounds
profound. Wikipedia documents the whole family; there are entire posts dedicated to
alternatives for this one construction. LLMs also chain it several times per page,
which no human does.

Alternatives considered: **asserting Y directly**, **"Y, not X"** (honest contrast —
only when someone actually claimed X), **"X, and also Y"**, **"more Y than X"**,
**two plain sentences**, "primarily Y", "Y matters more than X here", "both X and
Y", "X is secondary; the point is Y", "X — and beyond that, Y", "Y, mainly", "as
well as", dropping X entirely, "chiefly Y", "Y (X is a side effect)".

**Verdict:** assert Y directly; the reader doesn't need X demolished first. "Y, not
X" survives only as a *real* correction of a *real* claim. Any alternative that
keeps the seesaw shape ("not merely… but rather…") is the same tell in formalwear.

### 25. "shed light on" / "pave the way for" / "unlock" (stock idioms — also "navigate the complexities of", "unlock the potential of", "game-changer")

Fossilized metaphors for explain/enable/allow. Individually unremarkable; LLM prose
strings them densely, and "unlock/unleash/unveil" (the "un-" family) is a noted
cluster.

Alternatives considered: **"explain"**, **"clarify"**, **"enable"**, **"allow"**,
**"means you can now X"**, **"removes the blocker"**, "reveal", "make clear", "help
understand", "make X possible", "lead to", "permit", "make X easier", "is a big
improvement", "open the door to" (same disease).

**Verdict:** the plain verbs — explain, clarify, enable, allow, lead to. "Means you
can now X" and "removes the blocker" are concrete and earn their keep. Never swap
idiom for idiom.

### 26. "plays a crucial/vital/pivotal role in" / "stands as" / "serves as" (significance inflation + copula avoidance)

Two related patterns Wikipedia documents: inflating an entity's importance ("plays a
pivotal role in the ecosystem") and dodging plain "is" ("serves as the entry point",
"stands as a landmark"). Both pad the sentence while hiding what the thing actually
does.

Alternatives considered: **"is"**, **a concrete verb** — **"handles X"**,
**"controls X"**, **"implements X"**, **"decides X"**, "does X", "is responsible for
X", "drives", "provides", "matters for X because …", "X depends on it", "is central
to", "is one of the main …", naming the mechanism, an active-voice rewrite.

**Verdict:** "is" is not a word to avoid — copula avoidance is the disease. Better
yet, say what the thing *does*: handles, controls, implements, decides. If its role
matters, the mechanism will show it.

---

## D. Structural tics (patterns, not vocabulary — no synonym lists)

These are recognized tells where the fix is structural, so a 15-alternative list
doesn't apply:

- **Em-dash density** — multiple em dashes per paragraph. The dash isn't wrong;
  the density is. Fix: allow roughly one per paragraph; use commas, parentheses, or
  a second sentence otherwise.
- **Rule of three** — reflexive triplets ("innovative, transformative, and
  groundbreaking"). Fix: one precise adjective beats three vague ones; vary list
  lengths.
- **Tailing participial clauses** — "…, highlighting the importance of X",
  "…, ensuring reliability" tacked onto sentences to add vague significance. Fix:
  end the sentence; if the significance claim is real, give it its own sentence with
  evidence.
- **Bold-term-colon lists** ("**Scalability:** the system scales…") used for prose
  that isn't actually parallel. Fix: reserve the format for genuinely enumerable
  facts.
- **Excessive inline parentheticals** (nested asides (like this) mid-sentence). Fix:
  most asides are either worth a sentence or worth deleting.
- **Elegant variation** — cycling synonyms to avoid repeating a word. In technical
  writing, repeating the exact term is correct; synonym-cycling creates ambiguity
  about whether two terms name the same thing.

---

## Sources

- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) —
  the most thorough catalog: era-specific word lists, significance inflation,
  negative parallelism, copula avoidance, rule of three.
- [Kobak et al., "Delving into LLM-assisted writing in biomedical publications
  through excess vocabulary" (Science Advances, 2025)](https://www.science.org/doi/10.1126/sciadv.adt3813)
  ([arXiv preprint](https://arxiv.org/html/2406.07016v1)) — 15M PubMed abstracts,
  ~280 excess style words, the delve/showcasing/underscores frequency ratios.
- [HN: "How to stop Claude from saying load-bearing"](https://news.ycombinator.com/item?id=48905248)
  and [HN: claudisms thread](https://news.ycombinator.com/item?id=48910656) —
  load-bearing, key insight, push back, honest/genuinely, synthesize, land,
  battle-tested, "it's not X, it's Y", em dashes; the "pre-existing words
  mechanically overused" framing.
- [The Register: "Claude Code's endless sycophancy annoys customers"](https://www.theregister.com/2025/08/13/claude_codes_copious_coddling_confounds/)
  and [claude-code issue #3382](https://github.com/anthropics/claude-code/issues/3382) —
  "You're absolutely right!" / "Perfect!" documentation.
- [Will Francis: "How to stop Claude writing like an AI"](https://willfrancis.com/how-to-stop-claude-writing-like-an-ai/) —
  banned-word/phrase/structure lists aimed specifically at Claude.
- Substack round-ups of AI-tell phrases (e.g.
  [hardlyworking1 on "It's not X; it's Y"](https://hardlyworking1.substack.com/p/how-to-avoid-sounding-like-a-stupid),
  [tanrosado's "10 phrases that scream AI"](https://tanrosado.substack.com/p/week-16-10-phrases-that-scream-ai)) —
  corroborating phrase lists and the "tapestry" editor quote (via Forbes).
