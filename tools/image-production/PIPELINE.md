# The pipeline — one way to make an ad, every time

Ruled 2026-09-05 by Damon, after a four-ad batch took eleven passes because
there was no single way to do it.

**Damon never runs any of this.** He says what he wants; a session runs the
pipeline and hands him a link. This file exists so that every session runs the
*same* pipeline.

---

## The two rulings that shape it

**One generator: Higgsfield.** It holds the things nothing else has — the
thirteen roster identities (Elements and Souls) and `flex-360-true`, the product
reference built from seven real turntable angles. A picture is only as good as
its references, and they live there. The fal path is retired outright
(2026-09-13): `batch.py`, `generate.py` and `iterate.py` stop on their first
line, and the client is parked under `tools/superseded/fal/` so the <brand>
runs already built on it still read back.

**Auto-reject: he sees survivors only.** The machine kills anything failing a
checkable test and logs why. His eyes are the scarce thing; they do not get
spent on frames a script could have killed. **Every reject is a prompt defect —
fix the prompt, never the picture.**

---

## The six steps

### 1 · Write the batch spec

`runs/<brand>/<batch>/batch.json` — what is being made, and what it must pass.

```json
{ "brand": "<brand>", "product": "flex", "batch": "260909a",
  "avatar": "fedupking", "lane": "fed-up-king", "problem": "razorbumps",
  "ratio": "9x16", "model": "nano_banana_pro",
  "drive_root": "<the run folder's Drive id — RUN-01 fed-up-king is 10m4iiEGrPQtivHBtINjf_NkUr-OajyWI>",
  "offer": { "id": "flex-device", "bar_text": "90 days. If your skin doesn't transform, full refund. You keep the FLEX™." },
  "ads": [ { "slug": "01-void-ray", "cast": "ray", "sub": "forty-year-shaver",
             "angle": "forty-year-shaver", "concept": "specvoid",
             "format": "productvoid", "template": "prompted",
             "hook": { "text": "Forty years of shaving. Still bumped up.", "source_row": "unsegmented:15961" },
             "copy": { "headline": "…", "subhead": "…", "offer_bar": "…" },
             "checks": ["…anything ad-specific"] } ] }
```

**Added 2026-09-20 — the element keys.** `template` is `prompted` (the model
draws its own type) or a file in `templates/`; `pack` names a style pack in
`style-packs.json`; `picture_format` names a shape in `format-bank.json`. All
three are asked of the element library before anything is made, and an unknown
one is refused with the real ids. `format` is a different thing — the ad name's
own field — and is not checked against the format bank.

**Added 2026-09-09 — the record keys.** `lane` and `sub` (the sub-avatar the
unit embodies, bare slug, `null` when nobody declared it), `hook` (the
language-bank row the headline came from), `copy` (the words as declared, so
the record never has to read them off the pixels), `template` (`prompted` or a
layout path), `model`, and `drive_root` (where delivery lands). None of them
enter the filename; all of them enter the manifest row and the `made` record.

The offer is **copied from the offer bank, verified against the live store** —
never typed from memory. `angle` must be a signed angle from
`brands/<brand>/strategy/angles.json`; anything else names itself `unsigned` in
the filename, which is the machine telling Damon a strategy gap exists.

### 1b · One concept per ad unit. Every concept gets variations.

**Ruled 2026-09-05 by Damon. This is not optional and it is not a nice-to-have —
it is what an ad unit IS.**

A concept is one idea with one headline. "40 years of shaving. Still bumped up."
is a concept. "Nobody makes ads for my face." is a different concept. They are
never variations of each other.

A **variation** is the same concept photographed differently. Same headline,
same format, same layout, same offer bar, same cast — **only the picture
changes**: the angle, the crop, the pose, the setting, the light.

```
ad unit   <brand>-flex-static-ai-ray-…-40yearsshaving-…-260905b
          ├── a01.png   head and shoulders, product at the jaw
          ├── a02.png   chin lifted, neck to camera
          ├── a03.png   seated, product in the open palm
          └── a04.png   extreme close-up, beard and neck only
```

The intent was to upload **every variation of one concept into a single Meta
ad unit** and let Meta rotate them, so Meta would report one row for four
pictures. **That is not what happens** (proved 2026-09-11): Meta's bulk import
sheet carries one image, one headline and one body per row, so in the account
**one picture is one ad**. Variations inside a single ad need `asset_feed_spec`
on the Marketing API, which is blocked — `../meta-upload/API-ACCESS.md`.

This does not change how anything is named, and it is not a loss. Separate ads
are what let the report say *which* variation won; stacked inside one ad, Meta
picks silently and tells you nothing. The asset id still sits one field below
the ad name, so dropping the last field of any filename still gives the concept
it belongs to — that is now a grouping you do in the report rather than one
Meta does for you.

**A concept shipped with one picture is an unfinished concept.** Four
variations is the working default. Generate them in the same call so the copy
and the offer bar are identical across the set — a variation whose headline
drifted is a second concept by accident, and it will fight its own siblings
for the same audience while claiming to test the same idea.

**Every variation is checked separately.** They come off the same prompt, so it
is tempting to look at one and ship the set; the batch on the day this rule was
written produced four variations of one concept in which two rendered the wrong
product — one of them a white brush head, which is not a thing we sell.

### 2 · Cast from the roster, never from imagination

`brands/<brand>/core-avatars/casting/roster.json`. **One lane per batch** — the
offer's lane decides who is eligible, and fed-up-king never blends with glow-up.
Never the same face twice in a batch, and weight toward the ages and tones the
roster says have never been cast.

### 3 · 4:5-then-pad where the model draws type; 9:16 native where it does not

Put the reference ids in the prompt — cast Element **and** product Element —
and describe only what changes. Never describe a product from memory.

**Where the model draws its own type** — a headline, a badge, an offer bar —
generate at **4:5** and pad out to 9:16 afterwards with a flat band. Asking a
model to leave room for a safe zone does not work there; changing the canvas
does. Measured three times out of three (SAFE-ZONE.md, 2026-09-04).

**Where nothing is drawn as type** — a native photo reproducing an organic
post — generate at **9:16** and carry the safe-zone clause, which `prompt.py`
emits automatically off the ratio. Damon, 2026-09-14: *"the 4x5 is just for
the contents (subject, captions) to fit in there but the full images should
always be 9x16 so we can hit all placement."* The band is what breaks this
case: a flat bar top and bottom announces a native-looking post as an
advertisement, which is the one thing it cannot do. The 2026-09-04 ruling is
not overturned — it is scoped to the failure it actually measured.

One prompt per ad, saved verbatim to `prompts/<slug>.txt`. Frames land in
`inbox/<slug>.png`.

### 3b · The product goes in as an ELEMENT, never as words

**Ruled 2026-09-09 by Damon**, after five days of device slop: *"go look at the
device. You already have that identity tied in Higgsfield. All you need to do
is swap the device."*

Any prompt for a format that shows the product carries
`<<<8fad5612-d46f-4c19-baec-c3a636f22a4e>>>` — the FLEX Element built from
seven real turntable angles. **A device described in a sentence is a device the
model invents**, and it invented a spoon, a white brush head, a thing with a
handle, a thing the size of a head. The formats that do not show it —
`captionbox`, `commentreply`, `checklist` — are the only exemption.

Same rule for the man: his Element, not a description of his face.

### 4 · Corrections are image-to-image. Always.

The first pass is text-to-image. **Every pass after it feeds the approved frame
back in** as an `image_references` media and changes one thing:

> "Keep this image exactly as it is — same man, same layout, same type, same
> colours. Change ONLY «the one thing»."

A fresh text-to-image roll re-rolls the face, the type and the layout along with
the fix. That is what turned four ads into eleven passes.

### 4a · The reference is the bandless 4:5, never the padded 9:16

**Proved 2026-09-10, twice, the hard way.** An edit whose reference is the
finished 9:16 file comes back shrunken: the model reads the ink bands as part
of the picture, fits that whole thing into the new canvas, and adds fresh
bands around it. The man ends up small in a field of black and the type
shrinks with him. Asking for 9:16 output instead of 4:5 does not save it —
the second attempt did exactly the same thing.

So: **crop back to the centre 4:5 first** (`pad.content_4x5`), edit that, and
re-pad after. Same run, same instruction, correct reference — framing, scale
and type all held, and only the one thing asked for changed.

Say it in the prompt too, because it costs nothing: *keep the framing and
scale exactly as they are, do not add borders, margins or letterboxing.*

### 4b · A defect is a fix, never a hold

**Damon, 2026-09-10: "we want to get out the ads we made and if there are
issues then we need to solve them not just hold back."**

A check that fails is not a verdict, it is a work item. Nothing sits in a
held list waiting for someone to notice it.

Every failing picture goes down exactly one of three roads, and the road is
chosen by reading the picture against the check that failed:

| what is actually wrong | what happens |
|---|---|
| the picture really does contradict its words | it becomes a **kill with the fix written in it**, and the fix is an image-to-image edit by §4. The reason is the instruction |
| the check is wrong — it asked a still photograph to do something no still photograph can do, or judged text the picture never carried | it is **cleared and ships**, with the clearing written down beside it |
| the words are wrong, not the picture | the copy changes; the picture is untouched |

The clearing is written down because a cleared defect that leaves no trace
gets re-flagged on the next run and held again.

**Holding is only ever a state between finding and fixing.** A picture that
is still held when the sheet is built is a fix nobody ran, and it is reported
as that — not as a decision.

### 5 · Finish — judge, name, file, deliver

```
tools/finish.py runs/<brand>/<batch>
```

One command does the rest:

- **Measured checks** first, off the pixels — aspect, frame shape. No model, no
  argument, and a failure short-circuits the rest.
- **Seen checks** — a vision model against the standing tests plus the ad's own.
  A hedge counts as a FAIL.
- **The offer bar is judged again, alone and enlarged.** Inside the whole ad a
  vision model reads the price it *expects*: it passed a poster whose
  strikethrough turned $99.99 into a plain $90.99. Cropped away from that
  context, it catches it.
- Survivors are named by `naming/deliver.py` — the 13 fields, so Meta spend
  joins back to the creative that earned it — **in-process, with the per-asset
  extra** (sub, hook, copy, offer, model, references, qc) written into the
  manifest row.
- Every asset gets a **`made` record** (`naming/record.py`, kind
  `creative-asset`) — survivors and rejects alike. A `made` record is the
  machine's statement of what exists; it never reads as approval.
- Delivery goes **through the Drive API**, to `drive_root/<Man Age>/<format>/`,
  update-in-place. **Never the mount** — on 2026-09-07 Drive for Desktop went
  offline mid-copy and the server got names with no bytes.
- `report.md` says what passed, what died and why.

### 6 · Read the rejects, fix the prompts

The report is the tuning loop. A recurring reject means a standing rule is
missing from `SAFE-ZONE.md` or from the checks in `finish.py`.

---

## What is in git and what is not

Tracked: the code, the prompts, the manifests, the reports, this file.
Not tracked: rendered ads, which live in Shared Assets.

## Running it

```
run.py runs/<brand>/<batch> --dry-run     # free: every input, OK or MISSING
run.py runs/<brand>/<batch>
```

The dry run starts no model and writes nothing. The real run opens with two
gates — **elements** and **copy** (`tools/gates.py`) — and a held batch makes
nothing and says why in `check.json`. After the judge, the **media** gate
records every picture it failed as held from delivery, and the batch's record
(text only) is filed to `runs/image-production/<brand>/<batch>/` at the repo root.

Writes the plate jobs, and once a session has generated them and
`plates.py ingest` has filed them, judges them, names the survivors, files
them, delivers to Shared Assets and prints the link. `--generate-only` stops
before the gate; `--finish-only` judges frames already in `inbox/`.

Corrections do not go back through generation. `tools/make_variations.py`
feeds the approved frame in and moves one thing, in the same two halves —
prepare, a session, ingest.

## What the gate checks, and what it deliberately does not

Four standing checks — readable text, a complete offer bar, no competitor
branding, nothing grossly broken — plus one product check: would a customer
recognise this as the thing we sell. Then the offer bar is read a second time
on its own, cropped and enlarged, because a vision model reads the price it
expects when it can see the rest of the page.

**Narrowed on 2026-09-05, on Damon's call.** The first version counted fingers
and argued about the curvature of the product's base; it killed good ads and
cost more time than the defects were worth. The job is replicated structure,
brand injected correctly, consistent imagery. What survived is what costs money
or breaks the brand.


## Where the record goes

Every asset is a `made` record under `../creative-ledger/records/creative-asset/`
(the plane's shape, `platform/data/kinds/creative-asset.json`; the records move
to `platform/data/records/` when Dayu rules on lab writes there). People add
`signed`, `status` and `note` events on top; the machine never does.

Every finished run is also indexed by `../creative-ledger/ledger.py`, which reads the
manifests written here and makes production queryable — who has worn which
format and angle, and which combinations are untried. It is a separate tool
because it is not an image tool: statics, video and carousels all land in one
index off the same thirteen fields.

## The key

**There is no Higgsfield API key, and the workflow does not want one**
(Damon, 2026-09-14). Higgsfield's image models are reached through its
MCP, which a script cannot call, so generation runs in two halves with a
session in the middle: `tools/plates.py prepare` writes the jobs, the
session generates them, `tools/plates.py ingest` pads each 4:5 frame to
9:16 and files it. `tools/hf.py` is unwired notes on the API shape and
refuses to run.

### 4c · Higgsfield makes the pictures. Nothing else.

**Ruled 2026-09-11.** Damon, mid-run: *"remove fal from any workflow here...
just higgsfield only."*

fal had crept into this line as a convenience — `generate.py` and `polish.py`
called it for plates, and a variation runner written the same morning used it
because its key happened to be on the machine. It is out. Both callers now
refuse with a pointer here, and the client is parked at
`tools/superseded/fal/` so an old run's records still read.

Variations are made by `tools/make_variations.py`, which prepares the
bandless 4:5 references (§4a) and hands them to Higgsfield's
`nano_banana_pro` as `image_references` at 4:5. Higgsfield's image models are
reached through its MCP, so the run is: **prepare** the references,
a session submits the batch, **ingest** downloads and pads the results.

One model, one place, one look. A second generator means two houses of style
in the same ad set and no way to tell which difference the numbers are
reacting to.
