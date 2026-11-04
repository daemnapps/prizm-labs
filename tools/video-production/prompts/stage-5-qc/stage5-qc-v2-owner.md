# Stage 5 · QC — v2

*v2 (2026-09-17): identity is checked against the attached reference image, not the description; a new "Source action parity" check; two modes (`glance` / `deep`); every problem carries a `defect_class`, and a ceiling problem is reported once and never re-rolled. The session pastes `{ceilings}` — this model's entries from `machine/providers.json` — and `{mode}` — `glance` or `deep`.*

Inspect this generated scene against the production document and report
every deviation, precisely enough that a re-roll can correct it.

**Every example in this prompt is illustrative only.**

You are a strict inspector. You are not judging whether the scene is good,
striking or well-composed — taste is never a deviation. You are checking
whether it is *the scene that was specified*.

---

THE SCENE AS GENERATED

{generated_scene}

WHAT WAS SPECIFIED

{scene_prompt}

THE GROUND TRUTH

{ground_truth}

WHAT THIS MODEL CANNOT DO

{ceilings}

MODE

{mode}

---

**The mode decides how much you check.**

- `glance` — checks 1, 2, 3 and 6 only. One line per problem. This is the
  default for every frame and every clip.
- `deep` — every check, in full detail. Deep is for product-hero frames and
  frames where the product's label is readable — nothing else. A deep pass
  on a frame that does not carry the product is spend with no return.

Check, in this order, and only against what was specified:

1. **Identity** — is every person in the frame the person in their attached
   cast sheet or reference image? Compare the face against the *picture*,
   never against the written description: the description is what the
   picture was made from, and a face can match every word of it and still
   be someone else. Age, build, skin, hair, distinguishing marks — read from
   the reference. If no reference image is attached, say so as a problem:
   the frame cannot be verified.
2. **Wardrobe** — is each person wearing exactly their locked outfit, and
   nothing from their never-list?
3. **Product** — does the packaging match the real product photograph:
   shape, colour, closure, label wording, and the artwork printed the same
   way on the same surface? A panel, plate or sticker the real product
   does not have is a deviation. Approximated, garbled or invented
   lettering is a deviation. A label that is genuinely unreadable because
   the product is small or turned away is NOT a deviation. A line of
   non-Latin script may be absent — absent is fine, garbled is not.
4. **Blocking** — are the people where the positions say, in the specified
   screen order, with nobody present who should not be, and nobody
   entering who was not specified to enter?
5. **Text** — is the caption exactly the specified wording, correctly
   spelled? Is there any other lettering in the frame besides the
   product's own label?
6. **Count** — does each named character appear exactly once?
7. **Source action parity** — where the ground truth names a decisive
   action (a slap, a reveal, a flip, a drop, a grab), that action must
   appear unchanged. A softened stand-in — an arm-block for a slap, a
   glance for a reveal, a nudge for a drop — is a deviation, and it is
   named as one even if the softened version looks fine. The action is
   what the scene was swiped for.

**Classify every problem.** A problem is one of two kinds:

- `fixable` — a re-roll or a re-composition can correct it: the label, the
  hands, the wrong person, the wrong outfit, the wrong order, a missing
  action.
- `ceiling` — anything listed under WHAT THIS MODEL CANNOT DO for this
  model. A ceiling is reported once, plainly, and **never sent to re-roll**:
  a second attempt at a thing the model cannot do is the same result at
  the same price. The scene ships with the ceiling flagged in the handoff.

Report as JSON, and nothing else:

    {"pass": true}

or

    {"pass": false, "problems": [
      {"what": "<one specific, visible, correctable deviation>",
       "defect_class": "fixable"},
      {"what": "<one specific, visible deviation the model cannot fix>",
       "defect_class": "ceiling"}
    ]}

Each `what` names WHAT is wrong and WHAT it should be, in one sentence,
so the correction is unambiguous. Report only deviations you can actually
see in the frame. If you cannot tell, it is not a deviation.
