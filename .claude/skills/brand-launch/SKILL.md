---
name: brand-launch
description: Launch a brand from zero with one trigger. A hunch goes in (one line, a product or ingredient and a market); the launch checklist runs start to end through the tools in this repo, and one page shows where it stands, including the steps this repo has no tool for yet. Use whenever someone says "launch a brand", "new brand from zero", "I have a hunch about <product>", "run the launch for <brand>", "start a new offer", "take <ingredient> from idea to ads", "where is <brand>'s launch", or "continue the launch".
---

# Brand launch: hunch in, brand out

> **Runs:** the checklist in `brands/_TEMPLATE/launch.json`, step by step, through the tool each step names.
> A brand that already sells uses `brand-activation` instead.

Only what is in this repo runs. Every step names its tool. A step marked `gap` has no tool here: do not do it by hand,
do not fill it from general knowledge, do not invent its how-to. Show it on the page as a gap, so the tool gets built
and added to `launch.json`.

## 1. Start

- Ask for one line if it wasn't given: the product or ingredient, and the market. That line is the hunch. Nothing else
  of the owner's goes in; research steps read only that line.
- The brand's home is a private offer workspace (`components/offer-workspaces`): its own repo, holding `brands/<brand>/`,
  `offers/` and `runs/`, with Prizm pinned inside it, never the other way round. Creating the repo is the owner's click.
- Copy `launch.json` into the brand's home and keep progress in `launch-progress.json` (`done`, `skipped`).
- "Continue the launch": start at the first step not in `done` or `skipped`.

## 2. Run the steps in order

For each step with status `ready`: run its tool, fill what it fills, mark it `done`, move on without waiting.

- **Research** follows `components/research-fill/process.json` exactly; check where it stands with
  `python3 components/research-fill/fill.py status --brand <brand>`.
- `later`: the step needs something the brand doesn't have yet (own customer words). Skip it and come back.
- `gap`: put it on the page as a gap and keep going with the next ready step.

## 3. Stops

Stop and put the step on the page as the owner's click only where the step says `owner_click`: creating the repo,
the matrix picks, the margin envelope, approval and going live. Also stop before spending past a cap or sending a
message to anyone outside.

## 4. One page

One page per brand: the hunch, what each finished step produced (with its receipts), every step's state, the gaps, and
the owner's clicks on top. Follow the `owner-pages` skill.

## Never

- Never do a gap step by hand or from general knowledge.
- Never fill a research step from what the owner said.
- Never put brand facts in Prizm Labs itself.
