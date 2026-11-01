# Formats — one word, at least twenty-five vocabularies

Written 2026-09-11. the owner, on being shown the 50 organic video formats:

> *"All these formats are just for the organic swipe. This is not for the swipe
> files or for paid swipes. These are not formats for proven brand assets…
> This is literally where the issues come about. Technically, all of these are
> unique formats. Now I see, but we need to get really clear on how all of the
> formats of all of our different types of assets are truly classified."*

He is right, and the count is worse than it looks. **"Format" names at least
twenty-five different vocabularies in this repo**, living in six places, at three
different layers, with nothing saying which one a tool means. Two of them
contradict each other. One of them files `Angle` as a format.

## Every format vocabulary that actually exists

| Asset | Vocabulary | Count | Lives in | Layer |
|---|---|---|---|---|
| Page | page format | 10 | `components/naming/classify_pages.py` | **kind** |
| Page | section block | 82 | the funnel's repo, `_includes/landing/` | **section** |
| Organic video | organic format | 50 | `components/swipe-organic/formats.json` | **structure** |
| Image ad | build template | 5 | `tools/image-production/static/templates/` | **template** |
| Email | design format (FMT-01..) | 9 | `brands/<brand>/email/design-formats/components.json` | **template** |
| Email | module | 4 | same file | **section** |
| Email | layout, observed | 239 | `…/layouts.json` | **evidence** |
| Email | Figma template | 87 | `…/figma-templates.json` | **evidence** |
| Ad copy | copy surface | 16 | `lab/damon/copy/bank/format-bank.json` | **slot** |
| Ad copy | copy style | 4 | `lab/damon/copy/bank/formats.json` | **style** |
| Paid swipe page | block | 2,626 / 4 brands | `components/swipe-paid/<brand>/blocks.json` | **evidence** |
| Email | email type | 47 <brand> · 46 <brand> | `brands/<brand>/email/email-types.json` | **kind** |
| Offer | offer | 6 | `brands/<brand>/offers/offers.json` | **kind** |
| Offer | guarantee | 2 | `brands/<brand>/offers/guarantees.json` | **kind** |
| Swipe capture | channel tag | 6 | `components/naming/classify_pages.py` | **kind** |
| Swipe capture | product tag | 4 | same file | **kind** |
| Swipe capture | variant tag | 9 | same file | **kind** |
| Swipe capture | audience tag | 11 | same file | **kind** |

| Email | form | 5 | `brands/<brand>/email/email-types.json` | **template** |
| Email | treatment | 4 | same file | **style** |
| Email | modifier | 3 | same file | **style** |
| Email | arc | 3 | same file | **structure** |
| Email | family, observed | per send | `…/design-formats/census.json` | **evidence** |
| Video production | format profile | 4 | `tools/video-production/formats/` | **template** |
| Ad | media | 3 | `components/naming/names.py` MEDIA | **kind** |
| Ad | source | 4 | same file, SOURCE | **kind** |
| Ad copy | channel | 4 | `lab/damon/copy/bank/channel-map.json` | **kind** |
| Image teardown | template | 1 | `tools/image-teardown/templates/` | **template** |

**Found by the critics, 2026-09-11, after the first count said eleven.** Six of
these seven were missed because they do not have the word "format" anywhere
near them — `email-types.json` is a 47-entry per-brand vocabulary, and
`classify_pages.py` quietly holds four more closed sets besides the page
formats it is named for. A search for the word "format" will never find a
vocabulary that was not called one. **The count is a floor, not a total** — it
went 11 → 17 → 25 in a single afternoon, each rise from a different search
angle, and the next sweep will find more.

## The repo already solved this once — in email

`brands/<brand>/email/email-types.json` holds **five** vocabularies in one file
and keeps them straight, in its own words:

> *"A TYPE is what the email IS, and it belongs to exactly one CATEGORY,
> decided by one test: whose material is it made of? Types are multiplied by a
> FORM (how it is built), a TREATMENT (how it is played — humour, a question,
> proof, no ask) and an AWARENESS level."*

That is the answer, already written down and already working: **separate axes,
each with its own closed set, multiplied together — not one list called
"format" carrying four different kinds of thing.** It even states the entry
bar: *"A type earns its place by being genuinely distinct under the category
test, never by filling out a column."* Any standard that contradicts this file
is wrong, because this file is the one place the problem was solved before
anyone named it.

## A borrowed name with a new meaning is still an invented name

Caught by the adversarial pass, 2026-09-11, and worth stating because it is the
failure that survives a name check. The draft standard proposed filling
`receipts` on the page-section bank with the places each block is included —
a usage index. But everywhere `receipts` already exists (the angle bank, the
offer bank, the guarantee bank) it holds **proof that the entry is true**:
`{claim, source}`. Same word, different job.

Borrowing the word and changing what it means is the same fault as coining one
and is harder to catch, because a `git grep` finds the name and reports it
clean. **A field is looked up with its meaning attached, or it is not looked
up.**

## The three layers, which is what actually separates them

Most of the confusion is that these are not alternatives to each other — they
sit at different heights, and a single asset uses one from each:

- **KIND** — what the thing *is*. A page is a `salespage`. One per asset.
- **TEMPLATE / STRUCTURE** — how it is *built*: the beat order, the layout, the
  camera. `FMT-04`, `photo-strip`, `sticky-line-maker-demo`. One per asset.
- **SECTION** — the parts it is built *from*. 82 page blocks, 4 email modules.
  Many per asset.
- **EVIDENCE** — not a vocabulary at all: observed instances kept as proof.
  The 239 email layouts and the 162 swipe blocks are captures, not choices,
  and must never be offered as something to pick.

**The organic 50 are STRUCTURE, for one lane only** — organic video. They are
not paid-swipe formats, not proven-brand-asset formats, and not comparable to
the page formats or the email FMT set. the owner's ruling, 2026-09-11: within that
lane **all fifty are unique formats**. The three `family` groupings recorded on
them are a shared *text mechanic* — a way to browse, never a merge list.

## The four known faults

1. **Two copy banks disagree.** `format-bank.json` (16) lists *slots* — where
   words go: primary text, headline, description, hook line. `formats.json` (4)
   lists *styles* — short-form, long-form story, social proof. Different axes,
   same word, same folder. Neither says which one a tool should read.
2. **`Angle` is filed as a copy format** in `format-bank.json`. An angle is a
   claim (see CLAUDE.md, "Four things"); it is not a format, and having it in
   there is the same category error the <brand> angle bank made in reverse.
3. **Brand scoping is inconsistent.** Email formats are per brand; organic
   formats and image templates are brand-agnostic; page formats are in a
   component. Nothing states which of these *should* be per brand.
4. **No tool can ask for one.** There is no way to say "give me the video-ad
   structures" versus "give me the email templates" — every consumer hard-codes
   a path, which is why a vocabulary can be renamed or moved and nothing
   notices until a page renders blank.

## The address — RULED 2026-09-11

the owner: *"Yes — same shape as your swipe refs."* Formats get addresses in the
grammar the repo already uses for swipes, so there is no second syntax:

```
swipe:<brand>:<id>                   already in use — a competitor's asset
format:<asset>:<id>                  a brand-agnostic bank
format:<brand>:<asset>:<id>          a per-brand bank
```

**The brand segment is not optional decoration.** Without it `format:email:FMT-04`
does not say whose FMT-04, and <brand> and <brand> both have one. A bank is
per-brand exactly when its header carries `brand`; its address carries the same
segment, in the same position the swipe grammar puts it.

**Evidence banks get no address at all.** There is nothing to pick, so there is
nothing to name — see the evidence rule below.

## What is NOT in this map

**`page_type` in a funnel repo is not a format.** It carries `product`,
`checkout`, `upsell`, `receipt` and is rendered into `<meta name="next-page-type">`
for the Campaign Cart SDK to read: the repo's own words are *"it tells the SDK
how to behave on this page"*, and `INVALID_PAGE_TYPE` is an SDK build error.
It is a runtime role owned by a third party, not a vocabulary we choose from,
and it collides by name only with `classify_pages.py:page_type()` — which is a
different closed set doing a different job. Neither gets renamed; the funnel one
simply is not ours to file.

## The standard every vocabulary bank carries

Each field below is already in use somewhere in this repo — none is coined. The
bank that already uses it is named, because that is the whole discipline.

**Header** — `lane` · `scope` · `brand` (per-brand banks only) · `source` ·
`updated` · `note`

`scope` is the sentence saying what the bank is NOT. It is the sentence that
would have prevented today's confusion, so it is required, not optional.

**Entry** — `id` · `name` · `what` · `status` · `signed` · `receipts`

`status` uses the values this workspace already ruled for manifest entries
(`components/CLAUDE.md` rule 6, 2026-09-01): **`draft` / `approved` /
`deprecated`**. Nothing needed inventing here either; the banks that carry
`unreviewed`, `proposed` and `active` migrate onto it. `signed` is the approval
gate and is nullable — only the owner signs.

**Evidence banks carry the header and nothing else.** No `status`, no `signed`,
no `name`, no `what` — an observed instance is not a choice, and giving it the
shape of one is how it ends up in a menu.
