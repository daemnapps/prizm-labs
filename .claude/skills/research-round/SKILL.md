---
name: research-round
description: Run a research round for any avatar of any brand — what he actually watches, which formats pull the most views right now, ranked, with thumbnails, ready to pick and tear down. Use whenever someone says "research <avatar>", "run a research round for <avatar>", "what does <avatar> watch", "find formats for <avatar>", "pull formats for <brand> <avatar>", "what's working for <avatar> right now", or asks to pull, rank or index organic posts for an avatar.
---

# Research round

> **Activates component:** `components/swipe-organic (with components/apify)` — `round.py`, one research round for one avatar.


External dependencies (top-level project folders): `components/swipe-organic/`
(`round.py`, `RESEARCH-ROUND.md`, `METHOD.md`)
`components/apify/tiktok.py` (the pull; it refuses a paid search outside a round),
`brands/<brand>/core-avatars/<avatar>/profile.md`.

One avatar per round. "research <avatar>" with no brand: find the avatar's folder under
`brands/*/core-avatars/`. Two avatars named = two rounds, never one mixed list.
Pick a label: `<YYYY-MM-DD>-<what>`.

## Steps — in this order, every time (the why is RESEARCH-ROUND.md)

**1. Read him first (free).**
`python3 components/swipe-organic/round.py worlds --brand <b> --avatar <a> --label <l>`
It prints his feeds' top hashtags, the kinds of post, and the profile's lines on what he
watches. From that, write `runs/swipe-organic/<b>/research-<a>-<l>/worlds.json`: his
worlds, biggest first, each with a post count and the keywords a search must contain.
No feeds for him yet → run a Dig on My Feeds first; that is the round's first pull.

**2. Plan, and pass the coverage gate.**
`round.py plan ... --ask "<whose scroll, what the round is for>" --keep-rule "..." --drop-rule "..." --search "..." --search "..."`
(8–12 searches, `--max 85` ≈ 1,000 posts). The ask and rules are what My Feeds sorts every
post against, into its three sides: entertainment, educational, selling (`--lanes` keeps all
three by default). A problem round (the skincare, the product) lives on educational and selling.
Every one of his top five worlds needs a search; a new idea goes on top, never instead.
`HELD` → add the missing searches and plan again. Never edit worlds.json to get past it.

**3. Show the plan and the price. Wait for the person's yes.** Searches, posts, the dollar
cap, the coverage table. Nothing spends before "go".

**4. Pull.** `round.py pull ... --approved-by <who said go>`

**5. Rank.** `round.py rank ... --top 50` keeps posts from 1 Jan this year on (formats
evolve), drops ads and repeats, scores views + likes + comments, ranks his formats by how
many of their posts made his top 50 (typical views break ties), fetches thumbnails,
files every kept post into My Feeds as `<b>--<a>-<l>`, and runs My Feeds' own sorter
(`sift.py`) so each post lands on its side. Show the top 50 split by side.

**6. Show it on a page** — his format ranking, his top 3 formats with real thumbnails, his
top posts linked. Update the subject's existing page if there is one; record a new page's
link in `components/swipe-organic/context/artifacts.md`.

**7. Build the matrix** (once he has a formats round and a problem round). On "build the matrix":
`python3 components/swipe-organic/matrix.py --brand <b> --avatar <a> --hooks <format round labels> --problem <problem round label>`
It lands in `runs/swipe-organic/<b>/matrix-<a>/`: his top formats × the problem
moments in his own words × the problem videos that pull, every category and video clickable.
Write the merged concepts into `runs/swipe-organic/<b>/matrix-<a>/concepts.json` (hook search |
moment world → title, idea, open, turn, cut, angle from the angle bank; `body_how` per body;
`top` for the strongest) and build again. Never coin an angle; a missing concept shows its evidence.

**8. He picks.** Writing starts only on his picks. Teardowns trigger from My Feeds.

## Never

- A hand-written search list straight into `tiktok.py` — it refuses, by design.
- Posts from before this year in a format ranking.
- Two avatars ranked as one.
