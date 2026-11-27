# marketing-calendar — what runs, when, and why

**marketing-calendar** — takes **a brand and a month**, makes **the month's
sends: dates, audiences, arguments, offers**. Does not **write the emails**.
Triggered by `python3 machine/marketing_calendar.py <month> --brand <brand>`.

**Owner:** the owner · **Station:** `components/` — moved in 2026-09-19

Runs by: person — the planner is run by hand, monthly; the mini reaches a month only through email-production's lab_entry.py, which reads the committed month (2026-10-08, B4a (decide-now cards) card 3, R-person-or-mini: the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:49:43Z: "3 yes, 4 yes,5 yes, 6 yes"; the owner told after).

> **Where this lives, and why.** Built as a component on 2026-09-13, moved back
> to `lab/the owner/` the same day to be perfected, and moved here for good on
> 2026-09-19 on the owner's word: *"move these tools out of the lab… straight into
> the real production repo, components… so we can actually run QC on it as
> well… and everybody can have access to these things."* Settled by system review
> (the 2026-09-21 ruling: a move is the owner's act and a review follows it;
> marketing-calendar#11). Every path it uses is FOUND rather
> than counted, which is why the move cost nothing.
>
> **Stage one of the email line.** Brand record → calendar → review → hand-off
> is the planning side; `components/email-production/` is stage two, the writing
> and the pictures, and reads what this component hands it.

The first station of the creative line. It takes a brand's own record and
produces a month: every send placed at a real date, typed, carrying an offer
or explicitly carrying none, with the reason it was chosen written beside it.
Then a human reads that month on a board, corrects it, and hands the approved
sends to whatever writes them.

## Why it is its own thing and not part of the email machine

It planned email because email is what was built first. Nothing in layers 1,
2, 4 or 9 is about email — a holiday lands on the same date for a static ad,
a cultural moment has the same window, and spacing is spacing. Split out
2026-09-13 on the owner's word: *"that counter … is also going to be relevant for
our ads as well, that's why it needs to be a separate component, not just in
the email flow alone."*

What makes a month an EMAIL month is the type catalogue it is typed against
and the hand-off that writes it — both of which are configuration, not code.
An ads lane is a catalogue plus a `handoff.json` entry, not a second engine.

## Graduation checklist (components rule: four questions, answered once)

- **Engine + owner** — `machine/`, the owner. Nine layers declared in
  `machine/chain.py`; seven are code-only and free to re-run.
- **Definitions + curator** — `prompts/` (the two AI stages) and
  `definitions/send-types.seed.json` (the starter type catalogue a brand
  copies and then owns). the owner curates both. Every entry of the seed's types, forms, modifiers and treatments carries a components rule 6 `status` (seeded `draft` 2026-10-07, SI-75 (send-types status)); the owner flips the ones he blesses to `approved`. A brand's own catalogue always
  wins over the seed.
- **The plane it emits** — `platform/data/records/calendar-run/`, one record
  per planned month, filed by `machine/records.py`. Pointers and counts only.
- **What the manifest declares per entry** — see
  `platform/data/kinds/calendar-run.json`: brand, month, slot count, breaks,
  warnings, where the human got to in review, and which prompt version
  planned it.

## Rules for this folder

1. **The prompt is the product.** Both AI layers write the prompt *as
   actually sent* beside its output, and `run.json` stamps the file's sha.
   A month whose prompt version cannot be named is not reproducible.
2. **Brand-agnostic (workspace rule 7).** No brand name drives behaviour in
   this folder's code or prompts (a history comment may name one). Every fact — segments, moments, offers, avatars, learnings —
   resolves through `brands/<brand>/`, read-only, per rule-9 (brand home).
3. **The planner never writes the human's layer.** `slots.json` is the
   machine's record; `review.json` is the person's. Re-planning a month
   must never quietly re-approve it, and a reviewer's rewrite must never
   be lost to a re-run.
4. **Nothing here writes copy.** If this folder ever grows a sentence meant
   for a customer, the split has failed.
5. **The hand-off is configuration.** `handoff.json` names what turns
   approved slots into finished work. Never hardcode a downstream tool.
6. **Every write goes under `--out`.** No machine assumptions, credentials
   from the environment — the rule components hold to, met here already.
7. **Paths are found, never counted.** No `parents[N]` may point at another
   folder. This tool has moved twice in a day; each move broke a counted
   path silently, because a wrong path only means a file "isn't there".

## The layers

Each is dated before the next is laid on it — the owner, 2026-09-02, *"ground up
the calendar fundamentally"*. Seven are code and cost nothing to re-run.

**The chain is declared in `machine/chain.py` and nowhere else.** This table is
printed from it (`python3 machine/chain.py`), the run record is written through
it, and the board draws it from the same list — so the sequence cannot say one
thing here and another in the code.

| | Layer | Who | What |
|---|---|---|---|
| 1 | The holidays | code | The public holidays that land in this month, at their real dates. Calendar facts — the same for every brand. |
| 2 | The brand's moments | code | The brand's own cultural moments, each resolved to a real date from its anchor. A moment falling outside the month belongs to the month it falls in. |
| 3 | Who is live | **AI** | Which segments and avatars are in play this month and which rest. No counts, no ceiling, no floor — every why cites the record. |
| 4 | Pinned to the date | code | Every dated holiday and moment PINNED to the month at its real date, as one send to each live segment it fits. A retail holiday becomes a full arc — a build-up scaled by what it earned before, the ask, the close. (Named 'the anchors' until 2026-09-14, which collided with a moment's own `anchor` field — that is the rule for FINDING a date, this is the act of putting sends on one.) |
| 5 | The concepts | **AI** | The rest of the month, in order: an offer for every anchored ask, then the concepts the month makes timely, then education and the other categories. |
| 6 | Typed | code | Every send typed against the brand's own catalogue; any offer-carrying ask completed into its full arc. A type the catalogue does not know is dropped, never invented around. |
| 7 | Offers checked | code | Every offer checked against the brand's offer bank — the only place an offer may come from. An offer no variant can carry is stripped; an arc left with no offer collapses to its holiday send. |
| 8 | The affiliate floor | code | One affiliate partner a week, every week, if the brand has any on file. |
| 9 | The order | code | Dates resolved around the anchors, then hours, sources and links. One send a day. No send budget exists — the only thing ever refused is an exact duplicate. |

`--from-anchors` re-runs 4–9 from disk, `--reorder` just 9 and the board.
Neither spends anything, except one call when a holiday fill send has no angle yet (below).

**Holiday fill angles (2026-11-06, the email lead).** Layer 4's holiday-period extra sends (2-3 a day) are made
before any angle exists, so they all carried the first arc send's angle: December 2026 Brand A had 43
sends to six segments with the Lead cell's "never had a routine" argument, VIPs included. In layer 9,
`machine/fill_angles.py` gives each its own angle in one model call (`prompts/cal9-fill-angles-vN-the email lead.md`,
the `designs` tier), true for every segment the send reaches, held to the product files
(`brands/<brand>/products/`) and the order-by table (`operations/shipping.md`). Answers are cached in
`9-order/fill-angles/angles.json` by prompt version and slot, so a replay spends nothing. One angle per
send, not per variant: no email is added. The count of sends is unchanged (the owner's 2-3/day rule).

## Two words that are not the same word

**A moment's `anchor`** is the RULE that turns it into a real date — a
public-holiday key, a fixed window, a window with a peak, one real `date`
(a game day, a finale, a parade: one cultural send on the day, never sold;
added 2026-10-13 so NBA/NFL and her TV moments reach the queue), `any`, or `live`.
A culture moment's email sits on its day or the day before; only a sale warms up
for days ahead (2026-10-13). It lives on the moment, in the brand's file.

**Layer 4** is the ACT of putting sends on those dates. It was called "the
anchors" until 2026-09-14, which made the two indistinguishable in
conversation; it is "Pinned to the date" now.

So: layer 2 asks every moment *when are you?* (that is the anchor answering),
and layer 4 says *then a send goes there, and here is how many.*

## Where a send's FORMAT comes from

A send is written off a real email whose structure it borrows. Layer 9 picks
one per slot: the newest of the same type from the brand's own classified
sends, else the same category.

**A brand that has never sent anything has no formats of its own**, and its
whole month comes out unfilled. That is what
`brands/<brand>/email-sms/format-sources.json` is for — a brand may declare that it
borrows shapes from another brand, with who approved it and why. **No brand is
named in this folder**; borrowing is a per-brand decision, written down in that
brand's own file, and empty by default. A borrowed slot carries
`source_brand`, so the send stays this brand's while the shape comes from
somewhere else.

## Design or letter (2026-10-17)

Layer 9 also marks every send `kind` (design | letter), `format` (the email's section stack, from
email-production's `formats.json`) and `kind_why`, by `machine/kinds.py` from
`definitions/email-kinds.json`; a brand's own `brands/<brand>/email-sms/email-kinds.json` adds its
exceptions (`letter`, `design`, `by_weekday`). A person's call on the board (`kind_set_by`) is never
overwritten. Free re-run for a two-week window:
`python3 machine/kinds.py <brand> <YYYY-MM> --from <date> --days 14`.

## A promotion's calls (2026-11-03)

A promotion is planned once, in the files that already hold it; the month reads each call from there.

- **The offer bank, both shapes.** In a flat bank a `### ` section counts as an offer exactly as a `## ` one
  does — when its section says what it costs — and every section ends at the next heading of either depth.
  `brandrecord.render_offers` and `offer_bank()` read through that one rule. A ruled funnel offer or a dated
  promotion kept under the generated products is an offer the month can carry.
- **`offer` on a moment** (`strategy/moments.json`) rides on every offer-carrying send of that moment's arc —
  the ask, the close and the holiday-period sends — in place of the concepts stage's pick. Layer 7 still checks
  it against the bank and strips it if the bank has no such offer.
- **`early-access` on a sale moment** places one `early-access` send to the brand's VIP segment (by name in
  `email-sms/audience-matrix.json`) the day(s) before the arc's first offer-carrying send — the value is how
  many days (`true` is one). It is a member of that arc (same `arc`, same offer) and goes when the arc loses
  its offer. It is placed only when the VIP segment is live this month (the cells stage's call); otherwise
  `4-anchors/anchors.md` says so under "Early access, not placed".
- **Order-by dates.** A sale moment's `last-chance` sits on the brand's order-by date when that record covers the moment's peak (its arrive-by date in the three days up to it),
  read from the order-by table in `operations/shipping.md` (`brandrecord.order_by_dates`), and carries
  `order_by`; the ask moves ahead of it when it would fall after. A brand with no table keeps the arc as it was.
- **Arcs, in a holiday period** (2026-11-03). Every send of a sale arc carries `arc` (its ask's anchor
  id) — build-ups, the ask, the holiday-period sends, early access and the close. The promotional-arc check
  reads that link: an offer-carrying ask inside an arc has the arc's warm-up before it and its close after
  it, to the same segment. On and after the close's day the period's extra sends are only ones that do not
  ask, and each takes its well and role from the catalogue.
- **A sale's window** reaches back over its go-live lead (`holiday-cadence.json` `lead_days`) as well as
  its run-up, so its build-ups sit inside it; and a send on a dated moment whose days are full is dropped,
  never moved outside its window (any length of window, not only one or two days).
- **What a type needs** (`fill_needs`, layer 9): a product from the send's offer when it is a product, else
  its arc's offer, else the front-end product of its lane (`_hero: paid` in the offer bank); an offer from
  its product when that is an offer. A need the record cannot answer stays a Break.
- **SMS is a channel of the month** (2026-11-03). Every slot carries `channel` (`email` unless said). The
  SMS of a month are planned by `definitions/sms-cadence.json` (team-wide, beside holiday-cadence): a sale
  arc gets an SMS twin on each beat it lists — early access, the open, the moment's own day, the close —
  same day, audience, moment and offer, at the cadence's hour outside quiet hours, at most `daily_cap` a day
  to a segment, SMS-consented members only; a content moment only when the cadence names it. An SMS slot
  carries `sms_beat`, `audience_rule` and `kind: sms`, never merges with its email twin, and is written by
  email-production's `sms.py`, never by the email line. The brand's platform is its own record
  (`operations/brand.json` `sms_platform`); the plan is the same whatever it is.
  An SMS is always the companion of an email (2026-11-04): it `follows` the email of its beat (the email
  names it in `then` when it names nothing else), the month check breaks a text that does not, and its
  `sms_job` is the cadence's — reminder, engagement, or a reply ask only where the brand's record names
  its reply keyword. Texts are numbered after every email, so planning them never moves an email's id.
- **What a sale leads with** (2026-11-04). Every offer-carrying send of a sale arc names its `product`: the
  offer when it is a product, else the first product of the brand's own `storefront-order` note (bold product
  keys, in order; `brandrecord.lead_products`). `storefront-order` is a note, never an offer, whatever it names.
  A funnel-only line (one the bank marks for the funnel alone) never reaches an email or a text: both price
  checks take prices only from the send's own offer section.
- **The brand's mix** (2026-11-04, `brandrecord.storefront_mix`). A brand's `storefront-order` note may
  declare a lead mix (a line saying lead sends mix …) and a set's singles (a line naming a set's sends with
  the option to buy … on its own). A promo arc's lead emails then carry `offer_mix` — the mix, together, to
  every audience: inside a promo the one-lane-per-offer rule yields to it — and a set's emails carry the set
  and its singles. A text keeps its one offer. email-production carries the mix (`--offer-also`) and its
  price check takes each member's own prices, never a line the bank keeps off email.
- **Every week sells something** (2026-11-04, `weekly_standing_offer`): a week ahead with no offer gets the brand's
  standing offer (`brandrecord.standing_offer`: its storefront-order lead mix or first product, else its `paid-funnel`, else its one hero)
  on one email. **A past date never counts as a break.** **A sale is one argument:** sale, code-pinned and SMS sends are
  not counted by the same-argument check, only sends the concepts stage wrote an argument for. **The moment's
  `early-access` wins over the month's live cells** for that one send. Sale sends carry `deadline` (the arc's close).
- **When a moment ends** — `moment_window(brand, key, on)` (CONTRACT.md, library surface 4) — is how another
  tool reads a moment's dates from the same file, never from a list of its own.

## Gates

The words are `components/marketing-chain-checks`' own: a **check** reports, a **gate**
is a fixed point where checks run, a **review** is a person's verdict.

**Here a gate is RECORDED and never raised.** Everywhere else `hold()` stops
failing work. The calendar's rule is *"adoption stays a human act"* — so a month
that fails a gate is still written and still drawn, `check.json` says `HELD`
with the problems, and a person decides. **The review board is the Review**
(`machine/serve.py`, `review.json`): approve · needs work · cut, per send.
Nothing downstream writes a send the board has not approved.

| Gate | When | What it checks | If it fails |
|---|---|---|---|
| **inputs** | before any model runs | `chain.readiness(brand)` — every file each layer needs. A degraded layer passes, with a note saying what the month loses | blocked → `HELD`, and the run stops as it always has |
| **elements** | after layer 6, and on the finished slots | every send's `type` is an email format: in the element library (`components/elements`, `format/email`) **or** the brand's own `email-sms/email-types.json` | in neither → a **Break** in `checks.md` naming the real ids, and `HELD` |
| **the month's checks** | after layer 9 | `checks.md` — Breaks (spacing, warm-ups, offers the bank lacks, dead angles, the commercial floor, two sends one argument) vs Warnings | Breaks are listed on the board above the sends; the person fixes or cuts |
| **Review** | the board | a person | an unapproved send is never handed off |

`check.json` sits at the month's root beside `checks.md`, in `hold()`'s shape:
`{gate: {result: pass|HELD, problems: [], notes: []}}`. `run.json` carries
`gates` (the two results) and `elements` (every type the month used, where it
was found, and how many sends carry it). The code is `machine/gates.py`.

## Which model thinks

Both thinking layers (3 and 5) are the run kit's **`designs`** tier
(`components/run-kit/run_kit/model.py`) — they make calls nobody wrote down.
`--model <name>` forces one model onto both, as it always did. Out of usage is
not a broken layer: the run stops with one line, retries nothing, and everything
already written stays on disk — run the same command again when usage is back.

## Where a month is filed

The working month lives at the repo's one home for run records,
`runs/marketing-calendar/<brand>/<YYYY-MM>/` (`machine/paths.py` `month_dir()`;
moved out of this folder 2026-10-07, SI-22 (calendar months home), K2 (brands
write wall)): `run.json`, `slots.json`, `review.json`, `checks.md`,
`check.json`, every layer's output and prompt-as-sent. The board and
`components/email-production` read it there; a legacy
`runs/calendar-<month>[-<brand>]/` path still resolves for reading. Never the
board's HTML in git, nothing over 1 MB. A month written with `--out` somewhere
else stays where it was written.

## Running it

    python3 machine/marketing_calendar.py 2026-11 --brand <brand> --dry-run   # free: is everything there?
    python3 machine/chain.py --check <brand>        # can this brand run it?
    python3 machine/moments_mine.py --brand <brand> # what the record proves
    python3 machine/moments_apply.py --brand <brand> --write   # a PROPOSAL under runs/marketing-calendar/<brand>/moments-<date>/; a person commits it
    python3 machine/marketing_calendar.py 2026-11 --brand <brand>
    python3 machine/serve.py                        # the review board
    python3 machine/records.py --all                # file the records

Full command surface and the shape of everything a run emits: `CONTRACT.md`.

## Who reads its output

- `components/email-production/` — `run_month.py` writes the copy for a month,
  and is what `handoff.json` points at today.
- The board itself, for the human step.

Both read the run folder, never this folder's internals.

**Regular SMS (2026-11-04):** cadence weekly rule starts 9 Nov: one regular companion per week plus promotional reminders. Prefer Tuesday and an existing email; the regular text is at least one hour after its email, within quiet hours, and never on an existing reminder day. A boundary week is owned by the month containing Tuesday. `machine/weekly_sms.py` updates saved slots without planning/model calls; see CONTRACT.md.

**Identity sources (4 Nov):** planner type input omits free-form catalogue notes and includes only the selected brand’s position/story for identity and origin. A catalogue example is not a founder credential. Final-month checks flag credential claims absent from those identity sources. Regression checks: machine/test_identity_sources.py; these are local checks, not model-output validation.
