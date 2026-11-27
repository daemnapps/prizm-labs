# components/media-buying — the Ad Desk

Every live ad judged against its own offer's margin and the store's blended week; flags for the owner; his calls
recorded with reasons; Meta changes only on his go. Run by the `/analyze-ads` skill ("analyze ads").

**Engine:** the owner (built 4 Oct 2026). **Definitions:** the owner — `runs/media-buying/<brand>/desk.json`
(the lines, the funnel → offer map, `changes[]`), status `draft` until he approves the lines.
**Plane:** `runs/media-buying/<brand>/<asof>/report.json` + `REPORT.md`; `decisions.jsonl` (his calls),
`actions.jsonl` (what was done in Meta). **Manifest per entry:** each desk line is a multiple of the ad's
break-even CPA; each call carries the flag as shown, the suggestion, his call and his reason.
**Runs by:** person (on his word).

## The idea (the owner, 4 Oct 2026)

"On Meta, we're going to try to optimize to basically break even, and the goal of the store is to make their
profits... If something is spending and it's making money, and the CPA is within a reasonable range,
meanwhile the store still has a solid blended CPA, then we keep it on."

- **Break-even CPA per ad** = the store's contribution per order on that ad's funnel over 30 days (revenue −
  refunds − product − freight − both warehouses − card and platform fees, from `pnl_orders` +
  `order_economics`), so upsells are in. A funnel with fewer than `min_store_orders` falls back to the
  offer's first-order break-even (`lab/the owner/media-buying/Brand B-offer-lines.json`).
- **Store guardrail** = the last 7 days: all store contribution − all Meta spend. Below zero, no budget goes up.
- **Old ads are judged on their last 7 days**, young ones on their life — a long-runner's lifetime average
  hides a bad week.

- **One rule per desk (2026-11-24).** A desk whose `desk.json` carries `rule` (type `meta_cpa_windows`) is judged by it
  alone (`analyze.judge_windows`): Meta CPA over 3, 7 and 14 days against one line, at or under in any window = keep,
  over in every window with spend = kill, with a prospecting keep (14-day CPA to a cap, daily frequency and share of
  spend over 7 days). Judged on blended economics, so no funnel mapping is needed. The line, the marks and their
  evidence live in that block only. Brand A is the first; a desk without `rule` (Brand B) is judged as before.
  `windows_page.py` draws its page; `creative.videos` fetches the public posts; `names` in desk.json gives an ad a
  readable name. Its windows end on the last day the warehouse holds. `SHOPIFY_BLEND` fills an order not shipped yet
  with the 30-day average shipping cost, so a fresh week no longer reads as free shipping.

## Commands

    python3 machine/analyze.py <brand> [--asof YYYY-MM-DD]     # warehouse only; no Meta API
    python3 machine/desk_page.py <brand> --out <page.html>      # his page
    python3 machine/decide.py <brand> F<n> <call> --why "..."   # record a call;  --log to see them all
    python3 machine/calls.py <brand>                            # what the calls say: every call that differed
                                                                # from the desk's suggestion, with its reason
    python3 machine/act.py <brand> F<n> [--go]                  # pause an ad / budget ±step — only on his go
    python3 -m unittest discover -s tests

Reads the warehouse with `SUPABASE_DB_URL` (env, else the Keychain), read-only by session setting.
`act.py` uses `components/meta-upload/meta.py` (the Prizm Labs key).

## Open

- Brand A desk set up 2026-11-03 (`runs/media-buying/Brand A/desk.json`, draft): store is Shopify, so the desk says
  `store_source: shopify_pnl` and names its P&L table (`store_table`); that P&L has no funnel tag, so each funnel uses
  its own first-order line (`fallback_break_even`, with its source written beside it). Only the ICON funnel's flex
  offer page is mapped; other landing pages show as "not mapped". Its Meta spend is flowing again from 2026-10-09
  after a gap 2026-09-18..10-08 (checked 2026-10-22).
- A desk funnel calls its offer by `offer_key`, the offer bank section key; a funnel with no section says why in
  `offer_key_gap` (Brand B's V2C advertorial).
- Lines are starting lines (draft), tuned from his calls; on a desk with `rule` the ad lines are not used.
- Prospecting keep: past ads of that shape ran over the cap the next week (14 reads); watch it against the calls.

## Read from outside the desk (2026-11-18)

`machine/calls.py` (`read`, `summary`, `for_brand`; stdlib only, no warehouse) is the desk's public surface for a
reader that wants the calls: how many agreed with the desk, and every disagreement with its numbers and the reason
on record. The winners feed reads it (`components/winners/feed_sections.py`, "Desk calls"). It changes no desk line:
a retune from the disagreements is still shown to the owner first.
