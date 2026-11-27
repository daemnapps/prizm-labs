# Method: from teardown to a checked page

Every run names a brand, a product and an avatar (the customer type the page is written
for). Nothing about any of them is assumed. Six steps. Steps 1–4 write nothing customer-facing. Step 5 writes words only from the
brand's evidence, with ids. Step 6 is pass/fail.

## 1. Map ours

Every product page of the brand, element by element, with each product's kind
(`single`, `single-mechanism`, `bundle-mechanism`, `bundle`), in page order, word for word, using
the block ids in `blocks.json`. Note where a block is missing, repeated, or says something
another block contradicts (supply figures, counts, names, guarantee wording).

## 2. Map theirs

Two or three of the strongest competitor product pages in the category, mapped to the same
block ids, in our own words with their numbers. Measure each page with
`scripts/measure_page.js` (ours too). Facts only: what they have, not what is good.

## 3. Evidence

- `scripts/review_timeline.py` on the brand's reviews, with an outcomes file made from
  `outcomes.template.json` in the avatar's words: when it worked, per product.
- `scripts/rank_answers.py` on the avatar's language rows: what they bought for, what they
  like, how it feels, what annoyed them elsewhere, what the site did not answer, why they
  refunded.
- Count reviews with photos and video: the real artwork available.

## 4. Refine, block by block

One card per block, per product kind:

| Field | What goes in it |
|---|---|
| Block | the block id |
| On | which products carry it now |
| Now | what it says now |
| Theirs | what the competitors do for the same job |
| Customers say | counts and row ids from step 3 |
| Move | keep · amplify · add · refine · rebuild · merge · cut |
| Change | the structural change, no final words |
| Words from | the evidence source the words will be drawn from |
| Artwork | the slots the block needs |

Pros of the competitors become `add`; our gaps and contradictions become `refine` or
`rebuild`; our strengths become `amplify`; duplicates become `merge`. The brand owner gives
the go before step 5.

## 5. Write

Every customer-facing word comes from a review (quoted exactly) or a language row, and the
row id is recorded next to the block. Product facts come from the brand folder. Nothing is
invented: no claim, number or quote the brand does not hold.

## 6. Build and check

Build in the recipe's order. Run every block's checks in `blocks.json` and the
`page-look` checks on every product, at 1200 and 390 wide. A failed check is fixed, not
argued.
