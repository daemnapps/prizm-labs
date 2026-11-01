# Stage 1 — Cast (identity images)

Status: **baseline only** — to be built out in detail.

## Job

One clean identity image per character, made once, banked forever. It is
the face used in every scene downstream; nothing regenerates a face that
works.

## Baseline (from the proven run)

- Two routes: (a) 1–2 real reference photos → straight portrait;
  (b) written description → split-screen **character sheet** (full body
  left, close-up right, plain studio background, seed locked).
- Full-quality stills, house aspect ratio, no post-upscaling.
- Prompt pattern: identity block (age, ethnicity, face, skin texture,
  build) + wardrobe block (every garment named) + realism block (natural
  pores, no beauty filter, no AI-airbrushed look) + negatives (one person
  only, no props, no text, no celebrity likeness).

## The slot

Any image model that can: take reference images (or hold a detailed
identity from text), render natural skin without a beauty-filter look, and
lock a seed so a winning face is reproducible.

**Audition:** same face, twice, from the same seed — and skin that doesn't
look airbrushed.

## To build out

- [ ] The full identity-block template (what fields, in what order, what
      makes faces stable vs drift)
- [ ] Wardrobe/turnaround boards: when they're worth making, the board
      prompt patterns
- [ ] Cast bank: naming, storage, and how scenes reference a banked face
- [ ] Candidates for the local slot (proven / testing / rejected)
