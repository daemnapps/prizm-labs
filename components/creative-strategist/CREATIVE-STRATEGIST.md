# Creative strategist — link 00 of the ad workflow

**What it is:** link 00 of the ad workflow; the later links live in the writing, production and handoff components. the owner says one sentence,
*"I need N ads for brand X, avatar Y, product Z"*, and that becomes an **ask**:
one record that carries the brand, avatar, product, offer, moment and count through
every link, so no later step asks him again what it's for.

Ruled by the owner, 2026-10-01: *"establish the chain here so we can eventually automate
brief creation and I just say I need x number of ads for ex brand x avatar x product,
then you can activate workflows to get things done for me."* It's part of the
creative strategy process, which grows over the next few weeks as research
ingestion and team briefs scale.

**Standing rule on top of it (same day):** *"until you're popping out banger ads, we
always need to do some manual checks on briefs to ensure everything is pristine."*
So every gate below is **his, by hand** until he lifts it. Automation fills the
space between gates and never removes one.

## The ask record

`runs/creative-strategist/<brand>/<label>/ask.json`. Fields come from his sentence; anything
he didn't say is looked up in the brand folder, never invented.

| Field | From | Looked up in |
|---|---|---|
| brand, product, avatar | his sentence | `brands/<brand>/products/`, `core-avatars/` |
| sub-avatar | his sentence or "new" | `core-avatars/<avatar>/sub-avatars/` |
| count (ads) | his sentence | — |
| funnel stage | his sentence (default: bottom = offer-led) | — |
| offer + the exact lines allowed | the offer bank entry for that product | `products/offer-bank.md` |
| moment / deadline | the brand calendar | `strategy/moments.json` |
| swipe mix | default 3 paid + 3 organic | the swipe pools |
| who makes it | by role: statics designer · video editor · creator | `team/people/` |

## The steps, and who holds each

| # | Step | Runs it | Gate  |
|---|---|---|--- |
| 0 | Ask written | session from his sentence | —  |
| 1 | Swipes picked (3 paid + 3 organic) | `image-teardown/chain.py` ranks paid; `swipe-organic` records rank organic | **G1: he signs off the six**  |
| 2 | Avatar check: thin? → research → profile | `components/research-gatherer` (`gather.py --brand --avatar --sub`), then `prompts/avatar-profile-v1-owner.md` | **G2: he reads the sub-avatar**  |
| 3 | Teardowns + injection | image-teardown stages 1–2b, then image-writing stages 3–6 · video-teardown | —  |
| 4 | Briefs (statics, editor, creator) | image-writing's brief chain · video-writing's brief · editor brief | **G3: he checks every brief**  |
| 5 | Pictures, one per concept | `components/image-production/make.py` | **G4: he picks the concepts**  |
| 6 | Variations, 4 per concept | `components/image-edit/vary.py` | **G5: each picture checked alone**  |
| 7 | Handoff to the designer / editor / creator the ask names | `ad-handoff`, `naming` | sends only what passed G3  |

Every step's prompt and output shows on the ask's page. Nothing lives only in a
file path.

## Brand-agnostic — a run requirement (the owner, 2026-10-01)

Nothing in this folder names a brand, product, avatar or person. Every fact an
ask needs is read from `brands/<brand>/` or `team/people/` at run time. The
test is the ad workflow's: a brand that has never run an ask runs one
with no change here. Settings live in `definitions/search.json`; tools in `machine/`.

## How a paid swipe is found (the owner, 2026-10-01)

- **Velocity is the signal, not copies alone.** Group by creative, sort by new copies in the last 7 days; read new copies, their 7-day % change and live copies. Copies 5+ is a floor (median across our 614 pulled swipes is 4; top quarter 11+).
- **14+ days running, still active.** Long enough to have picked up spend, recent enough to still be moving.
- **Image or video.** Either can become either.
- **English-speaking countries by default:** US, UK, Canada, Australia, New Zealand, Ireland. A brand that sells elsewhere declares its markets in its own folder.
- **Affiliate or brand, any button.** The best marketing in the game, wherever it is.
- **Keywords come from the avatar's own words:** `machine/keywords.py --brand <b> --avatar <a> [--sub <s>]` ranks the phrases the bank repeats around the avatar's own desire statement. No seed list, never guessed.
- **Categories come from the avatar's affinity groups:** the product's own category plus the adjacent categories this avatar and sub-avatar also buy from. Never a category picked by feel.
- **Credits are planned first:** filters + cost shown, his yes, then the pull. Already-paid results are reviewed before buying more.

## Briefs read the newest avatar, always (the owner, 2026-10-02)

*"re-write with the most up to date avatar stuff. that should always be a thing"* and *"we have a chain."*

- Every brief comes out of the chain, never freehand: image-writing's chain for statics, the video chain for edits.
- Every brief reads the core avatar **plus the sub-avatar the ask names**: its card and its newest profile, at `brands/<brand>/core-avatars/<core>/sub-avatars/<sub>/profile.md`. The profile prompt writes over that file; git keeps the old ones.
- Image teardown takes `--sub <sub>` (`chain.py start|fill`, `tools/run.py`). It puts core + card + newest profile together fresh at every stage, so a profile rewritten after a run opened still reaches its brief.
- A brief drafted before the newest profile existed is re-run through the chain before he sees it.
- The ask's own offer travels too: `--ask <ask.json>` puts its allowed lines, its never-list and its deadline on top of the offer bank, and they win where they differ. Without it the 2 Oct briefs allowed "$29 a tube" and dropped "Ends Halloween".

## One standard brief (the owner, 2026-10-02)

*"we need a standardized briefing document literally."* Every static brief is
`components/image-writing/templates/` (newest `brief-standard-static-v3-owner.md`), filled in:
the same title line, the same box (for · built on · made by · size · offer ·
deadline), the same ten sections in the same order, the same tables, and every
decision for him in section 10, numbered. The brief step (stage 6, prompt v6)
fills it; the copy gate holds a brief that moved, renamed or dropped any part.
The machine's build data sits below it, out of the reader's way. Video and
creator briefs get their own standard when that lane is worked.

## Affinity groups — part of every avatar profile

What else the avatar buys and from whom: adjacent categories, named brands, the stores she buys through, every item with a source row. It sets which categories the swipe search covers and lets creative fit her life 1:1. First built on the face sub-avatar (2026-10-01).

## What's missing before this runs on its own

1. **Done 2026-11-03:** the ask record is written by `machine/ask.py` and read by image-writing, copywriter, video-writing, image-teardown and promo-calendar.
2. **Avatar thickness isn't measured.** Nothing decides "thin, research first".
3. **Organic picking has no ranker beside the paid one.** Views are on 13 records only.
4. **One page across image and video gates.** The Brief Board is image-only.
5. **Handoff doesn't know video editor briefs.** It knows the statics designer's.
6. **Keyword pull exists (`machine/keywords.py`) but the swipe step doesn't call it yet.**
7. **Affinity groups have no home in the profile schema yet.**
8. **The video chain doesn't take `--sub` yet.** Image teardown does (2026-10-02).

Each gets built when a real ask hits it, not before.

## Asks run so far

Every ask is a folder under `runs/creative-strategist/<brand>/<ask>/`; its gates and state live in its own `ask.json` (`gates`).

## The research route (2026-11-25)

A second way in, beside the swipe route above. It does the research first and lets the idea come out of it, so a piece can be ours from the start: evidence → what is true → tensions → insight → ideas → the owner's pick → form → the same chains. Order, rules and checks: `CLAUDE.md`, "Two routes into the same chains".
