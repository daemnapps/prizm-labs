# Playbook · Vo explainer (`vo-explainer`)

**Status:** draft · **state:** skeleton-from-nearest
**Family:** vo-explainer · nearest when drafted: `multi-speaker-scene`

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | 1 |
| address | to-camera |
| settings | 1 |
| product_role | none |
| pacing | medium |
| capture | animated |
| story | pitch |

## What is specialised, and why

- **audio first: voice** — read from the swipe's sound form
- **every picture in family-3d** — the swipe is animated; its style row locks every element

## Stage order

teardown → writing (the hook stays as the format has it) → elements (banked cast first) → voices (every line, every speaker) → storyboard → pictures → clips (Seedance 2.5, 480p, one take, three tries at most; the locked read goes in as the clip's audio) → the locked read goes into the clip as its audio (nothing is fitted afterwards) → words check → edit (cuts between whole takes; no repairs) → hook openings

## Stage settings

**audio**
- first: voice
- voice_model: elevenlabs
- on_camera: said inside the clip: the approved read goes in as the clip's audio (nothing is fitted afterwards)
- off_camera: the speaker's cloned voice on its own track
- voices_kept: on
- turns: each speaker waits their turn — no overlapping murmurs

**song**
- flow: the shared chain's own

**pictures**
- door: direct.openai
- model_key: model
- quality: high
- size: 1152x2048
- aspect: 9:16
- fix_calls: off
- subject_zone: 15–85% of the height, said in the first prompt
- style_lock: family-3d
- only_these_things: list every prop; nothing from the swipe's own props leaks in

**clips**
- model: seedance_2_5
- endpoint: image-to-video
- resolution: 720p
- seconds: 4, 10
- cut_at: line or sentence boundaries, never padded
- clips_per_picture: 1, 2
- takes: 1
- upscale: local Real-ESRGAN to 1080x1920 — the picked take only (VIDEO-RULINGS V6, 2026-10-21)
- stills_allowed: off
- person_from: the section's approved picture, never a made frame
- restart_on_same_picture: a new shot — the storyboard's next angle or framing — cut at a line boundary; never a punch-in to hide the join (VIDEO-RULINGS V15)
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least

**cast**
- reuse: banked cast first (the same presenter served four formats); new cast only for the roles a format adds (host, artist, doctors)
- recurring: on
- product: real pixels — real archive clip, studio render or the turntable paste (live-action family)

**hooks**
- shape: the hook stays as the format has it; 4–5 alternate openings swap the first scene or line (G01-H2…H6)
- count: 5
- generated: only the opening scene

**captions**
- look: ig-fb-native (Instagram/Facebook) unless the source has none

**gates**
- apply: all 13 (run.py start), line parity on every talking clip, voices kept, never re-recorded, mouths reviewed (a silent person's lips moving), picture QC with a working reviewer
- skip: song gates

**edit**
- method: video-edit machine cut on the voice track
- cover_before_remake: off
- broll: real b-roll about 4 s each
- lip_offset: measure in each clip's own frames; one global picture offset when the whole cut is a frame off
- loudness: -14 LUFS
- music: only when the swipe or the brief calls for it (VIDEO-RULINGS V14); then ducked about -19 dB under voice
- small_print: none (ruled 2026-10-07)

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $20

## Quality bar — not slop

- every word heard, none cut off (line parity on every talking clip)
- lips on the words within a frame
- a silent person's lips never move on screen
- every speaker sounds like their face — their own cloned voice
- no third hand, no words written on clothes or walls, no garbled labels left readable
- the product is the real thing at its real size and colour
- the room stays the same room across a scene (props, light, wardrobe)
- music only when the swipe or the brief calls for it, never fighting the voice

## Variants (same workflow, refined)

### narrated story (`narrated-story`, draft)
- differs: story: narrative
- from: runs/video-teardown/_work/<brand>-song-crew-knew
- matched at score 0.85


## Built from

- runs/video-teardown/_work/155495826
