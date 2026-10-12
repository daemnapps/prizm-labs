# The language bank standard — lanes by language, awareness and sophistication on every row, sources by the Naming Standard

> Brand-agnostic, product-agnostic. The rules themselves live in `brands/language-schema.md`; this is why they are what they are, with the evidence. Tools: `tools/language-layer/tools/`. Current state per brand: `runs/language-layer/_system/BANK.md`.

> What is built from this standard is in `tools/language-layer/tools/` and its history (`git log -- tools/language-layer/tools/`).
> Ruled 2026-09-28: "if they are clearly using language that does not speak to being a customer in some way then it should be a prospect, then if they show interest in their query then we can note them as lead language … this is going to further determine how we also apply our awareness and sophistication indexing … this is what actually helps us run a clean system."

## Why

- **The lane is decided by the relationship, not the words.** The rule on file (`brands/language-schema.md`, lane logic, 2026-08-26) files by who the speaker is to us. Words that show no purchase can end up in `customers/` — 21 TikTok comment rows sit in `customers/unsegmented.json` today (`fuk-customer-9607`–`9627`), hand-typed from the brand's language-bank notes ("Register A"), with no link to the comment.
- **No row says what its speaker knows.** 0 of Brand B's 14,243 rows carry an awareness level or a sophistication signal. The awareness map (4m) asks for problem-aware hooks, but the bank can only answer by `use` tag — so a solution-aware joke hook was handed problem rows on its first run.

## The doctrine's own definitions (verbatim, `components/marketing-doctrine/frameworks.json`)

| Level | Knows (verbatim) | Where the ad may begin (verbatim) |
|---|---|---|
| unaware | "Does not know the desire or the need exists — or will not admit it." | "At the person — a portrait, nothing sold in the opening at all." |
| problem-aware | "Feels a need but has not connected it to any product category." | "At the problem — the need, stated and felt, before anything is offered." |
| solution-aware | "Carries the desire and knows a result is possible, but does not know a product delivers it." | "At the desire or the result — the product arrives after the proof." |
| product-aware | "Knows the product exists but is not sold on it." | "At the product, but on the gap between knowing it and wanting it." |
| most-aware | "Knows the product, wants it, simply has not bought yet." | "At the product itself — name and terms in the opening beat." |

| Sophistication stage | The market has heard (verbatim) |
|---|---|
| stage-1 First in the market | "Nothing — no one has made this claim here before." |
| stage-2 The claim is in the market | "The plain claim, now from competitors." |
| stage-3 Claims exhausted | "Claims pushed to their limit, and it discounts about half of what it hears." |
| stage-4 The mechanism is in the market | "A mechanism, from a competitor." |
| stage-5 Exhausted field | "Every claim and every mechanism, and believes none of them." |

"The product" in the doctrine is **our** product. Someone who has tried a competitor's product knows a product category exists but not ours — by the definitions above that reads as solution-aware, not product-aware.

## Proposal 1 — the lane follows the language

Decided in this order, first match wins:

1. **Known relationship wins.** An order on file → `customers/` (segment if known); refunded / cancelled / lapsed → `churned/`. Unchanged.
2. **Otherwise the words decide:**
   - words that show they **own or use** the product ("mine came yesterday", "been using it two weeks") → `customers/unsegmented` with `attribution: "assumed"` (the words say customer; no order is on file)
   - words that show **interest in getting it** ("link?", "where do I get this", "does it work on…", "how much") → `leads`
   - everything else — reactions, jokes, opinions, stories — → `prospects`
3. Every re-filed row keeps its id and gets `"lane_by": "relationship" | "language"`, so the reason is on the row.

First application: the 21 comment rows in `customers/unsegmented.json` are re-read by this rule. The joke reactions ("<a joke reaction>", "<another joke reaction>") go to `prospects`; any row asking for the product goes to `leads`. **Once the gatherer can re-pull those two videos' comments with links, the linked rows replace them** rather than the unlinked ones being moved.

## Proposal 2 — two new fields on every row

```json
"awareness": {"level": "problem-aware", "why": "<the words that show it, quoted from the row>"},
"sophistication": {"signal": "claim-heard", "why": "<the words that show it>"}
```

**`awareness.level`** — one of the doctrine's five ids, read from what the speaker's own words show they know, by the "Knows" column above:

| Level | The row's words show… | `use` tags that usually carry it (a hint, never the rule) |
|---|---|---|
| unaware | the person, and no need named — or a need denied or joked away | `self-descriptor`, `emotion-identity`, `cope` |
| problem-aware | the need, felt and named, with no fix category in sight | `problem-language` |
| solution-aware | the want and that a result is possible — fixes tried, other brands named, methods named — but not our product | `tried-and-failed`, `alternative-solution`, `competitor-brand`, `method-name` |
| product-aware | our product known, not sold: doubts, questions, objections to it | `objection`, `comment-objection`, `unanswered-question`, `why-interested` |
| most-aware | our product wanted, just not bought | `buy-trigger`, `product-ask`, "link?" |

Rows from people who already bought (customers, churned) are **past the five levels** — the doctrine's levels describe a buyer before the purchase. Proposed value: `"post-purchase"`, marked plainly as ours, not the doctrine's. These rows are what proof, transformation and objections are written from, never an entry level. *(Decisions — see below.)*

**`sophistication.signal`** — a row can't set a market's stage (that stays one call per brand, in `position.md`'s `MARKET STAGE`), but it can be evidence for one. One of:

| Signal | The row's words show… | Points at |
|---|---|---|
| `none` | nothing about other claims | — |
| `claim-heard` | the plain claim, heard from others ("every brush says that") | stage-2 |
| `claim-discounted` | claims heard and half-believed ("they all say that and none work") | stage-3 |
| `mechanism-heard` | a competitor's how, named ("the silicone ones that vibrate") | stage-4 |
| `believes-none` | every claim and every how dismissed | stage-5 |

The brand's `MARKET STAGE` can then be checked against the bank: what its rows actually say they've heard.

## Proposal 3 — how the system uses them

| Where | Today | With the fields |
|---|---|---|
| Hooks (4b), per awareness branch | queried by `use` tag; result-level hooks get reaction tags (fixed 2026-09-28) | rows at **that branch's level** first — a problem-aware hook is filled from problem-aware words |
| Awareness map (4m) | reads the doctrine only | also reports how many rows the bank holds at each level — a level with none is a level we can't write in their words yet |
| Expansion / close (4d, 4e) | objection and proof by `use` | objections from product-aware rows; proof and transformation from post-purchase rows |
| The used lane | used / unused | used / unused **per level** |
| Brand position | `MARKET STAGE` stated by hand | checked against the rows' sophistication signals |
| Research gatherer | files rows with permalinks | writes lane-by-language, awareness and sophistication on every new row at pull time |

The engine change is small: `query(awareness=…)` beside `used=`, and the hooks query passes the branch's target level.

## Proposal 4 — backfill the 14,243 existing rows

- A model reads each row's text against the definitions above and writes `awareness` and `sophistication` with a quoted `why` — batches of 100, a cheap model, every batch saved as it goes, nothing overwritten that a person set.
- **The lane is never changed by the backfill** except for rows whose `speaker` is not `customer` sitting in `customers/` (the 21 today) — those are listed for review first, not moved silently.
- A report: rows per level, per lane, per sub-avatar; the thin levels named.
- Test: a fixed set of hand-labelled rows (20 per level, 120 with post-purchase) — the pass must agree with a person's labels before it runs on the whole bank.

## Decisions

1. The lane rule above — including customers-by-language as `attribution: "assumed"`.
2. `post-purchase` for buyers' rows (ours, outside the doctrine's five), or leave those rows without a level.
3. The five sophistication signals.
4. Go on the backfill — and the 120 hand-labelled test rows (I draft, you correct).

## Rulings, 2026-09-28 (after the first test set)

- **Approved and running** ("go ahead let's run it").
- **`post-purchase` withdrawn.** "bigger bottle is obviously from a customer — look at the source, so that's a most aware categorization." A buyer knows the product: `most-aware`, or `product-aware` where their words show doubt.
- **Read in context, not the words alone.** Each row is labelled with its source (a survey's question included), its speaker and its lane in view — the first pass saw only the words, which is why short survey answers ("Bigger bottles lol", "Results", "Curiosity") came back `unclear`.
- **`origin: internal | external` added** — "internal customer language is different than reddit language." Internal = our own relationship with the customer (surveys, tickets, DMs, our database); external = public spaces (comments, forums, reviews).
- **`voice: audience | brand` added** — our own captions, hooks and slides sit in the bank too; they are labelled for the level they are written to and never counted as the audience's words.

## Proposal 5 — every source named by the Naming Standard (added 2026-09-28)

*"I have naming conventions set up for this system … see how we can apply that to this index and all our different sources since this is a richer database."*

The Naming Standard (`the team notes`, v5 — lowercase; `-` joins the words inside a value, `_` joins the values; the type first; the brand spelled in full) already names the ROWS (`language_<brand>_<avatar>_<lane>_<NNNN>`, ruled 2026-09-28, Brand A renamed, Brand B in progress). The SOURCES are still free text: Brand B's 14,243 rows come from **164 differently-written source names** ("Brand Improvement (Customers) survey — Q: What do you like most about the the device?", "TikTok comments, campaign post #1 @creator-handle (1,800,000 views)", "29.9K podium slide", "reddit (r/wicked_edge, r/Blackskincare, …)"), and some point at a file path on one person's laptop.

**Each row's `source` gains four fields, and keeps its old `name` as a label:**

```json
"source": {
  "id":       "post_tiktok_creator-handle_7501234567890123456",
  "kind":     "post",
  "property": "creator-handle",
  "question": null,
  "ref":      "https://www.tiktok.com/@creator-handle/video/7501234567890123456?comment=…",
  "pulled":   "2026-08-14",
  "name":     "TikTok comments, campaign post #1 @creator-handle (1,800,000 views)"
}
```

**The source ids, one shape per kind — type first, brand or account in full:**

| Kind | Shape | Example from Brand B's bank |
|---|---|---|
| Survey | `survey_<brand>_<survey>` + `question` = `q-<nn>_<question-slug>` | `survey_brand-b_brand-improvement-customers` · `q-02_what-do-you-like-most-about-the-device` |
| Post (its comments) | `post_<platform>_<account>_<post id>` | `post_tiktok_brand-b_7000000000000000001` (#1's comments) · `post_tiktok_creator-handle_<id>` (campaign post #1) |
| Support | `ticket_<brand>_<system>` | `ticket_brand-b_gorgias` |
| Review | `review_<site>_<whose product>` | `review_amazon_<competitor>` · `review_site_brand-b` |
| Community | `community_<site>_<room>` | `community_reddit_wicked-edge` · `community_looksmax-org_guide` |
| Our own copy | `copy_<account>_<what>` (voice: brand) | `copy_creator-handle_podium-slide` |
| Database | `database_<brand>_<name>` | `database_brand-b_research-hub` |

**Post comments — the first sources, on all three platforms** (Ruled 2026-09-28: *"with post comments you're going to have to check both tiktok instagram and facebook as those are the first sources"*). The gatherer already pulls all three (`research_gatherer/comments.py`, `ownvoice.py`: TikTok, Instagram and Facebook scrapers, plus the warehouse's `meta_ad_comments`). One shape per platform, the platform's own post id last:

| Platform | Source id | The post id is |
|---|---|---|
| TikTok | `post_tiktok_<account>_<video id>` | the number in `/video/<id>` — `post_tiktok_brand-b_7000000000000000001` |
| Instagram | `post_instagram_<account>_<shortcode>` | the code in `/p/<code>` or `/reel/<code>` |
| Facebook | `post_facebook_<page>_<post id>` | the post number in `/<page>/posts/<id>` (Meta's `pageid_postid` keeps only the post half; the page is the account) |

- **Account names follow the Standard's creator rule**: lowercase, dots and underscores become hyphens — `jayy_cross0` → `jayy-cross0` — because `_` is the separator between values.
- **A post that runs as a Meta ad carries the ad too**: `"ad": "live_meta_<ad id>"` (the Standard's live-ad id). One Meta ad usually has a Facebook post AND an Instagram post; both sources carry the same `ad`, so every comment on the ad rolls up to it — and to its spend.
- **Each comment keeps its own permalink** in `ref` (TikTok `?comment_id=…`, Instagram and Facebook comment URLs), its likes in `signal`, and the date pulled.
- **Origin**: our accounts, our pages and our campaign creators' accounts are listed in `own-accounts.json` per platform — a comment on any of them is `internal`.

**What this unlocks — the richer database:**
- **origin reads off `property`**: a property on the brand's own-accounts list (`brands/<brand>/channels/own-accounts.json`) is `internal`, anything else `external` — no guessing from free text.
- **Per-source stats**: rows, awareness split and used-lane counts per source — which surveys, posts and rooms actually carry hook-grade language.
- **Joins**: a `post_…` id is the same post the swipe manifests and teardowns name (#1 = `7000000000000000001`), so language can be read beside the post's views and saves; a `survey_…` question groups every answer to it.
- **No local paths**: `ref` is a web address or a path inside the workspace, never a laptop path.
- **One registry per brand** — `brands/<brand>/core-avatars/language-sources.json`: every source id, its kind, property, owner (ours / theirs), date range and row count — generated, never hand-edited.

**Doing it:** a mapper assigns ids to the 164 existing names (rules + a short list of hand calls it prints for review), writes `source.id/kind/property/question` onto every row, and builds the registry. **It runs after Brand B's id rename (in its own session) finishes — two tools writing the same bank files at once would overwrite each other.** The gatherer writes these fields for every new row from the start.

**Decisions:** the kind list and shapes above (`post_` and `copy_` are new kinds for the Naming Standard).

## Verified — is the naming clear, clean and scalable? (2026-09-28)

Checked by code against both banks (`tools/language-layer/tools/check_names.py --brand brand-b --brand brand-a`), not by reading the rules.

**Row ids — clean.** Brand A: 1,118 of 1,118 on the standard (`language_brand-a_avatar-four_customer_0192`), no duplicates, every value lowercase and hyphen-joined. Brand B: not renamed yet (14,243 rows still `fuk-…`); the gatherer keeps a bank's own shape until its rename ("one bank, one shape"), so pulls before the rename don't collide.

**Source ids — mostly clean; Brand A's gatherer rows already carry them** (167 rows: `post_facebook_brand-a_100000000000000001`, `ticket_brand-a_gorgias`). Eight things to fix so it holds at scale:

| # | Found | Fix |
|---|---|---|
| 1 | Instagram's shortcode has capitals (and can hold `_` / `-`): `post_instagram_…_AbCdEfGhIjK` fails the lowercase rule — 1 Brand A row today | Use Instagram's **numeric media id** (decoded from the shortcode, one-to-one) — all digits, always clean |
| 2 | `source.post` means two things: Meta's raw `pageid_postid` on comments, "gorgias ticket 100000001" on tickets | One field, one meaning: `item` = the platform's own raw id of the exact post or thread (`100000000000001_100000000000000001` · `100000001`) |
| 3 | **The 4-digit number runs out.** Brand B avatar-one's customer lane has 9,525 rows; the next ~475 reach 9,999 | Rule: **at least 4 digits, never cut** (`…_9999` → `…_10000`); anything reading an id takes the last value as a number. The gatherer already writes it that way — the Brand B rename must too |
| 4 | Kinds the real banks have that the table missed: a customer interview, a paid creator panel, Amazon reviews, non-Reddit forums | Add `interview_<brand>_<date>`, `panel_<brand>_<date>`; reviews stay `review_<site>_<whose>`; any forum is `community_<site>_<room>` |
| 5 | One row drawn from several rooms at once ("r/AskWomenOver60, r/Menopause, r/grayhair — secondhand via bank extract") can't take one room | `community_reddit_several` + `"rooms": [...]`, and `"hand": "firsthand" \| "secondhand"` on every source |
| 6 | 752 Brand B rows point at a file on one laptop (`/Users/…/devel/daemn/…`) | Every `ref` is a web link or a path inside the workspace |
| 7 | Brand B's campaign comments name the post by its number ("campaign post #1 @creator-handle"), not its id | One lookup, #1–#13 → the TikTok video ids, done once when the sources are mapped |
| 8 | Hyphenating handles can make two accounts one (`jay.x` and `jay_x` → `jay-x`) | Keep the raw handle beside it: `"property_raw": "jayy_cross0"` |

**Verdict:** the shape is clear (type first, brand in full, one meaning per value) and scales across brands, platforms and sources once 1–8 are in. The checker runs on every bank and prints exactly what is off.
