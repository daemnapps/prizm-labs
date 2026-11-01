# Locked-frame escalating caption — rebuild sheet

An 11.5-second one-frame furniture demo: a green extendable sofa reconfigures six times inside a camera that never moves, while a quoted complaint shrinks into a mumble. 58,793,686 views · 2,962,929 likes · @marivellehome.

**Why it works**

Nothing in the frame moves except the product, so every transformation registers instantly — the viewer has no other change to look at and no cut to reset their attention. The caption starts as someone else's objection and gets shorter each beat, which plays as an argument the product keeps winning without a word of dialogue.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 0.92s | Locked high-wide of a narrow olive-green room from the doorway corner. The long tufted sofa runs down the left wall, one section pushed forward into a platform. Arched windows blown out behind sheer curtains, chest of drawers, dracaena, pink armchair, patterned rug, chrome side table in the foreground. Empty room. | "i hate extendable sofas" |
| 2.75s | Same frame. A person in a grey top and cream trousers kneels on the sofa and folds out a hidden panel in the backrest — a white tray with two cup holes. | you mean THIS sofa? |
| 4.59s | Same frame. Two people reclining, feet up, the tray now holding a bowl and two iced drinks; the sofa sits as a wide chaise. | you mean THIS sofa? |
| 6.42s | Same frame. Fully extended — backs down, the whole run one flat mattress filling the floor, both lying flat with pillows. | THIS sofa? |
| 8.26s | Same frame. Still flat, one person alone across it, so the width of the bed reads at its largest. | THIS? |
| 10.09s | Same frame. Backs up again, tray out with snacks, both lounging semi-upright. | this…? |

A small white script watermark, "marivelle home", sits in the lower third of every frame.

Only these six moments were read. The stills cannot show whether anything happens between them — no audio, no voiceover, no music, and no in-shot movement is observable from frames alone. The transformation is also not one-directional: it opens part-extended, goes fully flat by 6.42s, then returns to a lounge state at the end.

**What carries the value**

The furniture's transformation. Because the room, the light and the framing never change by a pixel, each beat reads as the same sofa becoming a different piece of furniture — and the shrinking objection turns that into a joke the viewer is on the losing end of.

**Shoot it**

- **Camera:** phone on a tripod, vertical, set high in a corner or doorway looking down the length of the room at roughly a 30° angle. Mark the legs with tape. It does not move once between the first shot and the last — every beat is the identical frame.
- **Composition:** the product runs the full length of the frame with a foreground object (here a chrome-and-glass side table) at the bottom edge for depth. Keep the background dressing — plant, drawers, armchair, art — fixed; if anything drifts between beats the trick dies.
- **Light:** big daylight windows behind the product, deliberately blown out. No lamps, no fill, no colour grade.
- **Wardrobe:** neutral, quiet, everyday — grey knit, cream trousers, no logos, no styling that pulls the eye. Faces are small and never address camera; nobody speaks.
- **Performance:** one beat per configuration. Do the least surprising version of the product first and the most extreme in the middle, and let people enter the frame casually — kneeling, lying, eating — rather than presenting.
- **Text:** same position mid-frame every beat, small white sans-serif. First beat carries the quoted objection; every beat after is the same challenge with words removed.

**Or generate it**

```
vertical 9:16 wide interior photograph shot from a high corner near the doorway, {PRODUCT} centred and running the length of the room in its most fully transformed state, {SUBJECT} lying on it relaxed and small in frame with the face incidental, olive-green panelled walls with framed art and a gold mirror, tall arched windows behind blown out white through sheer curtains, dark wood chest of drawers, tall dracaena plant, pink armchair, patterned rug, chrome-and-glass side table in the foreground, strong backlit daylight, styled but lived-in, phone-camera look, slight grain, no on-screen text
```

**Motion:** camera absolutely locked — no pan, tilt, push or handheld drift; only the product's configuration and the people change, so generate every beat from the same seed frame to keep the room identical.

**Text overlay pattern:** beat 1 is a quoted objection — `"i hate {product category}"` — then the same challenge shortening every beat: `you mean THIS {product}?` → `THIS {product}?` → `THIS?` → `this…?` Same position, same size, every beat. The shrink is the joke.

**Reference:** https://www.instagram.com/p/DT-wxYOk51n/
