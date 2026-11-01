# Third-theme test: metrics insights (signals from the KPI dashboards)

2026-10-02, ≈ STREAM · atlas [6941d8]. the team: "operational insights from metrics KPIs … we do want to start considering issues / insights from those", then "Make it new theme and the team owner".

## Result: the core held

The theme ran through the core with only a new pack (`themes/metrics-insights.json`, triage owner the team) and a new adapter (`tools/metrics_insights.py`, four detectors). The page renderer (`tools/triage_page.py`) drew it unchanged. The contract's kill-condition, "the core needs changing beyond a new adapter and pack", did not fire. Two small core assumptions surfaced; the contract is amended for both.

## The dry run (data cutoffs 2026-09-23 to 2026-09-30)

6 signals in 3 actions:

| Signal | Priority | Money at stake |
|---|---|---|
| <brand>: shipping cost billed for only 9% of August (0% July) orders | P0 | ~$10.9k/month the P&L counts as zero |
| <brand>: revenue down 47% over the last 28 days, with spend down about the same (looks like a spend decision) | P0 | ~$17.9k/month |
| <brand>: 31 orders with no cost and 69 with no price, of 594 | P1 | ~$5.8k/month of revenue whose contribution is unknown |
| <brand>: shipping cost billed for 40% of September orders | P1 | ~$2.1k/month |
| <brand> performance data stops 7 days before the other runs | P1 | holds <brand> movement signals |
| <brand>: 7 warehouse codes with no SKU lookup | P2 | — |

The forecast detector found **no product selling out before its resupply**. That is a real result, not a miss: every active product's next arrival lands before its sell-out date, at the last 30 days' rate.

## What fit the contract without change

- **Detectors as the adapter.** Items are built, not read. The pack holds the thresholds (`adapter.detectors`); the adapter holds only logic.
- **Priority by money at stake.** The pack's `priority.money_floors` set the tier, and the adapter stamps it, as the atlas does with its summaries' severity.
- **Data health holds movement.** A stale run's movement signal is held (`blocked_by`), so a week of missing data is not read as a drop.
- **Self-closing.** The next refresh recomputes every signal, as with red tests.

## What the core assumed, now amended in CONTRACT-themes.md

1. **Areas were repo paths.** A signal belongs to a brand, product or SKU, not a folder. Areas are now typed: `path:`, `brand:`, `product:`, `sku:`. Digests and cross-theme links match on any type.
2. **The renderer said "issue" and "close an item already fixed".** Both now come from the pack: `item.noun` and the close semantics in `adapter.still_true`. That renderer change is made: the model carries `item_noun` and `close_note`.

## Open, for the team as triage owner

- **No targets exist.** Threshold signals wait until owners set them; until then the detectors compare each brand against its own history.
- **The ads owner per brand is not on record.** The <brand> revenue signal's decider is "the brand's ads owner (not on record)". the team or the team to name.
- **Signal age needs the log.** A signal's first-fired date is only known once the triage log records it.
- **Stock is summed per product across warehouses.** Which warehouse should stock which SKU is not modelled. That avoided 45 false stockout alarms in this run.
