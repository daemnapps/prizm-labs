# Scene production — a brief in, cut-ready scenes out

> **In development (lab).** Proven on one format so far; the method is
> written to be format-agnostic and has not yet been run end to end on a
> second one. See `CLAUDE.md` for what graduation is waiting on.

Hand this method a brief and it carries the work end to end: every scene
generated, consistent with every other scene, delivered as a set an editor
can cut without asking a single question.

**It does not care what format the brief is.** A four-hander with a story
that turns, one creator talking to camera, a wordless product
demonstration, a testimonial montage — the format changes what a scene
contains. It never changes how a scene is made consistent, which is the
part that is hard and the part this method is.

Generalised 2026-09-01 on the owner's word: *"a workflow that can build on any
brief I give it so AI can carry it out end to end to the point of getting
all scenes ready for an editor to cut up."*

---

## The two ideas everything rests on

**The model cannot remember — it can only read.** Consistency between
scenes never comes from the model holding onto anything. It comes from the
same facts being pasted into every scene prompt, word for word: the same
wardrobe block, the same positions, the same product line, the same grade
sentence. Repetition is the mechanism. Every rule here is either a fact to
repeat, or a way to stop a fact from drifting.

**The identity carries the face; the text carries the clothes.** Leave
wardrobe to a reference photograph and the model dresses your character in
whatever that photo happened to show. Leave the face to text alone and it
drifts within three scenes. Both channels, each doing only its own job.

---

## The pipeline

```
    a brief
       ↓
 01 · PRODUCTION DOCUMENT      every fact decided once, before anything costs money
       ↓
 02 · IDENTITIES               each recurring face and object trained once, ever
       ↓
 03 · SCENE PROMPTS            assembled from constants + this scene's variables
       ↓
      GENERATE                 the whole set in one batch
       ↓
      QC GATE                  against the production document, before anything moves
       ↓
 04 · HANDOFF                  a cut-ready set, and the edit method if we cut it
```

| Document | What it is | When |
|---|---|---|
| [`01-production-document.md`](01-production-document.md) | Every fact the piece needs, decided before generation: cast locks, set, ledgers, per-scene mechanics, the anti-drift checklist | Once per piece, first |
| [`02-identities.md`](02-identities.md) | How a face or an object becomes a trained identity that holds across every scene and every future piece | Once per subject, ever |
| [`03-scene-prompt.md`](03-scene-prompt.md) | The eleven sections a scene prompt is assembled from, and the six ledgers pasted through them | Once per scene |
| [`04-handoff-and-edit.md`](04-handoff-and-edit.md) | What the editor receives and what it guarantees — plus the edit method when we cut it ourselves | Once per piece, last |

## Formats

A format profile says what a piece of that shape *contains* — how many
people, how many places, who talks to whom, how long. It never changes the
method. Profiles live in [`formats/`](formats/):

| Profile | Shape |
|---|---|
| [`micro-drama`](formats/micro-drama.md) | Several characters, one continuous set, a story that turns, an offer at the end |
| [`single-presenter`](formats/single-presenter.md) | One person to camera across several locations — the UGC shape |
| [`demonstration`](formats/demonstration.md) | The product doing the work; hands and results, little or no face |
| [`testimonial-montage`](formats/testimonial-montage.md) | Several different people, one claim each, no shared space |

Writing a new profile is the whole cost of supporting a new format. Copy
the nearest one, change what a scene contains, leave the method alone.

## The slots

Nothing here names a brand, a product, a person or a place. Brand detail
arrives through slots resolved from `brands/<brand>/` when the production
document is written (workspace rule 7):

| Slot | Resolves to |
|---|---|
| `{brand}` | the brand this piece is for |
| `{product}` | its product file — name, packaging, claim language, offer terms |
| `{cast}` | the people, **by role, never by name**, so a script survives a recast |
| `{set}` | the place or places the piece happens in |
| `{grade}` | the look, chosen once and repeated verbatim |
| `{avatar}` | who this is written to; the cast is built to look like them |

Roles, not names: `{LEAD}` whose story this is, `{FOIL}` who they
confront, `{WITNESS}` caught between, `{AUTHORITY}` who knows the truth
and carries the offer. A single-presenter piece uses only `{LEAD}`. A
demonstration may use none.

## What this method does not decide

The model. Identity training, generation and editing are described by what
they must achieve — a trained identity, audio in the same pass — never by
vendor (the owner's standing model-agnostic ruling). Where a document names a
capability, that is a requirement to satisfy, not a product to buy.
