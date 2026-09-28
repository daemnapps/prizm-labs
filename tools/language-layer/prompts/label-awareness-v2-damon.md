*v2 (2026-09-28, Damon: "I mean things like bigger bottle is obviously from a customer — look at the source, so that's a most aware categorization"): every row now arrives with its source (a survey's question included), its speaker and its origin, and the level is read from the words IN that context. A buyer knows the product: most-aware, or product-aware where their words show doubt. `post-purchase` is withdrawn. Lines our brand or creators wrote are labelled for the level they are written TO. `unclear` is kept for words that carry nothing at all. Everything else in v1 stands.*

*v1 (2026-09-28, Damon: "if they are clearly using language that does not speak to being a customer in some way then it should be a prospect, then if they show interest in their query then we can note them as lead language … this is going to further determine how we also apply our awareness and sophistication indexing"). Labels a batch of customer-language rows. Read, never improve.*

Here are the five awareness levels, each with what that reader knows:
{awareness_levels}

Here are the five sophistication stages, each with what the market has already heard:
{sophistication_stages}

Here is the product these rows are about, by name only — "the product" in the doctrine means THIS product, never a competitor's: {product_names}

Here are the rows. Each has an id, the lane it is filed in now, who spoke, where the words came from (a survey's question included), whether they came from inside our own relationship with the customer (internal) or from public spaces (external), whose voice it is (the audience, or our own brand and creators), and the exact words:
{rows}

For EVERY row, read its words IN THEIR CONTEXT — who said them, where, and in answer to what — and answer four things. A short answer to a survey question means what it means as an answer to that question: "Bigger bottles lol" to "What is the ONE thing you'd change?" from a customer is a buyer who wants more of the product.

1. **awareness** — what the speaker knows, by the "knows" line of the levels above, read from the words in their context. One of: `unaware` · `problem-aware` · `solution-aware` · `product-aware` · `most-aware` · `unclear` (the words carry nothing at all — a bare "lol", an emoji, a single laugh).
   - **A buyer knows the product.** A customer (or a churned customer) is `most-aware` — they know it and want it, or want more of it — unless their words show doubt about it (a complaint, a refund reason, "it didn't work"), which is `product-aware` ("knows the product exists but is not sold on it").
   - **Our own brand's or creators' lines** (voice: brand) are not the audience speaking: label the level the line is written TO — a line that names the problem to someone who has not met the product is `problem-aware`, a line selling the product by name is `product-aware` or `most-aware`.
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
