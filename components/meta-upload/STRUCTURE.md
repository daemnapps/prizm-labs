# How an account is shaped, and what it can hold

The limits and the rules here are Meta's and the flow's — they hold for any
brand. Where a concrete account is shown it is fenced as a worked example,
never as the shape a new brand should copy.

the owner, 2026-09-11: *"it was so efficient to just be able to upload these
individual ads… I'm pretty sure there's a limit on how many ads can be inside
of an individual ad set… Let's get these limit numbers so that we can work
backwards from there."*

So: the numbers first, then the shape they force, then the names.

## The limits

Every number verified against Meta's own Help Center on 2026-09-11, and every
count read off `1. Brand B` (act <META_AD_ACCOUNT_ID>) the same day.

| limit | number | where we are |
|---|---:|---|
| **ads per ad set** | **50** | the one that shapes everything |
| ad sets per ad account | 5,000 | 1,227 |
| campaigns per ad account | 5,000 | 197 |
| ads per ad account, on + off | 5,000 | **6,340** — see below |
| archived ads per ad account | 100,000 | 0 |
| of those account ads, on dynamic creative | 1,000 | 0 |
| **ads running or in review, per Page** | **1,000** | 14 |

Two of these are easy to misread, so plainly:

**The 5,000 account limit counts paused ads.** On, off, campaign-off, ad-set-off
— all of it. Only *archived* counts as gone, and archiving is effectively free
at 100,000. The account is sitting at 6,340, which is past the number Meta
documents for a regular account, and imports still go through — so this account
is not being held at 5,000. That is luck, not a plan. Archiving dead ads is the
release valve, and it is the one piece of routine hygiene this system needs.

**The 1,000 Page limit is a different limit, and it is the live one.** It counts
ads *running or in review* for one Page, across every ad account, and it
is set by the Page's highest-spending month in the past year — $__ in
November 2025, which puts the Page in the 1,000-ad tier. Paused ads do not count
against it. Turning 138 ads on at once costs 138 of those 1,000.

## Working backwards

The Page allows 1,000 ads live at once. An ad set holds 50. So:

> **20 fully loaded ad sets is the whole machine, live at one time.**

A 138-picture drop is 3 ad sets. At roughly one drop a week, the account holds
about five months of testing before anything has to be turned off to make room —
and turning old drops off is what we would be doing by then anyway.

The ceiling is not close. Build for the read, not for the cap.

## One drop, one ad set

> **Brand A, ruled 2026-09-28 (the owner):** an ad set is one avatar + one angle
> and holds many batches — `adset_brand-a_avatar-four_pigment-memory`, no date,
> no part number. Its account file sets `naming.ad_set_by` to avatar + angle,
> and `build.py` groups that way for any brand that does. What a full (50-ad)
> ad set does is not ruled yet; the builder stops rather than guess. The rule
> below still holds for brands that don't set `ad_set_by`.

the owner's rule, and it is the right one:

> Every batch of creatives gets its own ad set. Never add to an old one.

It costs nothing (5,000 ad sets available) and buys three things:

- **A clean read.** A drop's CPA is the ad set's CPA. No arithmetic, no
  untangling last week's winners from this week's test.
- **A clean kill.** A drop that does not work is one switch, not fifty.
- **No relearning.** Adding ads to a live ad set resets its learning phase and
  disturbs what is already working. A new ad set leaves the winners alone.

When video lands the day after a static drop, it is a new ad set. Same rule, no
decision to make.

## The ad set is a container, not a variable

A drop over 50 ads has to be split. The split is **round-robin, not sliced** —
every shard gets the same mix of sub-avatars and concepts, so the shards are
interchangeable and nothing is learned from comparing them. Slicing by
sub-avatar would make shard-vs-shard look like a result when it is an artifact
of which pictures landed where.

This is also why the ad set is no longer one-per-sub-avatar. The six sub-avatar
ad sets built for RUN-01 all target the same audience — United States, broad, no
interests — differing only in an age band, so they overlap heavily, compete in
the same auction, and split one budget six ways across six learning phases. The
sub-avatar is still a first-class thing: it picks the copy and it picks the
landing page. It reads out of ad-level reporting two ways — the ad name carries
the talent, who maps to one sub-avatar through the casting roster, and the
sub-avatar is written directly into `utm_term` on every link. It just is not an
audience, so it should not be an ad set.

An ad set earns its own existence only when it is buying something genuinely
different: a different country, a retargeting pool, a lookalike, a budget that
has to be ring-fenced.

## The names

**Read the convention off the account, never invent one.** Open its live
campaigns, see how they are already named, and add only the two things that
are usually missing: the funnel on the campaign, and the drop date on the ad
set. Everything else stays as the account already writes it.

Each brand states its shape as a template in its own account file, and
`naming.py` renders whichever it is given. Accounts really do differ — one
runs pipes and mixed case, another underscores and lowercase — so there is
no house style here to conform to.

> **Worked example, one account.** It already ran `MARKET | PRODUCT` at the
> campaign level and message themes at the ad set, so the drop became:
>
> ```
> CAMPAIGN   US | WIDGET™ | ICON | Avatar One
> AD SET       Forty-Year Shaver | Ray | Razor Bumps | 260911
> AD             <the 13-field ad name>
> ```
>
> A different account, same flow, its own convention:
>
> ```
> CAMPAIGN   cbo_us_purchase_body-scrub
> ```

**Campaign — which market, which product, which funnel?**
`MARKET | PRODUCT | FUNNEL`
It persists for months. It is the thing whose CPA is compared to its own last
month, so nothing dated, nothing about a theme, nothing about a batch ever goes
in it. A second funnel on the same product is a separate campaign.

**Ad set — which message theme, and which drop?**
`Theme | SHIP DATE | shard`
The theme is the account's existing vocabulary: the message bucket, not the
audience and not the format. The ship date is YYMMDD, the day the batch goes
into the account — which makes the ad sets sort into the order they were
tested in, and means a theme never fills up, because each drop opens a new ad
set under it. The shard suffix appears only when the 50-cap forced a split.

That date is not decoration. `Culture Integration` already holds 115 ads,
`Content Creator` 62 and `Problem Solution` 60 — all past the 50-ad cap.
Without a new ad set per drop, those themes are closed.

**Ad — which exact picture?**
The 13-field name, unchanged, specified in `../image-production/PIPELINE.md`.
It carries the talent, the angle, the concept, the format and the batch, and it
is the join back to the picture that earned the spend. The sub-avatar comes off
the talent through the brand's own casting roster, and is
also written straight into `utm_term` on every link.

Whatever separates the campaign and ad-set fields, it is not a hyphen: the
13-field ad name owns those.

`naming.py` owns all of this in code. `build.py` calls it; nothing types these
names by hand.

## A drop, end to end — worked example

One account's drop, 2026-09-12, as a sanity check on the numbers above.
Nothing here is a target for another brand; the column that matters is that
no ad set is near the 50 cap.

| | |
|---|---|
| campaign | one CBO, $__/day, imported paused |
| ad sets | **13**, split avatar × person × promise × drop date — largest 16 ads, none near the 50 cap |
| ads | **110**, every one paused, zero duplicates, every image bound |
| targeting | US, 18–65+, broad, all placements, Instagram on every ad |
| conversion | the brand's pixel, optimising for Purchase, on all 13 |
| copy | one headline and body per concept; a concept's variations share them |
| pages | one landing page for the drop, with per-sub-avatar presells still to come |

It went in as **one** import of a 158 KB text file, because the images were
already in the account library and the sheet carried `Image Hash`,
`Ad Set ID` and `Campaign ID`. Where that accelerator is not available the
same drop is one sheet plus six or seven goes at the Images tab — the 10 MB
single-upload limit, not a choice.

An earlier campaign holding the same creative in six ad sets was deleted once
this one verified complete. It had never spent.

## Two things the bulk sheet dropped silently

Worth knowing before trusting a future import:

- **`Gender: 2` did not take.** The sheet asked for men; the live ad sets have
  no gender restriction. Broad delivery will find men anyway for a shaving
  device, but the column was ignored, not applied.
- **One body, one headline per ad.** The sheet has a single `Title` and a single
  `Body` column, so an imported ad carries exactly one of each. Multiple text
  options inside one ad need `asset_feed_spec`, which is Marketing API only —
  see `API-ACCESS.md`. The copy variations that exist are spread *across* ads,
  not stacked inside one.

## Sources

- [Campaign, ad set and ad limits per ad account](https://www.facebook.com/business/help/652738434773716)
- [Ad limits per Page](https://www.facebook.com/business/help/766697140509126)
- [Ad account limits](https://www.facebook.com/business/help/1026272311098874)
