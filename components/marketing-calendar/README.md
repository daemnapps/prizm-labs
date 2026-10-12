# The marketing calendar

## How to use it → (team dashboard)

Give it a brand and a month. It gives back the month: every send at a real
date, what each one is, what it sells, and why it chose that. Then you read
it on a page, fix what's wrong, and press the button that writes the copy.

## The three commands

Check first, for free — is everything the month needs on file?

```bash
python3 machine/calendar.py 2026-11 --brand <brand> --dry-run
```

It spends nothing and writes nothing. It says whether the brand can run, shows
the holidays and moments it found, and lists every piece of the brand's record
each of the two thinking steps would be handed — OK, EMPTY or MISSING.

Plan a month:

```bash
python3 machine/calendar.py 2026-11 --brand <brand>
```

Open the board and review it:

```bash
python3 machine/serve.py
```

That opens `http://127.0.0.1:8788` on the newest month. Add
`--run calendar-2026-11-<brand>` for a particular one.

File the record so it shows on the platform:

```bash
python3 machine/records.py --all
```

## What the board is for

The month arrives as a calendar — the sends sitting on their real days, so
the spacing is visible at a glance rather than buried in a list. Under it,
one card per send.

On each card you can:

- **rewrite** the date, hour, segment, type, category, role, offer, product,
  what it's about, and **the angle** — the line the copy has to carry. The
  planner's original stays visible next to your change, so nothing is lost
  silently.
- **approve · needs work · cut**
- leave a **note for the writer** — what to fix, what to keep, what the copy
  must not say
- press **Write the copy**, for that one send or for everything approved

Above the sends: **Breaks** — rules the month violates and that should be
fixed before it runs — and **Warnings**, which a person should read but which
don't stop anything.

Your decisions live in `review.json` next to the month. Re-planning the month
never overwrites them, and the planner never re-approves anything on your
behalf.

## Re-running without spending anything

Five of the nine layers are plain code:

```bash
python3 machine/calendar.py 2026-11 --brand <brand> --from-anchors  # layers 4-9
python3 machine/calendar.py 2026-11 --brand <brand> --reorder       # layer 9 only
```

Use these after changing an offer bank, a rule, or how holidays are anchored.

## What stops a bad month

Two gates are written to `check.json` beside the month — **inputs** (is the
brand's record complete enough?) and **elements** (is every send's type a real
email format, in the element library or the brand's own catalogue?). Neither
one stops the month: a failed gate says `HELD`, shows up as a Break on the
board, and you decide. **The board is the review.**

A month lives in one place: `runs/marketing-calendar/<brand>/<month>/` at the
top of the repo, where the board and the email writer read it (SI-22 (calendar
months home), 2026-10-07).

Tests, no model, no network: `python3 machine/test_rollout.py`.

## The rest

- `CLAUDE.md` — what this owns, and the rules it holds to
- `CONTRACT.md` — exactly what a run emits, for anything reading it
- `handoff.json` — what "Write the copy" runs
- `prompts/` — the two stages that use a model, verbatim
- `definitions/send-types.seed.json` — the starter catalogue a new brand
  copies into its own folder and then owns
