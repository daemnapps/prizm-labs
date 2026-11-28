---
name: brand-launch
description: Launch a brand from zero with one trigger. A hunch goes in (one line, a product or ingredient and a market); the whole launch checklist runs start to end (research, brand, product and supply, selling), each step through the tool that owns it, and one page shows where it stands. Use whenever someone says "launch a brand", "new brand from zero", "I have a hunch about <product>", "run the launch for <brand>", "start a new offer", "take <ingredient> from idea to ads", "where is <brand>'s launch", or "continue the launch".
---

# Brand launch: hunch in, brand out

> **Runs:** the checklist in `brands/_TEMPLATE/launch.json` (copied into `brands/<brand>/launch.json`), step by step.
> Progress lives in `brands/<brand>/launch-progress.json`. A brand that already sells uses `brand-activation` instead.

The owner gives a hunch and nothing else. Everything after it comes from research, every line with its receipt,
and the research is free to prove the hunch wrong. Run every step yourself; talk in plain words.

## 1. Start

- Ask for one line if it wasn't given: the product or ingredient, and the market ("cranberry, men's urinary").
- Make the brand folder: copy `brands/_TEMPLATE/` to `brands/<working-name>/` (lower-case, dashes). The real name comes
  later, from the naming step.
- Write the hunch to `operations/brief.md`: the one line and the date. Nothing else of the owner's goes in.
  Research steps read only that line.
- "Continue the launch": read `launch-progress.json` and start at the first step not in `done` or `skipped`.

## 2. Run the phases in order

For each step in `launch.json`: run the tool it names, fill the file it names, keep the receipts it names, add the
step to `done` (or `draft` if a person should look), and move on. Do not wait between steps.

- **Research** first, always, and in its listed order. Its steps own their tools (`avatar-profile`, `research-fill`,
  `research-gatherer`, `product-research`, `trendtrack`, `swipe-paid`, `research-round`, `creative-strategist`).
- **Evidence** (no tool yet): search published trials and reviews for the ingredient; write each finding with the study
  link, sample size, dose and the number. The mechanism comes only from these.
- **Brand, supply, selling** follow, each through its named tool.

## 3. Stops (the only ones)

Stop and put the step on the page as the owner's click when it would:
- spend money past a set cap, buy anything, or open an account;
- send a message to anyone outside (supplier quote requests included);
- go live (an ad, a page, a store).

Everything else runs without asking.

## 4. One page

Keep one page per brand: the hunch, what the research found (with sources), the checklist with each step's state,
and the owner's clicks on top. Republish it as steps finish. Follow the `owner-pages` skill.

## Never

- Never fill a research step from what the owner said; only from receipts.
- Never skip a research step or change the order.
- Never put brand facts in Prizm Labs itself: the brand folder stays out of the public repo.
