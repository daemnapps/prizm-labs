# Product kits — every product, measured from its own photos

the owner, 2026-10-02: *"similar to how we have casting sheets for our avatars, you
basically have to build real models of products as well."* A product kit is the
product's casting sheet. Every picture with one of our products in it — video
stills, image ads, emails — is checked against it. No product is drawn from
memory or from words.

## What a kit is

One folder per product: `runs/ai-elements/<brand>/products/<slug>/`

| file | what it holds |
|---|---|
| `kit.json` | the measurements and **how each one was taken**, the photos used, the status |
| `sources/` | copies of the product's real photos from Drive (packshot first) |
| `model/` | the 3D model (`.blend`), the label pictures (`front.png`, `back.png`), the real packshot cut out (`packshot-cutout.png`), and the reference pictures: front, turned, back — each on white and transparent |

What gets measured, all from real photos (nothing invented):

- **Shape** — how many times longer than wide, along the product's own axis
  (`axis_ratio`), from its exact cut-out of the cleanest packshot; plus the
  width at every height (`profile`) and where the cap or pump starts.
  Cross-checked on the other photos.
- **Real size** — needs **one ruler measurement** (height and width in cm),
  written into `size_cm` by hand and `"size_cm"` added to `hand_set`. The
  machine reads the product against the hands and faces holding it in real
  photos (`size_reads`), but tested on every product on 2 Oct those reads run
  1.5–2× too big (the product is nearer the camera than the hand), so they are
  kept as evidence only and never written as the size. Until measured, the model
  is built to a nominal 10 units tall — its shape is exact either way.
- **Colours** — the product's own colour at each height, as hex.
- **Label** — the front lifted from the packshot; the back from a real back
  photo, or plain colour with no words when there is none. The label's biggest
  words are read (macOS Vision) and kept as `label_words`.

Media never goes in git. kit.json does.

## The one command

    python3 tools/video-production/machine/product_kit.py build <brand> <slug>

It copies the photos, looks at each (where the product is, which way it faces,
held or not, what kind of thing it is), picks the clean packshot (front-facing,
not held, straight, plain background, **whole product in frame**), measures,
lifts the labels, builds the model with the builder for its kind, renders the
references and checks them. Anything a person set by hand and listed in the
kit's `hand_set` is kept; the machine's fresh measures of those land beside them
in `remeasured`, so the two can be compared.

Then publish it for the team:

    python3 tools/video-production/machine/product_kit.py publish <brand> <slug>

This copies the team-usable kit to the product's own Drive folder,
`Shared Assets/brands/<brand>/products/<slug>/product-kit/` — a plain README for
designers and editors, kit.json, the .blend (labels packed inside), the
references on white and transparent, the label pictures and the real packshot
cut out. Older copies move to `product-kit/versions/`. It writes nothing else on
Drive.

Other commands: `list` (every product vs its kit — see the gate), `render
<brand> <slug>` (re-render after a hand edit to kit.json), `check <brand>
<slug>`.

## The kinds

| kind | builder | the model |
|---|---|---|
| tube | `blender/tube.py` | the measured outline, flat crimp at the top, the body narrowing onto the cap (bottom width = cap × 1.02, depth = cap depth × 1.05) |
| bottle, pump bottle, jar / tub | `blender/bottle.py` | the measured outline turned on a lathe, front and back labels wrapped on |
| box | `blender/box.py` | the measured front, depth from a side photo (unmeasured until one is read) |
| device (brush, case, tool) | none — **photo-only** | no honest procedural model; the real cut-outs are the references |
| soft goods (towel, pouch, bag) | none — **photo-only** | as above, and its shape is not fixed, so pictures are not measured for shape |

A new kind is one more builder in `blender/` and one row in `KINDS`
(`product_kit.py`). A product with no usable photos gets a kit that says
**"no real photos"** — never a made-up one.

## The check

The model's front render is cut out the same way every picture is (SAM) and
must be within **±3%** of the real packshot's shape, and its label's key words
must read. Status `model` = passed; `model — check failed: …` says what is off.

In production, every still made with a product photo among its references is
measured against the kit (`product_check.py`, ±12% on shape, label words read)
and, if off, fixed by one edit that keeps the picture and replaces only the
product (`product_fix.py`, with the kit's reference and the real packshot).

## The refinement pass — a kit is a draft until it passes this

the owner, 2026-10-05, looking at the Brand B kits: *"these product models are not
really that high quality … we did this same process for the Brand A product,
which helped us make really great video ads, so this needs to be
standardized."* `product_kit.py build` makes a DRAFT. The Brand A product
became good because it was then refined by hand, part by part, against the real
product — eleven fields in its `hand_set`, each with its reason in `how`. Every
product goes through the same pass before its kit is used in a picture.

1. **Best source first.** The studio renders on Drive
   (`products/<slug>/cgi/` — stills, turntable sequences, 360 spins) come
   before any packshot: they show the real shape, finish and label at every
   angle, at up to 4000 px. A packshot is used only where no studio render
   exists. A label is never lifted from a crop under 2000 px tall.
2. **Real size, worked out from photos of it in use.** Nobody holds a ruler
   to these products — the owner, 2026-10-05: *"you had to figure it out by taking
   in product images of it in use … because I don't actually know."* The size
   is judged, as the face scrub's was, from the real photos where it sits
   against something of known size: a hand holding it (palm heel to fingertip,
   knuckles across), a face beside it, a sink or shelf. Read several photos,
   say in `how` which anchor each used, and cross-check against the label's
   stated volume and the stock size of that container. Written into
   `size_cm` with a `plus_minus`. The machine's own `size_reads` run 1.5–2×
   too big and stay evidence only.
3. **Shape, part by part.** Body, shoulder, collar, cap, pump, nozzle — each
   one measured from the side view of the turntable and built as its own part,
   not one lathe outline.
4. **Finish, not just colour.** Every part names its finish (polished metal,
   matte, gloss, soft-touch, frosted, clear) and its exact colour, sampled from
   a studio render in neutral light. The model's materials are set from both.
5. **Labels at print sharpness.** Front and back, flattened from the
   turntable or taken from the print file; every word read and matched against
   `label_words`. A soft or smeared word fails the pass.
6. **Devices and soft goods get a real model too.** No lathe: the model is
   made from the studio 360 spin (`components/3d/`, `components/objects/`),
   then checked the same way. Photo-only is a temporary state, not a kind.
7. **Side by side, then signed.** Model next to studio render at the same
   three angles — front, turned, back. The status becomes `approved` only on
   the owner's word, recorded in kit.json.

**Every angle, not three** (the owner, 2026-10-09: *"hyper analyze this so we get
it 100% accurate … the depictions [must] be perfect so they pass as
believable"*). Where the store has a 360° video, the model is checked against
**every turntable angle it has** (the device: 24), outline by outline, aligned on the
body's centre — three views hid a front that was 7% too boxy at the
three-quarter angles. When a model carved from all the frames exists, the
shell takes its cross-sections and the hand-built detail sits on top. Fine
detail is measured too, not eyeballed: the bristle pitch by FFT of the store
frame, the band edges and the back's indents by their rows in the store
frames. And a model is built at its **true size**, so a product inside its
case or in a hand is at real scale. The working files for a pass live in the
product's own `model/work/` (not in git), never in a temp folder.

Every refined field goes into `hand_set`, with its reason in that field's
`how`, so a rebuild keeps it.

## The gate — every new product goes through this

`product_kit.py list` shows every product folder on Drive against its kit;
any product with no kit (or a kit that is not ready) is listed as **not ready**,
by name. The same gate runs inside every production run (`run.py`,
`product_gate`): a still whose references include a photo of a product with no
usable kit **stops before anything is paid for**, with one line naming the
product and the command that builds its kit. Bundles and shared shots are not
single products and are not gated.

## Where it is used

- **Video pictures** — `run.py` checks and fixes the product in every still.
- **Image ads and emails** — attach `reference-front.png` and the real
  packshot as the product references; check the result with `product_check.py`.
- **Designers and editors** — the Drive `product-kit/` folder: transparent
  PNGs for Photoshop / Figma / video, the .blend to pose the real product.
