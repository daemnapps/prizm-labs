# What the prompts actually say

Audit of the video-teardown chain, 27 Aug 2026. Six real problems, two things
already fine, and the answer to how frames get made.

Artifact: (team page)

---

## The contradictions in 4b

### 1. "The placement plan" is not the placement plan

Hooks runs *before* placement, and is handed the **Reading** stage's output,
deliberately:

```json
"stage4b": { "placement_plan": "@stage4r" }
```

So the prompt's line *"The placement plan names the opening beat by timestamp"*
instructs the model to read a document that does not exist yet. It reads the
source analysis and calls it a plan.

**Fix.** Rename the variable to `source_reading` — what placement already calls
the same input — and rewrite the paragraph to talk about the reading. The
wiring does not change; the name stops lying.

### 2. The hook ledger is half-built

It is a running list of every hook this brand has made and the real quote each
one was built on. Once a quote appears there it is **spent** — hooks may not
build on it again. It exists to stop the machine re-cutting the same five
quotable lines forever.

**Correction to the first version of this note:** the file does load. The
earlier claim that it was missing came from checking the copy build's folders,
not this one. It resolved on `mara-creator-06-dbtdq1qon4a`.

The real problem: it only ever gets *read*. Hooks emits append-ready rows in
its section 5 and nothing in `machine/` ever appends them. Last entry is
20 August. So it permanently blocks ten old quotes and records nothing new,
and that gets worse every run.

**Recommendation.** Cut it from hooks — not because the repetition problem
isn't real, but because avoiding repeats *across* runs needs something that
sees all the runs, and one teardown can't. That belongs to the variation
workflow. Keep the file; it is a real record.

### 3. Two rules fight over what an opening may be

"Never open with a template" bans eight shapes outright. "Prefer a behaviour
over a condition" sets a default. Both ignore the governing fact: what the
opening should be is decided by what the source did. If the swipe opens on a
condition, the replication opens on a condition. A ban list overrides the
teardown, which is the one thing the chain exists to obey.

**Fix.** Both become subordinate to the source: the record names the opening's
shape and that governs. The banned list survives only as "these shapes signal
an ad — if the source did not use one, do not introduce one."

---

## Naming and scope

### 4. It isn't all customer language

The variable is `customer_language` and the prompts say "customer language".
The rows include prospects who never bought, commenters, churned buyers and
paid panellists. Calling all of it customer speech is the flattening the
provenance rule exists to stop.

**Fix.** Rename to `language` throughout — config and all three prompts. Same
change in the ad-copy build, which carries the identical variable.

### 5. Topics: the count was arbitrary and the examples were brand remnants

Stage 1b said "three to six" with no basis, and listed `dark-spots`,
`razor-bumps`, `shipping`, `price` as examples — two brands' vocabulary inside
a brand-agnostic prompt. It is also unnecessary: `?roster` already ships the
brand's own topic list with counts.

**Fix.** No examples, no fixed count. Define what a topic *is* — the subjects
the source actually raises — and say: use the vocabulary the roster lists, take
as many as the source genuinely raises and no more.

### 6. "Videos owed" is creator-assignment logic in a teardown

Stage 5 carries `video_count`. A teardown rips one asset apart and rebuilds it;
how many videos someone owes is a contract fact from a different workflow.

**Open — the owner's call.** Cut it, unless the brief genuinely needs to say
"make N of these".

---

## Not a problem

**Creator vs AI execution is already handled.** When a run has no creator, the
runner passes a literal instruction telling the brief it is written to no one —
"never name a creator, never reference her habits, her posts or her style." AI
execution does not break it.

---

## How frames actually get made

The scene text becomes an image prompt in four steps:

1. The brief's `Film:` line is pulled per frame.
2. Second person becomes third — `as_picture()` rewrites "you are" → "she is".
3. Rig talk and `Hear:` are stripped (the generator was drawing the sound).
4. Sent with the face anchor first, then the seed frame, then product photos,
   then the text.

**The checkpoint is retries, not review.** It tries up to four times and takes
what comes back. Nothing looks at the finished picture, so a frame wrong in a
way the prompt did not anticipate reaches the brief.

### 7. Every generated frame says "She"

Step 2 is a hardcoded list:

```python
("You are", "She is"), (" your ", " her "),
("Hold ", "She holds "), ("Squeeze ", "She squeezes "), …
```

Point this at a male avatar and every image prompt still says *she*. This is in
code, which the component's own rule covers explicitly: "a word list, a regex, a
path or a default that only makes sense for one brand is a bug, not a shortcut."

**Fix.** Rewrite to a neutral third person — "the person", "their" — or take the
subject from the run rather than assuming it. The face anchor already carries
who it is; the words do not need to guess.

---

## Found by re-running it

### 8. Stage 1b asked the opposite question halfway through

The fresh run halted here and the halt was right. 1b answered `none fit` —
the source is a mother-of-the-bride dress poll that never raises a skin
subject, and the brand's only avatar is defined by one. A correct reading of
the source; the previous run had forced it onto that avatar unnoticed.

The rule underneath was wrong. The prompt opened with *"Decide who our version
speaks to"* and twenty lines later said *"You are deciding who the source
actually speaks to."* Opposite questions. On a swipe from another category
they give opposite answers — and rejecting off-category sources rejects
exactly the videos worth swiping.

**Fixed (v3).** The question is who *our* version speaks to. The source is
evidence about structure, never a veto on the avatar. `none fit` is reserved
for the one real case: the brand has no avatar this product could be written
to at all.

### 8b. Bank size was being used as an argument (v4, then v5)

1b then chose `funnel: customer` partly because *"this is the bank with real
depth (270 rows) versus a thin prospect bank (60)."* The "never pick the
biggest bank" rule existed but governed only the avatar, so the funnel walked
through the hole.

**the owner's ruling:** the funnel is not a judgment about the reader — *"it's all
dependent on the swipe to determine what level to pick from."*

**Fixed (v5).** The level is read off the source: what it explains, and what
it takes for granted. Three printed steps, then the funnel that combination
describes, with the moment that settles it. A thin bank is a finding, never a
reason to move. Verified: the same 60-vs-270 fact now appears as a limitation
and `prospect` stands.

### 9. Two rules fought over how different the variations may be

A rule added at v5 of the hooks prompt — *"a variation changes one thing about
the control and holds everything else"* — explicitly overrode the four-words
test written to stop near-identical lines. The v5 rule won, and five hooks
shipped sharing *"Three dresses… I need you to help me."*

**the owner's ruling:** *"I need bigger swings that still fit the format."*

**Fixed (hooks v11).** Each variation enters on a different moment, behaviour
or verbatim. "Fits the format" is now explicit and narrow: the format's
currency (spoken line / card / frame), its register and length from the spec,
and not being an ad-template the source did not use. The device case survives
capped at one variation. New ENTRY TEST prints what each variation is built
from; two sharing an entry means one is not a variation.

### 9b. The opening's formation was over-constrained

Finding 3's fix made the source's opening shape binding — *"if the source
opens by asking the viewer something, all five ask the viewer something."*

**the owner's correction:** the opening *"can be literally any formation sourced
from the language and context of the script."*

**Fixed (v11).** The formation is free. What governs is the material: every
opening is built from the language rows and the script's own context. The
source's opening is context to work from, never a template to copy.
