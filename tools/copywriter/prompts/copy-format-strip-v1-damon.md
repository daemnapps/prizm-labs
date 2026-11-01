*v1 (2026-10-27, the owner, on the Tella review of the picture board: "right now we keep writing brand new ad copy over and over and over again per ad, and that's not necessary at all ... when I read some of this copy back, it's not in a proven format, like in terms of how the writing is actually set up. It's just kind of like we're just freeballing it based off of the brief." And 2 Oct: "We're first going to use the formats that directly came from the ad account, nothing that we generated or wrote."): one real ad's words in, its format out — the same words with named [BLANKS], the way the video hook is a format (tools/video-teardown/machine/hook_format.py). Run by `tools/copywriter/machine/real_formats.py build`; the parts in {braces} are filled by that tool.*

---

You are stripping real ads that already ran and sold into FORMATS, so new ads can be written by filling the same structure instead of from scratch.

A format is the ad's own words, kept, with only the parts that belong to this one product, offer or story replaced by a named blank in square brackets. Like this:

    REAL:   You've already blown $150+ on face washes that didn't clear your acne. There's a reason why.
    FORMAT: You've already blown [MONEY SPENT] on [WHAT SHE ALREADY TRIED] that didn't [FIX THE PROBLEM]. There's a reason why.

    REAL:   Women are OBSESSED with this viral dark spot hack
    FORMAT: [WHO] are OBSESSED with this viral [PROBLEM] hack

## The rules

1. **Keep every word that carries the structure**: the openers, the turns ("There's a reason why", "But here's what most guys don't realize", "Most CEOs would lie, but I won't"), the rhythm, the sentence lengths, the line breaks and blank lines, the capitals used for emphasis, the emoji and their places, the ticks and bullet marks. A format may not paraphrase the ad: the fixed words are the ad's own, in its order.
2. **Blank only what changes from product to product or ad to ad**: product and brand names, ingredients and mechanisms, numbers, prices and offers, the problem, body parts, what was tried before, customer names and quotes, places, dates, holidays and seasons, links. Write each blank as a plain name of what goes there, in capitals: [PROBLEM], [PRODUCT], [PRICE], [WHAT THEY TRIED], [CUSTOMER QUOTE], [CUSTOMER NAME], [HOW LONG], [LINK]. Use the same blank name for the same thing everywhere in one format.
3. **Never blank a whole sentence** unless it is a customer quote, a list of bullet facts or a link. A format that is mostly blanks has lost the ad. Two or three fixed words beside a blank stay fixed.
4. **Keep the length**: the format has the same number of sentences and paragraphs as the ad.
5. **One format per ad below, in the same order, every one** — even if two look alike.

For each ad also read, from the ad's own words (never guessed from the numbers):
- `awareness`: where the ad begins, one of these ids — {awareness_ids}. (Opens on the product and the deal = most-aware; on the product but the doubt = product-aware; on a result or a desire = solution-aware; on the problem in her words = problem-aware; on the person, nothing sold = unaware.)
- `offer`: yes when the ad carries a price, a discount, a free gift, a sale or a deal; else no.
- `season`: the holiday or season it is tied to ("St. Patrick's Day", "Labor Day", "holiday"), or "" when none.
- `structure`: one plain line saying how the ad is built, in order, the way you would tell a copywriter ("problem question, the money already wasted, the hidden reason, the mechanism, the proof, the offer"). Plain words only, no labels you made up.
- `why_it_works`: one plain line.

## The ads ({slot})

{ads}

## What you return

Only one fenced json block, a list, one object per ad, in order:

```json
[
  {"n": 1, "format": "…the ad's own words with [BLANKS], line breaks kept as \n…", "blanks": ["PROBLEM", "…"],
   "awareness": "problem-aware", "offer": "no", "season": "", "structure": "…", "why_it_works": "…"}
]
```
