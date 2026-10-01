# The video machine — roadmap

**2026-09-17.** What lands, in what order, from the knowledge pack Damon
handed over (three 16 Sep run records, the director-layer QC spec, the
variation machine spec, the skills catalog) plus what was already built
today (gates, provider switch, format bank, one-file-per-format folder).
Ruling underneath: **no braindead entry** — every item below was judged
against what the repo already does; what duplicates it is skipped and named.

## The destination

**Print hundreds of ads a day, for several brands, with the machine doing the
work and Damon doing the judgment.** Three legs, in order:

1. **One command from brief to editor pack**, on any provider, every format,
   gated — and since 2026-09-18 nobody at the keyboard at all: every
   station direct, the talking beat and motion on fal Omni. (Was: except to submit on
   Higgsfield.
2. **The print line** — a queue of briefs, a worker that drains it (the Mac
   mini, on the company keys), sub-agents as the QC judges, a board that
   shows Damon the day's output and the receipts. Images and videos on the
   same line.
3. **Assembly** — the AI edit that cuts the produced scenes into finished
   ads, so hook / headline / scroll-stopper variations become a re-cut, not
   a re-shoot.

## What arrived, and the call on each

| In the pack | Call | Why |
|---|---|---|
| `pipeline-hardening-instructions` (R1–R10) | **done** | landed today as gates, slots and the provider table |
| `claude-code-patch-spec` | **mostly done; two pieces adopted** | its gates/ledger/preflight exist in better form. Adopted: PRODUCT LOCK + COMPOSITION into the **ai-lane brief** (the seam a Higgsfield session reads); the frames rules. Skipped: six prose guardrails appended to the teardown's CLAUDE.md — prose restated harder is the failure mode |
| `director-layer-qc-implementation` | **adopt** | genuinely new: the eye that catches a frame that passes the inspector and dies in the feed. Two prompts (motion QC, director pass), two gates, the self-correction tree, motion ceilings into the provider table, preflight refuses a clip with no verdict on file |
| `variation-machine-implementation` | **adopt the registry + copy axis; awareness via the teardown loop** | the registry is the scale lever (one row per axis, no code). Adopted: `machine/variations.json`, the stage-7 copy-variation prompt, `preflight.py variation`. Changed: the awareness axis runs the **teardown machine's own DR loop** (stages 4a–4e) with a new awareness input — not a 380-line prompt that re-describes it |
| `variation-framework-spec-v2` | **reference** | the definitions; superseded by the implementation doc |
| `copy-variation-stage-spec` | **skip** | superseded by the same |
| `skills-catalog` | **reference for leg 2** | the chat-side skills (video-generation, ad-frame-generation, character-sheet, soul-identity, audio-generation…) are what the sub-agents will mirror when the print line is built; nothing to embed now |
| worked examples: <run> · <run> · <run> | **file as run records** | the "lost" 16 Sep records. Text only, under `runs/video-machine/<brand>/<label>/`. They also correct the bank (below) |

**What the records corrected.** <run> = song-ad (as banked). <run> =
single-presenter with a demonstration beat (banked; not the expert-consult
piece). <run> = a three-person "expert consultation" vlog with price
anchoring — no row in the bank fit it at the time, so it entered as its own
draft row. **Update, 2026-09-17:** Damon ruled that draft row and the
storytelling draft (inferred from that same 16 Sep session, before <run>'s
record was filed) are one and the same piece — `expert-consult` is the
name, and `formats/storytelling.md` is retired. The meme draft stays a
draft: the run it was inferred from (the collar-pull slap, the eleven clips
of one man) is still unrecorded. Two of the three handoffs baked a post
effect into a generation prompt and none carried line coverage or a
receipt — exactly what today's gates now refuse.

## The order

| # | Build | Leg | Status |
|---|---|---|---|
| 1 | File the three run records; fix the bank | 1 | landed 2026-09-17 (tested locally; nothing live yet) |
| 2 | Director pass + motion QC (prompts, gates, preflight verdict check, motion ceilings in the provider table) | 1 | landed 2026-09-17 (tested locally; nothing live yet) |
| 3 | **`machine/run.py` — start · record · pack.** One command; fal submits itself, Higgsfield gets a submit sheet; every job to the ledger; the editor pack from the records | 1 | landed 2026-09-17 (tested locally; nothing live yet) |

**Known gap (build 3):** fal's motion station is image-to-video and the
talking-beat plan carries no start image — named in `machine/RUN.md`, first
real fal run decides.

| # | Build | Leg | Status |
|---|---|---|---|
| 4 | Ai-lane brief v6 — PRODUCT LOCK + COMPOSITION blocks (the seam) | 1 | next |
| 5 | Variation registry + copy-variation prompt + `preflight.py variation`; awareness axis wired to the teardown loop | 1→2 | next |
| 6 | The print line: `queue/` of briefs → worker on the mini (`lab-run`, company keys) → sub-agent QC judges → the board (day's output, receipts, flags). Image lane on the same queue | 2 | design after 3 |
| 7 | Retire the Cinema line's board/chain/pull behind the runner | 2 | after 3 — Damon's call which tools go; nothing moved (2026-09-18) |
| 8 | Assembly: the AI edit (`video-assembly-line`, ffmpeg) fed by the editor pack; hook / headline / scroll-stopper variation as a re-cut of the opening + the copy axis | 3 | after 6 |

## What is deliberately not done

- **Follow-up, not yet scoped:** image ads through the same second door —
  `components/video-teardown/machine/compose.py`'s choice-not-swipe lane
  (avatar x awareness x format x framework, `components/marketing-doctrine/
  ad-frameworks.json`) — so a photo ad can also be composed rather than
  torn down from a swipe.
- No new prose rule anywhere a gate exists.
- No chain-config stages that nothing runs — `chain_config.json` stays the
  rendered design; the runner is the truth.
- No second copy of the DR loop inside this machine.
- No format coined: <run>'s shape is named by Damon, not by a session.
