# image-production

## How to use it → https://dashboard.the company.com/atlas#c-components-image-production

One image engine every workflow uses. An email hero, a static ad frame, a
landing-page section picture and a scene still all go through the same models,
the same prompting structure and the same context structure — the only thing
that differs between them is one row in `purposes.json`.

Before this, an email's pictures were made one way and an ad's another, and the
two disagreed about the frame, about whether the real product photo was passed
in, and about who checked the result. Now there is one answer and it is
written down.

## What a caller does

```python
import sys
sys.path.append("tools/image-production")     # append, never insert at 0
import image_production as IP

result = IP.make({
    "brand": "…",                 # a folder under brands/
    "purpose": "email-hero",      # what the picture is for
    "direction": "…",             # the words describing the picture
    "people": False,              # is a photoreal person in frame?
    "product": "…",               # optional
    "out": "runs/<machine>/<brand>/<label>/media",
    "label": "…",
})
result["delivered"]               # the pictures that passed the judge
result["held"]                    # the ones that did not, and why
```

Or from a terminal:

```
python3 tools/image-production/make.py \
    --brand <brand> --purpose email-hero \
    --direction "a man in his forties at a bathroom sink, morning light" \
    --no-people --product <product> --style candid-ugc \
    --out <dir> --label <label> --dry-run
```

`make.py purposes` lists what a picture can be for.
`make.py route` prints the model table and says which keys are on this machine.

## The six pieces

| | |
|---|---|
| **One request shape** | `brand · purpose · direction · out` required, everything else optional. Declared in `CLAUDE.md`; a field nothing declares is refused |
| **One context builder** | `context.py` — the product photo and the product's real facts, the logo, the palette, the fonts, the element rows. All read from `brands/<brand>/` at run time |
| **One prompting structure** | `prompts/picture-vN-owner.md` — ten slots in a fixed order, the caller's direction in one of them, the standing rules on the end of every one |
| **One model route** | `models.json` — a forced model, else an edit, else a person, else an object. Read from the table, never decided in a caller's code |
| **The judge** | `judge.py` — measured off the pixels first, then the brand's own product tests and a direction-match test put to a vision model. A judge that did not run holds the picture |
| **Three gates** | inputs · elements · media, through `components/marketing-chain-checks`, into a gate-keyed `check.json` |

## The product comes from its 3D model (2026-10-14)

the owner: *"you need to use the 3d models moving forward for product because its
the foundation of everything now."* The image model kept drawing the product
wrong — standing it up on a round bottom it cannot stand on, changing its
shape. So it no longer draws the product at all.

When a request names a product whose kit has a 3D model, it happens by itself:

1. **The scene is made empty.** The image model gets no product photo and is
   told to leave a clear spot where the product goes (`prompts/product-space-v1-owner.md`).
2. **The product is rendered** from the kit's 3D model in Blender, in a pose the
   kit allows (for a device that cannot stand: seated in its holder), from the
   camera angle and light the scene needs.
3. **It is put in** with a contact shadow, the scene's light and colour, and the
   scene's grain. The empty scene is kept beside it (`generated/*-scene.png`).
4. **The judge looks at the finished picture**, with the product's own tests.

On for any product whose kit carries `model/render3d.json` (the model file, its
poses, and the real turntable pictures it is measured against); off for every
other product. `product_3d: false` (or `--no-product-3d`) turns it off;
`product_place` (or `--product-place '{…}'`) says where it goes, how big, which
pose, camera and light.

**Real size.** Unless the request names the spot, the empty scene is read
(`prompts/product-locate-v1-owner.md`): where the empty spot is, and a common
object of known size near it (a hinge, an outlet plate, a tap). The product is
then sized from its real measurements against that object, never by eye.
A brief that already reserves a `product_zone` gets the product fitted there.

**The cradle is a stand-in.** No real 3D model of the charging cradle exists
yet, so the one shown is built from the device's own back half to match the
brand's pictures. It is replaced when a real cradle model is made.

`product3d.py` does the same steps by hand: `render` a product, `place` it in
any picture (a box, or a point plus the scene's pixels-per-cm so it comes out at
its real size), `iou` to score the model against the real turntable photos,
`poses` to list what a kit allows.

## Where things land

```
<out>/                                  the caller names it
  <label>-01.png …                      the pictures that passed
  prompt-as-sent.txt                    the prompt, verbatim
  elements.json  check.json  run.json   the record
  rejected/<name>.png + -why.md         what was held, and why
  generated/                            every frame the model returned

Shared Assets/runs/image-production/<brand>/<label>/     the Drive mirror
```

Nothing is ever deleted on the Drive mount, and a mirror that cannot be written
prints SKIP rather than failing the delivery.

## What it does not do

It does not write the words, lay out an asset, composite type, upload to
Klaviyo or Meta, or decide what to make. A caller brings a direction and gets
pictures back.

## Lifted from

| Part | Source |
|---|---|
| the judge, the standing checks, the reject note | `tools/image-production/static/tools/finish.py` |
| the brand's product tests | `tools/image-production/static/tools/brand_facts.py` |
| slots not prose, the fixed order, the 9:16 safe-zone clause | `tools/image-production/static/tools/prompt.py` |
| the gates and their `check.json` | `tools/image-production/static/tools/gates.py` |
| paths found by walking up, the packshot for the product NAMED | `tools/image-production/static/tools/paths.py` |
| the OK / MISSING dry run | `tools/image-production/static/tools/dryrun.py` |
| the person/object model split | `tools/image-production/static/tools/plates.py` |
| the OpenAI door, and its transport seam | `tools/video-production/machine/direct_openai.py` |
| the Google door | `tools/video-teardown/machine/frames.py` |
| the offer picture made FROM the real product photo; the email frame and tier | `tools/email-production/simple_email.py` |
| the Drive mirror path, and the three loud mount failures | `components/run-kit/run_kit/filing.py` |
| `hold()` and the five gate names | `components/marketing-chain-checks` |
| every element id asked, never assumed | `components/elements` |

## Tests

```
python3 tools/image-production/tests/test_image_production.py
```

Stdlib `unittest` (the run prints the count). No network, no model, no real key. Every test
builds a throwaway workspace under `tempfile`, points `AI_WORKSPACE` at it and
passes a stub provider and a stub judge — nothing reaches `runs/`, `brands/`, a
real endpoint or the Drive mount.
