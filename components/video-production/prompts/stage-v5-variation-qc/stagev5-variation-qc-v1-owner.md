Inspect this restyled clip against the variation's rules and report every
deviation.

**Every example in this prompt is illustrative only.**

A variation has one extra way to fail that an original does not: the style
can slip. A clip that quietly resolves back toward the source's rendering
reads as a different film sitting in the middle of this one. That is the
single most important thing you are looking for.

---

THE CLIP AS GENERATED

{generated_clip}

THE STYLE FORMULA

{style_formula}

THE CONVERTED ASSETS

{converted_assets}

THE FROZEN SCRIPT FOR THIS CLIP

{approved_clip}

---

Check, in this order:

1. **Style hold** — does this frame read as the style formula describes,
   fully? Any part rendering in the source's manner — real skin texture,
   photographic lighting, depth of field where the style has none — is the
   primary failure. Name exactly which element slipped.
2. **Identity hold** — is each character recognisable as the same person as
   their converted design? Restyled is expected; a different person is a
   deviation.
3. **Product integrity** — is the product the real product, restyled? Shape,
   label wording and colours intact, label legible.
4. **World geometry** — is the location the same space, with fixtures in the
   same positions as the converted plate? A moved fixture breaks the
   blocking.
5. **Blocking held** — are the people positioned as the frozen script says,
   in the same screen order, with nobody present who should not be?
6. **Dialogue verbatim** — does any visible text or lip-synced line differ
   from the frozen script? The words never change in a variation.
7. **Style consistency** — does this clip read as the same style as the
   others in this set, not merely as "in style" on its own?

Report as JSON, and nothing else:

    {"pass": true}

or

    {"pass": false, "problems": ["<one specific, visible, correctable
    deviation>", "…"]}

Style slippage is always reported, however small — it is the failure this
gate exists for. Taste is never a deviation.
