# Page Naming — the plan (2026-11-14, waiting for the owner's yes)

Team copy of https://claude.ai/artifact/QJJK6hAYpy8QRJz6obWAPk (source `page-naming-owner.html`).
Replaces the 2026-11-13 draft (`page-0001` numbers, page list under `brands/`).

## The three things

| | What | Lives in |
|---|---|---|
| **Page** | a standing asset ads send traffic to; maintained and tested against. ID and address never change | the page list, `components/naming/pages.json` |
| **Page brief** | a work order: build a new page, a new control, or a challenger | the master brief register `components/image-teardown/briefs.json`, type `page` |
| **Page version** | one build of a page: `v1`, `v2`, `test-a` …; exactly one is `control` | inside the page's entry in the page list |

## The page ID

`page_<brand>_<funnel>_<page>` — lowercase, `-` inside a value, `_` between values, the same grammar as
`adset_<brand>_<avatar>_<angle>` and the catalog's `link_…` ids.

- `<funnel>` is the funnel id from the brand's funnel list (`body-scrub-cpk`, `flex-cpk`, `store`).
- `<page>` is the page's own address segment, read off the URL (`quiz`, `presell-five-ingredients`,
  `salespage-fedupking-razornotproblem`). Nothing is typed or coined.
- Chosen over a bare number: the Meta ad name already carries `<funnel>-<page>`, so the ID is the same pair
  and reports, referrers and pasted links all read without a lookup. Pages are few and permanent; ads are many.
- Every entry keeps `old_ids` (the catalog link ids), so `link_Brand B_cpk_quiz` still resolves.
- Every entry stores `meta` — today's Meta name page part, frozen — so **no live ad name changes**
  (e.g. the Brand A FLEX offer page keeps `icon-flex` though its funnel is now `flex-cpk`).

## Page list entry (manifest; rule-6 status)

```json
"page_Brand B_body-scrub-cpk_quiz": {
  "brand": "Brand B", "funnel": "body-scrub-cpk", "product": "brilliance-body-scrub",
  "url": "https://recipe.Brand B.com/Brand B-scrub-cpk/quiz/",
  "kind": "quiz",                 // advertorial | quiz | offer | store | money (checkout, upsell, receipt)
  "format": "quiz",               // classify_pages.page_type, for pre-sells
  "avatar": "spot-hider", "angle": null, "subs": [],
  "meta": "body-scrub-cpk-quiz",
  "old_ids": ["link_Brand B_cpk_quiz"],
  "status": "approved", "state": "live",          // state: planned | live | off
  "versions": [
    {"version": "v1", "control": true, "since": "2026-11-14", "brief": null, "run": null,
     "test": null}
  ]
}
```

A challenger version: `{"version": "test-a", "control": false, "brief": "Brand B_brilliance-body-scrub_brief-0312",
"run": "runs/page-chain/Brand B/body-scrub-cpk_quiz_test-a", "url": "<preview or split address>",
"test": {"flag": "page_Brand B_body-scrub-cpk_quiz", "variant": "test-a"}}`.
PostHog: one experiment per page, flag key = page ID, variants `control` and the challenger's version name.
`pages.py promote <page ID> <version>` makes the winner control; ID and address stay.

## Page brief (register row, type `page`)

New fields: `page` (the page ID — a planned one for a new page), `job` (`new-page` | `new-control` |
`challenger`), `version` (the version it will produce). A page brief carries **no** `landing_page` and no
`links`. Numbered at the START of the run (`briefs.py page --brand --product --page --job`), counting in the
brand + product's one brief count like every other type.

Fix: `brief-0285` (`p285`, face scrub salespage) loses its `landing_page`/`links`, gains
`page: page_Brand B_face-scrub-cpk_salespage-spothider-pigmentmemory` (state planned), `job: new-page`.

## Ad briefs

`landing_page.page_ids` holds page IDs; `link_ids` stays beside it for one release so meta-upload, the
hand-off and the card writer keep working unchanged. `page_pick.pick` ranks pages from the page list;
`meta_page()` accepts a page ID or an old link id and returns the stored `meta`.

## Page chain

`page-teardown`, `page-writing`, `page-production` take `--brief` (or `--page --job`, which opens one). The run
label becomes `<funnel>_<page>_<version>` under `runs/page-chain/<brand>/`. The finished build is filed as that
version on the page list. Existing runs `razor-bumps-3`, `face-scrub-1` are mapped, not renamed.

## Backfill (from today's data)

- Ad-facing pages from the catalog: Brand A 5 live with an address; Brand B 19 link ids → 18 pages (two ids
  point at the same subscription Yai portal).
- Funnel money pages (checkout, upsells, receipt, select, thank-you) from the funnel lists; each checked live.
- Every live page gets `v1` as control. Total ≈ 60, exact count after the live check.
- Flagged, not invented: `link_Brand A_flex_flex-new` (no address), `oto-up-bodycream copy` (v2c, a stray
  copy), the method.Brand A.com root quiz (sits in no funnel; placed under `flex-cpk`).

## Off-rule names mapped

| Today | Mapped to |
|---|---|
| `prelander-fedupking-razornotproblem-sub02baldbumpsguy` | `…-baldbumpsguy` |
| `…-sub03ingrownfighter` | `…-ingrownfighter` |
| `…-sub06fortyyearshaver` | `…-fortyyearshaver` |
| `*-construct.md` notes (3) | build notes of their page, not pages |
| v2c `(unnamed — the control)` `/adv` | `page_Brand B_body-scrub-v2c_adv` |

Live addresses are never renamed; the readable rule applies to new pages.

## Brand files (shown, need the yes)

1. `brands/*/web/funnels/funnels.json`: each funnel gains `page_ids`; its `pages` list stays one release.
2. `brands/Brand B/web/funnels/{body-scrub-cpk,body-scrub-v2c}/pages.md`, `brands/Brand A/web/funnels/icon/pages.md`:
   a pointer line to the page list at the top.
3. `brands/Brand A/web/funnels/flex/prelander/*-subNN*.md` renamed as above.

## Daily check

`pages.py check` — every live funnel page (funnel lists + catalog + addresses live ads use) that answers 200
and has no page ID is flagged; output under `runs/naming/<brand>/page-check/<date>/`. Hooked into the daily run
once the driving session confirms where.

## Tests

`components/naming/tests/test_pages.py` (ID grammar, one control, promote, alias lookup, meta frozen, check
flags a missing page), `test_page_pick.py` extended, brief register tests for `page` rows; `selfcheck.py` green.

## Revision 2 (2026-11-14, after the owner: "human readable but not bloated … conventions for our links … this covers all pages, not just funnels")

Supersedes the ID, version and link sections above where they differ.

**Three lengths, like ads** (ads: file `brand_product_brief_batch_asset-NN`, Meta `brand_product_brief_batch_funnel`, the rest in the brief):

| | Pages |
|---|---|
| Long — run folders, build files | `<brand>_<place>_<page>_v<N>` → `Brand B_body-scrub-cpk_quiz_v7` |
| ID — the key | `<brand>_<place>_<page>` → `Brand B_body-scrub-cpk_quiz` (no `page_` prefix; a page part never matches `brief-NNNN`) |
| In Meta — the ad name's last piece | `<place>-<page>` → `body-scrub-cpk-quiz`; **never a version**: a split test runs on the page, so ad names and ads never change when a test starts |
| Everything else | the page list (avatar, angle, subs, format, offer, swipe, headline, versions) |

**Place** = a funnel id, `store`, or (rarely) another site's place name the owner OKs once (the method.Brand A.com root quiz).
**Store pages** are in scope: page part = `<kind>-<handle>` with kind `product` · `page` · `collection` · `blog` · `home`
(`Brand A_store_product-war`, `Brand A_store_page-method-quiz`), read from the store's own API. Frozen Meta parts stay (`store-war`).

**Versions** are `v1, v2, v3 …` — every build numbered, never reused; one carries the control mark; the winner takes the
mark, its number unchanged. (Replaces `test-a`.) PostHog: flag key = page ID; variants `control` and `v<N>`.

**Links**
- New funnel pre-sell: `format-angle[-sub]` (`/advertorial-pigmentmemory-textureseeker/`). The avatar moves out of the address
  into the page list — shorter, and the customer never reads our avatar name. (Changes PAGES.md's 2026-09-11 `format-avatar-concept`.)
- Money pages plain (`/landing/`, `/checkout/`, `/oto-up-bodycream/`).
- New store page: the same rule as its handle (`/pages/quiz-razornotproblem`). Product pages keep the store handle; never renamed.
- Challenger builds sit under the page (`/quiz/v7/`); ads never point there — PostHog sends a share of the page's own traffic.
- Ad link = page address + today's UTM tags (`utm_content=<ad name>`), unchanged.
- Live addresses are never renamed.

## Revision 3 (2026-11-14) — test words, set by the owner in the PostHog session

Worded like the scientific method; "challenger" and "winner" are retired everywhere (they remain above only as history).
The page list's test entry uses PostHog's field names exactly:

| Field | Meaning |
|---|---|
| `hypothesis` | written before the test starts |
| `control` | the version running today |
| `variant` | the one new version, `vN` |
| `group` | which one a visitor got (`control` / `variant`) |
| `primary_metric` | `checkout_reached` |
| `confirm_metric` | `purchase` |
| `status` | the test's state (draft / running / done — in `state` on the page list, rule 6) |
| `result` | `variant wins` · `control holds` · `no difference` |

A page brief's `job` is `new-page` · `new-control` · `variant`. `variant wins` moves the control mark to the variant's
version; its number never changes. Flag key = page ID; variant keys `control` and `variant`.

## Revision 4 (2026-11-14) — the automatic testing loop's hand-off

session-teardown (steps 1–4) writes `runs/session-teardown/<brand>/<label>/hypothesis.json`:
`kind` hypothesis · `page_id` · `type` design|offer · `control` {version, path, offer} · `variant_offer` ·
`hypothesis` · `change` · `primary_metric` · `confirm_metric` · `stop` · `evidence` {leak, recordings, patterns, clips} ·
`by` · `status` draft. AGREED with the PostHog session 2026-11-14, plus: `id` `<brand>_<page>_hyp-<YYYYMMDD>-<n>` (also its
run label; carried onto the page brief and the test), `evidence.leak.source` all|ads|email|creator|bio,
`evidence.leak.device` all|mobile|desktop, `evidence.clarity` {rage_clicks, dead_clicks, scroll_depth_avg, window} or
null, and `replay` (PostHog replay link) on each clip.

The page system (steps 5–7):
- `briefs.py page --hypothesis <file>` — or the page chain's `teardown.py --hypothesis <file>` — opens a page brief with
  job `variant` carrying the hypothesis and the change; reserves vN on the page list; drafts the page's test (control =
  the version holding the mark, which must still be the one the hypothesis was written against; one test per page).
- The page chain tears down the control and runs `<place>_<page>_vN`; the build is filed as vN and the test's variant
  path set to `<control path>/vN/`.
- The test cannot go live until `test_problems` is empty: compliance pass with its run, the owner's dated approval.
Not built yet: page-writing's prompt slot for `change` (a prompt change, the owner's), the page compliance check,
and the approval card.

## Revision 5 (2026-11-14) — team fixes and big swings from session-teardown

Agreed with the session-teardown rebuild (owner's rulings relayed there: small fixes go to the team, at most 3 big
swings go to the owner; team fixes keep compliance plus the owner's click, ideally one click per page batch).
- Big swings: `runs/session-teardown/<b>/<label>/swings/swing-N/hypothesis.json` (N = 1..3, the agreed hypothesis
  record, id `<label>-sN`); the picked one is copied to the run's `hypothesis.json`; intake unchanged:
  `briefs.py page --hypothesis <run>/hypothesis.json`.
- Team fixes: `fixes.json` (`kind` fix-list · `page_id` · `control` {version, path} · `fixes` [{id, section, problem, fix,
  kind, at_stake_month, moments}] · `status` draft). `briefs.py page --fixes <file>` opens a `new-control` brief;
  refused while a test is open, when the control moved, or when the page is not live.
- Going live: `page_list.approve_version(page, vN, by, compliance_run=…)`. A new control takes the mark only when
  built, compliance passed and a dated click is recorded; a variant's approval opens its test's gate instead.
- Readers: `page_list.page_context(page_id)` → entry, control version, the brief that built it, its page-chain run and
  its section jobs (none for pages built before the page chain).
