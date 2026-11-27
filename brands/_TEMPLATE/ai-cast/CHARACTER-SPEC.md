# AI character spec — a generated actor, banked as a swappable asset

**AGNOSTIC ON EVERY AXIS**: brand, product, avatar, gender, model.
Nothing in this template assumes who the character is — a character file
speaks in the character's own pronouns as the brand defined them; the
machinery assumes nothing.

**The swap frame (the owner, 2026-08-30):** the whole game is swapping,
mixing and matching based on data — swap creators, swap formats, swap
angles, swap AI models, swap actors, swap headlines. An AI character is
one swappable axis: a banked actor who can be dropped into any brief,
any format, any angle, and re-shot for free. This spec is what makes a
character swappable — everything a run needs to cast them lives in one
folder.

## The template (character.md, exactly these sections)

```
# <Name> — <one-line role>

<one line: who this character is and why they exist>

## Basics
- Status: active / retired
- Pronouns/presentation: <as the brand defined the character>
- Avatar link: which core/sub-avatar this character embodies or plays
  to — THE reason the character exists; avatar names come from the
  brand's core-avatars folder, never hardcoded. No orphan characters.

## Identity block (paste-ready — proven verbatim where it exists)
> The exact text that generates this character. Age, look, skin
> texture, build, wardrobe register — concrete physical detail.
> Never re-described ad hoc in a run; runs paste THIS.

## Load-bearing details
- The physical facts the ads fail without (marked explicitly)

## Voice (the recipe, not a file)
- Persona paragraph OR preset voice id + settings (speed at natural —
  smooth beats runtime)
- Chaining rule: every line clones the character's best take; accent
  drift = stack the two best takes
- Banked best takes: links, as they accumulate

## Masters
- The banked images (character sheet, portraits) — clickable links
- Regeneration recipe: how to remake the master from the identity block
  (model slot + seed where locked)

## Swap record (what data says this actor can carry)
- Formats run · angles run · results — grows with every run; this is
  the data the mixing-and-matching reads

## Provenance
- The runs this character appeared in — clickable links
```



## Creating a new character — THE STANDARD (the owner, 2026-08-31)

This is the standard for every new character entering the machine —
especially as new avatars and new content creators come in:

1. **Source**: a new avatar/sub-avatar gets its embodiment; a new
   creator gets a variated twin (VARIATION RULE — written identity
   only, never their photos, deliberately different face).
2. **Identity block** written (concrete, load-bearing details marked).
3. **Canonical master** generated (description route) — ONE master,
   everything chains from it.
3b. **De-slop the master** (2026-11-09; inside `make_character.py` as step 2 since 2026-11-10, named by the spec's `texture`; texture bank `runs/ai-elements/_texture-refs/`): before any sheet, board or scene, run a
   texture-refinement edit on the master (the Model House picture-edit model) with real reference photos for skin and hair: visible pores,
   uneven tone, fine flyaways, real fabric weave. The references are
   attached to the edit, never only described in the prompt: real macro
   photos (free stock or owned), cropped to texture only, with no face in
   them and no customer photos. Save them in `deslop/refs/`. The de-slopped master
   replaces the raw one as the canonical master. Check: side by side with
   a real photo at 100% crop, skin and hair read as photographed — pass
   or redo.
4. **The full board set** generated, matching the <brand> baseline
   board-for-board (`brands/<brand>/ai-cast/<brand>/boards/` — the owner's
   reference set): wardrobe lineup(s), style board, expression+angle
   grid, hair grid, detail close-ups, context scenes in the character's
   world.
5. **Voice recipe** written and base take banked.
5b. **Video element** (2026-11-09, `cast-deslop` skill step 2; models from the Model House `clips.take` route, today Wan 3.0 with Seedance 2.5 as the backup; the owner picks the take): build the character's reusable video
   reference from the de-slopped master plus the banked voice: a short
   clip of the character moving and speaking, saved as a named element
   `@char_<name>_video_v<n>` (Higgsfield Elements; same name in every
   prompt and tool). Scene prompts reference this element for face,
   hair, wardrobe and voice; pose, props and light come from the scene
   prompt. Variants that must not drift (a wound, a transformed look) get
   their own image element `@char_<name>_<variant>_image_v<n>`.
6. Only then is the character castable in runs.

## The board (the production bible — every character gets one)

the owner's ruling (2026-08-31): each character carries a full board set —
who they are, what they wear, what they do, the unique elements that
make them themselves. The board is the engine behind production: the
character truly represented end to end. Boards are generated by
identity-chaining off the CANONICAL master (the machine's board
generator), and live as pixels on the brand's Drive mirror + local
disk — never in git (media rule).

Standard set (extend per character as their world demands):
- `boards/wardrobe.png` — full-body lineup, one panel per outfit
- `boards/expressions.png` — six-up angle/expression grid
- `boards/hair.png` — six-up hairstyle grid
- `boards/details.png` — macro close-ups: hands, footwear, skin
  texture, the load-bearing details
- `boards/context.png` — the character in their world (one or more)

Known trap: generated signage/text in context scenes comes out as
gibberish — ban readable signage in board prompts, composite real
artifacts when a scene needs them (the digital-artifact ruling).

## Rules

- **THE VARIATION RULE (the owner, 2026-08-31 — compliance, non-negotiable):**
  a real creator's face is NEVER used to generate a character. A
  character inspired by a creator is a NEW person: generated from a
  WRITTEN identity only (never from the creator's photos as an identity
  reference), deliberately variated — different face, different hair,
  different distinguishing details. Similar age, energy and register are
  fine; likeness is not. If the character could be mistaken for the real
  person, it fails. The clean mechanism: creator-inspired characters use
  the description route only; photo-reference generation is reserved for
  characters with no real-person source.
- These people do not exist — every character is generated and owned by
  the brand. Real humans live in the brand's creators/ folder.
- Identity chaining: every still of this character is an image-EDIT
  with their master as reference. Never describe the character fresh.
- The character's pronouns are whatever the brand defined; templates
  and machinery use they/the character.
- Everything clickable; unknowns marked OPEN; nothing invented.
