---
name: brand-research
description: The research system for any brand, run the same way every time — connect the brand's own customer words (surveys, support inbox, store reviews, ad comments, interviews) and build its stage-by-stage feedback forms, keep them pulling daily, then fill each avatar in order (language bank, rooms, profile, what he watches, his problem, the matrix) until the owner picks concepts, and refresh what goes stale. Use when someone says "set up research for <brand>", "connect <brand>'s reviews / surveys / support / ad comments", "set up feedback forms for <brand>", "what does <brand> need to give us for research", "run the research for <brand>", "where is <brand>'s research", "what's next for <avatar>", "refresh <brand>'s research", or "research is stale".
---

# Brand research

> **Activates component:** `components/research-fill` (`fill.py` where it stands, `connect.py` the connections), which
> hands each step to its owner: `components/research-gatherer`, `components/language-layer`, `components/profiles`
> through `creative-strategist/machine/who.py`, and `components/swipe-organic` (research rounds, the matrix).

One process for every brand. The steps and their order live in `components/research-fill/process.json`; never
skip one or change the order here. Talk in plain words and run every command yourself.

## 1. Where it stands (free, always first)

```
python3 components/research-fill/fill.py access --brand <b>
python3 components/research-fill/fill.py status --brand <b>
```

Tell them in one line each: how many own-words sources are connected, and per avatar "N of 9 done".

## 2. Connect what the brand has (one source at a time)

For each ✗ in `access`, ask the one question, then connect it. Every connect writes the brand's own config and runs
that source's dry run on the spot; tell them ✓ it pulls (with the count) or ✗ and why.

| Source | Ask | Connect |
|---|---|---|
| Store reviews | "Junip or Judge.me? (and the shop domain for Judge.me)" | `connect.py reviews --brand <b> --platform judgeme --key <KEY_NAME> --shop-domain <d>` |
| Surveys | "Paste the link to each survey's response sheet, and say if it's buyers, refunds or leads." | `connect.py surveys --brand <b> --sheet <id> --name "<name>" --relationship ordered` |
| Support inbox | "Which helpdesk do you use?" (Gorgias is read today) | `connect.py helpdesk --brand <b> --helpdesk gorgias` |
| Ad comments | "What's your Meta ad account id?" | `connect.py ad-comments --brand <b> --meta-account act_<id>` |
| Interviews | "Do you record customer calls?" | `connect.py interviews --brand <b> --speaker "<your people's names>"` (then drop transcripts in the inbox it makes) |
| Feedback forms | "Do you collect feedback in Klaviyo?" | `connect.py feedback --brand <b> --key <KEY_NAME>` |

- Keys: only the key's NAME goes in a command. The value goes in `.env` through the setup page
  (`python3 components/onboarding/serve.py`); never in chat. Before a key-backed connect, check it with
  `python3 components/keys/loader.py <NAME>` (prints set or missing).
- A survey sheet must be shared with the Drive service account (`GDRIVE_SA_KEY`); say so with the sheet link.
- The scraping account (`APIFY_TOKEN`, their own) is required for steps 4–7.

Keeping it pulling is the brand's choice, because labelling new rows every day uses paid model calls on its own
account. The daily switch is **off** by default. Turn it on only when the brand says so:
`python3 components/research-fill/connect.py daily-on --brand <b>` (and `daily-off`). The 05:30 job runs only
brands switched on; install it once per computer with `connect.py schedule`. Without the switch, pull by hand
when needed: `connect.py daily --brand <b>`.

## Feedback forms (once the brand's email platform is connected)

Every brand gets the eight-stage feedback forms (on the list · started checkout · first order · repeat · subscriber ·
refunded · cancelled · after support). The starter set is in `brands/_TEMPLATE/operations/feedback-stages.json` and
`feedback-questions.json`; the engine is `components/feedback-forms`.

1. Copy both files into `brands/<b>/operations/`. Set `klaviyo.public_id` (the brand's PUBLIC Klaviyo id, safe on a
   page), `form.url` / `form.link` (where the form will live on their store) and mark any stage their stack can't
   trigger as blocked, saying why.
2. Words: `python3 components/feedback-forms/language_pass.py --brand <b> --write` proposes every question, tap
   option and email from the brand's own customer words; show it, apply on the owner's yes.
3. Look: set `look.tokens`, fonts and logo from the brand's design system.
4. `python3 components/feedback-forms/build.py check --brand <b>`, then `preview` (nothing sends) and show the
   forms; `install` writes the per-stage flow sheet.
5. Answers come back with `connect.py feedback --brand <b> --key <KLAVIYO_PRIVATE_KEY_NAME>`.

Putting the form on the store, building the flows in Klaviyo and designing each stage's email are separate steps,
each the owner's go: nothing goes live or sends from here.

## 3. Fill each avatar, in order

```
python3 components/research-fill/fill.py next --brand <b> --avatar <a>
```

Run the step it names, by its own skill: the bank fills from the daily pull; rooms and the profile through
`avatar-profile`; what he watches and his problem through `research-round`; the matrix through `research-round`
step 7. Then `next` again, until it says the owner picks.

- **Money:** steps 4–7 show the price first. Show it, stop, and wait for the owner's go. Never run a paid pull
  without it.
- **Names:** a new avatar or sub-avatar name is the owner's to sign (`people.py check`). Ask; don't sign.
- **Picks:** writing starts only on the owner's picks from the matrix.

## 4. Keep it fresh

Ask `fill.py status` at the start of any research or writing work on a brand. A ↻ means the newest round or matrix
is older than 30 days: re-run that round (same searches, a new label) and rebuild the matrix, price first. Own words
refresh daily on their own.

## Rules

- Their accounts, their keys, their spend. Never use another brand's.
- Nothing is typed in by hand that a tool fills: rooms are found, profiles are built, lines keep their links.
- Brand data stays in `brands/<b>/` (git ignores it). Never commit it or paste it elsewhere.
