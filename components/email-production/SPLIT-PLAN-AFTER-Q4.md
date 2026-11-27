# Email split: a plan for after Q4

**Status: parked.** the owner, 2026-10-26: "Let's not make any massive changes. Let's just put it in the repo as a future plan, like after Q4... right now I need to just focus on video ads and static ads." Nothing in this plan is started. Do not begin it before Q4 ends (January 2027), and not without the owner's go.

## Why it is parked
Email works today. Other sessions are producing Black Friday emails through these files. Video ads and static ads are the focus. The email chain is already documented as seven stages (`components/WORKFLOWS.md`) and explained in `HOW-EMAIL-DESIGN-WORKS.md`, so the team can use it as it is.

## The idea, in one line
Email writing is its own thing. It should not be called "email production", because production is a bundle of stages. The likely end state is separate components, one per stage, with `email-production` left as the thin glue that chains them for a whole month.

## Proposed components (names are a proposal, not a ruling)
| Component | Owns | Today it lives in |
|---|---|---|
| `email-writing` | the 13 copy stages (subject lines, body, blocks, facts check) | `email-production/email_line.py` and `prompts/stage*` |
| `email-design` | job card, layout, pictures, Klaviyo build, final check | `email-production/design/` |
| `email-upload` | the Klaviyo draft and its approval card | `email-production/klaviyo_upload.py`, `approve_klaviyo.py` |
| `email-production` | only the glue: run a month through the stages | `email-production/run_month.py` |
`marketing-calendar` (plan) and `email-review` (look and change) stay as they are.

## The collisions this fixes
1. Re-running design overwrites a person's edits in `design/email.json`.
2. Re-running copy rewrites every stage file, and then a design re-run wipes review edits again.
3. Two Klaviyo draft paths can make two different drafts for one email.
4. `run_month.py` always chains write and design; there is no way to run one alone.
5. One shared `run.json` is written by three stages.

## Order of work, when it starts
1. Add a copy-only entry point and `run_month.py --stages plan,write,design,check,upload` (default unchanged).
2. Make design refuse to overwrite `design/email.json` when a person has edited it.
3. Retire the older simple-layout push so there is one Klaviyo path.
4. Only then move the code into the separate components, one at a time, repointing readers in the same commit.
5. Skills follow the components: a skill carries its component's exact name.

## Already in place (documentation only)
The seven email stages, the skills `email-design` and `email-upload`, and the written explanation of how a design is chosen. No email code was changed.
