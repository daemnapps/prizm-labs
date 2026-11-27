# Product page — one standard for every product page, any brand, any product, any customer

**Product page** builds product pages for any brand, any product and any customer type from one set of standard blocks. Brand, product and customer type are inputs; nothing about them is built in. It
takes the brand's current pages and the best competitor pages apart element by element,
finds the gaps, decides every block's words from the brand's own customer evidence
(reviews and language rows, cited by id), and checks the finished page against pass/fail
rules. Spoken name: "product page". The one-page definition is `CLAUDE.md`; the method is
`METHOD.md`; the blocks are `blocks.json` (readable as `BLOCKS.md`).

    python3 tools/product-page/scripts/review_timeline.py reviews.json --outcomes outcomes.<product>.json --out runs/product-page/<brand>/timeline.json
    python3 tools/product-page/scripts/rank_answers.py brands/<brand>/core-avatars/<avatar>/language --out runs/product-page/<brand>/answers.md
    # in the browser console, on any product page: paste scripts/measure_page.js

Runs file at `runs/product-page/<brand>/` and stay out of the repo.

## What is here

| File | What it is |
|---|---|
| `blocks.json` | The 26 standard blocks, the 3 inputs (brand, product, avatar), the 4 kinds of product and their recipes. The one source. |
| `BLOCKS.md` | The same, to read. Rebuilt by `scripts/build_docs.py`. |
| `METHOD.md` | The six steps from teardown to a checked page, and the element card every refinement is written on. |
| `scripts/review_timeline.py` | When customers say it worked: stages, counts, what changed, their own lines. |
| `scripts/rank_answers.py` | Every survey question in the language rows, answers ranked with counts and row ids. |
| `scripts/measure_page.js` | Words, text styles, backgrounds, height and first screen of any product page. |
| `outcomes.template.json` | The timeline's outcome list: three universal outcomes plus one slot for the product's main result in the avatar's words. |

## Inputs, kinds and recipes

Every run names a **brand**, a **product** and an **avatar** (the customer type the page is
written for). Each product is one of four kinds, set by how it works, not by category:
`single` · `single-mechanism` · `bundle-mechanism` · `bundle`. A product takes the recipe of
its kind; blocks never change order between products of one kind.

## Neighbours

Customer words come from `language-layer`; product facts from `brands/<brand>/products/`;
pictures from `image-production` and `3d`; the page is assembled by the brand's own store
theme or by `offer-workspaces/page`.
