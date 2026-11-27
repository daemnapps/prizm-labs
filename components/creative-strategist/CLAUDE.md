# creative-strategist — link 00: one sentence becomes the ask every later link reads

**creative-strategist** — takes **a sentence ("I need N ads for brand X, avatar Y, product Z") plus the brand folder**, makes **the ask record: brand, product, avatar, funnel, the offer lines the ads may and may never say, the moment and its window, the count and who makes it**. Does not **write briefs, pick swipes or make ads** (those are the later links, gated by hand: `CREATIVE-STRATEGIST.md`).

**Owner:** the owner · **Station:** `components/` — moved from `lab/the owner/creative-strategist/` on 2026-11-03 (builder-card rule 12: no component runs lab code, so the asks had to come from a team tool).

Runs by: person — a person says the sentence and reads the ask; the mini does not write asks.

| New-resident question | Answer |
|---|---|
| Engine + owner | `machine/strategy.py` (the research route), `machine/idea.py` (its block, the public surface the writing chains read), `machine/who.py` (who an ad is for and what it must say: the one read every writing chain makes; CONTRACT.md), `machine/wiring.py` (proves each workflow carries it), `machine/ask.py` (`new` writes `ask.json`, `check` validates it), `machine/keywords.py` (search phrases from an avatar's own words) — the owner |
| Definitions + curator | `prompts/research-to-idea-*` and `prompts/idea-to-form-*` (the research route; highest `-vN-` is live, `parked/` never runs), `definitions/forms.json` (forms an idea may borrow), `prompts/avatar-profile-v1-owner.md` (turns filed research rows into the sub-avatar profile; the owner's, moved verbatim), `definitions/search.json` (how the paid-library swipe step searches), `CREATIVE-STRATEGIST.md` (the process and its gates) — the owner |
| Plane | `runs/creative-strategist/<brand>/strategy/<label>/` (the research route: `evidence.json`, `idea.json`, every prompt sent and answer) and `runs/creative-strategist/<brand>/<ask>/`: `ask.json`, plus the ask's own page and step files. Filed by the shared runs filer; no adapter of its own |
| Manifest | none (no status words; an ask's gates are plain text inside `ask.json`) |
| Runs by | person |

## Two routes into the same chains

| Route | Starts from | Command |
|---|---|---|
| **Swipe** | a proven ad | `ask.py new`, then the teardown |
| **Research** (2026-11-25) | what is true about one sub-avatar | `strategy.py evidence → think → copy → choose → forms → ask → hand` |

The research route finds the idea before any swipe, format or teller. Its idea travels inside the ask (`strategy`), so image-writing and video-writing carry it on every step (`machine/idea.py` `block`) and it wins over the swipe's idea. A swipe then lends form only (`definitions/forms.json`). Video needs no swipe at all (video-writing `scratch.py --story`). The swipe route is unchanged.

Checked by code, never by trust: every receipt names a real row or file and quotes words that are in it; a number in the insight, idea or line needs a source; the position's never list holds; two men never get the same idea; what still fails is dropped and said. The evidence is ranked by his problem's words, never by likes. A problem-aware or solution-aware idea carries no price. The owner chooses the idea.

Copy is its own step (`copy`): his words and what has sold for the brand go in; machine phrasing, lines that do not name the problem and lines a cold reader cannot place are thrown out. The thinking's own sentences are never copy.

## The rules

1. **Nothing is invented.** Whatever the person did not say is looked up: offer lines in the offer bank's own section (the moment's, else the product's), the moment's window in `strategy/moments.json`. A fact not found is left empty and reported as a `note:` line.
2. **The shape is fixed** (`CONTRACT.md`). image-writing, copywriter, video-writing, image-teardown and promo-calendar already read it; a change to the shape is made here and in those readers in the same commit.
3. **One writer.** Sessions no longer write `ask.json` by hand. promo-calendar still writes its own fallback ask for a promo with no strategist ask (`components/promo-calendar/machine/queue_source.py`, `promo_ask`); it could call `ask.py new` instead so there is one writer (noted for that component's owner, not changed here).
4. **Brand-agnostic.** No brand, product, avatar or person is named in code. A brand that has never run an ask runs one with no change here.
5. **The offer parse** (bank section → quoted lines) is the same idea as `components/storefront-promo-edit`'s; a third user of it is a card to extract it, not a third copy.

## Commands

    ask.py new   --brand <brand> --ask <label> --product <offer-bank section> --avatar <avatar> --said "<his words>" --funnel "<funnel line>" [--moment <key> --window "YYYY-MM-DD to YYYY-MM-DD ..." --moment-line "<line>"] [--offer-line "<line>"] [--never "<line>"] [--count static_concepts=5] [--maker statics=<name>]
    ask.py check <path to ask.json>

`new` also takes `--sub-avatar`, `--offer-section <bank section>`, `--asked YYYY-MM-DD`, `--out DIR` and `--force`. `--moment evergreen` writes the always-on ask (window "always on"). Lines the bank does not mark as usable for the moment come in as `--offer-line` (each is checked against the bank word for word and reported if it is not there). `--force` replaces an ask but keeps what later links wrote into it (gates, swipes, evidence, page), its key order and its indent.

The avatar profile prompt (`prompts/avatar-profile-v1-owner.md`) is run by a session by hand at the gate in `CREATIVE-STRATEGIST.md`, not by a command here.
    keywords.py --brand <brand> --avatar <avatar> [--sub <sub>] [--top 25]

Tests: `python3 -m unittest discover -s components/creative-strategist/tests`.
