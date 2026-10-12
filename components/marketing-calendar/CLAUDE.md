# marketing-calendar — what runs, when, and why

**marketing-calendar** — takes **a brand and a month**, makes **the month's
sends: dates, audiences, arguments, offers**. Does not **write the emails**.
Triggered by `python3 machine/calendar.py <month> --brand <brand>`.

**Owner:** the owner · **Station:** `components/` — moved in 2026-09-19

Runs by: person — the planner is run by hand, monthly; the mini reaches a month only through email-production's lab_entry.py, which reads the committed month (2026-10-08, B4a (decide-now cards) card 3, R-person-or-mini: the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:49:43Z: "3 yes, 4 yes,5 yes, 6 yes"; the owner told after).

> **Where this lives, and why.** Built as a component on 2026-09-13, moved back
> to `lab/` the same day to be perfected, and moved here for good on
> 2026-09-19 on the owner's word: *"move these tools out of the lab… straight into
> the real production repo, components… so we can actually run QC on it as
> well… and everybody can have access to these things."* Settled by system review
> (the 2026-09-21 ruling: a move is the owner's act and a review follows it;
> marketing-calendar#11). Every path it uses is FOUND rather
> than counted, which is why the move cost nothing.
>
> **Stage one of the email line.** Brand record → calendar → review → hand-off
> is the planning side; `tools/email-production/` is stage two, the writing
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
Neither spends anything.

## Two words that are not the same word

**A moment's `anchor`** is the RULE that turns it into a real date — a
public-holiday key, a fixed window, a window with a peak, `any`, or `live`.
It lives on the moment, in the brand's file.

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

## Gates

The words are `components/quality-checks`' own: a **check** reports, a **gate**
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
`tools/email-production` read it there; a legacy
`runs/calendar-<month>[-<brand>]/` path still resolves for reading. Never the
board's HTML in git, nothing over 1 MB. A month written with `--out` somewhere
else stays where it was written.

## Running it

    python3 machine/calendar.py 2026-11 --brand <brand> --dry-run   # free: is everything there?
    python3 machine/chain.py --check <brand>        # can this brand run it?
    python3 machine/moments_mine.py --brand <brand> # what the record proves
    python3 machine/moments_apply.py --brand <brand> --write   # a PROPOSAL under runs/marketing-calendar/<brand>/moments-<date>/; a person commits it
    python3 machine/calendar.py 2026-11 --brand <brand>
    python3 machine/serve.py                        # the review board
    python3 machine/records.py --all                # file the records

Full command surface and the shape of everything a run emits: `CONTRACT.md`.

## Who reads its output

- `tools/email-production/` — `run_month.py` writes the copy for a month,
  and is what `handoff.json` points at today.
- The board itself, for the human step.

Both read the run folder, never this folder's internals.
