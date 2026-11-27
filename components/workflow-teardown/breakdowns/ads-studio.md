# Ads Studio

Makes static ad creatives (headline, primary text, CTA and the picture) for Meta, from a brand's website, a product page, a product photo with a description, or a prompt.
Source: `ads-studio/SKILL.md` (the only file it serves)

## Inputs it needs
- One of: a brand website, an existing Ads Studio brand/product, a product page link, a product photo plus description, or a plain prompt.
- How many ads (`total`) and the frame: `1:1` (default), `9:16`, `16:9` or `3:4` (`4:5` is not available).
- Optional: objective (`sales`, `leads`, `traffic`, `awareness`, `engagement`), up to four public style/product image links.
- Your yes to the quoted price before anything is generated.

## Steps in order
1. Decide brand vs product: a bare domain is a brand (research it, about 90 s); a path to one item is a product (read it, about 60 s). Ask one line only when the link is new and unclear.
2. `ads_studio_create_brand` (website) and/or `ads_studio_add_product` (page url, text, images). A name alone only returns a suggested website to confirm.
3. Wait until it has read it: brand `status: done` with `profile_ready`, products `texts_ready: true`, product `status: completed` and `images_count` above zero. Read once per user turn, never in a loop.
4. `ads_studio_list_products`, suggest which products fit the goal.
5. `ads_studio_quote` with the exact arguments you will generate; tell the credits and how many creatives that buys; wait for yes.
6. `ads_studio_generate` once (with an `idempotency_key`); report which products the runs are for.
7. When asked, `ads_studio_get_run`: copy exists first, pictures land after about 3 minutes; not ready until `still_rendering` is false.

## Prompt blocks, word for word
Ads Studio has no prompt template of its own: the product reads and the copy are written by its own back end. The only fixed text is the call shape and its rules.

**Generate call: what to pass**  
`ads-studio/SKILL.md`

```
Call `ads_studio_generate` once, with:

- What to advertise: `product_ids` (of any brand or none; each gets its own run), and/or
  `include_brand: true` for the brand itself, and/or a `prompt` in the user's own words. A
  generation advertises exactly what these say. `picked_for_ads` on a product only decides what
  the brand page shows in the web app; it does not select products for generation.
- `brand_id`, optional: the brand whose kit (logo, palette, tone) shapes the ads. Leave it out
  for ads with no brand kit, or send `brand_kit: false` to advertise a brand's product without
  its look. The kit only reaches its own brand's products: a product of another brand, or of
  none, is advertised without it, so never promise one brand's look on someone else's product.
  `include_brand` needs `brand_id` with the kit on.
- `images`, up to four public links the user supplied: `role: "product"` for a photo of the
  thing being advertised, `role: "style"` (the default) for a look to follow.
- `total`: the number the user named, or 1 for a singular request. Ads Studio splits it
  across the subjects, so it must be at least one per subject. "Two products, three ads each"
  is `total: 6` with two `product_ids`.
- `aspect_ratio`: one of `1:1` (default, square feed), `9:16` (stories, reels), `16:9`
  (landscape), `3:4` (portrait feed). **`4:5` is not available**: offer `3:4` as the nearest
  portrait frame. Always send the frame.
- `objective`, only when the user made the goal clear: `sales`, `leads` (sign-ups, demos,
  quotes), `traffic` (visits, clicks), `awareness` (a launch, being known), `engagement`
  (comments, shares). Otherwise leave it out and the product's own profile decides.
- `idempotency_key`: choose it once for this generation (any unique string) and repeat it
  unchanged if you must retry the same call. A new key on a retry buys the same batch twice.


```

**Product-or-brand question asked before anything starts (example line)**  
`ads-studio/SKILL.md`

```
"I can
file just this product, also research acme.com as a brand, about a minute and a half, so the ads
carry its logo, colours and tone, or add it to one of your Ads Studio brands. Which one?"
```

**Where it stops: the answers it never gives**  
`ads-studio/SKILL.md`

```
## Never

- Poll `ads_studio_get_brand`, `ads_studio_get_product`, `ads_studio_get_run` or `ads_studio_list_products` in a loop; the cards poll, and you read once per user turn.
- Quote or generate while a product to advertise is still `queued` or `in_progress`, shows `texts_ready: false`, or a brand involved is still `running`.
- Send a product photo plus a request for ads to `generate_image` or `generate_image_batch`.
- Start research on a domain nobody named, or generate before the user agreed to the quoted price.
- File a product page as a brand, or a homepage as a product; when the link's domain is new and the words do not settle it, ask.
- Send `4:5`, or an objective the user did not imply.
- Reuse the same `idempotency_key` for a different batch, or mint a new one for a retry.
- Hand Ads Studio ids to the generic job tools, or describe `picked_for_ads` as choosing products for ads.
- Call an Ads Studio brand kit a Marketing Studio brand kit, or the other way round.
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Research a brand site | none named (Ads Studio back end, `ads_studio_create_brand`) | about 90 s, five stages |
| Read a product page or photo | none named (`ads_studio_add_product`) | about 60 s |
| Write copy and render the pictures | none named (`ads_studio_generate`) | `total`, `aspect_ratio`, optional `objective`, `images`, `idempotency_key` |
| Quote | none (`ads_studio_quote`) | no spend |

## Checks and gates
- Stops if `ads_studio_list_brands` is not offered (not enabled on the connector); will not substitute plain image generation.
- Nothing is quoted or generated while a product is `queued`/`in_progress`, `texts_ready` is false, or a brand is still `running`.
- Spend only after an explicit yes to the quoted price; a cost question ends at the quote. A product-card or allocation click is not approval.
- Never starts research on a guessed domain; never sends `4:5`; never reuses or re-mints an `idempotency_key` on retry; on `ADS_STUDIO_UNAVAILABLE` it reads `ads_studio_list_runs` first.
- Edits and variations of finished ads are not available through these tools.

## Price pattern
Quote first with `ads_studio_quote` (returns credits and how many creatives they buy). Higgsfield does not publish a figure in this workflow and `_prices.md` has none: not quoted.

## Cheap swap
- Whole job: Claude writes headline, primary text and CTA from the plan (free to us), then pictures with `seedream_5_0_flash` 2k (0.5 credit) or `gpt_image_2_6_flare` 1k low (0.75) instead of Ads Studio's own render (not quoted): you control the cost but lose the brand-kit research.
- Brand/product reading: fetch the page and read it locally with Claude (free) instead of the 60-90 s Ads Studio read.
- Text on pictures: render the headline with local ffmpeg/overlay on a text-free picture so a cheap model never has to draw words.
- Resize to `3:4`/`9:16` locally with ffmpeg instead of paying for new frames.
