# How an email happens — every step, documented

Written 2026-08-31 on the owner's go ("document all these steps"). This is the
whole flow from brand to brief to wireframe, step by step, with the file that
runs each step. Brand-agnostic: brand context enters only through the brand
folder and the per-run flags.

## The shape

```
THE BRAND (read-only)  →  THE COMPOSER (a month of slots)  →  THE BRIEFS
                                                                  ↓
                THE CHAIN (10 stages, one slot → one wireframe)
                                                                  ↓
     THE HUMANS (designer for designed emails · copywriter for written ones)
```

Stage 1 ends at briefs (RULED 2026-08-29). Chain runs and everything after
are production — running now only on the owner's direct go, per category, to
prove the flow before stage 2 opens it up.

## Step by step

### A · The calendar — **now its own component**

`lab/marketing-calendar/` (its own folder since 2026-09-13, the owner: the planner is
"also going to be relevant for our ads as well"). Run it from there:

    python3 machine/calendar.py <month> --brand <brand>
    python3 machine/serve.py            # the review board, port 8788

A month lands in that component's `runs/` unless `--out` says otherwise, and
the copy stage below reads the run folder by path. Its contract — the slot
shape, and the `review.json` a human writes — is `CONTRACT.md` there.

Built from the ground up, in layers, each dated before the next is laid on
it (the owner, 2026-09-02: holidays → cultural moments → concepts → the other
categories → the catalogue → offers from the bank → production). Two AI
stages decide WHO and WHAT; code does everything mechanical, and every date
is a real date. Each layer writes into its own numbered folder under
`runs/calendar-<month>/`. Every stage, its prompt and its output live in
the run folder, and on the component's own review board. Full nuance of the cells stage: `CELLS.md`.

| Layer | Who | What happens |
|---|---|---|
| 1 THE HOLIDAYS | code | the public holidays landing in the month, with real dates from the tool's `holidays.py` table — calendar facts, the same for every brand |
| 2 THE CULTURAL MOMENTS | code | the brand's own moments in window, each resolved from its anchor in `calendar/moments.json` to real dates — the month's skeleton |
| 3 THE CELLS | AI | who gets spoken to, who rests — decided by what sending to it EARNS and by what the skeleton says the month is. No count, no ceiling, no floor, no sign-off |
| 4 THE ANCHORS | code | every dated holiday and moment laid onto the month AT ITS REAL DATE — ONE send to every live segment it fits (a holiday sale is one email with several audiences, not several emails) — a retail/season-opening holiday as a full arc around the day — a build-up of 1–4 sends scaled by what the holiday earned before (past sends vs the brand's median revenue per recipient), the ask, the close, an observance as one send on the day, a peaked window (Christmas) landing before the peak |
| 5 THE CONCEPTS | AI | an offer for every anchored ask (from the bank), then the concepts the month makes timely, then the educational/community/brand sends — each with a preferred date, each moment used only inside its printed window |
| 6 THE CATALOGUE | code | every send typed against the catalogue; every offer-carrying ask completed into its arc |
| 7 THE OFFERS | code | every offer checked against `products/offer-bank.md` — the only place an offer comes from; borrowed ones documented, unknown ones stripped, an offerless ask collapsing its arc |
| 8 THE AFFILIATE FLOOR | code | one affiliate partner a week, if the brand has any on file (`email/affiliates.json`) |
| 9 THE ORDER | code | dates resolved around the anchors, hours, sources, links; any identical sends to different segments merged into one send with several segments — no send budget; only an exact duplicate is ever refused |
| THE BOARD | code | every rule checked (including that every moment sits inside its real window), per-person math, one brief per slot |

Outputs per run: `1-holidays/` … `9-order/`, then `slots.json`, `checks.md`,
`briefs/` and `run.json` at the month's root. Adoption stays a separate
human act.

### B · The chain (`email.py <source> --brand <b> [--avatar] [--product] [--offer] --label <slot>`)

Ten stages, one file per prompt (highest `-vN-` wins), every stage saving its
output AND the prompt as actually sent:

0 Triage → 1 Read → 2 Spec → 2B Context scout → 3 Injection → 4 Placement →
5 Subject lines → (6 Expansion — organic sources only) → 7 Close → 8 Build →
9 Brief. Then `render.py` draws the wireframe at 600px.

Everything lands in `results/<slot>/`; the page's "Inside the runs" tab shows
each stage's real output with its prompt underneath.

### C · The humans (stage 2, parked — ruled in HANDOFF-TO-HUMANS.md)

The machine stops at a wireframe. Designed emails → the designer (images,
from the brand's Figma formats once access lands; generation via FAL AI,
she reviews). Written emails → the copywriter, so they sound human.

## The workflow matrix — how each category develops

One test cuts the categories: whose material is the email made of? That
answer decides the material pulled, the usual form, the sender, whether the
expansion gate fires, and which human finishes it.

| | Promotional | Educational | Cultural | Community | Brand | Affiliate |
|---|---|---|---|---|---|---|
| **Made of** | our offer | our expertise | the world outside | our customers | us | a partner's offer |
| **Material pulled** | offer bank (narrowed by `--offer`) + product file | language bank + objection bank + product | moments file + avatar territory | customer base, named people, verbatims | sender identity, what is actually true | `email/affiliates.json` — the partner's real product, link and terms |
| **Usual form** | designed template | text-led / designed | text-led, moment-fresh | designed with real photos / quotes | rich text or plain text with a name card | designed, one product, one link |
| **Sender** | brand | brand | brand | brand | a person (founder / pharmacist) — the form decides | brand |
| **Expansion gate** | usually skipped — source is ALREADY AN AD | fires on organic sources | fires on organic sources | usually fires — proof is organic | usually fires — letters are organic | skipped — written straight from the partner record, no swipe |
| **Arc habit** | asks; must stand behind an earns slot; obliges recovery | earns; obliges its `then` (stack, objection-shot…) | earns; often self-contained | earns; feeds proof-drop and spotlights | earns; trust-dense, no ask | earns; one a week, every week; never warms or closes our own arcs |
| **Finishing human** | designer | copywriter (text-led) or designer | copywriter | designer (photos carry it) | copywriter — the voice is the whole job | designer (the partner's product photo) |
| **Never** | invented deadlines or scarcity not in the offer file | category language the customer doesn't use | forced holidays outside the avatar's world | unnamed "thousands love it" proof | claims no named person can own | a commission claim, a first-person "we used it" nobody can own, a partner not on file |

## Proving runs (archived 2026-08-31)

The first end-to-end run, the September and October composes, and the five
category emails were proving runs — they exercised every stage for real,
then the slate was reset for the calendar flow proper. They live in
`results/archive/`, prompts and outputs intact.