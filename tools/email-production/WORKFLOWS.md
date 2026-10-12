# The workflows — five, each one command, run on an ongoing basis

Written 2026-09-09 on the owner's go ("turn this all into individual workflows
that can just be executed on an ongoing basis"). Brand-agnostic by design:
every command takes `--brand`, and the only place brand facts enter is
`brands/<brand>/` at the repo root (RULED 2026-09-09: the machine lives in the
repo; `paths.py` points there).

```
1 ONBOARD a brand  →  2 INTAKE its designs  →  3 BUILD a month  →  4 PRODUCE the emails  →  5 REVIEW & PUSH
   (once)               (once per board)        (monthly)           (monthly, per slot)      (per send, gated)
```

Every workflow is run by the session on the owner's behalf. He says what he
wants; the page at http://localhost:8785 shows the result.

## 1 · Onboard a brand — `python3 doctor.py --brand <brand>`

Walks the brand contract and reports OK / MISSING per row, then dry-runs the
composer inputs. Nothing is invented for a missing row; the row is the ask.

What a brand folder must hold for the machine to run (the contract):

| Row | File | Where it comes from |
|---|---|---|
| Plumbing | `email/machine.json` | store feed URL (or none), Klaviyo connector name, wordmark path |
| Cultural moments | `calendar/moments.json` | the brand's own moments per avatar, each anchored to a real date rule (holiday key · MM-DD window · any · live); holidays themselves come from the tool |
| Audience | `email/audience-matrix.json` + `email/segments.md` | the eight core segments; ids and counts from `pull/make_segments.py --brand` once Klaviyo is authorised |
| Types | `email/email-types.json` | the type catalogue, brand-owned (seeded from the tool's clean seed) |
| Offers | `products/offer-bank.md` | the ONLY source of an offer; founder-owned |
| Products | `products/<slug>/product.md` + `products/images.json` | from the store feed (`pull/products.py`, proposed under `runs/email-production/<brand>/facts-<YYYY-MM-DD>/` — a person folds it in) or the product files when there is no feed |
| Avatars | `core-avatars/language-index.json` + `objection-bank.md` | the language layer |
| Sender | `email/identity/sender.md` | the form decides the sender; a named person only when one is on file |
| Affiliates | `email/affiliates.json` | partner roster; empty list schedules nothing |
| History (fills over time) | `email/ledger.json`, `sends/`, `classified.json`, `performance.json`, `learnings.md` | `pull/` scripts against the brand's Klaviyo |
| Design | `email/design-formats/` | from workflow 2 |

State on 2026-09-09: **Brand B 19/19 rows connected. Brand A 10/19** — missing
the history rows (no Klaviyo access yet — connector `klaviyo-brand-a` needs
the owner to authorise it once), the design bank (workflow 2, waiting on the
Figma board), and the adopted calendar (workflow 3 writes it).

## 2 · Intake a brand's designs — `python3 sweep/fig_intake.py "<file>.fig" --brand <brand>`

The Figma file itself (File → Save local copy → `.fig`), dropped anywhere.
It is decoded locally: every page becomes a board, every email-sized frame
an artboard, every image fill an asset, and a reference picture is drawn per
artboard. Then the same engine as Brand B's bank: rebuild → checks →
pictures → contact sheets → QA page and team mirror, into
`results/format-bank-<brand>/`. Brand A's file went through on 2026-09-09:
122 emails, 115 clean on the first pass.

(`python3 sweep/intake.py <figma-html-export.zip> --brand <brand>` is the
same door for a Figma HTML export, the shape Brand B's bank arrived in.)

Figma board → format bank, the same door Brand B's 381 emails went through:
unpack → capture every artboard → the layout index (families, variants,
theme tags) → every export rebuilt as clean HTML on the brand's bedrock with
a replication spec per email → objective checks (copy, pictures, buttons,
order) → pictures, contact sheets, the QA page and the team mirror
(`brands/<brand>/email/design-formats/rebuild-qa.md`).

Hand the session the export (Figma → HTML export of the email board, as a
zip). The bedrock the rebuild renders on — wordmark, palette, faces,
modules — is read from `brands/<brand>/email/design-formats/components.json`;
the first intake of a brand writes a starter from the layouts it finds and
`identity/` (wordmark svg, `palette.md`), which the designer then tightens.

## 3 · Build a month — **`lab/marketing-calendar/`**

    python3 machine/calendar.py YYYY-MM --brand <brand> [--start-day N]
    python3 machine/serve.py                 # review it before any copy is written


Nine dated layers (see `WORKFLOW.md`): holidays → the brand's moments →
who is live (AI) → the anchors at their real dates, with build-ups scaled by
what each holiday earned before → concepts (AI) → the catalogue → offers
from the bank only → the weekly affiliate floor → the order. Then the review board: every rule checked, the month on its real
dates, and the fields a human may rewrite before a word of copy is written. `--start-day 14` starts production
mid-month (September 2026 runs from the 14th, RULED 2026-09-09).

Outputs: `results/calendar-YYYY-MM/` with `slots.json`, `checks.md`,
`briefs/`, and the nine layer folders — all visible on the page's calendar
tab. `--reorder` and `--from-anchors` re-run the mechanical layers without
spending on AI.

## 4 · Produce the emails — `caffeinate -i python3 run_month.py results/calendar-YYYY-MM`

One chain run per slot variant (the ten-stage chain, briefs → copy → build),
then `render_email.py` draws each on the brand's design system, and
`build_review.py` writes the month's review page (`review-YYYY-MM.html`).
Runs in the background; the page's runs tab shows every stage's output with
its prompt. Never sends anything.

## 5 · Brief in Figma — `python3 figma_brief.py results/<slot>` then the connector

**RULED 2026-09-09 (the owner), superseding the draft-building step below: the
machine does not design.** Per slot it writes `results/<slot>/figma-brief.js`
and `brief-for-design.md`; the session runs the code through the Figma
connector and the page "Briefs - YYYY-MM (machine)" gets, side by side, the
brief card (copy, subject, preview, date, segments, open facts, pictures) and
an untouched copy of the real reference email this one was written off — plus
that reference torn down into its framework with our copy injected slot by
slot. The reference is the email the chain actually swiped. Full account:
`DELIVERY.md`. Everything below is the retired draft-building step, kept as
the record.

## 5b · (retired) Draft in Figma — `python3 figma_draft.py results/<slot>`

RULED 2026-09-09 (the owner): the drafts are built directly in Figma from the
brand's existing templates; Eve tweaks them there and puts the finals into
Klaviyo herself. Per run, `figma_draft.py` picks the nearest template in the
brand's file (`design-formats/figma-templates.json`), writes
`results/<slot>/figma-draft.js`, and the session runs that code through the
Figma connector (`use_figma`, file key in `email/machine.json`). One frame
per run, named by slot, on the page "Drafts - YYYY-MM (machine)" (a SECTION
of that name on the `_ Approved` page in Brand B's file, whose plan caps
pages), with the copy typed in and a notes card beside it — subject,
preview, date, segments, open facts, pictures to place, and the font note
(the brand faces are not loadable by the connector; copy is typed in Inter
and restored by Eve in one action). `--record` stores the frame's link in
`results/<slot>/figma-draft.json`; the review page and the runs tab show it.
Details and limits: `DELIVERY.md`. The Klaviyo push (`push_klaviyo.py
--draft`) stays available but is not the line — Eve delivers from Figma.

## Doing it for the next brand (Brand A, 2026-09-09)

1. Workflow 1 ran: the folder is scaffolded (machine, moments starter,
   segments by rule, types, sender rule, affiliates, product images).
2. Workflow 2 ran from the `.fig` file (122 emails); the Figma file key is
   in `email/machine.json`; `design-formats/figma-templates.json` lists
   the campaign frames the drafts clone.
3. **No Klaviyo history yet → the send library comes from the designs:**
   `python3 pull/sends_from_bank.py --brand brand-a` (90 emails from the
   bank, dated from the frame names), `python3 pull/classify.py --brand
   brand-a` (tags them) — both PROPOSE under
   `runs/email-production/<brand>/facts-<YYYY-MM-DD>/` and a person folds
   them into the brand (K2 (brands write wall), SI-21 (email facts proposals)), then `python3 ../marketing-calendar/machine/calendar.py 2026-09 --brand brand-a
   --start-day 14 --reorder` finds a source per slot. Workflow 3 ran for
   Sep (from the 14th), Oct, Nov.
4. Workflow 4 runs with a `brand-a-` prefix on every run folder
   (`results/brand-a-sep-01`), so two brands never share a folder.
5. Workflow 5 follows the copy; the Brand A team's connector is not capped.
