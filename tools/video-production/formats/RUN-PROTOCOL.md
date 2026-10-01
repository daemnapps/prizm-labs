# The run protocol — the one run every format follows

**2026-09-17.** Written after six pieces ran the route end to end on
2026-09-16 across three formats and cost ~$55 an ad against a $3–4 floor.
Every dollar of the gap was a gate that did not exist: wrong-person frames
sent to motion, labels invented from prose, post-effects baked into
generation, re-rolls chasing what a model cannot do, lines dropped, spend
unrecorded, packs shipped unnamed. This page is those gates, in order.

**Format-, brand- and tool-agnostic, stated plainly.** Nothing here names a
format, a brand, a product, a person or a model. A format profile says what
a scene contains; the brand folder says whose product it is; the provider
decides the model. The protocol is the same run for all of them, and a
teammate who clones the repo runs it on their own accounts.

## The spine

1. **Teardown classifies and injects → a baseline brief.**
   `components/video-teardown`, its own machine.
2. **At stage 5 the route is decided** — creator (a real person) or AI. The
   teardown records `production_route`. This protocol *reads* it; it never
   re-decides.
3. **Stages 5–8 build the brief for that route.**
4. **Creator route** → the creator brief goes to the person through the
   Google Sheet system. This machine stops.
5. **AI route** → the AI-lane brief is this machine's intake. Everything
   below is the AI route.

## Intake

A run home at `runs/video-machine/<brand>/<label>/` (per `runs/README.md`)
holding `run.json`:

    machine: video-machine · brand · label · format · source_brief

`format` must be a row in `formats/bank.json`. An unknown format is
refused — a new one is written from `formats/TEMPLATE.md` and added to the
bank first. `source_brief` may itself carry a spice sheet — the
format-relevance line, the voice-print register brief, the lookalike-type
B-roll character and the styling notes the teardown machine's 4g-spice
stage wrote, every item cited. This protocol reads it as one more brief
input, same as the rest of `source_brief`; it never writes or edits one.
The run's other files: `frames.json`, `lines.json` (every line
the piece carries — spoken, sung, on-screen — as `{"L1": "the line as
written", …}`), `batches/`, `ledger.json`, `deliverable/`. The run's
verdicts live in `<run>/verdicts.json` —
`{"<item id>": {"inspector": {...}, "motion": {...}, "director": {...},
"parity": {...}}}` — written by `preflight.py verdict` (`parity` is written
automatically by `run.py record` / `machine/lineparity.py` on every clip
that carries a line).

## The scene shape (2026-09-18) — what a run is made of

**How a scene is actually generated, step by step, is `../SCENE-GENERATION.md`
— the method page; this section is the run's checklist of it.**

Damon's ruling that day, in one line: **a scene is a paragraph, and the
things inside it are frames, not scenes.** What that means for a run:

1. **VOICE FIRST, AS ONE TRACK.** The whole piece is read once, chunked per
   scene paragraph, stitched request to request so the read never restarts
   (`machine/voice.py`). It lands as `<run>/vo/track.mp3`, with
   `<run>/vo/timing.json` saying where every scene and every sentence sits
   on that one timeline and `<run>/vo/<scene>.mp3` as the slice the talking
   door dubs. **Nothing else in the run generates until this exists** — the
   clip prompts are timed against it.
2. **TWO STILLS A SCENE.** The FIRST FRAME is generated, in the stills
   door's own order, carrying the scene's references. The LAST FRAME is an
   EDIT of the first, naming only the delta, and it always sends two
   references — the frame first, the cast sheet second. A last frame whose
   camera pushes in or takes a new angle runs on the fidelity door instead;
   every edit is colour-matched back to its first frame before it is
   verified.
3. **BEATS ARE NOT PICTURES.** What happens between the two frames is
   written into the clip prompt's own timeline, one verb a beat, its span
   read off the voice track. Never generated as a still.
4. **ONE CLIP A SCENE.** One call carries the whole scene: the first frame
   as `start_image`, the last frame as `end_image`, and — to camera — the
   scene's own slice of the track as `audio_references`; otherwise silent
   motion. **Nothing else travels on the clip** — the first frame already
   carries the identity, the wardrobe, the room and the light, so a cast
   sheet or a style frame attached beside it is a second opinion about the
   same face. The prompt is the maker's four blocks. Aspect and resolution
   are the piece's, declared once; duration is the paragraph's, rounded up.
5. **THE CONTRACT GATE.** Every item is validated against
   `machine/model-inputs.json` — the model input contract, rendered for
   reading as `machine/MODEL-INPUTS.md`. A missing required field, a beat
   with two verbs or none, a frame with no delta, an edit with one
   reference, a scene with anything but its two frames, a to-camera scene
   with no audio slice, more beats than the maker's panel limit, a
   paragraph past the door's duration ceiling — each is RED with the field
   named, and **nothing submits red**.

## Stations

`cast` · `still` · `restyle` · `motion` · `voice` · `audio`. Provider-neutral
names. The provider decides which model sits in which station; the run
never names a model, it names a station. Rates and ceilings per model live
in `machine/providers.json`.

## The doors, as ruled 2026-09-18 evening

Damon's ruling, 2026-09-17 ("we scale tomorrow"), put motion and the talking
beat with the editors. **On 2026-09-18, twice:** the morning put every image
call on one door, and the evening put motion AND the talking beat on Seedance
2.5 through Higgsfield — "let's just do the higgsfield seedance frame" —
first frame, last frame and the voice slice on one call, proven live that day.
The fal Omni door from the afternoon is an alternate, not the print door.

| Station | Door | Who |
|---|---|---|
| voice | ElevenLabs, direct — one cloned voice per character, ONE continuous track for the piece, made first | nobody — `run.py start` |
| cast · still | OpenAI, direct (GPT Image 2.5) — the one image door | nobody |
| edit | OpenAI, direct (GPT Image 2.5, `images/edits`, input fidelity high) | nobody |
| song | Google Lyria, direct | nobody |
| talking | Seedance 2.5 on Higgsfield — `start_image` + `end_image` + `audio_references`, mode `omni_reference` · line parity on the way back | the editor's sheet |
| motion (silent) | the same door, the same recipe, no audio attached | the editor's sheet |

The editor sheet (`SUBMIT.md` → `results.json` → `record`) still exists
and is written **only when a house is forced** with `--provider`. The
editor's page moved to `../archive/EDITOR-SHEET.md`. History of the door
rulings: `machine/providers.json` → `_history`.

## One command

`machine/run.py` (see `machine/RUN.md`, the runner's own page — authoritative)
runs this protocol as three verbs:

| Verb | Gates it runs |
|---|---|
| `start` | 1–2 (platform plan, preflight), then makes every station direct — voice, cast/stills, edits, song, talking, motion — into `media/` + `direct.json`; writes a submit sheet only if a house was forced |
| `record` | 6 — `--direct` records the machine's own clips (line parity on every talking beat); `--results` takes a forced house's results back in |
| `pack` | 9–12 — coverage, receipt, naming, editor pack |

**The gates are unchanged; `run.py` runs them in order.** The by-hand commands
in the table below remain valid for running a single gate on its own.

## The gates, in order

Each gate names its command and the prompt it uses. A gate that is not
passed is not a gate that was skipped; it is a batch that did not run.

| # | Gate | Command / prompt |
|---|---|---|
| 1 | **Platform plan shown.** The platform is detected; station → model → rate → ceiling → estimated cost printed before anything runs. Confirm where the provider's `confirm` is true. | `python3 machine/platform.py --batch <batch.json> [--provider fal\|higgsfield-mcp\|higgsfield-ui] [--yes]` (run.py start) **(machine)** |
| 2 | **Preflight green.** Character reference present · product reference present · no post-effect words in a still's prompt · `start_image` is a UUID · batch ≤ cap · motion ≤ model ceiling and its start frame `verified` · line coverage · model offered by the provider · format in the bank · the no-cut line on every motion prompt · **the contract gate** (rule 12): every scene-shape item complete against `machine/model-inputs.json`, each defect named by its field. Exit 2 names every failure. Nothing submits on red. | `python3 machine/preflight.py check <batch.json> --run <run-dir>` (run.py start) **(machine)** |
| 3 | **Generate stills.** Cast sheets first, then TWO frames a scene — the first generated, the last an edit of it with two references, colour-matched back to it. Every still carries its cast sheet and, where the product is in frame, the packshot. | `prompts/stage-1-cast/stage1-character-sheet-v2-damon.md` · `prompts/stage-3-scenes/stage3-scene-prompts-v6-damon.md` · `machine/MODEL-INPUTS.md` **(machine)** |
| 4 | **QC each still.** Mode `glance` on every frame. `deep` only on product-hero frames. Every problem carries a `defect_class`. | `prompts/stage-5-qc/stage5-qc-v2-damon.md` with `{mode}` and `{ceilings}` pasted **(machine)** |
| 5 | **Verify each still against its cast sheet.** A check not written down did not happen. | `python3 machine/preflight.py verify --run <run-dir> <media-uuid> --shot <id> --by <who>` **(machine)** |
| 6 | **Motion, only on verified frames.** Batch ≤ cap. Fast tier unless the frame is a hero. **A ceiling ships FLAGGED with zero re-rolls**; a fixable defect gets one re-prompt, then a re-composition, never a third try on the same composition. **Every submission goes to the ledger**, billing-ambiguous ones (blocked, refused, stuck) with their status. | `python3 machine/preflight.py ledger --run <run-dir> --model <slug> --job <id> --seconds N --status done\|nsfw\|ip_detected` (run.py record) **(editor)** |
| 7 | **Motion QC.** Every clip checked: identity hold, product constancy, anatomy window, camera motivation, one-action, lip-sync class. Ceilings FLAG and ship, never re-roll. · **line parity**: the clip is transcribed and must say its line (≥ 85% match); a clip that says other words is not the clip. | `prompts/stage-5b-motion-qc/stage5b-motion-qc-v1-damon.md` · `python3 machine/lineparity.py --run <run-dir> <item-id> --clip <path>` (run.py record, automatic) **(machine)** |
| 8 | **Director pass.** Every scene read by the director's eye: half-second answer, scroll-stopper, dramatization, the motion read ACROSS its frames (first frame held, last frame reached, the delta happened), format register · believability bar · the delivery across the whole paragraph, with no restart between sentences. Two director FLAGs on one scene = rework the scene in the script, not the render. | `prompts/stage-5c-director/stage5c-director-v5-damon.md` **(machine)** |
| 9 | **Coverage gate.** Every line in `lines.json` is carried by exactly one clip. An uncovered line is an undeliverable pack. | `python3 machine/preflight.py coverage --run <run-dir>` (run.py pack) **(machine)** |
| 10 | **Receipt.** Jobs, credits, dollars, of which re-rolls, ambiguous jobs separate, model slugs as recorded — from `ledger.json`, never from memory. | rendered into the handoff's THE RECEIPT (run.py pack) **(machine)** |
| 11 | **Naming gate.** Nothing leaves a run unnamed. | `python3 machine/deliver.py <run>` (run.py pack) **(machine)** |
| 12 | **Editor pack.** Into `deliverable/`. Carries LINE COVERAGE, POST, THE LOOP, THE ASKS, THE RECEIPT and THE NAME. | `prompts/stage-6-handoff/stage6-handoff-v5-damon.md` with `{ledger}` and `{lines}` pasted (run.py pack) **(machine)** |

Two rules that run underneath every gate:

- **One blocking poll per run.** State is restored from the run record, not
  rediscovered by re-reading files.
- **Sweep every ledger page before quoting spend.** A total read from one
  page is a guess.
- **Two QC layers, two verdicts.** The inspector's PASS is "it is the scene
  that was specified." The director's PASS is "it will stop a thumb." An
  asset needs both; an inspector-PASS that fails the director is a feed
  death, caught here instead.

## What a format profile may add

What a scene contains · the beat shape · the references it needs · which
stations it uses. **Never its own copy of a gate.** A profile that adds a
gate is a profile that will drift from this page; the gate belongs here,
and the profile points at it. `formats/TEMPLATE.md` is the shape.

## Providers

The switch is `--provider` on `machine/platform.py`; with no flag the
platform is detected. Each provider's notes — the parameter shapes, the
misfires, the things learned at that house — are one page per provider in
`../providers/` (`fal.md`, `higgsfield.md`). A note learned on one format
applies to every format on that provider, so it is filed by provider,
never under a format.
