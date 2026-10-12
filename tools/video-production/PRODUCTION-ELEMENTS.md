# Production elements — the standard (2026-09-23)

Every element an ad uses is **named in the brief, banked to this standard,
made from a real reference, documented, and confirmed by the owner before
anything is paid for.** the owner, 2026-09-23:

- "I want to get surgical with casting, settings, outfit, voices, product,
  etc — everything needs to be dialed in."
- "The system should prompt to confirm the elements before going into actual
  production … and if elements need to be generated we need to go through
  that step … every single line of execution is literally fool proof."
- "If you need a second voice that should be clearly identified at the brief
  level."
- "ALL elements in this flow must be processed from a real reference."
- "Seriously every element documented."
- "We always need realistic references so we can build for real … all
  characters need to follow this principle when generating."

Why: the three-doctors run re-brief cast different people than the approved production,
borrowed another character's voice, and read two speakers in one voice. None
of it was visible until a person looked. Now a machine looks first.

## The flow

    brief (v17) ─► elements check ─► TO MAKE? ─► make them (real reference first)
                        │                              │
                        └──────── all banked ◄─────────┘
                                     │
                            the elements page ─► the owner confirms
                                     │
                              production starts (voice, frames, clips)

1. **The brief names every element** (`stage5-ai-brief-v17`): each person by
   `bank_id` (or `NEW` + real reference + adjustments), the `looks` each person
   wears per scene, the `speaker` of every scene with words and each speaker's
   `voice` (banked / NEW + persona / none), each place by `bank_id`,
   `piece.product`, and every scene's `props`.
2. **The elements check** (`machine/elements_check.py sheet`) resolves every
   element against the brand bank and says BANKED or TO MAKE with the exact
   missing pieces. `run.py start` runs it after the production gate and the
   banks, before the voice — `--dry-run` reports, a real run refuses.
3. **Make what is missing** — people with `machine/make_character.py`
   (refuses without a real reference and named adjustments); voices designed
   per person (three options, the owner picks by ear); sets and props the same way
   (real reference first).
4. **The elements page** shows every element — sheets, looks, voices, places,
   product — and the owner confirms. `elements_check.py confirm <run> --by the owner`
   writes `elements-lock.json` with a fingerprint of every file in every
   element folder. Change any element after that and the lock breaks: confirm
   again.

## What each element must hold — `elements-standard.json` is the rulebook

The standard is data, not code: change a row there and every run is held to
it. Built from three traditions (research 2026-09-23):

- **Film/TV continuity** — costume and hair/makeup continuity photos per look,
  the casting breakdown (age, look, mannerisms, speech), movement/physicality
  and voice/dialect notes. ([StudioBinder](https://www.studiobinder.com/blog/how-to-write-a-character-breakdown-for-a-script/),
  [Brushstroke](https://brushstroke.co.uk/makeup-continuity-film-tv/),
  [Moving Image Education](https://movingimageeducation.org/create-films/production/the-production-department/costume-and-continuity))
- **Animation model sheets** — turnaround (front, ¾, profile, back),
  expression sheet including mouth shapes, hands, colour key.
  ([CGWire](https://blog.cg-wire.com/character-sheet-animation/),
  [CharacterHub](https://characterhub.com/blog/character-resources/character-design-sheet))
- **AI video identity lock** — varied angles and lighting beat a pile of
  near-duplicates; a texture-real, forward-facing base portrait as the anchor;
  plastic skin, the unblinking stare and identity drift are the named failure
  modes. ([Higgsfield Soul ID](https://higgsfield.ai/blog/Soul-ID-AI-Character-Consistency),
  [LoRA Dataset](https://loradataset.com/blog/how-many-images-to-train-a-lora),
  [Midjourney omni-reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference))

| Element | Folder | Must hold |
|---|---|---|
| **Person** | `runs/ai-elements/<brand>/casting/<id>/` | `character.md` (identity block, load-bearing details, looks, movement, voice persona, real references, adjustments) · `master` · `sheets/turnaround` · `sheets/angles-expressions` · `sheets/details` · `sheets/light-test` · `sheets/look-*` (one per outfit, front + back) · `sheets/colour-key` · `looks.json` · `reference/` (real) · `provenance.json` · `spec.json` (the recipe) · `voice.json` when they speak |
| **Look** | inside the person | a `looks.json` row: outfit words, where it came from, continuity notes, its sheet |
| **Voice** | `voice.json` + `voice/` in the person | their OWN ElevenLabs voice id — never another character's |
| **Setting** | `runs/ai-elements/<brand>/sets/<id>/` | `set.md` (time of day, light direction, dressing, hero props, what resets, room tone) · `plates/wide` · two `plates/angle-*` · `reference/` (real) · `provenance.json` |
| **Product** | `brands/<brand>/products/<id>/` | `product.md` (label word for word) · `images/packshot*` (the real photograph) · `provenance.json` |
| **Prop** | `runs/ai-elements/<brand>/props/<id>/` | `prop.md` · a picture · `reference/` (real) · `provenance.json` |
| **Movement** | `motion/` in the person | performance references (real human clips) — required once real motion is the default (`brief.motion_reference_required`) |

## Real reference, then adjust — the principle for every character

Every character starts from a **real** person: the swipe's own person in that
role (a frame by timestamp), or a real photo from Pinterest. Never stock,
never words alone. Then named **adjustments** make them ours — hair, eyes,
face shape, age, wardrobe — so they are never a copy of the real person's face.
The master is an edit of the real references; every sheet is an edit of the
master. `make_character.py` refuses a spec with no real reference, a
reference whose kind is not real, or no adjustments. If a master comes out
too close to the real person, it is remade with stronger adjustments and the
first try is kept in `versions/` (Expert 2, 2026-09-23).

## Documented — `provenance.json`

Checked field by field (`elements-standard.json → provenance_rules`):
`element`, `kind`, `real_references` (each: `file` that exists in the folder,
`kind` ∈ real video frame · real photo · real packshot · real audio, `from`),
`rights`, `made_with` (model, door, tool, prompt file, prompts as sent),
`drive` (where the full-size files live), `runs`.

## Where things live (2026-09-23 — generated work never goes in `brands/`)

- **People:** `runs/ai-elements/<brand>/casting/<person>/` — record, sheets, `voice/`.
- **Every other element:** `runs/ai-elements/<brand>/<kind>/<id>/` — sets, props, …
- **Brand facts only in `brands/<brand>/`:** the real products and packshots, and
  the cast list (`ai-cast/casting/`).
- **Drive:** the same paths under `Shared Assets/runs/…` — full-size pictures,
  audio, real footage. Git holds the record and small copies; `full/`, audio and
  video are git-ignored.
- **In code:** `machine/element_paths.py` is the only place these paths are written.
- **Prompts:** `prompts/stage-0f-cast/cast-sheets-v*-damon.md`, newest wins.
