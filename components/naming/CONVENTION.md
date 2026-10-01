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
CAMPAIGN   US | FLEX™ | ICON
AD SET       Fed-Up King | 260911 | 1 of 3
AD             <the ad name, below>
```

This follows what the ad account already runs (`US | FLEX™`, and message
themes like `Problem Solution` at the ad set) rather than a new scheme. The
**campaign** says which market, which product, which funnel. It persists for
months, so nothing dated and nothing about a batch goes in it — it has to stay
comparable to its own last month. The **ad set** is one message theme plus one
drop of creative, created fresh every batch and never added to, dated the day
it ships; the shard suffix appears only when Meta's 50-ads-per-ad-set cap
forced a split. The date is what keeps a theme usable forever — three of the
account's themes are already past 50 ads and cannot take another. Both are written by `meta-upload/naming.py`, and
`meta-upload/STRUCTURE.md` carries the account's limits and why the
ad set is a drop rather than a sub-avatar.

## Two levels below that, because that is how the ads are built

The intent was **every variation of one concept in a single ad unit**, Meta
rotating them, one report row for six pictures. **That is not what the account
does today**: the bulk import sheet carries one image, one headline and one
body per row, so one picture is one ad. Variations inside a single ad need
`asset_feed_spec` on the Marketing API — see
`meta-upload/API-ACCESS.md`.

The two levels below the ad set are therefore the ad unit and the asset, and
the asset id sits one field below the ad name so a filename always prefix-
matches the unit it belongs to.

So the asset id sits one level below the ad name:

```
AD UNIT (this is what goes in Meta's Ad name field)
<brand>-static-spothider-photostrip-turmericreset-9x16-260902a
   |      |       |          |            |        |      |
 brand  media  avatar     format       concept   ratio  batch

ASSET (this is the filename — the ad name plus one field)
<brand>-static-spothider-photostrip-turmericreset-9x16-260902a-a01.png
                                                                |
                                                              asset
```

**The asset name is the ad name plus one field.** Drop the last field of any
filename and you have the ad unit it was uploaded in. That prefix match is
the whole mechanism — no lookup table, no id to keep in sync.

| Field | What it is | Examples |
|---|---|---|
| `brand` | the brand | `<brand>`, `<brand>` |
| `media` | **static, video or carousel** — the first thing anyone slices a report by, and recoverable from no other field | `static`, `video`, `carousel` |
| `avatar` | who it is aimed at — the core avatar's slug, no invention | `spothider` |
| `format` | the template it was built in — see `image-production/templates/` | `photostrip`, `confession`, `fullphoto` |
| `concept` | the angle, not the headline — a claim family reused across many ads | `turmericreset`, `agespots` |
| `ratio` | the frame, because the same concept ships in several | `9x16`, `1x1`, `4x5` |
| `batch` | `yymmdd` + a letter for the run that day | `260902a` |
| `asset` | **filename only, never the ad name** | `a01` … `a99` |

Rules that keep it joinable:

1. **Lowercase `[a-z0-9]` inside a field. Hyphen only between fields.** A
   hyphen inside a field breaks the parse, so `spot-hider` becomes
   `spothider`.
2. **Seven fields in an ad name, eight in a filename.** Always all of them.
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
| `brands/<brand>/strategy/angles.json` | The angle vocabulary. Only Damon signs one active. |

Run the self-check with:

```
python3 components/naming/selfcheck.py
```

## The swipe join

A competitor's ad and one of ours are the same kind of object. Both have a
form, a maker, a person in them (or nobody), a problem they speak to, an angle
on that problem, an execution of that angle, a template and a frame.

So the My Feeds library describes its creatives in **these fields**, not a
parallel set of its own:

```
media · source · talent · problem · angle · concept · format · ratio
```

`names.py` owns that list as `CREATIVE_FIELDS` and the My Feeds library imports
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
