# email-production — brand context in, campaign emails out


## Calendar handoff and local readiness

`calendar_handoff.py` owns reviewed slot identity, schedule and audience checks. `brief.py` carries its snapshot into writing; design, card building, upload and approval reuse it. A calendar-bound send never silently falls back to a design/brand send hour. Buyer assumptions for a lead audience and stale or ambiguous assignments hold before model/production work. Another released version with the same send/audience blocks a duplicate release.

Audit saved work without network, generation or rendering:

```sh
python3 reconcile_calendar.py --brand <brand> --month YYYY-MM --from-date YYYY-MM-DD
python3 reconcile_calendar.py --brand <brand> --month YYYY-MM --from-date YYYY-MM-DD --write
```

`--write` reconciles local unreleased card metadata, retains the original in `klaviyo/calendar-handoff-before.json`, and writes a report under `runs/email-production/<brand>/calendar-handoff-YYYY-MM/`. Approved/platform card fields stay frozen; divergence is reported for a separate explicit platform action. Reports separate saved copy review, holds and existing platform work. A passing saved alternative subject can be offered for copy review without selecting it or generating a replacement; saved fact holds remain unresolved until reconciled. No report is visual or launch approval. Tests: `python3 test_calendar_handoff.py`.

> **Current as of 2026-09-20: read `CLAUDE.md` first** — it has what this tool
> takes and makes, how to run it, the free dry run and the checks that hold an
> email back from Klaviyo. What follows below is the 2026-08-27 starting note,
> kept as history; its paths and counts are from then. Every command here now
> needs `--brand <brand>` — there is no default brand. Tests:
> `python3 test_rollout.py` (free — no model, no network).

The fourth lane of the content machine, beside `copy`, `image-teardown` and
`swipe`. **Campaigns only** — delivery, feedback and flows are parked in
`PARKED.md`, not dropped.

Three steps: **read the brand → build a dynamic calendar from it → produce the
email.**

## Where things are

| | |
|---|---|
| Brand context | `../brands/Brand A/` — read-only, never written to |
| Email swipes | `../brands/Brand A/existing-content/emails/` — **empty** |
| Variable map | `brand-maps/Brand A.md` |
| The chain | `prompts/` — one file per stage, highest `-vN-` wins |
| The runner | `email_line.py` |
| The picture | `render.py` |
| Pulled facts | `calendar/` — `derive.py`, `ledger.py`, `brands/` |
| Types | `email-types.json` — 38 types across 5 categories |
| Rules | `DOCTRINE.md` |

## Running it

Check the wiring first — free, no model calls:

```
python3 email_line.py <source> --brand Brand A --avatar fed-up-king --dry-run
```

Then the chain:

```
python3 email_line.py <source> --brand Brand A --avatar fed-up-king \
  [--product <path>] [--subjects 5] [--label <name>]
python3 render.py results/<label>
```

**A run declares an avatar.** `fed-up-king`, `glow-up` or `gift-buyer` — three
different audiences, not one with variations. Every language bank, profile and
sub-avatar resolves through it.

## State, 2026-08-27

Wiring verified by dry run: 8 of 10 variables resolve, and the language layer
returns real rows (~8,100 characters of customer sentences for subject lines)
where it previously returned "this brand has no language bank".

Still missing, all called out by the runner at start-up: `sender-identity.md`,
a `products/` folder, and any cultural-moments source. **And there is no email
to swipe** — `existing-content/emails/` is an empty folder, so the chain has
never been run end to end.

## Things a session here must not do

- **Never write into the brand tree.** Read-only, always.
- **Never let the machine pick a subject line**, rank them, or mark one
  recommended. All of them ship.
- **Never improve VERSION 0.** It is the control.
- **Never invent a block type.** The vocabulary is in `render.py`.
- **Never reuse a stage number without retiring the old prompt** to
  `prompts/superseded/`.
- **Never pad a category.** A thin one is a finding to call out.
