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

---

Check, in this order, and only against what was specified:

1. **Identity** — is every person in the frame the person their locked
   appearance describes? Age, build, skin, hair, distinguishing marks.
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

Report as JSON, and nothing else:

    {"pass": true}

or

    {"pass": false, "problems": ["<one specific, visible, correctable
    deviation>", "…"]}

Each problem names WHAT is wrong and WHAT it should be, in one sentence,
so the correction is unambiguous. Report only deviations you can actually
see in the frame. If you cannot tell, it is not a deviation.
