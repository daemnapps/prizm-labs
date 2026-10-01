# Frames are made by EDITING, not by generating

**Damon's ruling, 2026-09-02**, reached by working one scene until it was
right. This supersedes the "describe the scene and generate it" approach in
the frames stage. Everything below was proven on a real run — the <run>
song ad, torn down for the brand — and every number in it is measured, not
estimated.

---

## The one rule

**An edit instruction must never describe anything the source image already
shows.**

That is the whole finding. Length was a symptom; re-description was the
disease. An instruction that describes the room, the aisle, the shelves and
the blocking is telling the model to *rebuild* them — which is the
generation we were trying to escape.

## Why generating was failing

The frames stage was building a picture from a paragraph while a perfectly
good picture — the seed still, cut from the source at that timestamp — sat
unused as a hint. It already contained the framing, the blocking, the room,
the light, the lens and the pose. Throwing that away and rebuilding it from
words meant every drift had to be corrected with another written rule.

Each rule was sensible alone. Together they made the prompt argue with
itself. One frame's prompt, measured:

| | |
|---|---|
| length | **4,262 characters** |
| women described | **2** — a trained identity's description AND the brief's character |
| outfits pasted | **5** — all four of the lead's, plus a second character's |
| result | the model blended them and put the mistress's denim jacket on the lead |

QC then flagged **144 deviations across 54 of 60 frames** — which read as 144
failures and was really one failure counted 144 times.

## What "recreate this image with these words" actually is

It is an **edit off a reference**. The picture carries the composition; the
words carry only the change. Measured on the same scene, same source frame:

| approach | instruction | outcome |
|---|---|---|
| generate from description | 4,262 chars | wrong wardrobe, blended faces, garbled caption |
| edit, but still describing the scene | 766–1,133 chars | better composition, caption still missing or wrong |
| **edit, delta only** | **204–386 chars** | scene held, wardrobe right, **caption legible** |

The caption is the tell. Text had never once rendered correctly through
generation, and rendered perfectly the first time an edit was asked for it —
because writing text onto a real image is a different task from inventing it.

## The three defects that hid inside "edit"

Switching to editing did not fix it by itself. Reading the machine's own
instruction beside a hand-written one that worked exposed three:

1. **It dressed the wrong person.** The lead's identity and wardrobe were
   applied to every frame regardless of who was on screen. A shot written as
   *"Michelle's point of view down the aisle — the Mistress waves"* has
   Michelle BEHIND the camera, and the instruction told the model to turn the
   Mistress into her.
2. **It leaked markup.** `**Film:**` reached the model as content.
3. **It truncated mid-word**, ending an instruction on *"Shallow focus hol"*.

## The chain that solves it (Damon, same day)

**Use the image teardown to UNDERSTAND the frame, then use that
understanding as the reference for the edit.** The frames stage stops
guessing who is in the picture and reads it instead.

    the seed still
        └── image teardown (stage 1) → what this frame actually contains:
            who is in it, what they wear, the palette, the treatment
        └── replication spec (stage 2) → the frame split into
            LOAD-BEARING (never change) and SWAPPABLE (may change)
        └── THE EDIT = keep the load-bearing list · change the swappable ones

On the worked scene the spec returned, unprompted:

> **Load-bearing** — the clash of wholesome 3D-animation aesthetics against
> mature infidelity text; the mundane grocery setting; first-person
> confessional copy.
> **Swappable** — the wardrobe; the retail environment.

That is a machine-readable delta. The edit becomes mechanical, the keep/change
split is a written decision rather than a guess, and it is reviewable.

## Type is a layer, never a generation

**Generate the scene clean; put the words on afterwards.** The final step of
the worked scene removed the caption entirely and rebuilt the shelves behind
it, leaving a clean character plate.

- Text can never garble, because the model never renders words.
- The copy stays editable without regenerating the picture.
- One plate carries every hook variation — captions become free variations.

`image-teardown/tools/compose.py` already sets a type layer over a
plate. Both halves existed; they were simply not connected.

## The model house for PEOPLE (Damon's ruling, 2026-09-03)

Chosen by bake-off, not by argument: the same reference and the same prompt
through four models, judged side by side.

| Job | Model |
|---|---|
| **People — the default** | **Ideogram Character** (`fal-ai/ideogram/character`) — built for character consistency across images, which is exactly the problem |
| **People — the peer** | **Seedream 4** (`fal-ai/bytedance/seedream/v4/edit`) |
| **Fixing one thing in a finished frame** | **Nano Banana edit** — a wrong product, a bad detail. Its strength is preserving what it is given, which makes it the right EDITOR and the wrong generator of people |
| Motion | Seedance Pro image-to-video |

**Everything is 9:16.** These are social ads. `image_size: portrait_16_9`
on Ideogram; the equivalent on anything else. A landscape frame is a defect,
not a style choice.

**And the look has to be asked for.** Every one of these models defaults to
a polished studio result. Left alone they produce a portrait; the ad needs a
photograph. What earns the realism is naming the camera and the carelessness
— shot on an older phone by a family member, handheld and tilted, blown
highlights, sensor grain, head off-centre, no grading, no retouching — plus
naming the place honestly and refusing the performed smile.

## Trained identities are PARKED (2026-09-02)

**They are off by default. `--use-identities` brings them back.**

They were solving identity consistency, which edit-first now solves better:
the source frame carries the person. And they actively fight the one job
left over — converting a cast member into a format's visual style — because
**a LoRA trained on photoreal images encodes "photoreal"**, so asking it for
an animated look fights its own training. Four attempts, same result.

The same day showed the mirror problem in the other tool: an image EDIT is
built to preserve its source, which is exactly why it excels at scene work
(keep the aisle, change the sweater) and exactly why it refuses a full
aesthetic conversion (keep only who she is, change how everything is
rendered). Both tools are strong; neither does this job.

Nothing was deleted. Every `lora.json` stays where it is, and the flag is
the way back in. **Open question, unsolved:** what tool converts a photoreal
cast member into a format's style while holding identity. Candidates worth
one cheap test each — a purpose-built style-transfer model, or training a
STYLISED LoRA from stylised source images rather than restyling a photoreal
one.

## What this retires

- The caption instruction inside the generation prompt.
- The wardrobe menu (every outfit pasted into every frame).
- The written identity block wherever a trained identity is attached — a
  LoRA IS the person, and describing a second one is the contradiction.

Each was a rule compensating for information we had and discarded.

## The order to work in, next time

1. **Read the artifact before regenerating.** Both breakthroughs came from
   reading — the side-by-side, then the instruction file itself — never from
   another run. Regenerating to see if it improved is the expensive way to
   learn nothing.
2. **One scene until it is right**, then scale. Sixty frames of a wrong
   template is sixty times the cost of one.
3. **Measure the instruction, not just the picture.** Character count,
   how many people it describes, how many outfits. The prompt is the
   artifact that was broken; the pictures were only the symptom.

## Still open

- **The casting collision.** The brief invents its own characters while the
  machine casts from the brand's AI cast, and neither knows the other exists.
  Both fired on this run: the brief wrote Michelle, the machine cast Susan.
  Damon's call, unresolved: does the cast list feed the brief, or does the
  brief cast freely and an identity get trained per story?
- **Wiring the image teardown into the frames stage** so the understand →
  spec → edit chain runs per frame automatically. Proven by hand, not yet
  built.
- **Cloning versus making it ours.** A faithful edit of a frame whose cast
  was inherited wholesale from the source reproduces the source. Damon's
  current call is clone first; the cast becoming ours is the later move.
