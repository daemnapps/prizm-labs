# Email lane — stage deltas

The whole design in one page: what each stage changes from the copy chain,
and what it deliberately leaves alone. Read this before editing a prompt.

The rule the image lane set and this lane keeps: **reuse the name wherever the
job is the same job.** A stage that does the same thing gets the same number,
the same variable names and the same output shape, so the four lanes stay one
system and a fix in one is a fix worth porting to the others.

---

## 0 · Triage — `stage0-triage-v1-damon.md`

**Same:** lane (`ALREADY AN AD` / `ORGANIC`), voice binding, whether the
speaker is identifiable.

**Changed:** the lane test, and two new answers.

- **The lane test for email.** Not "is it polished" — every email is polished.
  The test is whether the email was **built to sell in itself**. A sale email,
  a launch, an abandoned-cart: `ALREADY AN AD`. A newsletter, a story, a
  how-to, a founder's note that happens to have a link at the bottom:
  `ORGANIC`. When genuinely between, default `ORGANIC` — building structure
  that turns out redundant is cheaper than assuming structure that was never
  there.
- **`FORMAT`** reads from `formats.md`, which is an email list, not the copy
  lane's. Campaign or flow, and which one.
- **`SENDER`** — new, email only. Brand name, a person's name, a person at the
  brand, or a support address. This is part of the argument, not metadata: the
  same words from "Brand A" and from "NOVA at Brand A" are two different
  emails. Everything downstream binds to it.

## 1 · Read — `stage1-read-v1-damon.md`

**Same:** observation only, lines quoted never paraphrased, voice markers,
what the source conspicuously never does.

**Changed:** the record covers the whole envelope, not just the body.

- From-name and from-address shape, subject **and** preview text quoted exactly
- The blocks in order, typed (copy / image / button / review / divider / PS)
- CTA census: how many, where each falls in the scroll, what each button says
- Link census: how many distinct destinations, and whether the copy links
  inline or only through buttons
- Weight: roughly how much is image and how much is text, and how many phone
  screens it runs
- Where the offer appears and where it does not

Same discipline as everywhere: this stage **observes**. It does not say what
would work better.

## 2 · Spec — `stage2-spec-v1-damon.md`

**Unchanged in intent, and this is deliberate.** The construct is brand-free
*and medium-free* — that is why a video teardown can feed the email lane at
all. It abstracts the argument, not the envelope.

The email-specific addition is the section the copy lane calls WHAT IS
MEDIUM-BOUND: here it names what was **inbox-bound**. A subject line's job is
to buy the open; a preview text's is to buy the first line; a hero image's is
to survive image-blocking. Those jobs are real and they must be named so a
later stage can achieve them — but the devices themselves do not transfer to
any other medium, and nothing downstream may treat "it had a hero image" as a
structural requirement.

## 2b · Context scout — `stage1b-context-scout-v1-damon.md`

**Unchanged.** Indexes the brand tree at run time, picks what *this* source
needs, publishes what it deliberately left out. It must finish the sentence
"the email will be different because this was read" for every file.

## 3 · Injection — `stage3-injection-v1-damon.md`

**Same:** substitution, never rewrite. `[UNFILLED: …]` rather than a deleted
move. Voice rules outrank house style, collisions logged.

**Changed:** the sender binding is now one of the things injection is
accountable for. If triage named a person, every first-person line in the
email is that person's, and a line the brand would say but the person would
not is a defect at this stage, not a note for later.

## 4 · Placement — `stage4-placement-v1-damon.md`

**Same:** decides, writes nothing. The source's own position is the default;
moving the product earlier needs a stated reason. Room is never bought by
compressing a source beat — an overrun is escalated with a number.

**Changed:** three email budgets replace the copy lane's single length budget.

- **Scroll budget** — in phone screens, taken from the source's own length
- **CTA plan** — how many buttons, where each falls, and whether the first one
  comes before or after the argument is made. The source's count is the
  default and adding a CTA needs a reason.
- **Image plan** — how many image blocks, what each is for. Every one becomes
  a job for the image lane, so an image with no stated job is not planned.

## 5 · Subject lines — `stage5-subjects-v1-damon.md`

The copy lane's hooks stage, renamed for what it actually writes here.

**Same:** VERSION 0 is the control, swiped straight, and may not be improved.
Variations each do a genuinely different job. Voice rules absolute. Never
spend one on a claim the files do not carry. Never reuse ground the hook
ledger records as spent. **All ship — the machine never picks.**

**Changed:** the unit is a **pair**, always.

Every version is a subject line *and* the preview text that runs under it,
written together. The preview is not a summary of the subject and it is not
the first line of the email — it is the second half of a two-part opening, and
its job is to buy the first line of the body. A version that ships a subject
without its preview is incomplete.

Plus, where triage allows it: a from-name variant, called out separately, so a
test of the sender is never confounded with a test of the words.

## 6 · Expansion — `stage6-expansion-v1-damon.md` · **gated**

**Unchanged, including the gate.** Runs only when the lane is `ORGANIC`. Five
candidate moves — problem, mechanism, proof, objection, ask — each gated, and
NOT NEEDED is the honest answer most of the time. Never trims a source beat to
pay for an addition; never changes voice.

## 7 · Close — `stage7-close-v1-damon.md`

**Same:** the objection where the reader flinches, then the landing the
construct calls for. Offer figures verbatim, conditions travelling with
guarantees. Assembles the whole thing so it can be read end to end.

**Changed:** email has one more landing than copy does — the **PS**. It is
optional and it is not a place to repeat the CTA. It exists when there is a
second, weaker reason to act that would have cluttered the argument. When
there isn't one, the honest answer is no PS.

## 8 · Build — `stage8-build-v1-damon.md`

The copy lane's Render stage, doing the same job for a different object.

Turns the argument into the email as it will actually be assembled: an ordered
list of typed blocks, each carrying its copy verbatim, and for image blocks a
direction and alt text.

It emits the human-readable version **and** a fenced ```BLOCKS JSON array, so
`render.py` draws the page deterministically instead of a script parsing
prose. The two must agree; the JSON is the one that renders.

Block vocabulary is fixed and lives in `render.py`. A stage that needs a new
block type says so; it does not mint one.

## 9 · Brief — `stage9-brief-v1-damon.md`

**Same shape as the copy lane's**, pointed at whoever builds it: what it was
built from and whether that was an ad or a post, the format, whose voice and
whose name it goes out under, every subject/preview pair with the control
marked, the blocks in order, the image jobs, the offer, what to watch, and
anything unresolved — stated plainly rather than smoothed over.

---

## What email does not get

- **A send-time or segment stage.** When an email goes and who receives it is
  the campaign calendar's job, not the asset's. This lane makes the asset.
- **A compliance stage.** Dropped from the copy chain on the owner's call
  2026-08-25 and not reintroduced here. Pricing and offer are a separate
  concern.
- **A deliverability stage.** Link count and image-to-text ratio are recorded
  at stage 1 as facts about the source. They are not a gate.
- **An audit stage.** The video chain's 4e has no equivalent in any text lane
  yet. Worth having; not now.
