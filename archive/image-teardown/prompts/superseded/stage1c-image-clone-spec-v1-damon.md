Here is a complete teardown of one static image ad, including its layout
system: {teardown_record}

Turn it into a **clone spec**: the two machine-readable blocks that rebuild
this exact ad. No abstraction, no brand swap, no improvement. The test of this
stage is a side-by-side against the original where a person cannot tell you
which is which.

**Cloning is not the same job as varying.** Every other stage in this chain
exists to change something. This one exists to change nothing. If you find
yourself generalising an element, naming a mandate, or writing what an element
is *for*, you are in the wrong stage — that is stage 2, and it runs after this
one has proved the format can be rebuilt at all.

Four rules govern everything.

**Copy the words exactly.** Every character, every capital, every punctuation
mark, every line break. The copy is not brand material at this stage — it is
part of the artefact being cloned. A clone whose words differ is not a clone.

**Take every number from the layout system, never from your own eye.** The
teardown measured margins, the alignment axis, the vertical rhythm, the type
scale, the measure and the keep-clear regions. This stage transcribes them.
If a number you need is missing from the record, write
`[MISSING: <what>]` in its place — do not estimate one. A missing measurement
is a stage-1 defect and it is cheaper to fix there than to guess here.

**Name a real typeface, with a fallback that exists.** "Condensed grotesque"
is a class, not an instruction a renderer can take. Give the class, your best
identification of the actual face, and a **named fallback file the renderer
will certainly have**. Judge width honestly: a *compressed* face (very narrow,
heavy, letters nearly touching — Impact, Haettenschweiler) is not a *condensed*
one (narrower than regular but still open — DIN Condensed, Avenir Next
Condensed). Measured cause, 2026-08-19: a headline identified only as
"condensed grotesque" was rebuilt in a condensed face when the original was
compressed, and the clone read visibly lighter and wider until the face was
corrected.

**The type layer holds set type only.** Words that exist as an object inside
the photograph — a label printed on the bottle, a sign on the wall, a logo on a
garment — belong to the plate, never to the type layer. They are described in
the plate prompt as part of the object that carries them, and they never become
an element. Measured cause, 2026-08-19: a brand name printed on a bottle was
emitted as a type element, and compositing it would have printed the logo twice.

**Split every multi-colour line into segments.** Where one line carries two
colours, write it as an ordered list of fragments, each with its own colour,
in reading order. A single `color` field on a two-colour line silently loses
the accent — and the accent is usually the thing carrying the brand.

Give me these three blocks and nothing else.

**1. THE PLATE PROMPT**

The photograph, with **no words in it**, written as a shot list a photographer
could execute — not as a description of what you observed, and **never as a
list of percentages**.

**Why this is a shot list.** An image model renders nouns a camera could see.
It has no compositor, so a measured band like "the subject occupies 14-70% from
top and 42-85% of width" is not an instruction it can act on — it is a phrase
that dilutes attention across everything around it, and the picture gets
rendered from whatever words survive. Measured cause, 2026-08-26: a plate prompt
that spent a third of its length on percentage bands rebuilt the room, the props
and the light correctly and still put the camera in the wrong place with the
subject's face toward it, because "face not visible" was one phrase competing
with thirty numbers. **Percentages belong to the type layer in block 3. The
picture is described in words.**

Write it in this order, one continuous prompt, every slot filled from the
teardown's camera-and-light spec in the vocabulary of
`reference/visual-lexicon.md`:

1. **Subject** — who is in frame, age band, hair, skin, expression; what every
   person is wearing to material, pattern and trim; every piece of jewellery.
2. **Action** — what each person is physically doing, as a verb caught in the
   middle of happening. A frozen verb carries tension; a state of being does not.
3. **Environment** — the space as it really is, its depth, and every prop with
   the plane it sits in.
4. **Composition** — the named pattern, where the subject sits in the frame and
   what it is cut at, what the room's lines do, and what sits at each of the
   four frame edges. **In words.** "Medium-wide from the foot of the bed, the
   subject right of frame cut at the hip, the bed running left-to-right into
   frame from the left edge, a nightstand entering the bottom-right corner."
5. **Camera** — shot size, height and angle as two facts, **where the camera
   stands in the room and which way it shoots**, lens feel, depth of field. The
   camera's position against the furniture is not optional and is not implied by
   the others: "from the corner at the foot of the bed, shooting lengthwise
   along the room."

   **Framing is the one slot words do not reliably win.** Measured across four
   runs on 2026-08-26: subject, wardrobe, props, light, grade and texture all
   came back correct from language alone; the camera's position in the room came
   back wrong every time, including when it was stated plainly and repeated in
   the negatives. **So the plate is generated with the layout reference
   attached, and this slot is written to agree with that picture rather than to
   replace it.** Where no reference exists — a variation whose frame has no
   precedent — say so in the spec, because that plate will need a human to look
   at its framing before anything is built on it.

6. **Subject orientation and face visibility — written in the strong form.**
   This gets its own sentence and its own space, because it is the fact most
   often lost and the loss is total when it goes.

   The lexicon's terms record it; they do not, on their own, generate it.
   `three-quarter-back, face partly visible` produced a full three-quarter face
   on 2026-08-26. What produced the correct picture was all three of these
   together:
   - **state what the camera sees of the body** — "her back and shoulder are
     toward the camera; the camera sees the back of her head and her bun";
   - **name each facial feature that is not visible, individually** — "no eye is
     visible, no cheek is visible", not "face not visible";
   - **repeat it in the negative constraints** — "no face, no eyes, no cheek, no
     profile turned toward camera".

   Do this wherever the record says anything other than `face fully visible`. A
   generator's default is a visible face, and a default is only beaten by being
   contradicted three times. **Then subject orientation and face visibility, in the lexicon's named
   terms, as their own sentence.** Never fold face visibility into a clause at
   the end of a long line — it is the fact most often lost, and it is lost by
   being buried.
7. **Light** — the named setup, its direction, its quality, and every practical
   light placed individually.
8. **Grade** — the named grade and the black point.
9. **Style anchor** — the kind of picture this is.
10. **Texture and stock** — grain, camera type, and the physical tells. Never
   leave this empty: an unstated texture renders as clean digital, and clean
   digital is what makes a plate look generated.

**Take every fact from the record.** If the teardown did not record a slot,
write `[MISSING: <slot>]` in its place rather than inventing one — a missing
slot is a stage-1 defect and it is cheaper to fix there than to guess here.

Close with the negative constraints, on their own line: no text, lettering,
captions, watermarks, signage or packaging copy · **no real brand names, no
recognisable logos, no existing product packaging, no trade dress** · plus
anything this particular picture must not contain, **including the specific
thing a model would default to and this picture does not do** — a face turned
to camera when the original's is turned away, a smile when there is none, a
bright room when the original is dark.

**One exception on text, and only one.** Where the record shows words existing
as an object inside the photograph — printed on a bottle, a sign on a wall —
those words are part of the picture and are described here as part of the object
that carries them. They are named as in-world text so the negative constraint
does not cancel them, and they never appear in block 3.

**2. THE ACCEPT TESTS**

Three to five checkable things a human accepts or rejects the plate on,
specific to this picture — not generic quality notes. At least one must be
about hands or anatomy, at least one about whether the load-bearing action
reads correctly, and at least one about each band you declared empty. **A
legible third-party brand anywhere in frame is an automatic reject**, always,
and it is listed every time.

**3. THE TYPE LAYER**

A single fenced ```json block. Valid JSON, no commentary inside it, no
trailing commas, no placeholder values. Shape:

```
{
  "layout": {
    "source": "<the file this was cloned from>",
    "margins": {"top": 0, "bottom": 0, "left": 0, "right": 0},
    "alignment_axis": "<which axis, and which elements share it>",
    "type_scale": "<the ratio series>",
    "keep_clear": [{"name": "", "top": 0, "bottom": 0, "left": 0, "right": 0}]
  },
  "elements": [
    {
      "element": "zone_a",
      "text": "<the whole line, exactly>",
      "segments": [{"text": "", "color": "#FFFFFF",
                    "box": {"fill": "#E3000F"}}],
      "top_pct": 0, "gutter_pct": null,
      "left_pct": 0, "right_pct": 0,
      "align": "left|center|right",
      "cap_pct": 0, "height_pct": 0,
      "case": "upper|sentence|as-set",
      "weight": "regular|medium|bold|black",
      "tracking": "tight|standard|wide",
      "color": "#FFFFFF",
      "font": "compressed-grotesque|condensed-grotesque|grotesque|humanist-sans|geometric-sans|serif|high-contrast-serif",
      "measure": 0, "max_lines": 0,
      "box": {"fill": "#000000", "pad_pct": 0},
      "file": "all"
    }
  ]
}
```

Rules on the block, all mechanical:

- **Elements appear in reading order**, top to bottom. The renderer takes
  declared order as reading order and does not re-sort.
- **Every percentage is measured from the frame's top-left corner.**
  `left_pct` is the left edge's distance from the frame's left edge;
  **`right_pct` is the right edge's position measured from that same left
  edge** — it is not a width, and it is not an inset from the right. A block
  spanning the middle two-thirds of the frame is
  `"left_pct": 16, "right_pct": 84`, never `"right_pct": 16`. Measured cause,
  2026-08-19: read as an inset, every element lands in the wrong place.
- **Use `gutter_pct` wherever the layout system measured a gap**, and
  `top_pct` only for a block whose position is independent of the one above
  it. A gutter survives a copy-length change; an absolute top does not.
- **`height_pct` is the zone's own height** from the layout system — never the
  distance to the next zone. Without it a block grows into empty frame and
  swallows the picture.
- **`measure` and `max_lines` come from the layout system's measure and line
  count**, unchanged. They are what tells a later variation whether its copy
  fits.
- **`weight` is required on every element.** A weight is a different typeface
  file, not a flag — recorded in prose and left out of the data, a bold headline
  rebuilds in regular and the ad reads wrong with every word right. Measured
  cause, 2026-08-26.
- **`segments` is present on every multi-colour line and omitted otherwise.**
- **A segment carries its own `box` where the fragments sit on different
  panels.** A two-tone badge — white knocked out of red, then black out of
  white, butted together — is one line of two segments each with its own fill,
  never one box on the element. Measured cause, 2026-08-26: with only an
  element-level box the badge rebuilt as a single red bar and the second panel
  disappeared.
- **`box` is present only where the teardown recorded a filled container**,
  with the fill as the hex the teardown measured.
- Every hex is a hex. Every percentage is a number, not a string.

Nothing else in your output — no explanation, no summary, no notes on how the
ad works. The next pass reads these three blocks and nothing more.
