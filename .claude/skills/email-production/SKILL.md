---
name: email-production
description: Make the emails for a month's slots — an approved calendar month (or a few slot ids) goes in; the copy, the pictures, the layout and a Klaviyo DRAFT come out, each email in its own run folder. Never sends or schedules anything. Use whenever someone says "write the <brand> emails for <month>", "make the <brand> emails for this week", "build the <brand> email for slot nov-02", "what would each <brand> send be handed, no spend", "dry-run the <brand> email", "is <brand> wired for email", "put the <brand> emails in Klaviyo as drafts", "redo the <brand> emails from the subject-line stage".
---

# Email production

> **Activates component:** `components/email-production` — `run_month.py <calendar run>` writes each slot's copy, pictures and layout and, on `--push`, makes a Klaviyo draft; `email_line.py` + `simple_email.py` do one email.

External dependencies: `components/email-production/` (the engine; `prompts/` one per step, `formats.json` the email layouts, `CONTRACT.md`, `EMAIL-CHAIN.md`), `components/marketing-calendar/` (the month it reads), `components/marketing-chain-checks/` (the shared checks and hold), `components/image-production/` (makes the email pictures), `components/elements/` (email formats), `brands/<brand>/email-sms/` (the brand's look, types, affiliates; read-only), `runs/marketing-calendar/<brand>/<YYYY-MM>/` (the input), `runs/email-production/<brand>/` (the output).

**Never sends. Never schedules.** This skill stops at a Klaviyo DRAFT. A person approves the draft; the team never sends. Do not use `klaviyo_upload.py --send` (the component refuses it) and do not touch the scheduling step on the email approval page. If someone asks to send or schedule, say plainly that a person does that, and stop.

**Resume the requested station.** Follow `components/WORKFLOWS.md` → Activation and review cycle. If the copy already exists, inspect it and its checks before deciding any rewrite. A writing-only request uses `run_month.py --no-design --no-images` for the selected missing/explicitly requested items, without --push; proceed to design only after writing review and production authorization. Do not treat the combined default month runner as permission to skip the writing-review stop.

**Hand over to `email-review`** when the person wants to look at, change, or approve emails that already exist: "open my emails", "warmer light on nov-02 P1", "move it up", "use my picture". Make the emails here; review them there.

Where it sits: `marketing-calendar` plans the month's slots; **this skill writes each email's copy** (the writing stages); `email-design` lays it out; `email-review` is the look-and-change step; `stage-check` says whether it is done; `email-upload` puts it in Klaviyo as a draft; a person approves. The default `run_month.py` chains writing and design; select the writing-only controls above until the production station is authorized.

**The commands, free ones first.**

```
python3 components/email-production/doctor.py --brand <brand>                          # is the brand wired — free
python3 components/email-production/copy_plan.py runs/marketing-calendar/<brand>/<YYYY-MM> [--only <slot ids>]   # what each send would be handed — no spend
python3 components/email-production/email_line.py <source> --brand <brand> --avatar <avatar> --dry-run          # free check of one email, writes nothing
python3 components/email-production/run_month.py runs/marketing-calendar/<brand>/<YYYY-MM> --only <slot ids> --avatar <avatar>   # writes the emails (paid)
python3 components/email-production/run_month.py runs/marketing-calendar/<brand>/<YYYY-MM> --only <slot ids> --avatar <avatar> --push   # same, plus Klaviyo DRAFTS
python3 components/email-production/klaviyo_upload.py --run runs/email-production/<brand>/<label> --dry-run     # checks a finished email before any draft
```

Honest note: there is no `--dry-run` on `run_month.py` itself. The free forms are `doctor.py`, `copy_plan.py`, `email_line.py --dry-run` and `klaviyo_upload.py --dry-run`. Run those first, show the person one line each, and run `run_month.py` only when they say so. It spends on models and pictures, so keep `--only` to the slots they named. Without `--only`, it builds the whole month.

- `--brand` is always named; there is no default brand anywhere in the component.
- `--avatar <avatar>` builds only that avatar's version of each send (plus sends with no avatar).
- `--from-date YYYY-MM-DD` skips sends whose day has passed. `--limit N` is a pilot of the first N.
- `--no-images` stops pictures; `--no-design` stops at the copy; `--rerun-from <stage>` rewrites from that stage on, keeping the steps before it.
- `--push` makes the Klaviyo DRAFT, only when the person has asked for drafts. A draft goes to the send's own segment, never "all".
- Python 3.9: on a Mac use `/usr/bin/python3` if `python3` is not 3.9.

## What it reads

The month's folder under `runs/marketing-calendar/<brand>/<YYYY-MM>/` (`slots.json`, `run.json`, `review.json`) and the brand's files under `brands/<brand>/` (`email-sms/simple.json` the look, products, offer bank, avatar and language banks). Only slots the person approved in the calendar's review should be built; if a slot is not approved, say so and ask.

## The rules the component enforces — do not work around any of them

1. **The elements gate, before any spend.** A send's type must be a real email format (element library `format/email` or the brand's `email-sms/email-types.json`); otherwise `HELD at the elements gate` and nothing is spent.
2. **The delivery gate, before Klaviyo.** Every price in the email is one the offer bank sells today for that send's offer; the check step has no product-fact errors or typos; no `[UNFILLED …]` note remains; every link to the brand's own sites carries the email tracking tags. Any problem prints `HELD — not sent to Klaviyo:` with each problem, and nothing is pushed.
3. **A held email is not a failed one.** It waits on a person's ruling and exits 0. Only a failed run exits 1. Report held ones with their reason; do not rule on them yourself and do not rewrite a price (prices are fixed in the offer bank, never ruled).
4. **Every prompt is shown as sent,** written beside its step's output; a prompt changes by a new `-vN-` file, never an edit in place.
5. **No brand names in prompts; brand facts come from `brands/<brand>/`,** which this component never writes (`paths.refuse_brand_write`).
6. **Pictures start from the real product photo,** never a drawn product; the layout is one fixed shape or a named format.
7. **The old email's furniture never reaches the writer;** only its message does.
8. **Sends go to the brand's Engaged segments; no mass sends.** Do not widen a segment.
9. **Never sent from here.** `--send` is always refused, and approval and scheduling are a person's act, after every check is re-run.

## What cannot be done from one command by a person

Each email is made by a script that needs the brand's keys on this machine; if one is missing, say which capability is missing and stop. Do not paste or open a key. Approving a draft and scheduling it are a person's acts and are not part of this skill. A run `--push`ed into Klaviyo needs the brand's Klaviyo connection; this skill does not authenticate it.

## What comes back, and where it lands

- `runs/email-production/<brand>/<label>/` — one folder per email (labels like `<brand>-nov-01`, or `<brand>-nov-01--<avatar>`): one file per stage (`stage0--triage.md` … `stage9--brief.md`), `run.json` (what the email was told to argue, the model per step), `deliverable/` (`email.json`, `preview.html`, `check.json`, and `pushed.json` once a draft exists), and `klaviyo/` (the approval card).
- `runs/email-production/<brand>/_klaviyo-drafts/` — the draft as made, one `.html` per draft campaign.
- Pictures: Drive `Shared Assets/runs/email-production/<brand>/<label>/`, or the run's `media/` folder if the Drive was unreachable (the command prints why).

Report: how many built, held (with each reason in one line), failed, and how many drafts exist. Say plainly that nothing was sent or scheduled and that a person approves each draft. Show `deliverable/preview.html` for one email so the person can look at it, then offer `email-review`.

Reply with the result and the folder it landed in (repo path or Drive folder name).
