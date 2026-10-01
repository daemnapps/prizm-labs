# AI video production

**A brief goes in. Finished clips come out — one command, nobody at a keyboard.**

This lane is brand-, provider- and format-agnostic. Nothing in `machine/`,
`prompts/` or `formats/` names a brand, a product, a person or a model — a run
names its brand and its format, and the provider is detected or picked. It is
the twin of `image-production`, which is stage two for statics.

## The spine

Full detail: `formats/RUN-PROTOCOL.md`.

1. **Teardown classifies and injects** → a baseline brief (`components/video-teardown`, its own machine).
2. **At stage 5 the route is decided** — creator (a real person) or AI. This protocol reads that decision; it never re-decides it.
3. **Stages 5–8 build the brief** for whichever route was picked.
4. **Creator route** → the brief goes to the person through the Google Sheet system. This machine stops.
5. **AI route** → the AI-lane brief is this machine's intake. Everything below is the AI route.

## Before a run: three choices

**Format** — a row in `formats/bank.json`, written from `formats/TEMPLATE.md`.
An unknown format is refused; a new one gets a profile and a row first.
Bank + all seven profiles: `formats/README.md`.

**The door** — not a choice since 2026-09-18: every station is a direct
call on our own keys (the one hand, below). `--provider fal |
higgsfield-mcp | higgsfield-ui` still exists to force a piece into a house
on purpose; nothing uses it by default. The ruling per model and door:
`providers/MODEL-HOUSE.md`; rates, ceilings, request shapes and the history
of every door ruling: `machine/providers.json`.

**Brand** — read, never written. A run's `brand` field points at
`brands/<brand>/`; there is no code to change to add one.

| the run names | and the lane reads |
|---|---|
| `"brand": "<brand>"` | `brands/<brand>/element-facts.json` — what is true of each product, and which elements are blocked |
| `cast.presenter` / `cast.who` / `cast.says` | the prompt shape names nobody; the identity comes from the plan |
| `cast.face` / `.room` | the cast sheet and the room reference the stills are seeded from |
| `brands/<brand>/ai-cast/<name>/voice.json` | the character's cloned ElevenLabs `voice_id` |
| — | Drive `Shared Assets/brands/<brand>/finals/<run>/` |

**To add a brand:** create `brands/<brand>/element-facts.json`, build its
cast (`building-the-cast.md`) with a `voice.json` per character, and point
a run at it. There is no code to change.

## The run — the protocol's gates, in order

One command runs the whole protocol (`machine/RUN.md`):

    python3 machine/run.py start  <brief.md | plan.json> --brand B --format F --label L [--provider P] [--yes]
    python3 machine/run.py record <run-dir> --direct          # (--results <file> for a forced house)
    python3 machine/run.py pack   <run-dir>

Full detail, including which gates each verb runs: `formats/RUN-PROTOCOL.md`.

| # | Gate |
|---|---|
| 1 | Platform plan shown |
| 2 | Preflight green |
| 3 | Generate stills |
| 4 | QC each still |
| 5 | Verify each still against its cast sheet |
| 6 | Motion, only on verified frames |
| 7 | Motion QC |
| 8 | Director pass |
| 9 | Coverage gate |
| 10 | Receipt |
| 11 | Naming gate |
| 12 | Editor pack |

### One hand (2026-09-18)

Every station is made by the machine, directly, in one command — the
17 Sep "two hands" folded when the talking beat and silent motion moved to
fal's Omni (Damon: "we don't need Higgsfield MCP for any of this now").

| Station | Door | Proof |
|---|---|---|
| voice | ElevenLabs, direct — cloned voice per character, made first | live 18 Sep |
| cast · still | OpenAI, direct — GPT Image 2.5 sunburst, fidelity high, moderation low | live 18 Sep |
| edit | Google, direct — Nano Banana Pro | live 18 Sep |
| song | Google Lyria, direct | live 18 Sep |
| **talking** | **fal Omni** → ElevenLabs speech-to-speech → remux · parity ≥85% twice (`machine/omni.py`) | live 18 Sep, one call, 63 s |
| **motion** (silent) | **fal Omni**, sound stripped | dry-run; first real cutaway proves it |

Wired and waiting: Seedance direct on BytePlus (`machine/direct_byteplus.py`)
— blocked on US billing. Declined: the Higgsfield API. Forced houses only:
Higgsfield (MCP / app), fal-as-a-house. Full ruling: `providers/MODEL-HOUSE.md`.

**The prompts are files.** `prompts/stage-0-read-brief` … `stage-6-handoff`,
versioned, on the teardown machine's convention. Each carries one fenced
`shape` block that `prompt.py` loads at run time. **Edit the file and every
brief made after it changes** — uniformly, without touching code. They are
rendered verbatim on the board, because a rule nobody can read is a rule
nobody can correct.

### Running it

    python3 machine/run.py start <brief.md> --brand B --format F --label L
    python3 machine/run.py record runs/video-machine/B/L --direct
    python3 machine/run.py pack   runs/video-machine/B/L

Or from the board — `python3 machine/board.py runs/<run>/` (:8456): press
Generate on a card and `machine/drain.py` makes the take on the direct
doors in the background (frame → line → Omni recipe; cutaway → Omni
silent), then the clip appears in the card. Proven live 2026-09-18 from a
two-order queue. `chain.py` (the gates as text), `pull.py` (a take back
from a house), `ship.py` (→ Drive finals) are unchanged in role.

## How a scene is generated (2026-09-18)

One setting, one paragraph of voice, one clip up to thirty seconds; two stills
(first and last) and the middle as timed beats. Voice first as one continuous
take with timestamps → first frame (GPT Image 2.5, cast sheet as reference) →
last frame (GPT edit, two references, colour-matched) → the clip (Seedance 2.5
on Higgsfield: start image + end image + the voice slice + the four-block
prompt) → line check → director. The method: `SCENE-GENERATION.md`; the
contract the gate enforces: `machine/model-inputs.json`.

## The doctrine and the research (2026-09-18)

The swipe side runs on Eugene Schwartz's frameworks, held once in
`components/marketing-doctrine/` and pulled into every machine: five
awareness levels (each with a must-not), five sophistication stages, seven
techniques, and the sections as a vocabulary of what each part of a
video is doing. Every swipe gets a doctrine read right after ingestion and
is banked in the framework bank; expansion reaches for a technique only with
a bank row or a research receipt; the spice pass adds the creative layer
with a cast voice cloned then adjusted, rights on file. The brief that
arrives here carries Section · Technique · Emotion · Outcome per scene, and
this machine's scene shapes and mood rules are bound from the same doctrine
(`{techniques}`, `{mood}`). Research fires by wiring: the language-bank
query and the research gatherer (`components/research-gatherer/`) resolve
as stage inputs on every run. Record: `PROMPT-CHANGES.md`.

## Where output goes

`runs/video-machine/<brand>/<label>/`, per the repo-root `runs/README.md`
(2026-09-17 ruling): `run.json`, `frames.json`, `lines.json`, `batches/`,
`ledger.json`, `deliverable/`. Media never enters git; `.gitignore` enforces
it. The local `M/runs/` and `machine/runs/` folders are gitignored media from
before that ruling — not the live destination.

## The map of this folder

| | What it is | Live / archive |
|---|---|---|
| `AI-CREATIVE-LINE.md` | the story of the whole line, swipe to motion | live |
| `BRIEF-SPEC.md` | the brief shape, ruled 2026-09-14 | live |
| `PLATE-CHECK.md` | the plate check — every still judged by measurement before anyone sees it | live |
| `building-the-cast.md` | how a character is built, once per person, serves every format | live |
| `frames-by-edit.md` | how a frame is made — a reference beats a description | live |
| `format-variation.md` | restyling an approved piece into a new visual format | live |
| `handoff-and-edit.md` | what the editor receives | live |
| `archive/THE-CINEMA-LINE.md` | the coded Higgsfield talking-ad route, proven 2026-09-12/13 — superseded by the Omni door | archive |
| `REPO-AND-DRIVE.md` | mirror of the Repo and Drive artifact | live |
| `PRINT-RUN-260912.md` | a print record — two finished ads, one torn-down source | live (record) |
| `chain_config.json` | the 13-stage design; only `machine/pipeline.py` reads it; two stages point at parked prompts | live (design, not the running code) |
| `formats/` | the bank (`bank.json`), one profile per format, `RUN-PROTOCOL.md` the run, `TEMPLATE.md` | live |
| `providers/` | `MODEL-HOUSE.md` (the door ruling per model) + `research/` dossiers + `fal.md` house notes; `higgsfield.md` and `EDITOR-SHEET.md` moved to `archive/` | live |
| `prompts/` | one folder per stage, versioned files, current at the top | live |
| `prompts/stage-5b-motion-qc/` | the motion QC prompt — gate 7 | live |
| `prompts/stage-5c-director/` | the director-pass prompt — gate 8 | live |
| `machine/` | the code — `run.py` + the direct doors (`direct_openai`, `direct_google`, `voice`, `omni`, `direct_byteplus`), the gates (`platform`, `preflight`, `lineparity`, `deliver`), `providers_fal` for a forced house | live |
| `machine/run.py` | the one runner — `start · record · pack` | live |
| `machine/omni.py` | the talking beat and silent motion on fal Omni — the controlled recipe as one call | live |
| `machine/providers_fal.py` | fal as a forced house, and the queue helpers `omni.py` reuses | live |
| `machine/RUN.md` | the runner's own page — authoritative for `run.py` | live |
| `ROADMAP.md` | the plan — three legs, in order | live |
| `archive/` | history — process, workplan, stages/, sequence-flow, evidence, parked-v1, the Cinema line, the editor sheet, Higgsfield house rules, See `archive/README.md` | archive |
| `runs/` | local pre-ruling media, gitignored | archive (superseded) |
| repo-root `runs/video-machine/` | where filed runs land, per `runs/README.md` — now holds the three filed 16 Sep runs | live |

## What is next

See `ROADMAP.md` — three legs, in order: one command (leg 1, landed), the
print line (leg 2), assembly (leg 3).
