# flywheel

**The read joined to the plan.** Each morning, what the numbers say becomes brief proposals the owner only has to
glance at, on Studio → Today → **Plan what to make**. Each one has a Start button that runs it as a dry run.

| Proposal | When | What it starts (dry) |
|---|---|---|
| **variations** | a KPI winner showing creative fatigue | an ad-variations plan of it, `--dry-run` |
| **matrix** | a spend winner not yet varied | the creative matrix column to test next, from what the winner already holds |
| **promo** | a promo window coming up (21 days) | the promo pack's hand-offs, `--dry-run` |
| **re-make** | a proven winner from the bank, no spend in 30 days | a baseline re-make: ad-variations plan `--n 1 --dry-run` |

Each row carries the numbers behind it and nothing else. It makes no money decision and nothing spends: a row's job
stops at the quote, as the chain does.

## The rules it reads

- **Spend winner / KPI winner**: the desk's own rule (`components/video-studio/workflow_desk.py` `live_ads`): top
  share of ads by 30-day spend; KPI winner = also at or under the brand's CPA target (`~/.prizm/targets.json`).
- **Creative fatigue** (Meta's line, `components/creative-diversity/META.md`): cost per result 2x or more the ad's
  past; above its past but under 2x is creative limited. Window (draft): the last 3 and 7 days from the desk report
  against the ad's own 14 or 30 days.
- **Next matrix column**: of the four seen columns (format, face, setting, look), the one whose value the most
  running ads share. The said columns (person, awareness, angle) stay. A winner whose 7 cells are not on file gets a
  row too: its job fills the cells first, then `flywheel.py column` picks.
- **Already varied**: `variation_of` in the brief register, an ad-variations run that names the brief, or a Studio job
  that asked for it.

## Run

```
python3 components/flywheel/flywheel.py run  --brand <brand>       # writes runs/flywheel/<brand>/<date>/proposals.json
python3 components/flywheel/flywheel.py show --brand <brand>
python3 components/flywheel/flywheel.py column --brand <brand> who=… awareness=… argument=… format=… face=… setting=… look=…
```

Scheduled through `components/job-meter` (job id `flywheel`), listed switched off; the owner turns it on in
Studio → Settings → Jobs. The Start button is the Studio job kind `flywheel` (`components/video-studio/studio_asks.py`).

## Reads (never Meta)

`runs/funnel-tracking/<brand>/<date>/warehouse.json`, `runs/media-buying/<brand>/<date>/report.json`,
`brands/<brand>/briefs/briefs.json`, `runs/creative-diversity/<brand>/`, `runs/winners/<brand>/bank.json`,
`brands/<brand>/products/offer-bank.md`, `runs/promo-pack/<brand>/`.

## Keys this tool needs

None.

Tests: `tests/test_flywheel.py`.
