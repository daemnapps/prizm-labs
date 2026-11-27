---
name: video-production
description: Run the video machine — an AI video brief goes in; the voice, the stills and the clips come out, judged, in the run's folder. Use whenever someone says "run this brief through video production", "produce this video for a brand", "make the clips for this brief", "run the AI lane", "generate the scenes", "start the video machine", "pack the run", or hands over a brief (or a plan) and names a brand and a format.
---

# Video production

> **Activates component:** `components/video-production` — `machine/run.py`, voice, stills and clips.


External dependencies: `components/video-production/` (the machine; `machine/RUN.md` is the full account, `formats/RUN-PROTOCOL.md` the protocol), `brands/<brand>/` (products, ai-cast, offers — read, never written), `components/elements` (the format and style rows), `components/marketing-doctrine` (scene shapes and mood, bound).

Read `components/video-production/CLAUDE.md` and the selected format's current workflow before running.
Check the registered brief's `production_route` against its writing run. This skill produces the `ai` route.
For `creator` or `founder`, use `components/image-edit/handoff.py <brief-key> --brand <brand> --no-drive`
to build the filming assignment; its return enters `delivery.py --ingest-filming` and the existing video-edit kit door.
Do not generate substitute scenes because a human route has no AI production run. A draft packet is planning only.

**One command in three steps. Nothing submits without a green preflight.**

```
python3 components/video-production/machine/run.py start <brief.md | plan.json> --brand <brand> --format <format> --label <label> --dry-run
python3 components/video-production/machine/run.py start <brief.md | plan.json> --brand <brand> --format <format> --label <label>
python3 components/video-production/machine/run.py record <run-folder> --direct
python3 components/video-production/machine/run.py pack <run-folder> [--dry-run]
```

- `--brand`, `--format` (a `format/video` row in the element library) and
  `--label` are all required. There is no default brand.
- **`--label` is the brief's register id, `brand_product_brief-NNNN` (e.g. `Brand A_flex_brief-0070`, from `components/image-teardown/briefs.json`) — so the production run, the edit run and the delivery all carry the brief number (the owner, 2026-10-15). A brief with no number yet gets one first (`components/video-teardown/machine/file_run.py` `number_brief`).**
- **`--dry-run` spends nothing** — the platform is detected, the models shown,
  the preflight run; nothing is submitted. Do this first, always, and say
  what a real run will cost before starting one.
- `record --direct` runs line parity and the ledger on the clips the machine
  made; `pack` runs coverage and finishes the run.
- Exit 0 done · 1 declined at the confirm gate · 2 a gate failed, nothing
  submitted · 3 bad input.

## The rules the command enforces — do not work around any of them

1. **The brief comes from a teardown.** This machine turns the brief into
   output; it never writes the script.
2. **Nothing moves unverified.** A still goes to motion only after the
   inspector has verified it against its cast sheet, in writing.
3. **Every shot has a route, labelled before anything runs** (the owner,
   2026-10-20; `components/video-production/SHOT-ROUTES.md` is the only rule):
   REAL when we own the footage, SWAP (Genjutsu on the swipe's own clean shot)
   when the motion is the point, AI for everything else, talking to camera
   included. `machine/shot_route.py label <shots.json>` prints each shot's
   route and cost and the total. An AI-route shot is frames, not scenes: two
   stills, first and last, the last an edit of the first, the beats between
   them timed off the voice.
4. **No scene length is ever a number.** A scene plays out fully; a scene that
   cannot name its Emotion and its Outcome is a transition — merged or cut.
5. **The contract gate.** Every item is validated against the model input
   contract before anything submits; red names the field.
6. **Two QC layers, two verdicts** — the inspector (is it the scene specified)
   and the director (will it stop a thumb). Motion QC on every clip. Every
   talking clip is transcribed and compared to its line; lip-sync to the
   wrong words is a FLAG. A ceiling ships FLAGGED with zero re-rolls —
   except a clip that stops mid-line: that is CUT_OFF, never shipped, and
   goes to the `remake-clip` skill, which remakes only the broken element.
7. **The element library is asked** (rule 13): an unknown format, style or
   delivery dial is refused with the real ids named.
8. **The models:** what each model does is ruled in
   `components/generative-model-house/MODEL-HOUSE.md` alone: every still and every edit on
   GPT Image; every clip on Seedance 2.5, made at 480p and upscaled on this Mac. Voices on
   our ElevenLabs, one custom voice per character.
9. **Sweep every ledger page before quoting spend.**

## What comes back

`runs/video-production/<brand>/<label>/` — `plan.json`, `media/` (stills, clips,
voice), `direct.json`, `verdicts.json`, the ledger, every prompt as sent.
The run's live board is `machine/board.py` (:8456); the shared picture is
"The Video Machine" (`lab/the owner/context/artifacts.md`).

Report: scenes made, which clips passed both verdicts, which shipped flagged
and why (one clause each), the spend, and the board link.

Reply with the result and the folder it landed in (repo path or Drive folder name).
