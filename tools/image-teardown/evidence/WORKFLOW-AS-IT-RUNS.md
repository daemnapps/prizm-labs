# The image lane, described plainly — how it actually ran on 2026-08-19

Filed verbatim as evidence, in my own words, for breakdown into a workflow.
This is what happened, not what the docs say should happen.

## What the workflow is for

the owner has static ads running that work. He wants more of them without a
designer: take an ad that performs — his own, a competitor's, a swipe — and
either reproduce it exactly, or produce variations of it that hold the same
layout while the words and the picture change. The end state is that a
variation costs a prompt and a minute, not a designer and a day.

## Who does what today

**the owner** supplies the source image and the judgement. He looks at the output
and says whether it is right. Every ruling in this build came from him looking
at a picture: the images are garbage, the spacing is wrong, think like a
graphic designer, clone it exactly before you vary anything. He also owns the
brand facts — the offer file, the guarantee wording, the likeness position —
and every decision the chain refuses to make on its own.

**Claude (me)** runs everything else: writes and edits the prompts, calls the
models, writes the tooling, reads the outputs, finds the defects, and reports.
No other person was involved.

**Gemini 3.1 Pro** does all the reading and writing — the teardown, the clone
spec, and every stage of the variation chain. It sees the image directly for
stage 1 and works text-to-text after that.

**fal.ai (Seedream 4.5)** generates the photographs. Text-to-image for a first
plate, image-edit for everything after, so a character and a composition can be
held by reference.

**ImageMagick** sets the type. Nothing renders words through the image model.

## How a run actually goes

1. **Get the image.** A file from the owner, a scrape, or a folder. Instagram pulls
   go through an Apify actor.
2. **Teardown** (`stage1`, Gemini + the image). Produces a long record: frame
   spec, subject and setting, a zone table with every element positioned as a
   percentage, the layout system — margins, alignment axis, vertical rhythm,
   type scale, measure in characters per line, keep-clear regions — then the
   reading path, the psychology, an index.
3. **Then one of two paths.**
   - **Clone:** `stage1C` turns the teardown into a plate prompt, accept tests,
     and the type layer as JSON. Generate the plate on fal, set the type with
     ImageMagick, put it beside the original.
   - **Vary:** stages 2 → 5 abstract the format, inject the brand, decide
     placement and ratios, write six headlines, add support copy, add the offer
     block, and emit generation prompts plus a job list.
4. **Generate and composite.** `iterate.py` runs the job list against fal and
   collects a manifest; `compose.py` sets the type layer over each plate.
5. **Look at it.** the owner looks. The loop restarts wherever he points.

## What hurts

**Nothing checks itself against the source until a human looks.** Every real
failure this build had — the wrong ad generated six times, five lines of type
over a subject's face, a competitor's bottle in frame, a clone that was not a
clone — was found by a person looking at a picture. The chain produced clean,
confident, well-formatted output every time.

**Defects propagate silently and get expensive fast.** Stage 2 dropped a person
from the record and turned a demonstration into an assertion. Nothing
downstream re-read the record, so six plates of the wrong ad were generated
before anyone noticed. One wrong sentence at stage 2 cost the whole batch.

**Measurements are recorded as prose and lost on the way to the tooling.** The
teardown said the headline was white with the last words in orange; the JSON
that drove the renderer had one colour field, so the accent vanished. Same for
line breaks, same for typeface width class.

**Copy length and layout are decided in different places by different stages,
and nobody reconciles them.** Stage 4c added a sentence, stage 4d added an
objection line, and stage 5 sized type from the *source's* word count. The
result did not fit and nothing objected until it was rendered.

**The renderer had to become a typesetter mid-flight.** It started by stacking
blocks at absolute positions. Every layout defect — collisions, text off the
frame, a badge as a wide bar with the words shoved left, a lost full stop — was
a compositor bug found by rendering and looking. That is six rounds of
debugging in front of the person the work is for.

**Generation drifts unless you hand it a picture.** Describing a composition in
prose produces a different frame every run. Two references — one for who, one
for where — fixed most of it, and prose in the same prompt still overrides the
reference when the two disagree.

**Some things exist but never run.** The hook ledger has never had a row
written to it: stage 4b emits ledger rows and nothing appends them, so the
anti-repetition machinery has never actually operated.

**Brand facts collide with layouts and nobody rules.** The approved guarantee is
86 characters; the zone it must live in measures 27. The chain correctly refuses
to shorten it and correctly flags it. It has been flagged three times and is
still not decided.

## What I would change

1. **Clone before vary, with a hard gate.** Already the ruling. A format that
   cannot be reproduced cannot be varied, because the clone is the control.
2. **Every stage carries the measurements forward as data, not prose.** One
   machine-readable spec object that stage 1 creates and every later stage
   reads and never re-derives. Most of the damage came from a stage inventing a
   number it should have inherited.
3. **Automate the comparison.** A side-by-side and a difference report should be
   produced by the run, not by me deciding to look. Cheap checks first: does
   every zone still clear its keep-clear box, does the copy fit its measure, is
   the type share inside budget.
4. **Make the accept tests block.** Stage 1C already writes them. Nothing
   enforces them. A plate that fails one should not reach the compositor.
5. **Fail loudly on inherited slots.** Stage 5 marked a rights slot RESOLVED by
   reasoning about it. Slots that name a fact — a price, a claim, a consent —
   can only be filled from a file or by a named human.
6. **Close the ledger loop**, or stop pretending it exists.
7. **Decide the guarantee.** It is one decision and it blocks the offer block on
   every ratio.
