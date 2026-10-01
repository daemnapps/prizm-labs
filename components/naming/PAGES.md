# Page naming — the key that ties a page back to the avatar

Extends the ad convention (`components/naming/CONVENTION.md`) to funnel pages.
Same discipline, same reasons: a name is a **key you group by**, not a
description, and everything it deliberately leaves out lives in a manifest
that is recovered by joining on the name.

**The precedent is already in the My Feeds library.** Resilia slugs carry codes
— `adv1-w40-cc`, `men-6problems-adv-ooo-google`, `brain-fog-25-google` —
format, audience, channel, variant. Our `by-type` capture parses them into
Channel / Product / Audience / Variant code on every `_PAGE.md`. They are
doing this because it is the only way to read a report across 229 pages.

## The name

```
<format>-<avatar>-<concept>[-<variant>]

listicle-fedupking-neckbumps
   |         |         |
 format    avatar   concept
```

| Field | What it is | Vocabulary |
|---|---|---|
| `format` | the page's structural shape — **never chosen, always read from `classify_pages.py:page_type()`** | `salespage` · `advertorial` · `prelander` · `listicle` · `quiz` · `comparison` · `review-page` · `blog` · `product-page` · `utility` |
| `avatar` | the **core** avatar the page is aimed at, slug with hyphens stripped | `fedupking` · `giftbuyer` · `glowup` · `faceback` |
| `concept` | the angle, not the headline — a claim family reused across pages | `neckbumps` · `baldnape` · `triedeverything` · `fortyyears` |
| `variant` | only when two pages test the same three fields | `v2`, `b` |

Funnel pages that are not pre-sells keep their plain names — `flex`,
`checkout`, `receipt`, `oto-*`. There is one of each; a key buys nothing.

## The folder is the format

Added 2026-09-11, Damon: *"sales pages should live in their own folders, offer
pages in their own folders, advertorials in their own folders."*

On the shared drive a funnel groups its pages by format, because format is the
axis a report groups on and the axis a person browses on:

```
brands/<brand>/funnels/<funnel>/
    README.md                       the map, regenerated on every sync
    <format>/<page-name>/           a pre-sell, under the format it is
    offers/<plain-name>/            the pages that take the money
```

The format folder is the page's own `page_format`, which is read from the
classifier — so **no one names a folder here either**. A format folder appears
the first time a page of that format exists; the funnel README lists all ten
whether or not they have pages, so the available vocabulary is visible without
looking anything up.

## The rules, inherited

1. **Lowercase `[a-z0-9]` inside a field, hyphen only between fields.**
   `fed-up-king` becomes `fedupking`, `bald-bumps-guy` becomes `baldbumps`.
2. **Three fields always, four when a variant exists.** A missing field
   shifts every field after it into the wrong column.
3. **The name is a key, not a description.** The headline, the offer, the
   sub-avatar, the swipe it came from — all in the manifest.
4. **A name is never reused or re-pointed.** A materially different page is a
   new name. Re-pointing silently merges two pages into one row.

## Why the SUB-avatar is not in the name

A page is aimed at a core avatar and usually speaks to several of its subs at
once — the razor-bumps page opens with the barbershop regular's Monday neck,
the bald guy's braille crown and the ingrown fighter's shelf of bottles, in
one list. Forcing one sub into the key would make the name a lie.

So the sub-avatars a page actually serves are declared in its front matter
and recorded in the registry, where a page can name several. Group by
`avatar` in a report; look up `subs` when you want to know which of them the
copy actually spoke to.

## The manifest

Every pre-sell declares this block in its front matter, and `pages.md` in
this folder is the registry:

```yaml
page_name:   listicle-fedupking-neckbumps
page_format: listicle
page_avatar: fed-up-king
page_subs:   [barbershop-regular, bald-bumps-guy, ingrown-fighter]
page_concept: neckbumps
page_swipe:  swipe:<competitor>:pages-acne
page_next:   flex          # where it hands off — never checkout
```

`page_swipe` uses the same `swipe:<brand>:<id>` reference the ad convention
defines, so a page and an ad torn down from the same competitor join.

## What this lets us answer

- **Which format earns** — group on field 1 across avatars
- **Which avatar earns** — field 2 against the order's `attribution.funnel`
  and the Meta demographic split, the same join the ads use
- **Which concept earns** — field 3, the same angle run as a listicle and as
  a prelander
- **Whether a swipe was worth stealing** — join `page_swipe` across every
  page built from it

## Live

| Page | Name |
|---|---|
| `/icon/salespage-fedupking-razornotproblem/` | `salespage-fedupking-razornotproblem` |

**Settled 2026-09-11.** The URL *is* the name — a key that lives only inside
the file cannot be read off a report, a referrer or a pasted link.

**`salespage` is a class Damon named**, 2026-09-11, because the page matched
no positive rule in the classifier and was only being called an advertorial
by a `len > 6000` fallback. An advertorial is an *article* — byline, read
time, "sponsored content". A salespage carries the whole argument itself and
hands off rather than taking the money.

`classify_pages.py` now tests for those markers instead of length, which
also corrected the capture. Re-run from this folder on 2026-09-11, resilia's
229 pages come out **75 advertorials · 75 salespages · 18 listicles ·
17 prelanders · 13 utility · 11 blog · 11 product-page · 5 quiz ·
3 review-page · 1 comparison** — where the old length rule called every long
page an article. (An earlier note here said 76 and 97; the split above is what
the classifier actually returns now and supersedes it.)
