---
name: voice-pull
description: Pull the newest words from a brand's OWN audience — comments under its ads and customer support emails — sort them into the brand's customer-language bank, and show them on a page grouped by what they're good for in an ad. Use when someone says "pull new comments", "pull the latest comments for Brand B", "what are customers saying lately", "refresh the language bank", "any new customer language", "run the voice pull", or wants recent ad-comment / support-email language to build ads from.
---

# /voice-pull <brand>

> **Activates component:** `components/research-gatherer` — pulls customer language.


External dependencies (greppable): `components/research-gatherer/gather.py`
(the `ownvoice` mode, `research_gatherer/ownvoice.py`), its intake prompt
`components/research-gatherer/prompts/annotate-row.md`, the language layer's
labeller `components/language-layer/tools/label.py`,
`brands/<brand>/operations/brand.json` (the ad account + helpdesk it reads),
`brands/<brand>/context/artifacts.md` (where the page's link lives),
`lab/the owner/ACCESS.md` (why Brand B's comments come from scraping).

The person asking does not run anything. You run it, then show them the page.

## Steps

1. **Run it** from the workspace root:
   `python3 components/research-gatherer/gather.py ownvoice --brand <brand>`
   It picks up where the last run stopped (`runs/research/<brand>/ownvoice-state.json`).
   First run for a brand starts 2026-07-01. `--since YYYY-MM-DD` overrides;
   `--dry-run` counts without sorting or filing; `--no-scrape` spends nothing on Apify.
2. **Publish the page.** The run prints `page: runs/research/<brand>/ownvoice-<run>/page.html`.
   Read `brands/<brand>/context/artifacts.md`: if a "Voice Bank Intake" row exists,
   republish over that URL (read it first, then publish with `url`); if not, publish a new
   artifact and add the row (subject, title, URL, mirror = the run folder).
3. **Tell them in three lines:** how many new rows went into the bank, the two or three
   most striking quotes, and the link. Name anything the run says it could not read.
4. **Commit only what the run wrote**: the bank files it touched under
   `brands/<brand>/core-avatars/*/language/`, the run folder, the state file, and the
   artifacts row. Never stage anything else — other sessions work in this tree.

## What it does, so you can answer questions about it

- Reads support emails from the warehouse (customer-written, real customer tickets
  only) and ad comments from the warehouse, then scrapes the brand's top-spend ad
  posts with Apify. Dark posts cannot be scraped.
- Cleans each row (quoted mail, signatures, emails, phones, addresses, order numbers),
  skips anything already in the bank, and reads the rest twice: the intake prompt
  above (keep or drop, use, topics, sub-avatar, ad use, names to remove) and the
  language layer's labeller (`components/language-layer/tools/label.py`: awareness,
  sophistication, the lane the words point to). The lane: an order on file decides,
  otherwise the words (customer "assumed" / lead / prospect).
- The run's `report.md` says rows per lane, per awareness level, per sub-avatar, and
  which awareness levels came back thin — say the thin ones when you report.
- To pull the comments on one post (any brand's, any public TikTok / Instagram /
  Facebook post): `gather.py comments --brand <brand> --url <post> [--sub <sub>]`.
- Files kept rows in the bank's own schema, so the copy and video tools
  (through `components/language-layer`) use them from the next run.
- Rows the sort could not handle are held, not filed, and the next run retries them.

## When to stop and ask

- The run says the warehouse or Apify is MISSING: say which, in one line, and
  whether it is a key or a spending cap (only the owner can raise a cap).
- A brand has more than one avatar: ask which one, then pass `--avatar`.

tested: Brand B, 2026-09-28, first run since 2026-07-01.
