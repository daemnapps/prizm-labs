# Ad series

Status: draft, unsigned. Dry runs only; no series has been produced. Round 3 (2026-11-07): the ask is used as filed, setups are dated to the brief that says them (L8), and no offer is added that is not on file. Registered in `../bank.json` from `format.json` (2026-11-07); no run uses it unless the run names `ad-series`.

This folder is the format's one home (`../README.md`, "One home per format"):

| File | Holds |
|---|---|
| `format.json` | the arc card, the tap laws, the ledger kinds and checks, the adaptation steps, the playbook and its workflow |
| `FORMAT.md` | this page: what the format is and how each step is done right |
| `LEARNINGS.md` | one entry per run, each with the home its fix went to |
| `series_check.py` | checks a series ledger (L1 to L8); `tests/test_series_check.py` |

## What it is

Three or more ads that run as one story. Each ad is a full ad in its own production format (`narrator-montage`, `single-presenter`, ...) with its own hook, proof and ask. The series adds two things on top: an **arc card** that gives each ad one task, and a **ledger** that carries the card, the product, the cast and the open promises from one ad to the next.

- A series is not a longer ad. Every ad must work for a viewer who never saw the others.
- It is not a set of variants. Variants test one ad's hook or format; a series tells one story across ads that run in order or to the same audience (retargeting).

## Inputs

- One accepted brief (writing station) to be ad 1, or a long source to adapt (step Adapt).
- The brand's product file, offer and guarantee files, and language bank (`brands/<brand>/`), for the rules ledger.

## Steps

1. **Arc.** Fill the arc card below. Ad 1 is usually the accepted brief as it stands.
2. **Ledger.** Write `ledger.json` (shape below). Every carried item, person and rule names its source file. Run `python3 components/video-production/formats/ad-series/series_check.py ledger.json`; fix every FAIL before any ad is written.
3. **Write each ad** through the writing station, ad by ad. Before ad N: read the ledger's hot rows (the last 3 ads, open setups). After ad N: update the ledger and rerun the check.
   A creator brief for ad N is built with `components/briefs/creator-brief/build.py inputs ... --ledger ledger.json --ad N`; its header takes the ledger's ask for ad N word for word, as filed, and raises nothing about it. Name the finished draft on the arc row (`creator_brief`) so L7 holds it to the same ask.
4. **Produce** each ad through its own format's workflow.
5. **Learn.** Each lesson into `learned.md` with its home from `LEARNINGS.md`.

## The arc card (first three ads)

| Ad | Task | Must | Banned |
|---|---|---|---|
| 1 | The loss and the stance | the viewer knows who to back and what is at stake; the lead takes a clear stance or action | background with no conflict; the lead hit with nothing said or done back |
| 2 | The evidence, replayed | new information: at least one new proof item or demonstration; the recurring object again in close-up; the pressure goes up | ad 1's lines repeated; no new information |
| 3 | The stakes go public | the clash moves from private to public, money or relationship level; the strongest proof and the strongest offer sit here | ad 3 still setting up |

Across all three:
- One or two recurring objects in every ad (a card, the product, a screenshot). The feeling lands on the object, not on a claim. Shoot or cut a close-up of it in each ad.
- One doubter who says the hard thing for the viewer; the lead stays calm.
- Each ad ends on a contrast line or the ask, never on an open question.

Length curve, picked by cost and the story (source sample lengths in seconds):

| Curve | Shape | Fits |
|---|---|---|
| descending | ad 1 longest, each next one shorter and denser (86 · 72 · 58) | one place, owned footage, rising pressure |
| fluctuating | set-up ads long, push ads short (82 · 115 · 69) | many places, a softer story |
| v-shaped | ad 1 all in, ad 2 short, ad 3 back up (89 · 47 · 82) | a comeback or glow-up |
| micro | ad 1 sets the rules, then short one-point ads (76 · 40 · 41) | a long run of single points |

Self-check after writing the three:
1. Does ad 1 set both the loss and the lead's stance?
2. Does ad 2 bring new information instead of repeating ad 1?
3. Does ad 3 move the stakes to public, money or relationship?
4. Is the same recurring object in all three, with a close-up in each?
5. Is there a doubter, and does the lead stay calm?
6. Does each ad end on a contrast line or the ask, not a question?
7. Does the length curve fit the footage and the story?

## The tap: where the ask goes

In a paid series the pay point is the ask. Paid traffic moves it forward: every ad carries an ask, and the strongest offer sits on ad 3, not later.

- Build the pressure in the ad before the strongest ask: the doubt said out loud, the cost of doing nothing.
- Put the ask at the peak: straight after the proof answers the doubt. Never after the energy has dropped.
- The next ad pays off what the last one promised in its first seconds. No bait and switch.
- The offer is what the brand's guarantee file and the run's rulings carry, as written. An offer that is not on file (a store credit, a gift) is never added to any ad.

## The ledger

The single source of truth for the series. When a script and the ledger disagree, settle which one changes before writing on.

- **The ask is used as filed.** Ad 1's ask is the brief's own ask line (its `ASK:` header). Every draft for an ad, a creator brief included, takes the ledger's ask for that ad word for word; nothing is raised about it.
- **A setup is dated to the ad whose brief first says it.** A doubt line ad 1's brief already says is planted 1, and paid 1 when ad 1 answers it. Name the filed brief on its arc row (`brief_file`) so L8 holds the dates to it.

| Kind | Tracks | Rule |
|---|---|---|
| `carried` | the card, the product, a prop: its source, its state, the ads it is in | the same real item in every ad; never redrawn or altered |
| `cast` | every person and voice: source, state (`in` / `out`), ads | a person marked `out` does not come back; a voice is one voice for the whole series |
| `setups` | a promise, question or claim planted in one ad and paid in a later one | paid by its due ad; overdue one ad later |
| `rules` | each sayable line or claim with its source file | an ad line cites its rule or bank row |
| `proof` | the main proof type of each ad | never the same type in two adjacent ads |

Proof types: `verdict` (a stranger's or customer's judgement), `before-after`, `demonstration`, `press`, `guarantee`, `customer-line`, `scarcity`.

`ledger.json` shape (all keys required; lists may be empty):

```json
{
 "series": "<brand>-<product>-<slug>",
 "brand": "<brand>", "product": "<product id>",
 "contract": "<one sentence: the feeling the whole series runs on>",
 "curve": "descending | fluctuating | v-shaped | micro",
 "current": 1,
 "arc": [{"ad": 1, "task": "the loss and the stance", "brief": "<path or label>", "ask": "<the ask line>",
          "creator_brief": "<optional: path to the creator brief draft for this ad>",
          "brief_file": "<optional: path to this ad's filed brief, for L8>"}],
 "carried": [{"id": "C1", "item": "", "source": "", "state": "", "ads": [1]}],
 "cast": [{"id": "P1", "who": "", "source": "", "state": "in", "ads": [1]},
          {"id": "P2", "who": "", "source": "", "state": "out", "out_after": 2, "ads": [2]}],
 "setups": [{"id": "F1", "setup": "", "planted": 1, "due": 2, "status": "planted", "paid": null}],
 "rules": [{"id": "R1", "rule": "", "source": "", "ads": [1]}],
 "proof": [{"ad": 1, "type": "verdict", "item": ""}]
}
```

`current` is the last ad written; the arc may plan ads past it. Checks (`series_check.py`): **L1** a setup still `planted` once `current` is past its due ad · **L2** a cast member marked `out` appears in a later ad · **L3** a carried item, person or rule with no source · **L4** the same main proof type in two adjacent ads · **L5** the arc lacks ad 1, 2 or 3, or an ad has no task · **L6** an ad in the arc has no ask · **L7** an arc row names a creator brief whose header Ask is not that ad's ask, word for word, or the file is missing · **L8** a setup whose words an ad's filed brief (`brief_file`) already says is planted in a later ad, or the brief file is missing.

## Adapt: a long source into a series

A long creator video, customer story, podcast or sales video becomes a series by its strongest line, never by shortening the whole thing.

1. **Extract** three tables: the moments (every turn, proof and reveal in order, function only), the functions (merge people who do the same job), and the one-sentence contract the source runs on.
2. **Cut** every side thread that does not touch the contract; fold its one needed fact into a line or a prop.
3. **Map**: one ad holds one pressure and one answer. The strongest moment goes on the ad with the strongest ask.
4. **First version**: the first third of the source plus its strongest moments. The rest waits for the next series.

Red lines: the lead's core want stays as it is. A source we do not own gives its structure and each line's function, never its words. Our own customers' and creators' filmed words are used as said, cited by row.

## Example: brief 5 "The brush your hands are missing" as ad 1 of a series (dry run, 2026-11-07)

Contract: hands only clean the surface; the brush reaches the rest. Curve: micro (a whiteboard explainer: ad 1 sets the rule, then short one-point ads). Recurring objects: the drawn fingertip (brief 5 PROPS: "same silhouette at pump and comparison") and FLEX.

| Ad | Task | What carries it (brief 5's own material) | Main proof | Ask |
|---|---|---|---|---|
| 1 | the loss and the stance | brief 5 as written: "Fingertips only clean the surface." → "Meet the FLEX." and the GQ line at S5 | press | "Tap below and get your FLEX now." |
| 2 | the evidence, replayed | opens on the drawn fingertip beside FLEX; answers ad 1's "Does it actually work?" with the brush at work: "ten sonic vibrations, up to twelve thousand RPM, plus it's waterproof." | demonstration | the same ask |
| 3 | the stakes go public | money level: "90 days. If your skin doesn't transform, full refund. You keep the FLEX." | guarantee | the same ask, on the guarantee |

Ad 3's offer is the guarantee's verbatim wording in `guarantees.json`.

## Sources

Built from short-drama-factory (MIT, commit `33d9988`): `references/continuity-ledger.md`, `templates/ledger.md`, `references/first-three-eps-beat-card.md`, `references/hongguo-beat-sheet.md` (paywall laws, paid-traffic front-loaded variant), `references/webnovel-adaptation.md`. Rules are adapted from series episodes to ads.
