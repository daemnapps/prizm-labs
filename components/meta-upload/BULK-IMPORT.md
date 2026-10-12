# Meta bulk import — what the template holds

**This is the column reference.** For the order you do things in, and the
traps between the steps, read `RUNBOOK.md` beside it.

Read off Meta's own template, downloaded from the **1. Brand B** account
2026-09-10: `AdsManagerTemplate_v2.3.xltx`, 143 columns, two sheets. Not from
a blog post. Everything below is what the file itself enforces.

**Where it lives in Ads Manager:** the campaign table → **More** →
*Import and export ad configuration* → **Import ads in bulk** /
**Download Excel template**. (Not under the Export icon, not under the ⋯ menu.)

---

## The three situations, and what changes between them

The ID columns are the switch. Blank id = make a new one; a real id = attach
to the existing one.

| situation | Campaign ID | Ad Set ID | Ad ID |
|---|---|---|---|
| 1 · new campaign | **blank** | blank | blank |
| 2 · existing campaign → new ad set | **the id** | blank | blank |
| 3 · existing ad set → new ads *(the usual)* | the id | **the id** | blank |

In situation 3 you still repeat the campaign and ad-set columns on every row,
but Meta reads the ids and does not re-create anything. One row is always one
ad.

---

## What a drop looks like — situation 1

the owner's frame, and it maps cleanly onto Meta's own three levels:

- **campaign = the offer**
- **ad set = the targeting**, and here the targeting IS the avatar / sub-avatar
- **format = the packaging** — the message shaped the way that avatar responds to

So: one CBO campaign, one ad set per sub-avatar, the ads inside each.

### Campaign — CBO at $__/day
| column | value | why |
|---|---|---|
| Campaign ID | *(blank)* | makes a new campaign |
| Campaign Name | rendered by `naming.py` from the brand's own template — never typed | |
| Campaign Status | `PAUSED` | nothing spends on import |
| Campaign Objective | `Outcome Sales` | The template's VALIDATION sheet still lists the legacy names, but the live account answers *"This objective cannot be published"* for `Website Conversions`. **ODAX names only now** (proved row by row, 2026-09-11) |
| Buying Type | `AUCTION` | |
| Campaign Daily Budget | `100` | |
| Campaign Bid Strategy | `Highest volume or value` | **budget + bid strategy at campaign level = CBO.** Leave every Ad Set Daily Budget blank or it becomes ABO |
| Special Ad Categories | *(blank)* | not housing/credit/employment |

### Ad set — one per avatar / sub-avatar
| column | value |
|---|---|
| Ad Set ID | *(blank)* |
| Ad Set Name | rendered by `naming.py` from the brand's template. Split by the person in the picture too (the owner, 2026-09-11) so Meta cannot pick one face and starve the others |
| Ad Set Run Status | `PAUSED` |
| Ad Set Daily Budget | **blank — CBO** |
| Ad Set Minimum Spend Limit | **blank** — the owner: no min |
| Ad Set Maximum Spend Limit | **blank** — the owner: no max |
| Optimization Goal | the brand's `optimization_goal` — **read it off the account.** Accounts disagree: conversions on one, value on another |
| Billing Event | `IMPRESSIONS` |
| Ad Set Bid Strategy | *(blank — inherits the campaign's)* |
| Link | the landing page for THAT sub-avatar — the brand's `inputs.pages` |
| Link Object ID | the brand's Facebook Page — `page_id` in its account.json |
| Countries | the brand's `countries` |
| Gender | **blank — broad.** The live ad sets carry no gender restriction and the avatar is creative separation, not audience targeting |
| Age Min / Age Max | the brand's `age` |
| Publisher Platforms | the brand's `publisher_platforms` — again, accounts disagree; one runs two, another five |

### Ad — one row per picture
| column | holds |
|---|---|
| Ad ID | *(blank)* |
| Ad Name | the 13-field name + the picture, so spend joins back to the record |
| Ad Status | `PAUSED` |
| Title | **the headline** |
| Body | **the primary text** |
| Link Description | **the description** |
| Display Link | the brand's `display_link` |
| Image File Name | the file, exactly — one image per row |
| Call to Action | the brand's `call_to_action`. Read what the account already runs before overriding it |
| URL Tags | the UTMs |

---

## Two things the template settles

**One image per ad row.** The column is `Image File Name`, singular. There is
no multi-image column for a normal link ad — the product columns (`Product 1
… Product 3`) are catalog carousel, not our case. So the owner is right: the
flexible/multi-image path is gone from this sheet, and **each picture becomes
its own ad**. Three pictures of one idea = three ads. They still group in the
report because the ad name carries the idea; drop the last field.

**That is why copy is per format, three ways.** If every picture is its own
ad, every picture needs its own words — and the words have to match the
picture, not float above it. Three copy variations per format, so the three
pictures of one idea each carry copy written for that format's shape.

---

## What the template does NOT carry — the honest gaps

- **No pixel or conversion-event column.** Neither is in the 143. **Settled
  2026-09-12: create the ad sets through the API instead**, which carries
  `promoted_object` from birth, and hand the sheet their `Ad Set ID`.
- **No Advantage+ / Advantage audience toggle.** Detailed targeting expansion
  is not expressible here.
- **No Instagram account column.** `Link Object ID` is the Facebook Page.
  **Every imported ad therefore lands with no Instagram profile, which blocks
  publishing.** One bulk edit fixes all of them — `RUNBOOK.md` §7.
- **No custom-audience exclusions beyond ids** — `Custom Audiences` and
  `Excluded Custom Audiences` take ids, which we do not have written down yet.

---

## The values Meta will accept (from the template's own VALIDATION sheet)

- **Campaign Objective**: App Installs · Brand Awareness · Clicks to Website ·
  Catalog Sales · Traffic · Event Responses · Local Awareness · Messages ·
  Offer Claims · Page Likes · Page Post Engagement · Post Engagement ·
  Product Catalog Sales · Reach · Video Views · **Website Conversions**
- **Buying Type**: AUCTION · FIXED_PRICE · RESERVED · MIXED
- **Campaign Bid Strategy**: Bid cap · ROAS goal · **Highest volume or value**
- **Ad Set Bid Strategy**: Bid cap · Highest volume or value · Highest Value
- **Optimization Goal**: … LINK_CLICKS · **OFFSITE_CONVERSIONS** · LEAD_GENERATION …
- **Billing Event**: **IMPRESSIONS** · LINK_CLICKS · THRUPLAY · PURCHASE …
- **Status** (campaign / ad set / ad): ACTIVE · PAUSED (campaign also ARCHIVED · DELETED)
- **Publisher Platforms**: facebook · instagram · audience_network · messenger · whatsapp
- **Facebook Positions**: feed · right_hand_column · instant_article · instream_video · group
- **Instagram Positions**: stream · story
- **Call to Action**: … LEARN_MORE · SEE_DETAILS · **SHOP_NOW** · SIGN_UP …


---

## The gate before the sheet (added 2026-09-10)

A picture reaches the account only if it survives **three** checks, all of
which happened before the builder ran:

1. **the owner did not kill it** in review (`queue/review.json`).
2. **The headline audit did not mark it MISMATCH** — the picture actually
   shows what the headline claims (`queue/headline-audit.json`).
3. **Copy exists for its format and its sub-avatar.** No picture ever ships
   with words written for someone else.

Anything failing a check is listed with its reason, never dropped silently.
`build.py --strict` turns a copy gap into a failure instead of a list.

## Reading spend back

`URL Tags` carries `utm_content=<the full 13-field ad name>` and
`utm_term=<sub-avatar>`, so the funnel's own analytics can join a session to
the exact picture. Meta's own report joins on `Ad Name`, which is the same
string. Drop the last field of either and you have the ad unit.
