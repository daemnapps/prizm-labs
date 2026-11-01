Here is a complete teardown of a STATIC IMAGE AD: {teardown_record}

Turn it into a replication spec: the discrete, reusable elements that make
this asset work, abstracted from its brand, product and subject so it can be
executed for any brand in any category.

This is a single frame. There is no timeline, no scene order and no runtime —
the structure is spatial. Everywhere the video chain counts seconds, you
count **area and position**.

Three rules govern everything below:

**Abstract, never copy.** No mandate may carry the source's brand, product,
or subject. Convert every specific into its generic function — "positions the
speaker as a practitioner of a tradition the audience believes predates the
category," not the tradition's name.

**A style reference is a descriptor, not a brand.** "Dolce & Gabbana-style
baroque," "athleisure," "condensed grotesque," "editorial magazine spread" —
these name an aesthetic precisely, the way "brutalist" or "art deco" does,
and a designer in any category can act on them. Keep them; a vague mood word
in their place makes the mandate weaker. The rule is about the brand being
sold, not about vocabulary for describing a look.

**Every element is discrete and injectable.** One element is one thing to
build. Each one names where a new brand's material enters.

Give me these eight sections.

**1. FORMAT**

What kind of asset this is, in one line, ending with the aspect ratio it was
built for.

**2. THE LAYOUT SKELETON**

A table: `Zone | Function | Area & position | Fixed position? | Fixed or flexes?`

**Area & position** is percentages, taken from the teardown record — the
zone's top and bottom edge as a percentage of frame height, its horizontal
span, and the share of frame area it occupies. No seconds anywhere.

For **fixed position**, say whether the zone must stay where it is — a
headline that reads before the image cannot move below it. For **fixed or
flexes**, say whether the zone's size is fixed by what it does — a legibility
floor, a safe-zone margin, a thumb-stop mass — or whether it stretches and
compresses with the ratio the ad is cut for. Give the fixed ones their floor
or ceiling as a percentage.

**3. THE ELEMENT INVENTORY**

The core section. Number every discrete element. For each, give all four of
these as separate labeled lines:

- **ELEMENT** — a name for the thing.
- **MANDATE** — what must be true. Written generically, executable without a
  judgment call, numbers where numbers apply. No brand, product, or subject
  from the source.
- **SOURCE INSTANCE** — how the reference did it, quoted exactly for copy and
  measured exactly for design, so the standard is visible.
- **INJECTION SLOT** — what brand-side material fills this: customer
  language, product truth, the offer, identity/character, or FIXED if the
  element is structural and nothing gets injected.

Cover the design elements as well as the copy ones. A container, a highlight
box, a type-color split inside one line, a safe-zone margin — each is an
element with a mandate, and a spec that inventories only the words cannot be
built from.

**4. THE COPY ARCHITECTURE**

The copy deck as a slot-based template, zone by zone in reading order. Write
each line as a fill-in with its slots marked in brackets — for example:
"[PROHIBITION] my [ARTEFACT THE SPEAKER OWNS] on [THE PROBLEM, IN HER WORDS]
more than [FREQUENCY LIMIT]." Under each line, state its job in one line and
quote the source's version.

Include the zones that carry no words. A zone whose job is to be empty is a
decision, and a template that loses it fills it.

**5. THE IMAGE MANDATE**

What the photograph itself must do, as an instruction someone could shoot,
source or generate from. Cover, each as its own line: who is in frame and
what they are being · what they are doing with their hands · where the gaze
goes · what the light does · the lens and distance · the depth of field · the
set and what it must contain · which props are load-bearing. Generic, no
brand — the mandate is "the practitioner's hands are mid-preparation of the
remedy, in the sharp plane," not the ingredient's name.

**Account for every person in the record.** Before you write the mandate,
list every human the teardown record puts in frame — including a partial one:
an arm at the edge, a second pair of hands, a body part being worked on. Each
one gets a role in the mandate or an explicit line saying why the format does
not need them. **A person in the record who is absent from the mandate is a
defect, not an abstraction** — and it is the most expensive defect this stage
can produce, because every downstream pass builds the picture from the
mandate and nobody looks at the record again.

Say plainly whether the mandate requires the frame to **demonstrate** the
mechanism on the problem, or only to **assert** authority near it. That
distinction is the largest single difference between two ads that look alike.
**Cite the record for the call** — quote the row that shows the mechanism
being applied, or quote the absence. Measured cause, 2026-08-19: a source
frame whose entire proof was a paste being spread on a second person's
spotted hand was abstracted as "asserts authority, no application shown", and
six generated plates lost the proof before anyone saw them.

**6. LOAD-BEARING**

The elements that carry the performance — change them and the asset stops
working. One line of why for each.

**7. SWAPPABLE**

The elements that can change freely per brand at no cost. One line of why for
each.

**The two lists may not contradict each other, and the subject is where they
usually do.** If a mechanic you called load-bearing depends on *what the
subject is* — neoteny or a cute response (that is the animal or the baby), a
child's scale, a body part the proof is performed on, a face whose age is the
claim — then the subject is load-bearing too, and it does not go in section 7.
Write it in 6 and say which mechanic holds it there. Section 7 may still carry
the subject's *attributes* (breed, hair, wardrobe, room) — never its kind.

Measured cause, 2026-09-14: a frame of a dog standing over the photographer's
lap had "wide-close lens distortion → neoteny/cute response" in section 6 and
"the specific subject: can be swapped to any demographic, character, or
animal" in section 7. Injection followed section 7, replaced the dog with a
woman, and the draft lost the only mechanic the source had.

**8. THE LAYOUT, AS DATA**

Sections 1–7 describe the format in words. This section is the same layout as
numbers, because a format nobody can render is not a format. **Take every
value from the teardown's measurements — never from your own eye.** Where the
record does not carry a number, write `[MISSING: <what>]` in its place rather
than estimating one; a missing measurement is a teardown defect and it is
cheaper to fix there than to guess here.

A single fenced ```json block. Valid JSON, no commentary inside it, no
trailing commas, no placeholder values.

```
{
  "layout": {
    "source": "<the ad this format was taken from>",
    "margins": {"top": 0, "bottom": 0, "left": 0, "right": 0},
    "alignment_axis": "<which axis, and which elements share it>",
    "type_scale": "<the ratio series>",
    "keep_clear": [{"name": "", "top": 0, "bottom": 0, "left": 0, "right": 0}]
  },
  "composited": [
    {
      "element": "zone_d",
      "kind": "product|logo|badge|seal",
      "top_pct": 0, "left_pct": 0, "span_pct": 0,
      "rotate_deg": 0,
      "outline": {"color": "#FFFFFF", "width_pct": 0},
      "note": "<what it is, in the format's terms — never the source's brand>"
    }
  ],
  "elements": [
    {
      "element": "zone_a",
      "text": "<the SOURCE's words, verbatim — replaced at injection>",
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

- **`composited` holds everything placed into the frame that is not type** —
  the product, a logo, a seal, a badge cut from a real asset. **Its position is
  data, exactly like a headline's is.** A format that records where the product
  sits only in prose cannot be built from: the compositor reads numbers, and a
  builder left hunting for the product's place will either guess or skip it.
  Measured cause, 2026-08-31: four finished ads shipped with no product in them
  because its position lived in a sentence.
- **One element per copy-carrying zone**, in reading order, top to bottom. A
  renderer takes declared order as reading order and does not re-sort. Zones
  that hold only imagery or structural fill carry no element.
- **The text is the SOURCE's words at this stage.** This section records the
  layout, and the layout was measured around the words that were in it. The
  injection replaces the words and keeps everything else — which is the whole
  point of measuring first.
- **Every percentage is measured from the frame's top-left corner.**
  `left_pct` is the left edge's distance from the frame's left edge;
  **`right_pct` is the right edge's position measured from that same left
  edge** — it is not a width, and it is not an inset from the right. A block
  spanning the middle two-thirds is `"left_pct": 16, "right_pct": 84`, never
  `"right_pct": 16`.
- **Use `gutter_pct` wherever the record measured a gap**, and `top_pct` only
  for a block whose position is independent of the one above it. A gutter
  survives a copy-length change; an absolute top does not.
- **`height_pct` is the zone's own height** — never the distance to the next
  zone. Without it a block grows into empty frame and swallows the picture.
- **`measure` and `max_lines` come from the record's measure and line count,
  unchanged.** They are the numbers every later pass prices its copy against,
  and one number governs every line in the element.
- **`weight` is required on every element.** A weight is a different typeface
  file, not a flag — recorded in prose and left out of the data, a bold
  headline rebuilds in regular and the ad reads wrong with every word right.
- **`segments` is present on every multi-colour line and omitted otherwise**,
  and **a segment carries its own `box` where the fragments sit on different
  panels.** A two-tone badge — white knocked out of red, then black out of
  white, butted together — is one line of two segments each with its own fill,
  never one box on the element.
- Every hex is a hex. Every percentage is a number, not a string.

Output rules: mandates only, no principles and no "consider." Leave out
anything that does not control this format. Never name the source's brand or
product in a mandate — **section 8 is the one exception, because it records
the source's own words as the thing the layout was measured around.** Say
nothing about how the asset gets produced — the same spec must be executable
as a generated image, a photographed shoot, or an illustration.

## The ground and the picture treatment

Two properties of the format that decide what the whole ad looks like, and
neither has been recorded so far. Both go in the layout JSON's `layout`
object, always:

```
"ground": "#FFFFFF",
"picture": {"treatment": "band", "top_pct": 32, "bottom_pct": 60}
```

- **`ground`** — the colour the ad sits on, sampled off the source. A format
  whose ground is not recorded gets rendered on a guess.
- **`blocks`** — every filled colour panel in the format, as a list. A
  panel is any solid area of colour that type sits on: an offer bar at the
  foot, a banner behind an eyebrow, a tinted footer.

  ```
  "blocks": [
    {"name": "offer", "color": "#E8577E",
     "top_pct": 60, "bottom_pct": 100, "left_pct": 0, "right_pct": 100}
  ]
  ```

  **Measured cause, 2026-08-31: an offer block rendered as nothing.** The
  format's foot was a pink panel carrying white type. The panel was not in
  the data, so the builder drew white words on a white ground and the whole
  offer vanished — the ad shipped with an empty bottom third and no error,
  because invisible type is not missing type. If a zone's colour is light,
  something dark is under it. Record it.

- **`marks`** — every non-text graphic element in the format. An icon, a
  symbol, an arrow, a rule, a seal. Position, size, colour, and what it is.

  ```
  "marks": [
    {"kind": "warning-triangle", "color": "#E8577E",
     "top_pct": 8, "left_pct": 8, "span_pct": 14}
  ]
  ```

- **`stickers`** — angled callout labels stuck onto the product cluster: the
  "60% OFF" flash, the "FREE Mystery Gift" tag. These are furniture, not
  copy zones, and they carry the offer.

  ```
  "stickers": [
    {"text": "60% OFF", "color": "#E8577E", "text_color": "#FFFFFF",
     "top_pct": 46, "left_pct": 22, "span_pct": 26, "rotate_deg": -12}
  ]
  ```

  **Measured cause, 2026-08-31.** A rebuilt ad was missing the format's
  warning-triangle icon and both of its sticker callouts, because the layout
  data has only ever described *text zones*. Everything that was not a
  paragraph fell through. The rebuilt ad had the right words in the right
  places and still did not look like the ad — the marks and the stickers
  were carrying the urgency and the offer, and both were simply absent.

  If it is drawn on the ad and it is not a photograph, it goes in the data.

- **`picture.treatment`** — `"band"` when the photograph is a contained
  block with ground above and below it, `"full_bleed"` when the photograph
  is the whole frame and the type sits on top of it. For a band, give its
  top and bottom as percentages.

**Measured cause, 2026-08-31.** Two swiped formats were both white-ground
designs with a picture band in the middle. Neither property was in the
data, so the builder laid the type over a full-bleed photograph — a
different kind of ad from the one that was swiped, and no amount of correct
zone positions repairs it. The difference between these two treatments is
the difference between the ad you swiped and one that merely shares its
words.

Sample the ground; do not assume white. Say which treatment it is; do not
leave the builder to infer it from the zones.
