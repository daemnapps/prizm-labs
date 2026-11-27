---
name: media-buying
description: Run the media-buying desk on a brand's live Meta ads and bring the owner the calls to make — "analyze ads", "analyze ads effectively", "analyze the ads", "how are the ads doing", "what should I turn off", "media buying check". Judges every active ad and campaign against its own offer's break-even (store contribution per order) and the store's blended week, flags turn-off / your call / budget up / budget down / double down, publishes his Ad Desk page, then records each call he makes WITH his reason and, only on his go, carries it out in Meta.
---

# /analyze-ads [brand]

> **Activates component:** `components/media-buying` — reads live Meta ads against the offer's break-even and makes the calls.

External dependencies (greppable): `components/media-buying/machine/` (analyze.py, decide.py, act.py,
desk_page.py), `runs/media-buying/<brand>/desk.json` (the brand's lines + funnel map),
`runs/media-buying/<brand>/decisions.jsonl` (his calls), `components/meta-upload/meta.py` (act.py only).

the owner, 4 Oct 2026: "Every time I say 'Analyze ads effectively,' it's going to run through this process of
looking at all of the live ads that are active in the campaign. It runs criteria, and then it flags whatever
needs to be flagged, and then I can make final decisions. Over time, you're going to just record all of my
decision-making... and then you can learn from there."

**The idea:** Meta is run to about break-even; the store makes the profit (repeat orders, email, SMS). So an
ad is judged in multiples of ITS OWN offer's break-even CPA — the store's real contribution per order on
that ad's funnel, upsells in, refunds out — and no budget goes up while the store's week is negative after
ads. Talk to him in plain words; he is not technical. Data, not suggestions: show the flags and numbers; he
makes every call.

**A desk with one rule.** When `runs/media-buying/<brand>/desk.json` carries `rule` (type `meta_cpa_windows`),
that rule is the only keep / kill rule for the brand: Meta CPA over 3, 7 and 14 days against one line, judged on
blended economics, not attribution. At or under the line in any window = keep. Over in every window = kill, unless
the ad is prospecting (14-day CPA within its cap, low daily frequency, a real share of spend). The numbers live in
`desk.json` and nowhere else; the Ads tab and the Acquisition page read the call from the desk's report, and the old
ad filter refuses that brand. The calls are binary: show them, never soften them.

## Steps

1. **Brand.** The one he names; none named = every brand with a `runs/media-buying/<brand>/desk.json`.
   A brand without one has no desk yet — say so in one line.
2. **Run.** `python3 components/media-buying/machine/analyze.py <brand>` — warehouse only, never the Meta
   API (no usage cost). It writes `runs/media-buying/<brand>/<date>/report.json` + `REPORT.md`.
   If the store's last order or Meta's last day is more than 2 days old, say it first — the read is stale.
3. **Page.** `python3 components/media-buying/machine/desk_page.py <brand> --out <scratchpad>/ad-desk-<brand>.html`
   and republish over the brand's ONE Ad Desk artifact (`page_url` in the brand's desk.json, else
   `components/media-buying/context/artifacts.md`; never a second page), passing every
   `runs/media-buying/<brand>/<date>/art/*.jpg` and `*.mp4` as `art/<name>` in the publish's `files` (the page shows each ad's own picture — the owner decides by looking). Private — his page.
   Look at it in the browser before telling him it's there.
4. **Tell him** in a few lines: the store strip (spend · orders · blended CPA · earned per order · after ads),
   then the calls by group with their flag numbers (F1…). On a desk with a rule: kills first, then prospecting,
   then keeps, each with 3 / 7 / 14-day CPA; and any ad whose picture says a retired price, date or offer
   (look at the pictures), because the rule reads cost, not words. Nothing else.
5. **Record every call he makes, with his reason**: `python3 components/media-buying/machine/decide.py <brand> F<n> <call> --why "<his words>"`.
   Calls: off · keep · watch · up · down · hold · double · skip. No reason given → ask for it once; the reason
   is what the desk learns from. Republish the page so his calls show on it.
6. **Carry out, only on his go, per action, in the same conversation:**
   `act.py <brand> F<n>` (dry run, shows exactly what changes) → he says go → `act.py <brand> F<n> --go`.
   Only pause-ad and campaign budget ±step are Meta changes. "Double down" files to the brief queue as a
   note (format, angle, avatar of that ad) — never auto-makes anything.
7. **Learn.** `decide.py <brand> --log` shows where he agreed and where he overruled. When a line is overruled
   3+ times the same way, propose the changed line to him with the calls behind it; on his yes, edit
   `desk.json`'s `lines` (or `rule`) and append to its `changes[]` with his words. Never change a line on its own.

## Never

- Never pause, unpause or move a budget without his go on that action.
- Never pull account-wide from the Meta API; the warehouse is the source.
- Never turn Meta's automated rules back on (switched off on purpose, 4 Oct 2026, until new assets get spend).
