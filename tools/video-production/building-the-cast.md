# Building a cast that holds

> **THIS IS NOT A FORMAT.** Building a character is its own process, done
> ONCE per person, and the result serves every format without being
> rebuilt. A format *consumes* a character; it never makes one. Song ad,
> micro-drama, demonstration — same cast, no rework. Keep this separation:
> the moment character-building leaks into a format, every format starts
> reinventing the same people.
>
> **What a built character is, as of 2026-09-03:** a folder in
> `brands/<brand>/ai-cast/<name>/` holding `character.md` (who she is),
> `master-sheet.png` (the face reference) and `boards/` — and the boards
> matter more than they look. `boards/details.png` carries her hands,
> forearms and lower legs, which is the SKIN reference every format needs.
> **Crop those panels; never regenerate them.** Four generations were spent
> inventing age spots for a character whose own board already had them.
>
> A format's reference set is: her master + the crops from her boards.
> Nothing else, and nothing invented.

A character has to be the same person in the first scene and the last, and the same
person again in next month's ad. That is one problem solved in two
channels at once, and the split between them is the whole technique:

> **The identity carries the FACE. The text carries the CLOTHES.
> They never mix.**

Leave wardrobe to the reference photograph and the model dresses the
character in whatever that photo happened to show. Leave the face to text
and it drifts within three scenes. Both channels, each doing only its own
job, and the cast holds.

---

## 1 · What a trained identity is

A **trained identity** is that person's face learned into a small model
file, once, from a set of images. After training, any generation can call
that identity and get the same person — with no reference photo attached
at all. This is different in kind from showing the model a picture and
asking it to match: a trained identity is *known*, not *referenced*.

Proven on this workspace's own cast: a character trained from her image
set generated across four unrelated scenes — with **zero reference images
passed** — came back recognisably the same woman every time, carrying her
distinguishing marks unprompted.

The machine has a tool for this: `components/identity-training/`, which
takes a brand's character, retained creator or product and returns a
trained identity recorded as `lora.json` beside that asset in the brand
folder. Model-agnostic by design — the tool picks the trainer; this
document only specifies what the result must do.

## 2 · Where the training images come from

| The subject | The training set |
|---|---|
| **An AI cast character** | Their certified board set — master plus every board panel, sliced into individual images. The boards you already built ARE the curriculum. |
| **A retained creator** (a real person under contract) | **Her own footage.** Frames sampled evenly across a video she published. She is contracted, the ad is of her, and nothing else looks like her. |
| **A product** | Every clean packshot, plus rotations, plus close crops of the label bands — the crops are what teach the typography. |

**A hero character deserves more than one source.** Several angles and
expressions of the same face train a stabler identity than a single
photograph. One image trains; three trains better.

## 3 · The four ways training fails

**No face in the photograph.** Submitting a product shot, a texture plate
or a cropped hand as a person's training set fails outright — twice, in
the production this method came from, before anyone checked. *Verify every
training image actually contains a clear, sharp, large-enough face before
you train.*

**Too many jobs at once.** Trainers cap concurrent work. Train in small
waves, wait for completions, queue the rest.

**A timeout is not a failure.** A poll that times out usually means "still
training". Re-poll before you retrain — retraining a job that was already
running wastes the money and the wait.

**A contaminated set.** An image showing two products, or two people,
teaches both. One subject per training set, always.

## 4 · What the product identity can and cannot do

A trained product identity holds **colour, shape, proportion, logo and
layout** — reliably, across scenes, with no reference attached.

It does **not** reliably hold **small type**. At hero size, where the label
fills the frame, generated text wobbles no matter how it was trained. This
is a ceiling, not a bug to be prompted around.

**So the rule is:** the trained identity carries the product wherever it
lives in the scene — in a hand, on a counter, mid-action. Where the label
is the shot, **composite the real packshot instead of generating it.** The
artwork stops being drawn at all, so it cannot be wrong.

## 7 · Where a trained identity lives

**The record is `lora.json`, sitting beside the subject it belongs to** —
in that brand's folder, next to the character's own page or the product's
own images. Nothing is filed centrally, because a subject and its identity
should never be able to drift apart.

```
brands/<brand>/ai-cast/<character>/lora.json
brands/<brand>/creators/<handle>/lora.json
brands/<brand>/products/<slug>/lora.json
```

The file says what it is, what to call it, and where the weights are:

```json
{
  "kind": "character",
  "trigger": "<the word the trained weights answer to>",
  "lora_url": "<the weights>",
  "trained": "<date>",
  "steps": 1000,
  "training_images": 25,
  "account": "company fal",
  "note": "<what it was trained from, and what it proved>"
}
```

Words in git, weights on the training account. The record is small, it is
committed, and it is what every machine reads.

## 8 · Trained once, reused forever

**An identity is trained once and reused for as long as the brand wants
that character.** Training the same subject twice does not "refresh" it —
it produces a second, slightly different version of someone who is supposed
to be the same person in every ad you ever make. That is the exact failure
identities exist to prevent.

So the record is also the check, and it is enforced in the machinery, not
left to memory:

- **Before training**, the trainer looks for `lora.json`. If it is there it
  reports what already exists and **spends nothing**. Overriding takes an
  explicit `--retrain`, and the only honest reason to use it is that the
  subject itself changed — new packaging, a recast face.
- **Before generating**, the run reads the same file and passes the
  identity to the scene prompts automatically. Nobody has to remember that
  a character is trained; the folder knows.

A new brand, a new product line or a new cast member is the only thing that
should ever start a training run.

## 5 · Registering the world, not just the faces

The same register-once-reuse-everywhere discipline applies beyond people:

| Asset | Locked by |
|---|---|
| The set | One generated plate, attached to every scene + the scene-setup text with its zones and coordinates |
| The product | The real photograph, attached every scene + the verbatim label lock |
| A signature texture (the paste, the foam, the residue) | One reference plate + a text lock naming its colour and consistency |

Record every trained identity and its source images together in the cast
ledger, next to the character in the brand folder. A future ad reuses the
identity untouched; only the script, the positions and the dialogue change.

## 6 · The standing order for a new cast member

1. **Gather the sources** — a board set for an AI character, her own
   footage for a creator, packshots for a product. Verify each one:
   right subject, one subject, clear and sharp.
2. **Train**, in small waves, polling to completion.
3. **Record** the identity beside the asset in the brand folder, so every
   machine and every future session finds it without being told.
4. **Never let the identity dress the character** — wardrobe is text, in
   every prompt, forever.
5. **QC every batch against the identity**: same face? wardrobe held?
   product label right? Check before anything moves downstream.

A character built this way is castable in any script, in any ad, for as
long as the brand wants them — which is the point.
