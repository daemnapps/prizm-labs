# Stage 6 — a reference frame on every scene

Stage 5 requires a picture on each scene so the maker sees the shot instead of
interpreting a paragraph. Stage 5 is a text pass and cannot cut a still or run
an image model, so this stage does it. It writes no words: it puts pictures on
the brief stage 5 already wrote, or says plainly that a scene has none.

## Where a frame may come from

1. **The source video first, always.** For every scene the brief names a
   timestamp. Cut the still from there. A photograph of the subject actually
   doing the shot beats anything generated and cannot invent a person, a
   garment or a product.
2. **Generate only what the source does not contain** — a product beat it
   never had, an angle it never showed — seeded image-to-image from its own
   still, so it is the same person, the same room and the same light, not a
   stranger of the same age.
3. **Never a generic stand-in.** A frame showing someone who is not the
   subject, in clothes they do not own, is worse than no frame: the maker will
   shoot what they see. If neither route is available, the scene goes out without a picture and
   the brief says so.

## What a generated prompt must state, in full

- **Framing and light.**
- **What the subject is wearing, completely** — taken from the scene's own words, never
  inferred and never inherited from the seed still. A seed frame carries its own
  wardrobe into every generation: on 2026-08-20 seven frames came back as an
  identifiable real person in swimwear because the scene's clothing was left
  unstated. If a scene does not state the wardrobe, no frame is generated.
- **The product exactly as it really looks**, colour and finish from the product
  file, never assumed from its name. If the product file does not describe the
  product, a scene holding it is not generated — a model with nothing to go on
  invents the packaging, and on 2026-08-20 it produced a plain white tube that is
  not the product.
- **The exclusions**: no on-screen text, no invented branding, no result the
  product has not been shown to deliver, no retouching that makes the subject
  look better than they really do.

## Every frame is looked at before it enters the brief

Not a glance at the prompt that made it — the frame itself is opened and
described, and anything wrong is **deleted, not captioned around**. A frame fails
and is cut if any of these are true:

- **Anyone in it is unclothed, partly unclothed, or ambiguous about it.** Checked
  first, before anything else, on any frame with a person in it.
- It shows a person there are no likeness rights for.
- It shows the product with invented branding, or a competitor's.
- It contradicts its own scene — wrong room, wrong object in hand, a light
  burning when the scene says it was switched off.
- It shows a claim we do not make.

Every frame lands recorded as unchecked. **A brief with an unchecked frame in it
is not finished.**

---

## EXAMPLES ARE EXAMPLES

Every specific in this prompt — an age, a gender, a garment, a body part, a
product category, a named person — is **illustrative only**. None of it
describes the asset in front of you. Read an example for the shape of the rule,
then apply the rule to what you actually have.

The subject may be any age, any gender, anywhere, selling anything. This chain
runs the same on a woman on a beach, a man talking to camera in his car, two
people in a kitchen, or a pair of hands on a countertop. Nothing in this prompt
assumes which.

**Who is on camera comes from the teardown record, never from this prompt.** If
the teardown says a man in his fifties in a parked car, that is the subject —
every rule below applies to him unchanged, and any pronoun in an example above
is about that example, not about him.

**And the variables are agnostic too.** An example may be reworked freely — it
is illustrative and always was. But nothing that gets filled in at run time
may name a brand, a product or a category: brand detail arrives only through
the variables above, resolved from that brand's own folder. A rule that
cannot be written without naming the brand belongs in the brand folder, not
in this prompt. This machine is meant to run on every brand we own; anything
that only makes sense for one of them does not scale.
