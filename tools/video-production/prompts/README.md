# Prompts

Same convention as the teardown machine: one folder per stage, one file per
version, `stageN-name-vN-damon.md`, superseded versions in `archive/`.

Two chains have prompts in here. **The cinema chain is the live one.**

---

## The cinema chain — LIVE

Brief in, assets out. It ends at the offer cards; captions, the cut and
delivery are the editor's, downstream. `machine/chain.py` gates every stage on
the brief's own counts.

| stage | prompt | what it makes |
|---|---|---|
| 0 · Read the brief | `stage-0-read-brief/` *(mechanical, no model)* | the plan, covering every item the brief asks for |
| 1 · Openings | `stage-1-openings/stage1-openings-v1-damon.md` | one hook per opening in the brief |
| 2 · A-roll | `stage-2-aroll/stage2-aroll-v2-damon.md` | the talking spine |
| 3 · B-roll | `stage-3-broll/stage3-broll-v1-damon.md` | the cutaways |
| 4 · Offer cards | `stage-4-offer/stage4-offer-v2-damon.md` | price and guarantee on screen |

**These files are the product.** The shape a prompt takes is what makes the
output consistent, so it lives here as a readable file rather than as a string
buried in `machine/prompt.py`. Change the file and every clip made after it
changes with it — uniformly, across every brief, without touching code.

### How a shape is read

Each file carries exactly one fenced `shape` block. `prompt.py` loads it and
fills the braces from the plan row. Everything outside the block is for the
person reading it — the rules, and what each rule cost when it was missing.
Any element referenced in the output has its facts appended automatically from
`../element-facts.json`, so a prompt never restates what a product is.

Every spoken stage runs the same two calls: `cinematic_studio_3_0` with the
line in the prompt and `generate_audio` on, then `voice_change` to the cast
member's voice element. Nothing silent sets `generate_audio`. See
`../THE-CINEMA-LINE.md`.

---

## The scene-production chain — SUPERSEDED

`stage-0-format-read`, `stage-1-cast`, `stage-1b-identity-plan`,
`stage-2-voices`, `stage-2b-ledgers`, `stage-3-scenes`, `stage-4-motion`,
`stage-4b-sound`, `stage-5-qc`, `stage-6-handoff`, and the `stage-v*`
variation stages.

The earlier, model-agnostic process driven by `machine/chain_config.json`.
Kept because the writing stages in it are good and some are worth lifting —
but it predates Cinema Studio, and its motion stage assumed a still-then-clip
route that married an audio file to a picture. That is the route the cinema
chain exists to replace. Do not run it for a talking ad.

**Four of its prompts are live again, by hand (2026-09-17).** The checklist
route in `../formats/RUN-PROTOCOL.md` — the run every format follows since
six pieces ran it end to end on 2026-09-16 — uses these four, the session
pasting the variables itself:

| stage | prompt | used at |
|---|---|---|
| 1 · Cast | `stage-1-cast/stage1-character-sheet-v2-damon.md` | before any still — clone from the source frame where the person is on film |
| 3 · Scene prompts | `stage-3-scenes/stage3-scene-prompts-v4-damon.md` | the stills; carries the product lock, the post list, the result budget, the section/emotion/outcome and the lines covered |
| 5 · QC | `stage-5-qc/stage5-qc-v2-damon.md` | every still, mode `glance`; `deep` on product-hero frames; problems classed fixable / ceiling |
| 6 · Handoff | `stage-6-handoff/stage6-handoff-v3-damon.md` | the editor pack, with line coverage, the post list, the loop, the scene arc, the receipt and the name |

The v1 files are in each stage's `archive/`.
