# The Prompt Changes — the marketing doctrine, applied (2026-09-18, extended 2026-09-19)

Page: **The Prompt Changes** (team page). Siblings: The Video Machine, The Model House.

Eugene Schwartz's *Breakthrough Advertising* is the backbone every machine reads from. This file is the team's record of what changed and where it lives. It replaces the earlier spec that forced a private moment / bias / cultural rule onto every hook — the owner rejected that framing.

## The line, the mechanism, the stage (2026-09-19)

the owner's read: every brand wins through one clear **line** — why the product exists for this reader — and the amplifier is the **unique mechanism** set against the **market's sophistication stage**. The machine had the doctrine and read the swipe's market state (1b), but nothing declared *our* line or *our* stage, so injection swapped facts into a borrowed skeleton with no spine. Three things landed.

### 1 · A position file per brand — `brands/<brand>/position.md`

A labelled block under `### the line` (LINE · SPINE · PROBLEM WORD · MECHANISM · MECHANISM NAME · DISPLACES · MARKET STAGE · STAGE WHY · LEADS WITH · TRUST MOVE · SIGNATURE ASSET · NEVER · confirmed by). Brand B's file already held the prose (ruled 2026-09-13); the block is copied from it. Brand A's file is new, written from `strategy/plan.md`, the four signed angles, the core avatar profile, the product file and a competitor teardown — every quote verbatim. `brands/_TEMPLATE/README.md` lists it; a brand without one refuses at 1b (`brand file missing`).

| Slot | Brand A | Brand B |
|---|---|---|
| **LINE** | For [the reader, named by her problem in her words], Brand A is the [product] that [what it does to the cause] — because [the reframe of why the problem persists]. | For [the reader, named by his problem], Brand B is the only brand built around [the moment the problem starts] — because [the reframe that lifts the blame]. |
| **SPINE** | [one short reframe line — the problem was never what she thought]   (PROPOSED — cut from the lead angle's own sentence; the owner rules) | [one short line that moves the blame off the reader] |
| **PROBLEM WORD** | [her dominant word] · [two variants] — never [the clinical terms] | [his words] · [a verbatim simile from the bank] (never [the clinical term]) |
| **MECHANISM NAME** | [the brand's own mechanism name]   (the brand's own — product page, read on a date) | [a plain-words name] |
| **DISPLACES** | [the aisle of alternatives] · [the expensive option, in a customer's verbatim] · [the option that makes it worse] | [competitor approach one — what it changes] · [competitor approach two — what it treats on the surface] |
| **MARKET STAGE** | 3. Claims exhausted | 4. The mechanism is in the market |
| **STAGE WHY** | she has heard every claim and discounts them — [the avatar's most-used sentence], [two more verbatims]. The largest objection clusters in the bank are [cluster] (__ entries) and [cluster] (__ entries). No competitor in her feed pitches a mechanism: [what the competitor teardown found]. | the market has already been pitched two mechanisms and this customer has tried both and says so — [two verbatims]. [Who won the mechanism position and what they stopped saying] (read live on a date). |
| **LEADS WITH** | the mechanism — WHY the problem comes back — before any claim. The plain claim is the thing she has already discounted. A mechanism angle answers her sentence; a benefit angle argues with it. | a third mechanism, stated against the two the market already knows, enlarged on completeness — [why nothing the market offers reaches the cause]. Never enlarged on speed. |
| **TRUST MOVE** | [the origin story the brand can stand behind — things she already recognises]; __% of the account's spend. Claim limit: never imply an origin the brand cannot stand behind (verbatims show customers checking). | [the authority figure who replaces the expected one]. [Why the viewer believes him.] |
| **confirmed by** | open — the owner rules the stage and the spine | open — the owner rules the stage |

### 1b · One format, every brand (ruled 2026-09-19)

`brands/_TEMPLATE/position.md` is the shape; it names no brand. Part 1: ONE fenced block under `## The line`, fourteen slots in fixed order — LINE · SPINE · PROBLEM WORD · MECHANISM · MECHANISM NAME · DISPLACES · MARKET STAGE · STAGE WHY · LEADS WITH · TRUST MOVE · AUTHORITY · SIGNATURE ASSET · NEVER · confirmed by — `LABEL: value`, `open` allowed, empty not. Part 2: ten `##` sections in fixed order (The line · The goal, in one counterintuitive sentence · The position · The thing nobody in the category will say · The competition, by mechanism · The territory · The words · The binding rules · Receipts · Open), optional `## Also on file`, and the template closes with "The method, for the next brand". `components/marketing-doctrine/lint_position.py` gates every brand's file and the template (brand-agnostic check); wired into `test_doctrine.py`. Both brand files rewritten into the shape the same day, content intact.

### 1c · Colour is the design system, not the position (the owner, 2026-09-19)

The palette left `brands/<brand>/position.md` (roles + Leather → `identity/web-tokens.md` "Roles"); `lint_position.py` now refuses any hex colour in a position file. Design system = `brands/<brand>/identity/` — `palette.md` (sampled from product photography) · `web-tokens.md` (sampled from live CSS) · `fonts.md` (licences, from purchase records) · the marks. Template: `brands/_TEMPLATE/identity/` (four files + README with the six-step method). Tool: `the team notes` — `scaffold` (never overwrites) · `palette` (PIL quantize over `products/**/images/`, packshots first, near-whites dropped; a person names rows) · `tokens --url` (colours by declaration count, families, radii) · `check [--all]`. Brand B scaffolded: `identity/README.md` + `fonts.md` with open slots; no marks in the repo — the owner's to drop in.

### 2 · `{position}` bound into five stages

`extra-stages.json` `stage_vars` binds `position: brands/<brand>/position.md` on stage1b, stage2f, stage3, stage4b, stage4a (placement); both brands' `variables/video.md` map it to `position.md`; `prompts/reference/VARIABLES.md` carries the row.

| Stage | What it now does | File |
|---|---|---|
| 1b audience | prints `BRAND STAGE`, `STAGE VS BRAND: agrees | disagrees` (what each rests on), `LINE CARRIED: yes | no`; a disagreement is a finding, never smoothed | `stage1b-audience-v7` |
| 2f compose | unique-mechanism mandatory at stages 3–4 (B-roll, slot = the position's mechanism), dropped at 5; brand stage printed beside the market state's | `stage2f-compose-v3` |
| 3 injection | THE LINE IS THE SPINE OF EVERY SWAP: source mechanism → MECHANISM in MECHANISM NAME's words; problem → PROBLEM WORD; competitor → DISPLACES; the one sentence → LINE/SPINE; NEVER words substituted and logged; dominant trait settled by the position first; check 3 THE LINE (`LINE HAS NO BEAT`); `POSITION` source tag | `stage3-injection-v10` |
| 4b hooks | THE STAGE TEST — fifth list: what each of six openings leads with vs `LEADS WITH`; control flagged, variations rewritten | `stage4b-hook-v13` |
| 4a placement | mechanism rung priced by the stage; `LINE BEAT: <timestamp>` or `none — why`; inherited gendered pronouns in the examples block fixed | `stage4a-placement-v11` |

Verified: every stage's prompt slots bind for both brands on both lanes (swipe and framework); `chain.py` reports the new versions; compose (27), research-gatherer, doctrine tests green; `lint_prompts.py` clean on all five.

### 3 · Research on a timer

`a nightly script` + `a launch agent` (02:30 nightly). Per brand with sub-avatars: `gather.py deep --brand <b> --pick-thinnest --cap 150` (the gatherer gained per-brand `--pick-thinnest` today), then commits ONLY the files the pull produced (`core-avatars/**/language/`, `/research/`, the sub-avatar card's rooms block) with `git commit -- <paths>` and pushes; nothing else in the tree is touched. `DRY=1` prints and spends nothing. Log: `the job's log`. First picks: one Brand A sub-avatar (15 rows), one Brand B sub-avatar (0 rows). ≈ $__ per sub-avatar.

**Open for the owner:** Brand A's stage (3) and spine are declared, not confirmed; Brand B's stage (4) likewise. `confirmed by: <name>` locks a block.

## Where it lives

`components/marketing-doctrine/` — a resident component every machine pulls in. `frameworks.json` is the truth (five awareness levels, five sophistication stages, seven techniques, the sections an argument is built from, the research questions); `slices/` are rendered from it and a prompt binds only the slice it needs by path; `SCHWARTZ.md` is the readable doctrine; `lint_prompts.py` gates gendered generic pronouns. The book sits beside the doctrine at `components/marketing-doctrine/source/` on the owner's ruling.

## The doctrine in one screen

### Awareness — five levels, each with a must-not

| Level | Knows | Must | Must not |
|---|---|---|---|
| Most Aware | Knows the product, wants it, simply has not bought yet. | State the product and the price or the deal, and stop. | Explain anything; Re-sell a want that is already there |
| Product-Aware | Knows the product exists but is not sold on it. | Do one of seven named jobs on the claim already in the market | Reintroduce the category from scratch; Talk as if the product were new |
| Solution-Aware | Carries the desire and knows a result is possible, but does not know a product delivers it. | Crystallise the desire or its solution in one line, then prove it | Mention price; Assume the product name means anything yet |
| Problem-Aware | Feels a need but has not connected it to any product category. | Name the problem or the need directly, in the words the audience uses | Assume a solution is already known; Lead with a category the audience has not entered |
| Unaware | Does not know the desire or the need exists — or will not admit it. | Open on pure identification: describe the audience to itself until it is recognised | Mention price; Name the product; State the direct claim or the desire itself |

### Sophistication — five stages

| Stage | Market has heard | Lead with |
|---|---|---|
| First in the market | Nothing — no one has made this claim here before. | The plain claim, stated simply and with no embellishment. |
| The claim is in the market | The plain claim, now from competitors. | The same claim, enlarged to the edge of what is still believable. |
| Claims exhausted | Claims pushed to their limit, and it discounts about half of what it hears. | A NEW MECHANISM — how the result happens, not what the result is. The mechanism leads the opening. |
| The mechanism is in the market | A mechanism, from a competitor. | The same mechanism, enlarged, made easier, faster or more complete. |
| Exhausted field | Every claim and every mechanism, and believes none of them. | Drop claim and mechanism both and sell on identification alone — the same move as the Unaware level. |

### The seven techniques

| Technique | What it does | Owning stage |
|---|---|---|
| Intensification | Keep generating fresh, concrete pictures of the desire already fulfilled — never the same picture twice; vary the angle so repetition reinforces instead of tiring. | 4d-expansion; 4b-hook; 4e-close |
| Identification | Build a saleable personality into the product by attaching roles the audience wants to be seen playing. The product then does double duty: physical satisfaction plus a badge of identity. | 4d-expansion; 1b-audience |
| Gradualization | Belief is structural, not only a matter of content. A claim's strength equals its own content plus how far the copy has already prepared the audience to accept it — so build a chain of acceptances from a fact already believed, each step earning the next. | 4d-expansion; 4b-hook; 4e-close; 5-brief |
| Redefinition | Give the product, or the problem, a new definition that removes an objection before it is consciously raised. | 4e-close; 4d-expansion |
| Mechanization | Verbal proof of HOW the product delivers — reason-why copy answering the silent question of how the thing works. | 4d-expansion; 4b-hook |
| Concentration | Destroy the alternate ways of satisfying the desire — a direct attack on the competing option or on the status quo. | 4d-expansion; 4e-close |
| Camouflage | Borrow believability from the medium the ad lives in. Editorial and organic content is trusted more than advertising voice, so minimise the gear change between the two. | 3-injection; 4c-placement |

### The sections — a vocabulary, not a sequence

Any ad carries any subset, in any order, with repeats. The awareness level decides which sections an ad needs at all. The framework a swipe follows is read off the video and named, never imposed.

| Section | What it does | Built by | Needed at |
|---|---|---|---|
| Hook | The point of entry. One job: force the next beat to be watched. Its content is set by the awareness level and the sophistication stage, not by taste. | intensification, camouflage | every level |
| Problem | The need named and felt, described in enough specific detail that the audience recognises its own situation before anything is offered. | intensification, gradualization | problem-aware, unaware |
| Failed solutions | The alternatives already tried, each failing at a moment the audience recognises — every named weakness answered immediately by the matching strength. | concentration | problem-aware, solution-aware |
| Root cause | The real reason the problem persists, reframed so it is a different problem than the audience thought, and reached by steps already accepted. | redefinition, gradualization | problem-aware, solution-aware |
| Unique mechanism | How the product produces the result — named, described or featured, at the depth the market's sophistication stage demands. At stage 3 and above the mechanism leads. | mechanization | solution-aware, product-aware |
| Solution | The product in action and the desire fulfilled, stretched across time, carrying the role the audience wants to be seen in. | intensification, identification | solution-aware, problem-aware, unaware |
| Product | What the thing actually is — the physical facts, used only to justify price, document quality, promise durability or sharpen the picture, never as the lead sell. | redefinition, identification | product-aware, solution-aware |
| Offer | The terms: price set against a bigger anchor, and the guarantee restating every promise as the final intensification beat. | intensification, redefinition | most-aware, product-aware |
| Call to action | The conclusion of the accepted-step chain — the single step still left once every prior step has been agreed to. | gradualization | every level |
| Identification | Who this is for. The call-out that names the viewer to themselves — their situation, their role, their words — before any problem is stated or anything is offered. At unaware this is the only opening allowed; everywhere else it is the beat that earns the right to name the problem. | identification | unaware, problem-aware |
| Agitation | The stakes. What it costs to leave the problem alone, and the future that arrives if nothing changes — the black side of the picture, reached one already-accepted step at a time rather than asserted. | intensification, gradualization | problem-aware, solution-aware |
| Proof | Evidence placed at the beat where doubt peaks, never front-loaded because it happens to be proof: results, testimonials, authority, demonstration, before and after — and written as selling copy, dramatic and specific, not as a dry fact block. | intensification, mechanization | solution-aware, product-aware |
| Transformation | The after. The fulfilled desire pictured — the first-use moment lived, the benefit stretched across weeks and months, and the role the viewer gets to be seen playing once it has happened. | intensification, identification | solution-aware, problem-aware, unaware |
| Objections | The flinch answered. The specific reasons not to buy — named in the viewer's own words — redefined or resolved before the ask, never after it. | redefinition | product-aware, most-aware |
| Urgency | Why now. The reason to act in this moment rather than later — real and receipted: a dated deal, a real limit, a cost that compounds. Invented scarcity is never this section. | gradualization, intensification | most-aware, product-aware |

_The last six were added 2026-09-18 on the owner's ask — the first nine are the owner's own list; any of the six can be struck._

| Framework the video follows | Its parts, as sections |
|---|---|
| PAS (problem · agitate · solve) | problem → agitation → solution → product → offer → call-to-action |
| AIDA (attention · interest · desire · action) | hook → problem → solution → call-to-action |
| BAB (before · after · bridge) | problem → solution → unique-mechanism → product → call-to-action |
| Story / testimonial (life · tried · found · now) | hook → problem → failed-solutions → product → proof → solution → transformation → call-to-action |
| Mechanism-led (the new way) | hook → root-cause → unique-mechanism → solution → product → offer → call-to-action |
| Us-vs-them / comparison | hook → failed-solutions → unique-mechanism → product → offer → call-to-action |
| Direct offer (most-aware) | hook → offer → urgency → call-to-action |
| Identification-only (unaware) | hook → identification → problem → solution → call-to-action |

## The swipe loop now

read the video → **1c doctrine read** → 1b audience (market state + lane) → 2 construct → 3 injection → 4a read · 4b hooks · 4c placement · 4d expansion (**the depth pass**) · 4e close · 4f audit → **4g spice** → 5 brief on the chosen lane.

| Stage | What it now does | File |
|---|---|---|
| 1 ingestion | scenes with frames; each scene labelled with the section it is doing | `stage1-teardown-v9` |
| **1c doctrine read** (new) | framework · sections carried · awareness entry→exit · sophistication signature · mass desire · techniques observed · mood · what makes it unique — cited, then one JSON block the machine files as `doctrine.json` | `stage1c-doctrine-v1` |
| 1b audience | MARKET STATE for our reader (lead desire on three dimensions, awareness level, sophistication stage) + ROUTE RECOMMENDED (creator · founder · ai) | `stage1b-audience-v6` |
| 2 construct | carries the sophistication signature as what is load-bearing | `stage2-replication-v3` |
| 3 injection | DOMINANT TRAIT + FUNCTIONAL LEAD; native register held (camouflage) | `stage3-injection-v9` |
| 4a read | awareness on the named levels: entry, exit, the entry level's must-not quoted | `stage4r-read-v4` |
| 4b hooks | THE RUNG TEST — price/product/claim too early for the level is a defect; nothing forced onto hooks | `stage4b-hook-v12` |
| 4d expansion | THE DEPTH PASS — sections carried, technique options per section, mechanism leads at stage 3+, every option cites a bank row or research receipt or the beat stays clean | `stage4c-expansion-v12` |
| 4e close | PROOF PLACEMENT · THE ANCHOR · THE GUARANTEE; redefinition for the bank's objection | `stage4d-close-v7` |
| 4f audit | checks 9–11: rung test, receipt test, market test | `stage4e-audit-v4` |
| **4g spice** (new) | research questions answered by the gatherer, never guessed; voice = a cast voice cloned then adjusted, rights on file; lookalike-type B-roll character (written identity, different face); styling; mood register | `stage4g-spice-v1` |
| 5 brief (AI lane) | LANE printed first; per scene Section · Technique · Emotion · Outcome; PRODUCT LOCK; COMPOSITION; `{spice_sheet}` input | `stage5-ai-brief-v6` |

Wiring: `tools/video-teardown/machine/extra-stages.json` (order, stages, stage_vars), `chain.py` (prompt homes + labels), `run.py` (lane from 1b when `--route` is absent, `market_state` and `production_route` on the run record, `doctrine.json` filed after 1c, `~research` bound via `research.inputs(st)`, the framework bank refreshed at the end of every run).

**The framework bank:** `machine/framework_bank.py` compiles every run's `doctrine.json` into `runs/video-teardown/framework-bank.{json,md}` with plain headers, and filters like `--awareness problem-aware --signature mechanism`.

## The second door — an ad from a choice, not a swipe (2026-09-18)

`tools/video-teardown/machine/compose.py plan|run|grid` builds an ad from **avatar × awareness × format × framework** with no swipe: `components/marketing-doctrine/ad-frameworks.json` holds the frameworks (section sequence with technique and scene shape per beat, awareness entry → exit, formats that fit; seeded from the crosswalk, grown by promoting a swipe's doctrine read with `framework_bank.py --promote <run>` on the owner's word); a FRAMEWORK lane in the chain skips the swipe stages, runs the new `stage2f-compose` prompt in stage 2's slot (same output shape as the replication spec), then injection → the loop → spice → the brief as today. `grid` runs every cell of the chosen lists. Brand A's cast sheet `runs/casting/<brand>/<run>` is compiled from `ai-cast/<name>/character.md` (moved out of the brand folder 2026-09-21). The compose tests run in a temp folder — they once deleted a real run that shared their label.

## Across the rest of the OS

| Machine | What changed |
|---|---|
| Production (`tools/video-production`) | scene contract with no fixed length (TEMPLATE, song-ad and the six other profiles); stage-3-scenes v4 (Section · Technique · Emotion · Outcome), director v3 (the scene landed), handoff v3 (the loop, the scene arc); `{techniques}` and `{mood}` bound; run.py passes the four fields through |
| Image teardown | stage1 v2 emits MARKET STATE; stage4b v2 the rung test; stage6 v2 technique per element; slices bound in tools/run.py |
| Pages | stage2b v2 binds the research questions; stage3 v4 sections per block + dominant trait / functional lead; stage4 v3 proof placement / anchor / guarantee; stage6 v3 technique per block |
| Copy | stage1-read v2 awareness; stage5-hooks v3 rung test; stage6-expansion v3 depth pass; stage7-close v3 proof/anchor/guarantee |
| Email + calendar | stage0-triage v2 awareness per send from the segment; stage5-subjects v2 the headline rule; stage9-brief v2 technique; cal5-concepts v2 technique per concept |
| Research (five domains) | `_METHOD.md` carries the Schwartz question bank; forums → roles / accepted beliefs / objection language / mechanism acceptance / in-words; competitor → the market's stage; synthesis → lead desire, level and stage into the profile |
| Avatar profile | template slots: lead desires on three dimensions, awareness level per desire, sophistication stage, roles claimed, beliefs accepted, rooms where they talk |
| Lanes | each lane in `control-room/registry/lanes.json` names the awareness levels it serves |
| Language layer | tags added to `brands/language-schema.md`: mechanism, role-claimed, accepted-belief, subculture, in-word; `depth` + `spice` stage keys in both chains' `STAGE_USE` |

## How the sub-agents fire — every run

A stage's inputs are wired: `@stage` (a prior output), `~var` (gathered per run), `?stage` (the language-bank query by what the stage is looking for), and now `~research` — the **research gatherer**, a resident component (`components/research-gatherer/`) with a thin shim in the teardown machine, exactly how the language layer is pulled. It queries the bank with the Schwartz-shaped tags, pulls Reddit and forums through the Apify door using the avatar's named rooms, and reads the comments on the swiped post. Receipts on every claim, two bands, counts with denominators, cached per (brand, avatar, desire); no key or a blocked site means an unfilled slot and a clean beat, never a guess.

**The deep-research trigger** (`gather.py deep --brand --avatar --sub`, `--all`, `--pick-thinnest`) runs for any brand's sub-avatar and files subculture language into the avatar's language tree as rows tagged with the sub-avatar (`core-avatars/<avatar>/language/deep-research/<sub>-<date>.json`), with permalinks, shown on the Control Room page at `/deep-research`. **Rooms are found, not written:** the gatherer runs one small discovery search in the sub-avatar's own words (posts only, sorted by relevance over the last year), tallies which forums the winning threads came from, writes the top five back into the sub-avatar's file dated (add `confirmed by: <name>` to lock a list), then asks the sixteen questions inside those rooms. Proving runs 2026-09-18: the first, on agent-guessed rooms, came back off-topic and stayed in the run record; the second, on the sun-damage sub-avatar with discovery, found five on-topic forums and filed 124 receipted rows into `brands/<brand>/core-avatars/<avatar>/language/deep-research/`. The copy machine fires the same gatherer before expansion and close (`the team notes`, prompts v4).

## the owner's corrections, applied

1. Agnostic pronouns — the viewer, the avatar, the speaker, they; a linter gates every prompt.
2. Depth is an option at expansion, sourced from the bank and research, never forced on a hook.
3. Voice cloning is the process — clone a cast voice, adjust it; the guard is rights on file, not a ban.
4. The lane is selected per run and printed; without a flag the run takes 1b's recommendation.
5. New stages are wired and the chain resolves every stage on both routes.

## Deliberately not done

- The doctrine is our own words with line pointers; the book sits beside it on the owner's ruling. No coined framework or section. No scene length as a number anywhere.
- The acceptance run (one fresh swipe through the whole chain on the AI lane) is the owner's call on when to spend it.
- The chain runner's copy of the teardown chain is a snapshot its owner resyncs; `the team notes` lists the cloned lanes for a ruling.

