# Scenes and spice — the plan (not yet applied)

**2026-09-18.** Damon's read of `copy-scene-implementation.md` (written in
Higgsfield after another run) plus his rulings in chat. Format-, brand- and
tool-agnostic; every change lands at the place in the chain that owns it.
Nothing below is installed until he says go.

## The rulings that reshape the document

1. **No fixed scene length, ever.** The document's "every song-ad scene is
   30–40 s" is NOT the intent. The intent: **a scene plays out fully** —
   its characters, its elements, its words, its pain or proof — and its
   length falls out of that. A format profile gives the length
   *philosophy*, never a number. A motion model's cap splits a scene at
   its boundary only, never by line.
2. **The swipe is number one.** Ingestion gets granular: every video is
   scenes; scenes have frames; every scene is labelled with the section of
   the argument it carries and every element in it is recorded.
3. **Clean injection first, then the spice.** After teardown + injection,
   a creative pass adds the flare: why this format is relevant to *this*
   avatar, and what makes it stand out — with research sub-agents fired in
   real time (the avatar's comedians, references, styling → a voice print
   in that register, a lookalike-type character in a failed-solution
   B-roll, styling per avatar). Receipts on every item; never a real
   person's face or voice.
4. **The week's goal:** one ad end to end with a clean DR edit, lip-sync
   working, captions with adjustable styles, and variants at scale.

## What the document gets right, and where each piece lands

| Doc | Call | Where it lands (owner) |
|---|---|---|
| A1 scene contract — 8 fields (duration, event, emotion, outcome, camera, staging, delta, boundary) | **adopt**, with *Duration* reworded: "chosen from the scene's content — long enough for its words, its action and its landing; never a number set by the format" | `formats/TEMPLATE.md` + every profile |
| A2 song-ad 30–40 s sections, "3:40 ad" | **reject** (ruling 1). The song-ad profile keeps "a scene never splits a section"; length = the section's own length | `formats/song-ad.md` — one sentence, no numbers |
| A3 chain note "song-ad scenes are 30–40 s" | **reject** | — |
| A4 stage-3 scene prompts: `Emotion:` `Outcome:` lines; rule 7 "the scene lands" | **adopt** (v3 → v4) | `prompts/stage-3-scenes/` |
| A5 director pass: "THE SCENE LANDED" (feeling readable, delta moved, outcome reached) | **adopt** (v2 → v3) | `prompts/stage-5c-director/` |
| A6 scene-arc table in the edit doc | **adopt** | `handoff-and-edit.md` |
| A7 CLAUDE.md ruling paragraph | **adopt**, agnostic wording (no song-ad sentence) | `CLAUDE.md` hard rules |
| B1 4a read: "WHAT THE SOURCE KNEW" (private moment · bias · cultural rule, cited) | **adopt** (stage4r-read v3 → v4) | `components/video-teardown/prompts/stage-4-loop/4a-read/` |
| B2 4b hooks: private moment + bias + cultural rule per variation; THE KNOWN TEST | **adopt** (stage4b-hook v11 → v12) | `…/4b-hook/` |
| B3 close: name the flinch before the offer | **adopt** (stage4d-close v6 → v7 — the doc's file names are off by one stage; the real files are `stage4d-close`, `stage4e-audit`, `stage4r-read`) | `…/4e-close/` |
| B4 audit: checks 8–10 (KNOWN, SOURCE, BIAS) | **adopt** (stage4e-audit v3 → v4) | `…/4f-audit/` |
| B5 ai-lane brief: every section carries `Emotion · Outcome · Bias` | **adopt** (v5 → v6) **and fold in the roadmap's pending PRODUCT LOCK + COMPOSITION blocks** so the brief bumps once | `…/stage-5-brief/ai-lane/` |
| B6 stage-3 rule 8 "the copy is the spine" | **adopt** (same v4 as A4) | `prompts/stage-3-scenes/` |
| B7 handoff: THE LOOP + the scene arc in THE INTENDED SHAPE | **adopt** (v2 → v3) | `prompts/stage-6-handoff/` |

## What the document does not have — Damon's additions

### N1 · Granular ingestion — teardown stage 1 → v9, with a section vocabulary
- **The section vocabulary** (a bank, not prose — Damon's own list, in his
  words): hook · problem · failed solutions · root cause · unique mechanism
  · solution · product · offer · call to action. A swipe whose scene fits
  none is labelled with the teardown's plain description and **flagged as
  a candidate row** — never coined into the bank by a session.
  Lives at `components/video-teardown/banks/sections.json` (brand-agnostic;
  the teardown component is Damon's).
- **Stage 1 records per scene:** its section label · its frames (one row
  per distinct visual change, as today) · the eight scene-contract fields
  *as observed in the source* · every element present: characters,
  props/products, words said, on-screen text, sounds, the pain or proof
  shown. The record is what stage 2 (structure) and stage 3 (injection)
  build on, so the brief's sections and the production's scenes stay 1:1
  with the source's.
- Scene = a section of the asset; frame = a distinct visual moment inside
  it. Stated once at the top of the prompt.

### N2 · The spice — a creative pass after injection, with research triggers
- New teardown stage **4g · spice** (after 4f audit, before the brief):
  input = the injected script + the avatar profile + the brand's banks;
  output = a **spice sheet** appended to the brief, every item with a
  receipt (the avatar profile line, a customer verbatim, a cited research
  result).
- **Research sub-agents fired from the stage:** "what does this avatar
  laugh at / watch / quote / wear" → cited options. In a Claude Code run
  the machine spawns them as agents; on the print line as worker jobs.
  The stage names the questions; the sub-agents return receipts; the
  stage picks and writes the sheet.
- **What the sheet may hold:** voice direction (which cast voice, cloned
  and then adjusted — pitch, pace, register — with its rights entry on file
  in the brand's cast folder; the guard is rights, not a ban — Damon,
  2026-09-18: "we are cloning people's voices and then adjusting them"), a
  lookalike-type character for a B-roll beat
  (written identity only, deliberately different face — the variation
  rule already in `brands/_TEMPLATE/ai-elements/characters/CHARACTER-SPEC.md`), styling
  and register per avatar, format-relevance line ("why this format works
  for this avatar").
- **Gates:** every spice item cites a source; no real likeness, no real
  voice; the spice never changes the offer boundary or the product truth.

### N3 · The week's goal — leg 3 pulled forward
- Assembly: the DR edit from the editor pack (scene arc + the loop as the
  cut's spine); lip-sync from the proven talking door; **captions from
  the ElevenLabs character timestamps** (they exist already — the direct
  door returns them) with a **caption-style bank** (a row per style, the
  editor's slot); variants = hook / headline / scroll-stopper swaps as a
  re-cut of the opening plus the copy axis.

## Order

| # | Build | Where | Why first |
|---|---|---|---|
| 1 | Section vocabulary + teardown stage 1 v9 (granular scenes) | video-teardown | the swipe is number one; everything downstream inherits the scene record |
| 2 | Intimate copy through the loop: 4a v4 · 4b v12 · close v7 · audit v4 | video-teardown | the words are the spine of every scene |
| 3 | Spice stage 4g + research triggers + the spice sheet | video-teardown | the flare, after clean injection |
| 4 | Ai-lane brief v6: sections · Emotion · Outcome · Bias · product lock · composition | video-teardown | the seam both machines read |
| 5 | Scene contract in the template and profiles; stage-3 v4; director v3; handoff v3 + arc + loop; CLAUDE.md | ai-video-production | production renders the scenes as authored |
| 6 | Assembly: edit · captions + style bank · variants | ai-video-production (leg 3) | the week's goal |

## Deliberately not done
- No numbers on scene length anywhere.
- No song-ad-specific rule outside the song-ad profile.
- No coined section names — the vocabulary is Damon's list; gaps are flagged.
- No real person's face or voice, in the spice or anywhere.
