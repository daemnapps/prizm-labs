# Stage 5 · Subject zone — v1

*v1 (2026-09-23), the owner: "safe zones for text and subjects (this should mostly
be handled at the production level)". The standing frame rule (2026-09-22):
every asset is 9:16, and the face, the product and the hands doing the beat
sit inside the CENTRED 4:5 zone of that frame — the middle 70% of its height.*

**How it is used.** `machine/safezone.py` sends the prompt below the rule,
word for word, with every still production makes — first frames, last frames,
card / screen / split / greenscreen plates, the endcard packshot — before a
clip is made from it. Nothing is pasted into it.

**Why it asks WHERE, not WHETHER.** image-production measured it: asking a
model to keep the top and bottom empty failed 13 of 13 live rolls, so the
zone is held by geometry and a judge, never by a request. This prompt does
not ask the model whether the subject is "in the zone" — it asks where the
subject is, as a box, and `safezone.py` compares the box with the zone. The
same box is written into the frame's record (`subject_box`) so the edit can
put words away from the face.

**What happens to a frame that fails.** ONE edit, the frame-edit discipline:
the failed frame first, the cast sheet second, the delta below as the only
change, then the house keep-line. Measured again. Still outside after that
one fix → the frame is HELD: no clip is made from it, and `pack` refuses the
run until the frame is remade (`remake.py order --element frame`). A frame
the judge could not measure is also not shippable — a check that did not run
is not a pass.

The one change, as sent to the edit door (`{what}` is what was outside;
`{top}` / `{bottom}` are the zone's edges, as a share of the frame's height):

```delta
Move the {what} down or up into the centre of the frame, so all of it sits between {top}% and {bottom}% of the frame's height, with only background above and below it
```

---

You are measuring where things sit in one picture. The image is attached.
You are not judging the picture — only locating what is in it.

Find, in this order:

1. every human FACE — forehead to chin, ear to ear;
2. the PRODUCT the picture is showing — a pack, tube, bottle, jar or box;
3. HANDS doing something — holding, applying, pointing, pressing — the hands
   and what they touch, as one box.

Give each one a box, as percentages of the whole picture: `x_pct` and `y_pct`
are its top-left corner (0 is the left edge and the top edge), `w_pct` and
`h_pct` its width and height, all from 0 to 100. Measure the edges of what you
can actually see; a box a little loose is better than one too tight. A face or
a product cut off by the edge of the picture gets a box that runs to that edge.

Do not box a person's body below the neck, the room, furniture, a wall, the
sky, or words. If the picture has none of the three — a bare surface, an empty
background — return an empty list.

Reply as JSON and nothing else:
{"subjects": [{"what": "face", "label": "<two to five words: whose face, which product, what the hands do>", "x_pct": 0, "y_pct": 0, "w_pct": 0, "h_pct": 0}]}

`what` is one of `face`, `product`, `hands`. If you cannot tell where
something is, leave it out rather than guess.
