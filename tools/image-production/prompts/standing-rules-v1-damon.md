# The standing rules — on every picture, whatever it is for

These go on the end of every prompt this component sends. Each one is here
because a real picture failed without it.

A caller can add to them. A caller cannot take one away — that is what
"standing" means.

**Where each rule came from.** This table is documentation and is NOT sent to
the model; everything below the rule is.

| Rule | Came from | The failure it was written after |
|---|---|---|
| No invented text | `components/email-production/simple_email.py` — "No words, letters, numbers or logos anywhere in the image." | A hero invented its own headline and argued with the real one underneath it. |
| The product is ours | `tools/image-production/static/tools/paths.py` `product_cutout` — "A generated tube is a different product wearing our name." | The judge correctly failed a generated product, 2026-08-31. |
| No other brand | `finish.py` STANDING_CHECKS | A competitor's wordmark legible in a paid frame. |
| Nothing grossly broken | `finish.py` STANDING_CHECKS, narrowed 2026-09-05 on the owner's call | Finger-counting and micro-geometry killed good pictures and cost more than the defects they caught — so this is deliberately coarse. |
| No equipment in frame | `prompt.py`, the C2 split | "Shot on a phone on a tripod" put a phone on a tripod in the middle of a barbershop. |
| Surface truth | `style-packs.json` `texture`, on every pack | A phone photo of a real person came back looking like a campaign, which is a different ad. |
| One coherent object | `brand_facts.py` PLAIN_PRODUCT_CHECK | A product whose parts changed between appearances in one frame. |

---

STANDING RULES — these hold for this picture whatever else is asked above.

1. NO INVENTED TEXT. Do not render any words, letters, numbers, captions,
labels, callouts, watermarks, subtitles or user-interface furniture anywhere in
the frame. If words belong in this picture they are named in the direction
above, spelled exactly as written there, and nothing else is spelled at all.

2. THE PRODUCT IS OURS OR IT IS ABSENT. Where the product appears it is the
object described or attached above — the same pack, the same proportions, the
same colours, the same label. Do not redraw it, restyle it, relabel it, improve
it or invent a second version of it. If you cannot render the real object,
leave it out of frame rather than approximate it.

3. NO OTHER BRAND. No third-party or competitor brand name, logo, wordmark,
packaging or storefront is legible anywhere in the frame.

4. NOTHING GROSSLY BROKEN. No limb attached wrongly, no melted face, no body
with the wrong number of arms. Judge this the way a viewer scrolling past
would: a partly hidden hand, a foreshortened grip or an odd-looking finger is
fine and is not what this rule is about.

5. NO EQUIPMENT IN FRAME. Describe the result, never the apparatus. A camera, a
phone, a tripod, a ring light or a lighting rig appears in frame only when the
direction above puts it there on purpose.

6. SURFACE TRUTH. Skin keeps its pores, follicles, marks and micro-shadow;
surfaces keep their grain. Nothing is smoothed, beautified, airbrushed or made
cleaner than the thing it is a picture of.

7. ONE COHERENT OBJECT. Anything that appears more than once in the frame is
the same object each time — same parts, same marks, same label.
