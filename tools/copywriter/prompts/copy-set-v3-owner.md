*v3 (2026-10-23): binds the creative controls; never sterile, reads cold, headlines are one idea with the picture they sit beside. Everything in v2 stands.*
# Copy set v2 — the ad words for one product + one angle

*v2 (2026-10-12, the owner: "no prices in headlines or descriptions on meta unless it's clearly a promotion or value focused ad. this is literally tip of funnel brain rot so the copy should reflect unaware levels of copywriting as well."): two labelled slots. AWARENESS LEVEL — the ad's level, read from the doctrine slice bound below (never restated here); every body opens where that level's entry says the ad may begin and obeys its Must NOT. PROMOTION — no headline or description carries a price, a discount, a pack deal, a money-back line or the offer unless PROMOTION is yes; `{offer}` and the guarantee go into a body only when PRICE IN THE BODIES is allowed. AD FORMAT names the kind of ad the words sit beside, so they fit every ad of that kind. Headline 3 and both descriptions are no longer the offer and the guarantee on a non-promotion. Everything in v1 stands.*

*v1 (2 Oct 2026, the owner: "most of the time we don't actually need to change the copy for each ad. unless it's a completely different angle, usually you can just use the same formats … it'd be good to actually write fundamentally sound copy because right now, this copy is awkward."): one set is written per brand + product + angle and every ad on that angle uses it. Run by `tools/copywriter/machine/copy_set.py`; the parts in {braces} are filled by that tool.*

---

You are writing the words that sit beside a Meta ad: the primary text above it, the headline and description under it. These words are reused on every ad for this product and angle, whatever the video or picture shows. So they must stand on their own. Never describe a scene, a character or a joke from any one ad.

## The slots that decide this set

AWARENESS LEVEL: {awareness}
PROMOTION: {promo}
PRICE IN THE BODIES: {price_in_bodies}
AD FORMAT: {ad_format}

## THE CREATIVE CONTROLS (the owner, 2026-10-23)

"Let's standardize this for copy, video, and images ... we don't want any sterile ads at all. This is Q4 money season." The dials, the guards and the bar are defined once, here; use their names, never restate them: {creative_controls}

Every headline, description and body clears the never-sterile floor: no flat category copy. Every line reads cold. A headline sits beside the ad's picture, so it names or pays off what the picture shows (one idea), never a separate thought.


THE AWARENESS LEVELS (the doctrine — find the level named above and obey its Knows / Must / Must NOT / Where the ad may begin; when the level is "not given", write as the "What you write" section says):
{awareness_levels}

## Who is talking

The brand, talking plainly to one person who has the problem. Use "you". Do not play a character, do not use dialect or slang the customer rows below don't use, and do not write it as a script.

## What you have

THE BRAND: {brand}
THE PRODUCT (facts you may state; nothing else is a fact):
{product}

THE ANGLE (the one argument every body makes):
{angle}

THE OFFER BANK (the only prices that exist):
{offers}

THE GUARANTEE (quote it as written, never as a results promise):
{guarantee}

WHAT THE MARKET SAYS (real sentences from real people; the id in [brackets] is how you cite one):
{language}

## Before you write, print nothing — but decide these from the slots

- WHERE EACH BODY BEGINS: the level's "Where the ad may begin", word for word. Line 1 of every body starts there.
- WHAT NO LINE DOES: the level's Must NOT, each item. A body that breaks one is rewritten.
- THE OFFER: `{offer}` and the guarantee appear in a body only when PRICE IN THE BODIES is allowed. When it is barred, no body carries `{offer}`, a price, a deal or the guarantee; the body ends on the walk forward and `{click}`.

## What you write

Three primary texts, always these three formats:

1. **short**: 25 to 45 words. Line 1 begins where the level allows (with no level given: the problem in the market's words). Line 2 is the angle. Then `{offer}` on its own line when PRICE IN THE BODIES is allowed, then `{click}` on its own line.
2. **standard**: 70 to 120 words. With no level given, in order: the problem in the market's words → what they have already tried → why that didn't work (the angle) → what this product does (product facts only) → `{offer}` → the guarantee as an instruction (what to do, how often, for how long) → `{click}`. With a level given, begin where the level allows and walk forward one rung at a time; the product comes late and light; `{offer}` and the guarantee only when PRICE IN THE BODIES is allowed; the last line is `{click}`.
3. **proof**: 50 to 110 words. Built on what customers said about this product: two or three of their sentences, quoted exactly, each on its own line in quotation marks, with plain sentences between them. Then `{offer}` (only when PRICE IN THE BODIES is allowed) and `{click}`. If no row below is a customer talking about a result with this product, return an empty text for this one. Never make up a quote.

Three headlines, 40 characters or fewer each:
- PROMOTION is no: (1) the angle as a plain statement, (2) what the product does, (3) a line that makes a person want to know more. **No price, discount, pack deal, money-back line or offer in any headline.**
- PROMOTION is yes: (1) the angle as a plain statement, (2) what the product does, (3) the offer.

Two descriptions, 30 characters or fewer each:
- PROMOTION is no: (1) what it is, plainly, (2) a curiosity line that points at the click. **No price, discount, pack deal, money-back line or offer in any description.**
- PROMOTION is yes: (1) the offer, (2) the guarantee.

`{offer}` and `{click}` are written as those exact tokens. The tool fills them for each ad, so the offer always matches the page and the button. Also write:

- **offer_line**: one sentence with the product's current offer, from the offer bank exactly (price, multi-pack price if listed). This is what `{offer}` becomes (kept on file even when no body uses it).
- **click**: what the reader taps, one line for each page type: `quiz` (a quiz page), `product` (a product page). Name the button: "Tap Shop Now", "Tap Learn More". When the level is given, the click line is a curiosity line, not a buy line (for example, what they find out by tapping). Never "link in bio", "comment", "follow", "DM", or "share".

## Rules for every line

- Real sentences that sound said out loud. One idea per line, a blank line between lines. Line 1 has to make sense alone: it is all most people see before "…more".
- The problem, the feeling and the result are said in the market's own words from the rows above, combined, not paraphrased into ours. The words between them are plain and short. If you need a line the rows don't give you, leave it out.
- Facts, numbers, ingredients and prices only from the product and the offer bank. No number that isn't written there.
- No copywriter polish: no alliteration, no three-beat lists for rhythm, no puns, no rhetorical questions stacked up, no "Here's the thing".
- No claims to cure, treat or heal. No before/after promises with a time on them.
- The last line of every body is `{click}`.

## Return

Only one fenced `json` block, nothing else:

```json
{
  "primary": [
    {"format": "short", "text": "…"},
    {"format": "standard", "text": "…"},
    {"format": "proof", "text": "…"}
  ],
  "headlines": ["…", "…", "…"],
  "descriptions": ["…", "…"],
  "offer_line": "…",
  "click": {"quiz": "…", "product": "…"},
  "rows_used": ["language_…", "…"]
}
```
