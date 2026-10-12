# The offer bank — how the machine reads it

Markdown mirror of the artifact **The Offer Bank**
((team page)).
Snapshot of 2026-09-10; regenerate after the bank changes.

## One bank, two questions

| Surface | Asks | Answer |
|---|---|---|
| Static / video ads | *what is the hero?* | one front-end offer per lane, `_hero: paid_` |
| Email | *what may this send carry?* | any usable offer for that lane on that date, or none |

In September, 14 of 17 sends carry no offer at all.

## The catalogue

| Key | Lane | Status | Hero | Window | Note |
|---|---|---|---|---|---|
| `flex-vitals-sub` | avatar-one | live | yes | — | price only — outcome unwritten |
| `vitals-onetime` | avatar-one | live | — | — | price only — outcome unwritten |
| `volume-tiers` | avatar-one | live | — | — | price only — outcome unwritten |
| `flex-labor-day` | avatar-one | live | — | 2026-08-27 to 2026-09-07 |  |
| `king-skin-set` | avatar-one | draft | — | — | DRAFT — the set price is OPEN. The theme renders it from Shopify and n |
| `flex-preorder` | avatar-one | expired | — | — | EXPIRED. The FAQ ships this June 2026 and it is now September — the ol |
| `method-offer` | avatar-two | live | yes | — |  |

## Reading it

```bash
python3 offers.py --brand <brand> --hero
python3 offers.py --brand <brand> --avatar <lane> --on <YYYY-MM-DD>
python3 offers.py --brand <brand> --write     # regenerate offers/offers-parsed.json
```

The prose bank (`brands/<brand>/products/offer-bank.md`) stays the human's source of
truth. `offers.py` reads its own `## Live` / `## Draft` / `## Expired` structure into
rows. An offer filed inside a lane's context section instead declares `_status: live_`
so it stays visible. A dated offer carries `_window: <start> to <end>_` and is refused
outside it, on every surface.

## Still open

- `gift-buyer` has no offer and no hero — nothing for an ad or a send to point at.
- Three of four avatar-one live offers are prices, not offers: the outcome line in the
  customer's own words is unwritten for each.
- Named-set prices (King, Clear Skin, Revival) render from Shopify; no asset may state them.
- September to December beyond Labor Day, and BFCM, are founder-set and unwritten.
