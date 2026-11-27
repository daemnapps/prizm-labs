# Funnel Map (mirror)

Artifact: https://claude.ai/artifact/G8sfWLXyygzkg4oPWrNM7s (v5) · source `funnel-map-owner.html` · 2026-10-12, data 5–12 Oct (full journey 12 Sep–12 Oct, Clarity 9–12 Oct). Both funnels tracked live 12 Oct. Rebuilt every morning at 06:00 (`com.daemn.funnel-daily`). Meta was not read; counts are from Next Commerce, Shopify and Klaviyo (read only).

## Full journey — Brand A, 12 Sep to 12 Oct (added 12 Oct, v4)
Every customer whose first funnel order landed in the 30 days, followed through Klaviyo email and every later order (funnel and Brand A.com), joined on email (hashed; never shown). Source: `runs/funnel-tracking/Brand A/2026-10-12/journey.md`, built by `components/funnel-tracking/machine/journey.py` (daily: `daily.py --brand Brand A`).

| Stage | Count | Revenue |
|---|---|---|
| Ad click | not read (Meta rule) | |
| Checkout started (email typed) | 36 | |
| Bought | 30 (24 new to Brand A, 4 already Brand A.com buyers) | $2,666 |
| Took an upsell | 12 | $453 (+17%) |
| Got our emails | 28 (22 opened, 8 clicked) | |
| Bought again within 30 days | 4 (all on Brand A.com) | $293 |
| Worth so far | | $2,960 ($99 per customer) |

| Ad | Checkouts | Buyers (new) | First orders | Upsells | Opened / clicked | Bought again | Worth so far |
|---|---|---|---|---|---|---|---|
| VSL · the owner to Rashad 2.0 | 7 | 10 (10) | $1,007 | 10 · $355 | 7 / 4 | 0 | $1,007 |
| No ad tags (pre-standard) | 25 | 10 (7) | $845 | 3 · $78 | 7 / 2 | 1 ($0) | $845 |
| Meta click, ad unknown | 0 | 3 (3) | $147 | 1 · $0 | 3 / 2 | 2 · $201 | $348 |
| Email · Happy 4th Of July (old link) | 0 | 2 (0) | $140 | 0 | 2 / 0 | 1 · $40 | $180 |
| King static · Marcus poster | 0 | 1 (0) | $150 | 0 | 1 / 0 | 0 | $150 |
| LeBron ad · bump-check portal (brief-0019) | 1 | 1 (1) | $140 | 0 | 1 / 0 | 0 | $140 |
| Email · TS FLEX vs Hands | 0 | 1 (1) | $77 | 0 | 1 / 0 | 1 · $53 | $130 |
| A King ad with broken tags ({{ad.name}}) | 1 | 1 (1) | $90 | 1 · $20 | 0 / 0 | 0 | $90 |
| Evergreen offer · IG story images | 0 | 1 (1) | $70 | 0 | 0 / 0 | 0 | $70 |
| King static · Brett two-panel | 1 | 0 | $0 | | | | $0 |
| ACH-DAN-17 · ICON page | 1 | 0 | $0 | | | | $0 |
| Song ads (live 10–11 Oct) | 0 | 0 | $0 | | | | $0 |

**Emails that brought the second order (these buyers):** campaign "6 Years of Brand A" 1 order $52.99; campaign "Happy 4th Of July" 1 order $39.98; no email touch 2 orders $200.52. Credit = the order's own klaviyo tags, Klaviyo's attribution, or a click in the 5 days before.
**What they got after buying:** TS New Customer Post Purchase + Thank You (19 buyers, 6 clicks), T Delivered (18), T Carrier Picked Up (17), T Out for Delivery (16), C12 2+ Purchases Follow Up (9), 7 Level Up Guarantee (6).
**Revenue per flow, whole list, 30 days (Klaviyo's credit):** TS Next Order Flow $897 · TS UGC request $832 · 6 Customer Winback $741 · 7 Level Up Guarantee $725 · TS Abandoned Checkout $415 · T Delivered $272 · 9 Replenishment $147. Campaigns sent in the 30 days: one (12 Oct, 14 recipients). 588 orders ($29,779) had no email credit.

**Still blind:** Klaviyo UTM setting per account (pending until Klaviyo works again); Brand B Klaviyo key (pending); steps inside a funnel (Clarity export gives landing pages only); song ads (0 checkouts so far, live 10–11 Oct); 13 of 30 buyers carry no ad name (bought before the standard); clicks and spend (Meta never read); repeat window is only 30 days.

**Brand A tracking is live** (merged 12 Oct): checker on the live pages `check-after-live.md` = 82/82 (was 12/82).
**Brand B tracking is live** (PR #13 merged 12 Oct): checker on the live pages `runs/funnel-tracking/Brand B/2026-10-12/check-after-live.md` = 134/134 (was 24/134), pixel 1294318978367829 on all 22 pages.

Refreshed 12 Oct evening (Klaviyo skipped on the refresh, so the email rows above are from the afternoon read).

## Full journey — Brand B, 12 Sep to 12 Oct (added 12 Oct, v5)
Source: `runs/funnel-tracking/Brand B/2026-10-12/journey.md`. Email side waits on Brand B's Klaviyo key; no Shopify store to join (Brand B.com is on Next Commerce).

| Stage | Count | Revenue |
|---|---|---|
| Checkout started (email typed) | 105 | |
| Bought | 208 (181 new to Brand B) | $13,064 |
| Took an upsell | 44 | $2,650 (+20%) |
| Got our emails | waits on the Klaviyo key | |
| Bought again within 30 days | 13 | $972 |
| Worth so far | | $14,036 ($67 per customer) |

Top sources of buyers: Meta click with no ad name 57 ($4,276 so far) · ad 120246009360730591 (sends its id) 48 ($3,595) · no ad tags 49 ($3,013) · ad 120247623050700591 (id) 17 ($843) · ad 120247796220700591 (id) 14 ($771) · face scrub brief-0286 3 ($230) · body scrub static p152 3 ($189). 82 buyers came from ads sending their id instead of their name.

## Clarity, landing to order (12 Oct, last 3 days)
Clarity's Data Export only knows the page a visit LANDED on (query string included, so the ad name is read off the landing link), plus pages per visit, scroll and dead / rage / quick-back clicks. Steps inside the funnel are watched in Clarity itself (each step is tagged). The drop joins Clarity's landings to the store's own checkouts, orders and upsells for the same days. Source: `runs/funnel-tracking/<brand>/2026-10-12/clarity.md`, built by `components/funnel-tracking/machine/clarity.py` (two Clarity calls per brand per day, cached).

| Funnel | Landed (Clarity) | Checkout started | Ordered | Took an upsell | Biggest drop |
|---|---|---|---|---|---|
| Brand A ICON | 4 (portal-ingrown, brief-0039 ×3, brief-0038 ×1) | 3 | 2 | 0 | ordered → upsell, 2 of 2 |
| Brand B face scrub | 12 (portal-yai, 1.17 pages per visit) | 1 | 3 | 0 | landed → checkout, 11 of 12 (92%) |
| Brand B body scrub | 0 (Clarity on these pages from 12 Oct) | 6 | 5 | 1 | ordered → upsell, 4 of 5 |

**Brand A.com, where visits land (3 days):** products 239 · home 77 · collections 46 · cart 5. Top: /products/flex 106 visits (1.9 pages per visit, 19% scroll, 5.7% quick-back) · home 77 (17% quick-back) · King Skin Set 29 · The Lift 23 · Formulas 19 · CORE 16 (44% quick-back). Shopify checkout isn't visible to Clarity. Brand B.com has no Clarity yet.

## Acquisition tracking standard (12 Oct)
One spec for both brands: `components/funnel-tracking/` (STANDARD.md, standard.json). Every step sends the same event to Meta, GA4 and Clarity; every event carries ad_name, brief, batch, campaign, ad set, ad id, funnel, page, step and an event id (Purchase = `<store>-<order>`, matching the store's server copy; upsells = UpsellTake with value, never a second Purchase).

**Ad URL tags (every Meta ad):** `utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}&utm_term={{adset.name}}&utm_content={{ad.name}}&ad_id={{ad.id}}&sub1={{ad.id}}`. The uploader now sets these on every ad. Email links: `utm_source=klaviyo&utm_medium=email&utm_campaign=<campaign or flow>&utm_content=<message>`.

| Step | Meta | GA4 | Clarity |
|---|---|---|---|
| Every page | PageView | page_view | page_<page> |
| Quiz / portal screen | QuizStep | quiz_step | quiz_step_<n> |
| Quiz finished | Lead | generate_lead | quiz_complete |
| Offer page | ViewContent (value) | view_item | offer_view |
| Add to cart | AddToCart | add_to_cart | add_to_cart |
| Checkout | InitiateCheckout | begin_checkout | checkout_start |
| Payment | AddPaymentInfo | add_payment_info | payment_info |
| Order | Purchase (id <store>-<order>) | purchase | purchase |
| Upsell page | ViewedUpsell | upsell_view | upsell_view |
| Upsell taken | UpsellTake (value, id <store>-<order>-u<n>) | upsell_purchase | upsell_take |

**Pull requests (one per brand, Clarity + standard):** Sellmore-Co/Brand A-cpk#7 and Sellmore-Co/Brand B-cpk#13.

**Checker, live today → after the PR** (headless browser under the real host, hits answered locally, no order placed): Brand A 12/82 → 82/82 (14 pages); Brand B 24/134 → 134/134 (22 pages). Per page: `runs/funnel-tracking/<brand>/2026-10-12/check-before-live.md` and `check-after-pr.md`.

**What each ad really sold, 5–12 Oct** (Next Commerce, no Meta; `runs/funnel-tracking/<brand>/2026-10-12/truth.md`):
- Brand A: LeBron ad brief-0019: 1 order $139.98. A King ad sending literal {{ad.name}}: 1 order $89.98 + 1 upsell. Untagged/email: 3 orders $284.77. (10 renewals left out.)
- Brand B: body scrub ad 120247796220700591 (tagged by id): 10 orders $585. Face scrub brief-0286: 3 orders $230. Scrub V2C ad 120246009360730591 (by id): 3 orders $147. Untagged: 11 orders $895.10. Klaviyo email: 4 orders $188.

**Loose ends (the owner / the email lead):**
1. Done: #7 (Brand A) live 82/82; #13 (Brand B) merged and live 134/134.
2. If not done yet: Brand B pixel 1294318978367829, allow recipe.Brand B.com under Traffic permissions (the checker can't see that setting).
3. Ads Manager: paste the standard URL tags on Brand B ads 120247796220700591 and 120246009360730591 (they send the ad id), and on the Brand A "Brand A - CC" ad sending literal {{ad.name}}.
4. Brand A shared pixel: recommended keep 303712903971974 and add a custom conversion "Funnel Purchase" (Purchase on method/flex.Brand A.com); a new pixel is cleaner but restarts learning.
5. Done: Clarity Data Export tokens in both projects. Clarity on Brand B.com comes with the storefront pass.
6. Brand B Klaviyo read key (pending; checked once Klaviyo works again).
7. Klaviyo UTM setting in each account, when Klaviyo is working.

**The whole journey:** built for both brands (above), rebuilt daily at 06:00.

**Corrections to the audit below:** Brand B quiz steps reached the dataLayer but not GA4 (the GTM container maps only six events). The Brand A funnel showed no GTM-PB5X9PSJ on 12 Oct.

## Verdicts (before the standard)
- **Brand A CPK (method.Brand A.com):** works, with gaps. Pixel 303712903971974 sends PageView on every page, the portal custom events (PortalStart, PortalAnswer, PortalQualified, PortalOfferView, PortalOfferClick), ViewContent and InitiateCheckout at checkout, and Purchase on the receipt (matched to the Next Meta app's server copy, event id `Brand A-<order>`). Gaps: no ViewContent on the FLEX offer page; 5 portal screens (why, truth, match, proof, told) send nothing; the Willow quiz page has no pixel; upsell revenue probably doesn't reach Meta; no event id on the other browser events.
- **Brand A.com (Shopify):** sends to the same pixel, 303712903971974. Clarity bfqhd8izrw is live.
- **Brand B CPK (recipe.Brand B.com):** no Meta pixel on any page. GA4 G-CN1VVV08V2 gets the steps through GTM-5DTVWB3B. Clarity yucxlsdity runs on the portal pages only.
- **Brand B.com (Next store):** pixel 1294318978367829 and GA4 are live. No Clarity.

## Attribution
- Real CPK orders from Meta ads: 1 order, $139.98, from the LeBron ad `brief-0019_batch-2026-10-09-b_cpk-bump-check-portal`. Song ads (`batch-2026-10-10-a`): 0 orders and 0 checkouts with an email entered.
- Brand A.com Shopify: 130 orders, AOV $50.94, on the same pixel. This is the AOV Meta shows.
- 10 Next subscription renewals may also be posted to the same pixel (not confirmed).

## Ladders
- Brand A CPK: emailed carts 4 (LeBron 1, song 0, untagged 3); orders 3 (LeBron 1, untagged 2); upsell takes 2 of 3. The portal steps can only be counted in Events Manager today.
- Brand A.com: 966 sessions → 83 added to cart → 65 reached checkout → 44 bought. Biggest drop: visit → cart.
- Brand B face scrub CPK: emailed carts 3; orders 6 (brief-0286: 3); upsell takes 1 of 6. Body scrub CPK: 13 orders, tagged by ad id instead of ad name.

## Clarity
Both PRs are merged and live (12 Oct): Sellmore-Co/Brand A-cpk#7 (every page plus the quiz, project bfqhd8izrw) and Sellmore-Co/Brand B-cpk#13 (all 22 pages, project yucxlsdity, quiz steps). Every recording carries ad_name, brief, batch, campaign, adset, source and page.

## Fixes, cheapest first
1. Merge the Clarity PRs.
2. Turn on the Brand B CPK Meta pixel.
3. Build a daily ad truth table from Next Commerce.
4. Fix ad URL tags (Brand B scrub ads send the ad id; one Brand A King ad sends literal {{ad.name}}).
5. Send each portal and quiz step to Meta and GA4, add ViewContent on the offer page, and add an event id on every browser event.
6. Put the pixel on the Willow quiz.
7. Send upsell revenue to Meta.
8. Add GA4 to the Brand A CPK.
9. Use a separate CPK pixel, or report on a CPK-only custom conversion.
