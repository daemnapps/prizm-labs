---
name: image-production
description: Run the image engine — a picture request (brand, what it is for, the direction in words) goes in; the pictures come out, judged, filed and mirrored to Drive. Use whenever someone says "make the picture for this brief", "produce this image for <brand>", "generate the hero for the email", "make a product shot", "make the still for scene 2", "make the covers for this ad", "thumbnails for the versions", "run image production", or names a brand and a purpose and describes a picture.
---

# Image production

> **Activates component:** `components/image-production` — `make.py` makes a picture, 9:16 from the start.


External dependencies: `components/image-production/` (the engine; `purposes.json` is what a picture can be for, `models.json` the route), `brands/<brand>/` (the product photos and facts — read, never written), `components/elements` (style, format and template rows), `components/models` (the developer's registry — read, never edited).

**One command.**

```
python3 components/image-production/make.py --brand <brand> --purpose <purpose> --direction "<words>" --out runs/image-production/<brand>/<label>/ [--aspect 9:16] [--count 2] [--product <key>] [--people | --no-people] [--from-image <png>] [--ref <png>] --dry-run
python3 components/image-production/make.py --brand <brand> --purpose <purpose> --direction "<words>" --out runs/image-production/<brand>/<label>/ [...]
python3 components/image-production/make.py purposes          # what a picture can be for
python3 components/image-production/make.py covers --job <job.json> [--only <version>] [--dry-run]   # every version's cover for one video ad
```

- `--brand`, `--purpose` (`email-hero` · `email-offer` · `ad` · `page-section`
  · `video-still` · `product-shot` · `cover`), `--direction` and `--out` are all
  required. `--set <filed 3D set>` is required while the set gate is on: the
  set's kept print is the base (`components/image-production/CLAUDE.md`, GATE-4). `--out` is the session's choice; use the run shape in
  `runs/README.md` — `runs/image-production/<brand>/<label>/`.
- `--people` / `--no-people` must be said when the purpose has not decided —
  the model route splits on it and the gate refuses a guess.
- `--from-image` makes it an edit of that picture, not a fresh render
  (for a spot fix or a variation use `image-edit` / `image-variation`, which
  add the two-picture judge).
- **`--dry-run` spends nothing** — prints the prompt exactly as it would be
  sent, the model and why, whether each key is on this machine, what the
  judge would ask, and where the files would land. Nothing written, nothing
  on Drive.

## References — every picture starts from something real

1. **IMAGE 1 is real:**
   - a video cover (thumbnail): the strongest clean frame of that version's own video, through the cover job below (`frame`);
   - a scene or room: a real photo (own shoots, customer photos, creator footage).

   Never words alone. Never an AI-made picture as a reference.
   No reference given: the tool pulls the nearest REAL brand assets itself, through the Drive key (shelves listed by the key and kept a day; a picked file fetched by its id), plus the footage index's own frames: creator footage, product photos, brand shoots. Generated folders are never pulled: `ai-elements`, `set`, `core-avatars`, the archive, intake, finished ads.
2. **Faces from their reference.** Pass the person's real photo or casting sheet as `--ref`, for every face, including faces on phone screens, cards and billboards. One face per creative.
3. **The product comes from its kit and is never drawn.** `--product <key>` reads the kit's real pictures and its 3D model. On a cover the product is rendered from the 3D kit and placed by the tool, with a set named too; a cover that names no product shows none.
4. **Words go on top**, through `image_production.words`, never on a face, lips or hands. Whether a purpose's model may paint words is its `words` row in `purposes.json`. A cover's words are never painted by the model: the cover job sets the headline (`words.set_headline`) before the cover is delivered, and nothing is added to a cover after that.
5. **Turn it up with the dials.** Add `creative_controls.target_md('maxed', <brand>, 'image')` to the direction. Write one real-looking idea that says the claim.
6. **Check each picture by eye** (the model judge is off, `models.json` `judge.on`). These are misses:
   - the wrong face on a screen;
   - added words;
   - a drawn or changed product;
   - words on a face or hands;
   - a polished or cinematic look.

   A miss is remade through the tool, never patched by hand.

## Covers — one job for every version of a video ad

A cover is purpose `cover`, never `ad`. One call makes every version's cover (`--dry-run` first; it spends nothing):

```
python3 components/image-production/make.py covers --job <job.json> [--only <version>] [--dry-run]
```

```
{"brand": "<brand>", "ad": "<ad id>", "out": "runs/image-production/<brand>/<label>/", "set": "<filed 3D set>",
 "people": true, "references": ["<cast sheet>"], "product": "<key, when the product is in frame>",
 "versions": [{"version": "control", "headline": "<its headline>", "video": "<its own video>", "t": <second>,
               "frame": "<the frame of that video at t>", "swipe": "<id of the real cover it follows>",
               "direction": "<the moment, the concept, the one thing pushed>"}]}
```

1. One cover per version, each from a different frame of its own video (a real video stream, never a still picture), checked against that video at `t`; a picture the tool made is refused as a frame, a re-saved or re-encoded copy of a cover or its plate too. The frame is the composition; the filed set's kept print decides the people and the room.
2. `product` puts the product in from its 3D kit (`product_place`: `x`, `y`, `height`). `"product": false` on a version leaves it off.
3. The headline is set by the tool in one type for the whole ad: same face, weight, size and band. `type` on the job follows the swipe's type. `direction` never carries the words; a version with none gets the job's standing direction, with the concept taken from its swipe's rated move in the cover index (no rated move: refused).
4. In `out`: a folder per version, `covers.json` and `cover-type.json`. File only covers whose row says `ok`, each from its own folder: the record the approval filer reads sits beside it. A single cover request exits 1 when its cover is not `ok`.
5. The tool reads the faces under the words; a cover whose faces were not read is not `ok`. Check every cover by eye against its cast sheet and beside its swipe. A miss is made again through the job (`--only`), never patched.

The whole contract, the single-version request and the switches: `components/image-production/CLAUDE.md`, "Covers".

## The rules the command enforces — do not work around any of them

1. **A field nothing on the list names is REFUSED, not ignored.**
2. **Refused, never guessed.** An unknown purpose, element, model or aspect
   stops the work and names the real ones. A row whose definition starts
   `[TO DEFINE` is refused as named but not defined yet.
3. **Three gates:** inputs (brand real, direction given, purpose and frame on
   their lists, `people` declared, the product's photo a file on this machine,
   a real reference for `ad` · `video-still` · `product-shot` (`purposes.json` `reference_required`),
   no AI-made picture as a reference)
   · elements · media (a picture the judge failed is HELD and never reaches
   `out`; survivors still ship; fix the prompt, never the picture).
4. **Every photo and video asset (not email) is 9:16, made 9:16 from the start** (the owner, 2026-10-26). A safe-zone
   purpose (`ad`, `video-still`) asks the model for 9:16 with the centre 4:5 as the safe zone in the prompt; the judge
   measures the zone. Nothing is made at 4:5 and painted out.
5. **No brand, product, person or model name in code or in a prompt.**
6. **Nothing is ever deleted on the Drive mount.** Copied in or replaced in
   place only.
7. **A changed prompt is a new file** `-v<N+1>-owner.md`; highest wins.

## What comes back

In `out`: the pictures, `prompt-as-sent.txt`, `elements.json`, `check.json`,
`run.json`, `rejected/*-why.md`; pictures mirrored to
`Shared Assets/runs/image-production/<brand>/<label>/` on Drive.

Report: how many made, how many passed, which were held and why (one clause
each), the model used, and the Drive link — and send the passing picture as
an image so it is seen without opening anything.

Reply with the result and the folder it landed in (repo path or Drive folder name).
