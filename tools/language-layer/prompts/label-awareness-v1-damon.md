*v1 (2026-09-28, Damon: "if they are clearly using language that does not speak to being a customer in some way then it should be a prospect, then if they show interest in their query then we can note them as lead language … this is going to further determine how we also apply our awareness and sophistication indexing"). Labels a batch of customer-language rows. Read, never improve.*

Here are the five awareness levels, each with what that reader knows:
{awareness_levels}

Here are the five sophistication stages, each with what the market has already heard:
{sophistication_stages}

Here is the product these rows are about, by name only — "the product" in the doctrine means THIS product, never a competitor's: {product_names}

Here are the rows. Each has an id, the lane it is filed in now, who the source says spoke, and the exact words:
{rows}

For EVERY row, read only its words and answer four things. Never guess from the lane or the source; the words decide.

1. **awareness** — what the speaker's own words show they know, by the "knows" line of the levels above. One of: `unaware` · `problem-aware` · `solution-aware` · `product-aware` · `most-aware` · `post-purchase` (the words show they already bought or use this product — past the five levels, which describe a buyer before the purchase) · `unclear` (the words show nothing either way — a bare "lol", an emoji).
   - Someone naming a competitor's product or a fix they tried, but not this product, is `solution-aware`, never `product-aware`.
   - Someone who denies or jokes away the need is `unaware` ("or will not admit it").
2. **sophistication** — what the words show the speaker has already heard from the market. One of: `none` · `claim-heard` (the plain claim, heard from others) · `claim-discounted` (claims heard and half-believed) · `mechanism-heard` (a competitor's how, named) · `believes-none` (every claim and every how dismissed).
3. **lane_words** — which lane the WORDS alone point to: `customer` (they own or use this product) · `lead` (interest in getting it: asking for the link, the price, where to buy, whether it works for them) · `prospect` (anything else — reactions, jokes, opinions, stories, problems).
4. **why** — the few words from the row that show the awareness level, quoted exactly.

Return ONE fenced json block and nothing else:

```json
{"labels": [{"id": "<row id>", "awareness": "<level>", "sophistication": "<signal>", "lane_words": "<lane>", "why": "<quoted words>"}]}
```

Every row in, one label out, in the same order. Never skip a row, never add one.
