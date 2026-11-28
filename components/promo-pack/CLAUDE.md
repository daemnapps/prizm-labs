# promo-pack — one offer change, one pack, every workflow follows

**promo-pack** — takes **a brand and a month that has a promo-calendar row in the brand's offer bank**, makes **one
pack per moment: the offer words for the owner to approve, the stock that blocks it, and one hand-off per workflow
the offer has to reach** (video, static, email, SMS, store promo, funnel offer), each with its workflow, role, brief
count and dates from the calendar. Does not **write, make, send, publish or spend**: each workflow does its own work
behind its own gates. Triggered by
`python3 components/promo-pack/machine/pack.py build --brand <brand> --month <YYYY-MM> [--stock <runway.json>]`.

Stage: **plan**, the stage between reading the numbers and feeding the workflows. Role: growth-strategist.

## The door and the skills inside it

| Say | Runs |
|---|---|
| "make the <moment> promo pack for <brand>" | `pack.py build --brand <brand> --month <YYYY-MM>` (the door; skill `.claude/skills/promo-pack/`) |
| "the offer words are approved" (the owner, only) | `pack.py approve --brand <brand> --moment <moment> --by <who> --said "<his words>"` |
| "hand the pack off" | `pack.py hand --brand <brand> --moment <moment> [--only static,video,sms]` |
| "where is the promo pack" | `pack.py status --brand <brand> --moment <moment>` |
| the month's calendar is planned (marketing-calendar runs it) | `pack.py tick --brand <brand> --month <YYYY-MM>`: builds every pack touching the month; once the words are approved, hands off and says `loaded` |

Skills inside the component, one job each: `skills/stock-check.md` (the stock read every pack needs) and
`skills/switch-list.md` (every place the old offer still lives).

## The gate

- **A call, the owner's:** approve the offer words. `approve` stores the words' fingerprint; `hand` refuses until
  an approval matches the pack's current words, and an approval goes stale the moment the bank's words change.
- **Going live, sending and spending stay calls inside each workflow.** `hand` runs only doors marked
  `spends: false` (`definitions/handoffs.json`); a door that spends is written into the hand-off for the role's
  holder to run under that workflow's own gates, except doors that only write drafts (email and text copy), which
  run when the owner's approval also says go on drafts (`approve --drafts`). A hand-off with no door is a gap and is listed on every pack.

## What it reads

- `brands/<brand>/products/offer-bank.md`: the `promo-calendar` row whose dates cover the month (no row, no pack:
  the offer change starts there), every line a section lets creative use **word for word**, each `- Funnel offer`
  bold line (funnel and its ads only). A line marked `(through <date>)` before the window, a line dated in another
  month, and the standing pop-up lines are dropped and listed.
- `runs/marketing-calendar/<brand>/<YYYY-MM>/slots.json`: the sends inside the window, their dates, offers,
  order-by date and the moment (`occasion` of the window's sale sends, unless `--moment` is given).
- email-production's `calendar_handoff.snapshot` per send (its own hand-off check), and what email-production has
  already written under `runs/email-production/<brand>/`: a funnel-only or retired line, or a selling send that never
  names its offer's free gift (`<offer> + Free <gift>` lines), is flagged.
- `runs/winners/<brand>/bank.json`: the top video and image winners by spend in their latest audit.
- A stock runway read given with `--stock` (rows: sku, name, available, backup, per_day, runs_out, reorder_by,
  status). Items the offer names or gives away that are `LATE`, `ORDER THIS WEEK` or run out inside the window are
  blockers for the brand-operator, on top of the pack.

## What it writes

`runs/promo-pack/<brand>/<moment>/`:
- `pack.json`: the contract (window, offer words and fingerprint, stock, hand-offs, gaps, approval).
- `PACK.md`: the same for people.
- `approval.json`: the owner's approval, only through `approve`.
- `handoffs/<id>/handoff.json`: what `hand` did per workflow (commands, runs, state);
  `handoffs/video/campaign-plan.md` is what ad-variations reads through `--plan`.
- `hand` also starts the statics sprint (`runs/ad-variations/<brand>/<moment>-<year>-promo-pack/sprint.json`) and
  fills its offer, moment, until and never from the approved words.

## The hand-offs and their doors

| Hand-off | Workflow | Role | Door | Run by `hand` |
|---|---|---|---|---|
| video | Winner variation workflow | video-editor | `ad-variations/machine/run.py plan <ad> --plan <campaign plan> --dry-run`, one per winner | yes |
| static | Winner variation workflow | graphic-designer | `ad-variations/machine/natural_statics.py start` | yes |
| email | Email campaign workflow | retention-strategist | `email-production/run_month.py <run> --only <unwritten sends>` | on the owner's go on drafts (`approve --drafts`) |
| sms | Email campaign workflow | retention-strategist | `email-production/sms.py <run> --only <unwritten sends>` | on the owner's go on drafts |
| store | Store promo workflow | page-builder | `storefront-promo-edit/machine/storefront_promo_edit.py plan` where that component is in the checkout | yes (read only) |
| funnel | Funnel offer workflow | page-builder | none | gap |

## Gaps (listed on every pack)

- Store promo workflow: `storefront-promo-edit` is not in the toolkit yet (the team workspace has it; the door is used where it exists).
- Funnel offer workflow: no funnel component has a door.
- Video: ad-variations has no lever for an offer ending alone; the ending goes to its planner as the campaign plan.
- Stock: `stock-runway` is not in the toolkit yet; its read is handed to the pack as a file.

Keys: none. Runs by: person or agent. Tests: `python3 -m unittest discover -s components/promo-pack/tests`.
