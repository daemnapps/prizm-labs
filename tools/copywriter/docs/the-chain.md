# The chain

Ten stages, mirroring the video teardown chain (`components/video-teardown`) stage for
stage. Rebuilt 2026-08-25 on Damon's call — the first shape was invented, this
one is derived from a chain that already worked.

## What goes in

One `source`, of either kind:

- **A teardown record** — video ad, organic video, image ad, organic image,
  or caption
- **Raw copy** — a swipe

There is no separate "existing copy" input and no bank-match stage. Damon's
two live <brand> ads are swipes; existing copy is a source, not something to
match against. That collapse removed a whole stage.

## The stages

### 0 · Triage — `stage0-triage-v1-damon.md`
Three answers, and everything downstream binds to them.

- **Lane** — `ALREADY AN AD` or `ORGANIC`. The test is not tone or polish but
  what the piece was *built to do*. A slick creator post is organic; a
  scrappy phone-shot ad is an ad. When genuinely between, it defaults to
  ORGANIC, because building structure that turns out redundant costs less
  than assuming structure that was never there.
- **Format** — one key from `bank/formats.json`. What the source *is*, not what we
  might turn it into. An unlisted shape is reported as unlisted rather than
  forced into the nearest key.
- **Voice** — whose mouth this comes out of, and the binding that follows.

Plus: what it's about, what it's doing, length, and whether the speaker is
identifiable — which decides whether later stages may write first-person
claims a real human would have to stand behind.

### 1 · Read — `stage1-read-v1-damon.md`
An objective record. Observation only. Handles either input kind: reads a
teardown that already exists (without redoing or contradicting it), or tears
down raw copy the way the video chain tears down a video.

Beats in order with lines **quoted, never paraphrased**; the opening in full;
the turn (or `no turn` — some formats have none and inventing one distorts
the spec); every specific proof; the close; **voice markers**, which are the
most load-bearing section when the lane is organic; and what the source
conspicuously never does, because absences are structure too.

### 2 · Spec — `stage2-spec-v1-damon.md`
The record abstracted into a **brand-free construct**: same beats, same order,
same lengths, same voice rules, with every specific thing turned into a
labelled slot.

**This is the stage the first chain lacked.** Writing from a record produces
copy *about* our brand in roughly the source's direction. Writing from a
construct puts our brand *into* the source's shape. Only the second
replicates anything.

The test: the construct should be equally usable by a skincare brand, a
supplement and a piece of software. If it isn't, it's still a record.

### 2b · Context scout — `stage1b-context-scout-v1-damon.md`
Indexes the brand tree at run time — including each file's own `status`,
`contested` and `known-issues` lines — and picks what *this* source needs. It
must finish the sentence *"the copy will be different because this was read"*
for every file, and publish what it deliberately left out.

### 3 · Injection — `stage3-injection-v1-damon.md`
Fill the slots. Substitution, never rewriting. A slot with no honest filler
becomes `[UNFILLED: …]` and the move stays standing — a later stage can
rewrite around a marked hole, never recover a deleted one.

Voice rules bind over house style. Where a language-bank phrasing collides
with a voice rule, the voice rule wins and the collision is logged.

### 4 · Placement — `stage4-placement-v1-damon.md`
Where the product enters and the length budget. Decides; writes nothing.

The source's own position is the default and moving it earlier needs a stated
reason. The source's proportions are structure. **Room is never bought by
compressing a source beat** — an overrun is escalated with a number, not
absorbed.

### 5 · Hooks — `stage5-hooks-v1-damon.md`
**VERSION 0** is the source's own opening, substituted and otherwise
untouched. It may not be improved — an upgraded control measures nothing.
Then variations, each doing a different job, each in the bound voice, none
reusing ground a hook ledger records as spent.

**All ship. The machine never picks.**

### 6 · Expansion — `stage6-expansion-v1-damon.md` · **gated**
Runs **only when the lane is ORGANIC**. An already-DR source inherited its
structure at injection; building another on top would be two arguments in one
piece.

Five candidate moves — problem, mechanism, proof, objection, ask — each
gated, and NOT NEEDED is the honest answer most of the time. Never trims a
source beat to pay for an addition; never changes voice.

### 7 · Close — `stage7-close-v1-damon.md`
The objection where the reader flinches, then the landing the construct's
shape calls for — not the landing an ad would have. Offer figures verbatim,
conditions travelling with guarantees. Assembles the whole piece so it exists
in one place and can be read end to end.

### 8 · Brief — `stage8-brief-v1-damon.md`
What the buyer opens: what it was built from and whether that was an ad or a
post, the format, **whose voice it's in**, the full copy, every hook with the
control marked, what to watch, the offer, and anything unresolved — stated
plainly rather than smoothed over.

## The gate, in one line

`ALREADY AN AD` → structure inherited, stage 6 skipped.
`ORGANIC` → structure built from nothing, stage 6 runs.

Lifted unchanged from the video chain's `ROUTES`.

## What was dropped, and why

- **Compliance** — Damon's call, 2026-08-25. Pricing and offer are a separate
  concern, not a copy-writing stage.
- **Bank match** — dissolved when existing copy was understood as a source.
- **Audit** — the video chain's stage 4e (seven checks, reports, gates
  nothing) has no equivalent here yet. Worth having; not now.
