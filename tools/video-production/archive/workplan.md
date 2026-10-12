# The Video Machine — the surgical map

> **⚠ STALE — a planning map from 2026-08-30 with item ids (A2, B4, E2…).** The items were written before the method changed. Treat the ids as history, not as a queue.
>
> Live method docs: `frames-by-edit.md` (how a frame is made), `building-the-cast.md` (how a character is built — its own process), `formats/song-ad/` (a format, proven end to end).


v2, 2026-08-30 (the owner's reset: assume nothing is complete, nothing is
final — this is a foundational build-up, brand-agnostic and model-agnostic,
fal as the model source, always picking the best). Every discrete piece of
the workflow, top to bottom. Items are addressed by id (A2, B4, E2…).
Status: **ran once** = worked at least once, NOT final; **baseline** =
partially there, needs real work; **open** = not built or not tested.
Priorities at the bottom are proposals until the owner rules.

**Current focus (the owner's ruling): A — brief intake.** The workflow is
drafted in `stages/00-brief-intake.md` from his real brief format.

## Standing rulings (the owner, 2026-08-30)

1. **Smooth and human beats runtime.** Voice runs at natural pace by
   default. The brief's timecodes are guides, never a reason to rush a
   line. The pacing dial's job is flagging lines that would sound rushed —
   not fitting a stopwatch.
2. **Everything on screen is a digital artifact.** The machine is agnostic
   on every axis — brand, video, product, avatar, content. The general
   capability is: generate the imagery, animate it, sequence it so people
   understand the message. Where something can't be generated believably
   (a phone screen, a real photo, a real label), the SAME pipeline
   composites a real or constructed artifact into the shot — a standard
   move, never a per-video hack.
3. **Minimize the models — and each plays to its strengths
   (2026-08-31).** Approved: Google (Omni · Nano Banana) · ByteDance
   (Seedance · Seedream) · GPT image · ElevenLabs. MiniMax and Kling
   retired. The role map: Seedream = stills + identity chaining ·
   Nano Banana = EDITING (layout-exact recreations, compositing real
   artifacts into shots) · GPT image = photo-referenced / exact-recreate
   work · Seedance + Omni = clips as first-class peers, picked per shot
   · ElevenLabs = voice.
4. **Control first, variants after.** Build the control opening + body,
   review, then generate the other hook variants once the body is
   approved. Draft-first applies to variants too.

Sources: process.md, stages/*.md, sequence-flow.md, the three-sleeves and
elder-presenter runs, the handoff spec.

## The swap frame (the owner, 2026-08-30) — what this system IS

Swapping, mixing and matching based on data: **swap creators · swap
formats · swap angles · swap AI models · swap actors · swap headlines.**
Every axis is a bank of interchangeable assets (creators/, ai-cast/,
formats from teardowns, hooks from stage 4b, model slots); a run is one
combination; the data decides the next combination.

## The production routes (the owner's frame, 2026-08-30)

Every teardown record adapts to any production route, and to any format
the avatar is receptive to — that is the point of the system.

| id | Route | Status | Note |
|---|---|---|---|
| R1 | Creator — a real person films the brief | ran once | the teardown machine's current output; workflow essentially done |
| R2 | AI — this machine generates it | baseline | current focus; no dependencies on anyone |
| R3 | Founder — she films it herself | **open** | founder is an influencer; same script + a founder-only adjustment (e.g. the "why I made this" close). Built into the teardown vars, never fleshed out |

## A — Brief intake (brief → timeline)

| id | Piece | Status | Note |
|---|---|---|---|
| A1 | Brief contract — what a finished brief hands over | baseline | written down 08-30 from the real brief (stage-0 doc); the owner to correct |
| A2 | Brief parser: brief in → inventory → timeline out | ran once | machine/intake.py runs 0.1–0.10 on the real brief: checks, gate, manifest, draft timeline |
| A3 | Brief = read-only truth, timeline = working copy | ran once | the standing rule |
| A4 | Openings as variants — one body, six hooks, six cuts | baseline | variants land in the draft timeline, control flagged first (ruling); carrying them through assembly still open |
| A5 | Hard-shot playbook — phone screens, photos-in-hand | **open** | AI can't render real screens; each needs a standard treatment |
| A6 | Pacing check | ran once | RULED: smooth beats runtime — natural pace always; the dial just flags rushed lines |

## B — Cast

| id | Piece | Status | Note |
|---|---|---|---|
| B1 | Master still (photo-ref route / description route) | ran once | both routes shipped |
| B2 | Identity chaining — every still an image-edit with the master as reference | ran once | killed drift across 9 shots, 3 outfits |
| B3 | Cast bank: reusable characters across runs (name + master + voice binding) | baseline | brands/<brand>/cast/ holds 6 refs from the proven runs; per-character folders + voices + board rail still open |
| B4 | Real packshot bank per brand | baseline | the REAL Brand A tube + full product context live at brands/<brand>/products/body-scrub/ (the owner's convention: folder per product, MD + images + Drive links); wiring it into shots is the cast-station pass |
| B5 | Wardrobe table per run | ran once | three outfits, no drift |

## C — Voices

| id | Piece | Status | Note |
|---|---|---|---|
| C1 | Persona paragraph → base take → chain every line | ran once | |
| C2 | Accent lock (stack two best takes, name the phonetics) | ran once | |
| C3 | Voice picker: browse voices, preview (one cheap TTS call), bind per character | **open** | board element |
| C4 | Pacing calibration — VO duration drives the cut | ran once | RULED: natural pace, timecodes are guides; the cut follows the voice |
| C5 | Take banking: keep/pick across takes | open | |

## D — Scenes

| id | Piece | Status | Note |
|---|---|---|---|
| D1 | Locked blocks (person / room / camera) pasted into every prompt | ran once | |
| D2 | Realness dial: camera-block presets | baseline | UGC proven verbatim; Polished/Cinematic drafted, unproven |
| D3 | Multi-scene briefs: per-scene room blocks, maybe per-scene masters | **open** | the 18-frame brief needs it |
| D4 | Multi-reference scene composition (2+ faces, product in frame) | ran once | ran once in the elder-presenter run; not yet in the fal flow |
| D5 | Drift rate down — prop timing, framing, eye-line | baseline | 3/9 drifted on first pass; per-shot redo is the answer, drift rate is THE metric |

## E — Motion

| id | Piece | Status | Note |
|---|---|---|---|
| E1 | Talking shots — draft lip activity from "she is speaking this line" | ran once | believable at draft, not close-up-shippable |
| E2 | True lip-sync pass on approved clips only | **open** | audition needed; the shippability gap |
| E3 | Cinematic shots (refs + written direction) | ran once | |
| E4 | Product heroes | ran once | blocked on B4 for shipping |
| E5 | Transitions (first frame + last frame) | baseline | wired via Omni; endpoint unstable |
| E6 | Cheap-draft clip slot (360p) vs stable slot | baseline | Kling stable; Omni ~10× cheaper, buckling — re-audition when it settles |
| E7 | Second on-screen character | open | untested |

## F — Sequence & assembly

| id | Piece | Status | Note |
|---|---|---|---|
| F1 | timeline.json as the edit surface | ran once | |
| F2 | Free deterministic assembly (pad/trim to VO, text cards, concat) | ran once | |
| F3 | Invalidation table — every edit priced before running | ran once | wired into the board today |
| F4 | Music/SFX bed | open | trivial in assembly, untested |
| F5 | Graphic-card shots ($__ — held still + text, no generation) | baseline | pattern named; not wired as a shot kind |

## G — Finalize & delivery

| id | Piece | Status | Note |
|---|---|---|---|
| G1 | Approval gates quality spend (draft-first) | baseline | checkboxes on the board; nothing enforces the gate yet |
| G2 | Finalize: re-render approved shots at delivery quality (draft→4K) | **open** | the quality unlock; Omni upscale is the candidate |
| G3 | Delivery: naming, packaging, where finished films land | open | |

## H — The board (the working surface)

| id | Piece | Status | Note |
|---|---|---|---|
| H1 | Shot grid — still+clip+VO per card, editable fields, priced redos | ran once | today |
| H2 | Scene panel — blocks, presets, blast warning | ran once | today |
| H3 | Voice controls | baseline | id + speed; picker/preview is C3 |
| H4 | Sequence lane | baseline | reorder arrows + free assemble; drag/trim later |
| H5 | Economics strip | baseline | estimates; true per-job cost accounting open |
| H6 | Brief intake on the board | open | pairs with A2 |
| H7 | Cast rail | open | pairs with B3 |
| H8 | New run from the board | open | today a run folder is made by hand |

## I — Going local (the stated end state)

| id | Piece | Status | Note |
|---|---|---|---|
| I1 | Slot auditions for local models — cast / voices / scenes / motion | open | audition criteria written in process.md |
| I2 | Cloud occupants (fal) as the working baseline | ran once | measured costs in sequence-flow.md |

## Proposed priority (the owner rules)

**P1 — the foundation, stage by stage (current, per the owner's ruling):**
A brief intake first — contract, parser, variants, hard shots, pacing
budget (A1–A6) → then B cast → C voices → D scenes → E motion → F
sequence & assembly, each rebuilt as if new. FAL key on the machine
(the owner, one action) unlocks live testing while we build.

**P2 — reuse and shippability:** B3+H7 cast bank/rail (run #2 gets cheap) →
C4 pacing rule → E2 lip-sync audition → G2 finalize pass.

**P3 — board comfort:** C3 voice picker, H4 drag-reorder, H5 true costs,
H6 brief intake UI.

**P4 — scale-out:** D3 multi-scene, E7 second character, F4 music bed,
then I1 local auditions once the cloud line is ramped.
