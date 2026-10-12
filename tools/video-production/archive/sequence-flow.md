# The Sequence Flow — from station outputs to an assembled draft

v1, 2026-08-30. The edit/sequence process `process.md` deliberately leaves
out of scope, proven end to end in the owner's sandbox on 2026-08-30 (the
"three-sleeves" brand-a brief: 9 shots, one consistent character through
three outfit changes, voiced, assembled — ~$__ of generation, ~40 minutes
brief → film, every shot independently redoable). This document is the
fresh write-up of that proven flow for this machine; the run record is
`machine/runs/three-sleeves/`.

The stations (cast, voices, scenes, motion) make assets. The sequence flow
is what makes them a **film** — and what makes the film **editable without
regenerating it**.

## The one idea everything hangs on

**The timeline is the edit surface, and assembly is free.**

One `timeline.json` per run holds: the locked scene blocks, the wardrobe
table, and per shot — the spoken line, the on-screen text, the still prompt
(picture) and the motion prompt (what happens). Every generated asset
(still, voice line, clip) belongs to exactly one shot. Assembly is a
deterministic local render (ffmpeg) that reads the timeline and what exists
on disk. Re-running it costs nothing, so reordering, retiming and retexting
are always free, and a redo of one shot never touches the others.

## The flow

```
BRIEF ──parse──► TIMELINE (shots · lines · on-screen text)
CAST master ──identity reference──► one STILL per shot
LOCKED BLOCKS (person · room · camera) ──pasted into──► every still + clip prompt
STILL ──first frame──► CLIP        VOICE line ──duration──► clip length + timing
CLIPS + VOICE + TEXT CARDS ──ffmpeg──► DRAFT FILM
```

Two additions to the station model in `process.md`:

1. **Identity chaining for multi-shot consistency.** The cast master is not
   just the character record — every shot's still is generated as an image
   EDIT with the master passed as reference ("IMAGE 1 is the identity, room
   and camera-style reference. Keep the exact same woman… the exact same
   bedroom… the exact same amateur phone-camera look."). One woman, three
   outfit changes, nine shots, zero drift. Never describe the character
   fresh per shot.

2. **Voice duration drives the cut.** Each clip is generated at (its voice
   line's length + ~0.6s), and assembly pads (`tpad` clone) or trims each
   clip to the line + 0.4s. The film's pacing is therefore a voice setting,
   not an editing task — slow VO = slow film (the proven run's voice ran a
   1:16 brief at 1:45; the speed dial is the fix).

## Invalidation — what an edit re-runs, and what it costs

This table is the heart of "control over edits", and the core logic of the
production board being built on top of this flow. Show the blast radius and
price before confirming.

| Edit | Regenerates | Cost (proven run) | Untouched |
|---|---|---|---|
| a spoken line | that voice line → maybe that clip's length → assembly | ~1¢ | every other shot |
| a shot's action | that clip → assembly | 35–70¢ | still, voice |
| a shot's picture | that still → that clip → assembly | <$__ | voice |
| a locked block | ALL stills → all clips | ~$__ | voice |
| the cast member | master + all stills + clips | ~$__ | voice unless it changes too |
| order / timing / on-screen text | assembly only | $__ | everything generated |

## The locked blocks — where realness lives

Scene prompting is structure, not prose. Three blocks, written once per run,
pasted into every prompt; per-shot text stays at two sentences of action.
The **camera block is the realness dial** — the whole UGC-vs-polished
decision in one editable paragraph. The proven UGC block, verbatim:

> Vertical 9:16 smartphone front-camera footage look: phone propped at
> chest height, slight wide-angle distortion, natural amateur framing a
> touch off-centre, true-to-life colour, mild sensor grain, real skin
> texture with pores and lines visible. Absolutely no cinematic grading,
> no studio light, no beauty retouching, no editorial gloss. It must look
> like a real woman filmed herself in her bedroom on her own phone.

Motion prompts additionally carry the spoken line —
`She is speaking this line: "…" — her mouth and expression follow real
speech` + `no camera movement, no cuts` — which keeps lip activity tracking
the audio believably at draft quality.

## Draft-first economics

Everything generates at draft quality (cheapest resolution the clip slot
offers) until a shot is approved; approval is what triggers quality spend.
A full draft film costs single-digit dollars, so the iteration loop is
priced for volume. Finalize = re-render only approved shots at delivery
quality.

## The slots (model-agnostic, per house rule)

**SUPERSEDED OCCUPANTS (the owner's model ruling, 2026-08-31):** MiniMax and
Kling are retired — minimize the model set to Google Omni + ByteDance
Seedance/Seedream + GPT families. The table below records what the
proven run used; current occupants live in `machine/sequence.py`.
Note: the old framing of Omni as the cheap-draft slot is WRONG per
the owner (2026-08-31) — Omni is a first-class clip model, picked per shot.

| Slot | Must be able to | Proven occupant (2026-08-30, fal) | Cost |
|---|---|---|---|
| Master still | t2i, natural skin, no beauty-filter look | `fal-ai/bytedance/seedream/v4.5/text-to-image` — `{prompt, num_images:1, image_size:"portrait_16_9"}` | $__ |
| Chained stills | image edit with identity reference | `fal-ai/bytedance/seedream/v4.5/edit` — `{prompt, image_urls:[master], …}` | $__ |
| Voice | per-line TTS, voice id + speed control | `fal-ai/minimax/speech-02-hd` — `{text, voice_setting:{voice_id, speed}, output_format:"url"}` | ~1¢/line |
| Clip (stable) | i2v from a still, holds a propped-camera frame | `fal-ai/kling-video/v2.6/pro/image-to-video` — duration is a STRING enum `"5"`/`"10"` | $__/$__ |
| Clip (cheap drafts) | i2v at low res, first+last frame | `google/gemini-omni-flash/v1.1/image-to-video` — `{…, end_image_url?, resolution:"360p"}` | $__/s |
| Transition | first frame + last frame, invents the move | same Omni endpoint with `end_image_url` | $__/s |
| Assembly | pad/trim to VO, overlay cards, concat | ffmpeg, local | $__ |

Status notes (2026-08-30): Omni 1.1 is three days old and buckling —
repeated `downstream_service_unavailable` and 504s including on status
polls; treat 408/429/5xx (504 included) as transient with backoff, and keep
Kling in the stable slot until it settles. Omni stays wired: ~10× cheaper
draft seconds, transitions, and draft→4K upscale fits draft-first
economics exactly.

## Traps (all hit, all built around)

- **Per-shot failure isolation.** A batch never dies on one bad shot:
  catch per shot, report "redo these ids", continue.
- **Apple's ffmpeg lacks drawtext.** Render on-screen text as transparent
  PNGs (auto-shrink font until the longest line fits ~980px on a 1080
  frame) and overlay. Text is an assembly concern — retexting never
  regenerates anything.
- **Product truth.** AI-drawn packshots are not shippable. Real product
  stills per brand, passed as an extra reference into any shot that shows
  product.
- **Graphic-card shots** (receipts, grids, price cards) skip generation
  entirely — a held still + text card in assembly is the shot.

## Runner

`machine/sequence.py` — reads a run's `timeline.json`, regenerates by shot
id, assembles:

```
python3 machine/sequence.py <run> stills [ids…]
python3 machine/sequence.py <run> vo     [ids…]
python3 machine/sequence.py <run> clips  [ids…]
python3 machine/sequence.py <run> assemble
```

Auth: `FAL_KEY` env var or `machine/.env`. Media lands in the run folder
(gitignored); the run's record in git is `timeline.json` + `notes.md`.
Heavy outputs for sharing go to the Drive lab
(`Shared Assets/the team notes`).

## Open items

- Drift rate: 3 of 9 shots drifted from the brief on the proven run's first
  pass (early prop, wandering framing, eye-line). Per-shot redo is the
  designed answer; drift rate is the metric to push down as the scene
  prompts tighten.
- Multi-scene briefs need per-scene room blocks and possibly per-scene
  masters; graphic-card shots already cost nothing.
- Second on-screen character: untested.
- Music/SFX bed: trivial in assembly, untested in this flow.
- Lip-sync is believable at draft, not close-up-shippable; if a lane needs
  true sync, audition a dedicated lip-sync pass on approved clips only.

## References

- Run record: `machine/runs/three-sleeves/` (timeline + notes; media on the
  Drive lab and the boards below)
- the owner's boards: The Sequence Machine
  (team page),
  The Production Board Handoff
  (team page)
