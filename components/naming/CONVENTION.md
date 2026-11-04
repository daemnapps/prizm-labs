# The short form — folder, file and Meta ad (the owner, 2026-09-29)

Ruled 2026-09-29. The 13-part name was too long to read in Ads Manager, and every detail it
carried is already in the brief. So a name now says only what finds the ad; the rest is looked
up by the brief number in `brands/<brand>/briefs/briefs.json` (`names.brief_header`).

**Brief numbers count per brand and product.** the owner, 1 Oct 2026: "brief numbers count per brand AND product — each product starts at 1 inside its brand." Older briefs keep their numbers; a brief is
brand + product + number, which the short name already carries. A bare number two products share is
refused ("say which"), never guessed.

**The product token is the catalog id — one product, one name.** A product is named by its full catalog id everywhere — the name
its kit folder (`runs/ai-elements/<brand>/products/<id>/`), its Drive folder and the hand-offs already
use: `widget-face-brush`, `crush-bump-eliminator`, `core-supplement`, `war-face-wash`, `prime-face-quench`,
`miro-face-towel`, `widget-charging-case`; a bundle is its Drive id (`vitals-set`, `king-set`). The short
store handles (`widget`, `crush`, `core`, `war`, `prime`, `miro`, `the-starter-set`, `the-bundle-set`)
are **aliases**: every lookup resolves through `names.product_id(brand, any_name)` (the reverse is
`names.product_aliases`), built from each kit's `kit.json` `aliases`, the brand's Drive index and
`product-aliases.json` here. So `<brand>_widget_brief-0076` and `<brand>_widget-face-brush_brief-0076` are
the same brief. New brief keys are minted with the catalog id; every register entry carries
`product_id`. Nothing already made or live is renamed — old keys, Meta cards and live ad names keep the
handle and still resolve.

| | Shape | Set by |
|---|---|---|
| **Delivery folder** | `brand_product_brief_batch` | the delivery rule, from the brief |
| **File** | `brand_product_brief_batch_asset-NN` — **no funnel** | the delivery rule |
| **Meta ad** | `brand_product_brief_batch_funnel` — **one per batch, no asset** | the upload tool at launch (`names.short_meta`) |

```
folder    brand_b_brilliance-body-scrub_brief-0136_batch-2026-09-27-a
file      brand_b_brilliance-body-scrub_brief-0136_batch-2026-09-27-a_asset-01.mp4
meta ad   brand_b_brilliance-body-scrub_brief-0136_batch-2026-09-27-a_body-scrub-cpk
ad set    adset_brand_b_spot-hider_pigment-memory          (avatar + angle, from the brief)
campaign  campaign_brand_b_us_brilliance-body-scrub_body-scrub-cpk_purchase_cbo
```

- The file carries no funnel because one file can launch to several pages.
- The Meta ad carries no asset: a batch's variations run under one name, and the batch is what
  gets read. Each launch of a batch to a page is its own ad, named for that page.
- Media, source, talent, avatar, problem, angle, concept, format and ratio live in the brief.
  A report joins on the brief number.

**The number is given when the brief is written (the owner, 2026-10-09).** An AI-route video brief gets
its brief-NNNN from the register (`tools/image-teardown/tools/briefs.py open … --type video-ai`)
the moment the teardown machine files it (`video-teardown/machine/file_run.py number_brief`); the run.json
of the teardown, the writing shelf and every production run made from it carry `brief`, and
`video-edit/deliver.py` names the delivery from that same field. One number, idea to Meta.

**Editors and designers never name files.** They drop finished work into a folder named with the
brief number, any file names. `delivery_rule.py` names the folder and every file from the brief,
writes `naming.json` (old → new) and `READY-TO-LAUNCH.md` (deliveries grouped by ad set). A
brief missing its product holds the delivery; a brief missing its angle is named but listed with
no ad set until the angle is set. Nothing is guessed.

The 13-part form below still parses (old deliveries and live ads keep it); new names are short.

---


# Ad naming — the key that ties creative to spend

**Applies to every lane: statics, video and carousels.** It lives here rather
than inside `image-production/` because a naming scheme that only one lane
follows cannot answer the question everyone actually asks, which is whether
static or video earns more.

Every static we ship carries a name that survives the round trip: repo →
Ads Manager → Meta's reporting → back here. Meta gives us one field we
control at upload, `ad_name`, so that field is the join key for the whole
feedback loop.

## Three levels in the account

```
CAMPAIGN   US | WIDGET™ | ICON
AD SET       Fed-Up King | 260911 | 1 of 3
AD             <the ad name, below>
```

This follows what the ad account already runs (`US | WIDGET™`, and message
themes like `Problem Solution` at the ad set) rather than a new scheme. The
**campaign** says which market, which product, which funnel. It persists for
months, so nothing dated and nothing about a batch goes in it — it has to stay
comparable to its own last month. The **ad set** is one message theme plus one
drop of creative, created fresh every batch and never added to, dated the day
it ships; the shard suffix appears only when Meta's 50-ads-per-ad-set cap
forced a split. The date is what keeps a theme usable forever — three of the
account's themes are already past 50 ads and cannot take another. Both are written by `components/meta-upload/naming.py`, and
`components/meta-upload/STRUCTURE.md` carries the account's limits and why the
ad set is a drop rather than a sub-avatar.

## Two levels below that, because that is how the ads are built

The intent was **every variation of one concept in a single ad unit**, Meta
rotating them, one report row for six pictures. **That is not what the account
does today**: the bulk import sheet carries one image, one headline and one
body per row, so one picture is one ad. Variations inside a single ad need
`asset_feed_spec` on the Marketing API — see
`components/meta-upload/API-ACCESS.md`.

The two levels below the ad set are therefore the ad unit and the asset, and
the asset id sits one field below the ad name so a filename always prefix-
matches the unit it belongs to.

So the asset id sits one level below the ad name:

```
AD UNIT (this is what goes in Meta's Ad name field)
brand_b_brilliance-body-scrub_static_ai_none_spot-hider_dark-spots_pigment-memory_turmeric-reset_photostrip_brief-0136_9x16_batch-2026-09-02-a

 brand    <brand>                 problem  dark-spots           brief  brief-0136
 product  brilliance-body-scrub   angle    pigment-memory       ratio  9x16
 media    static                  concept  turmeric-reset       batch  batch-2026-09-02-a
 source   ai                      format   photostrip
 talent   none
 avatar   spot-hider

ASSET (this is the filename — the ad name plus one field)
brand_b_brilliance-body-scrub_static_ai_none_spot-hider_dark-spots_pigment-memory_turmeric-reset_photostrip_brief-0136_9x16_batch-2026-09-02-a_asset-01.png
 the last field, asset-01, is the asset
```

`names.ad_name()` writes this form (`_` between fields, `-` between words);
the old form (`-` between fields, words squashed, `p136`, `260902a`, `a01`)
still parses.

**The asset name is the ad name plus one field.** Drop the last field of any
filename and you have the ad unit it was uploaded in. That prefix match is
the whole mechanism — no lookup table, no id to keep in sync.

| Field | What it is | Examples |
|---|---|---|
| `brand` | the brand | `<brand>`, `<brand>` |
| `product` | the product it sells — its catalog id; a store handle is an alias (`names.product_id`) | `brilliance-body-scrub`, `widget-face-brush` |
| `media` | **static, video or carousel** — the first thing anyone slices a report by, and recoverable from no other field | `static`, `video`, `carousel` |
| `source` | who made the picture — `ai`, `ugc`, `studio` or `mixed` | `ai`, `ugc` |
| `talent` | who is in it — a trained AI identity, a real creator, or `none` when no person appears | `susan`, `andrea`, `none` |
| `avatar` | who it is aimed at — the core avatar's slug, no invention | `spot-hider` |
| `problem` | the customer's problem | `dark-spots` |
| `angle` | the angle taken on that problem — signed in `strategy/angles.json` | `pigment-memory` |
| `concept` | the ideation and execution of that angle, not the headline | `turmeric-reset`, `hands-application` |
| `format` | the template it was built in — see `image-production/templates/` | `photostrip`, `confession`, `fullphoto` |
| `brief` | the brief that produced it, or `none` | `brief-0136` (old `p136`), `none` |
| `ratio` | the frame, because the same concept ships in several | `9x16`, `1x1`, `4x5` |
| `batch` | the date + a letter for the run that day | `batch-2026-09-02-a` (old `260902a`) |
| `asset` | **filename only, never the ad name** | `asset-01` … `asset-99` (old `a01`) |

Rules that keep it joinable:

1. **Lowercase `[a-z0-9]` inside a field. Hyphen only between fields.** A
   hyphen inside a field breaks the parse, so `spot-hider` becomes
   `spothider`.
2. **Thirteen fields in an ad name, fourteen in a filename.** Always all of them.
   A missing field shifts every field after it into the wrong column.
3. **The name is a key, not a description.** It carries what you group by.
   The headline text, the offer, the plate, the prompt, the swipe it came
   from — all of that lives in the batch manifest and is recovered by
   joining on the name. Never encode a headline in a name.
4. **A name is never reused or re-pointed.** If the creative changes it is a
   new asset in a new batch. Reusing a name silently merges two creatives
   into one row and the report is then wrong in a way nobody can see.

## What is measurable, and what is not

Because all six variations share one ad unit, **Meta cannot tell you which
headline won.** That is a real cost of building ads this way, and it is
worth stating plainly rather than discovering it during a report.

What the ad unit *can* answer, cleanly:

- **static against video against carousel** — field 2, the split that
  decides where production time goes
- **which concept earns** — group on field 5 across every format
- **which format earns** — group on field 4 with the concept held constant
- **which frame earns** — field 6, the same concept at 9x16 against 1x1
- **whether the avatar is right** — field 3 against
  `meta_ad_insights_demographics.age` / `gender`. If `spothider` converts
  55+ women the avatar is real; if it converts 35s it is not, and that is
  the most valuable thing this can tell us.
- **whether a batch regressed** — field 7 dates every change to the machine

To measure a headline you have to give it its own ad unit — same concept,
same batch, one asset in it. Worth doing for a small number of contenders,
not for everything.

## The manifest

Every batch writes `manifest.json` beside its ads: the ad unit name once, and
one row per asset carrying what the name deliberately leaves out — the
headline verbatim, the offer, the template, the plate file, the model and
size that made it, and the swipe it was torn down from.

Meta hands back `ad_name`, spend and purchases. The manifest turns that row
back into *a concept, a format, an avatar and six known pictures*.

The Meta side lives in `ecom_data_sync_supabase_demo` — `meta_ads`,
`meta_ad_insights`, `meta_ad_insights_demographics`, joined on `ad_id` /
`campaign_id`. Nothing there needs to change: we are only agreeing to fill
one field it already stores.

## Where it is wired

Naming is a step in production, run by machine at delivery. Nothing in
either lane reaches Drive unnamed.

| Piece | What it does |
|---|---|
| `naming/names.py` | Builds and parses names. Refuses an unknown `media` or `source`, refuses a rename onto an existing name, and picks the next free batch letter by scanning both lanes' runs. |
| `naming/deliver.py` | The delivery gate: renames every asset, writes the manifest, runs the audit, prints the ad unit. Reads `problem` / `angle` / `concept` from the brief and warns when a flag disagrees. Warns on an angle the brand has not signed. |
| `naming/selfcheck.py` | Twenty checks over the real code and every delivered batch. Run it before trusting a report. |
| `image-production/batch.py` | Statics. Calls the gate itself, so a run that makes ads makes named ads. |
| `ai-video-production/machine/deliver.py` | Video. Same standard, `media=video`, `talent` usually a creator or a trained identity. Refuses to guess a field the brief does not state. |
| `image-teardown/build_ui.py` | The board shows each run's ad unit and each asset's name, so a picture on screen can be found in a report. |
| stage-6 prompt | Declares `problem`, `angle`, `concept` in the brief, and is told never to coin an angle slug. |
| `brands/<brand>/strategy/angles.json` | The angle vocabulary. Only the owner signs one active. |

Run the self-check with:

```
python3 components/naming/selfcheck.py
```

## The swipe join

A competitor's ad and one of ours are the same kind of object. Both have a
form, a maker, a person in them (or nobody), a problem they speak to, an angle
on that problem, an execution of that angle, a template and a frame.

So the swipe library describes its creatives in **these fields**, not a
parallel set of its own:

```
media · source · talent · problem · angle · concept · format · ratio
```

`names.py` owns that list as `CREATIVE_FIELDS` and the swipe library imports
it. The remaining ad-name fields — brand, product, avatar, brief, batch — are
ours alone and have no meaning on someone else's ad.

**Why it matters.** Group a Meta export on `problem` and group the swipe corpus
on `problem`, and the two answers are comparable. Two vocabularies for one idea
is how you end up unable to say whether the thing that won was the thing you
swiped.

### The reference

`swipe:<brand>:<ad_id>` — for example `swipe:resilia:162098799`.

Competitor brand, and the id the ad tool gave the creative. Not a description
and not a path: the Drive file gets renamed, the teardown gets rewritten, and
this still resolves. It goes in the **manifest**, not the ad name, for the same
reason the prompt and the plate do — the name carries what you group by, and
you do not group a report by which competitor an idea came from. You look it up
once you have a winner.

### Derived, and judged

Two of the eight fields are facts about the file and are filled by machine:

- **media** — a creative with a video is a video ad, otherwise static.
- **ratio** — measured off the file itself.

The other six are judgements a person makes: is this AI or a creator, who is in
it, what problem does it speak to, what angle on that problem, what execution,
what template. Until someone judges, they read `unclassified` — written, never
blank, because blank reads as an answer (`none` means "nobody is in it") and a
missing key reads as a bug.

`selfcheck.py` fails if the two vocabularies drift, if a described creative is
missing a field, if any field is blank, or if a creative has no reference.
