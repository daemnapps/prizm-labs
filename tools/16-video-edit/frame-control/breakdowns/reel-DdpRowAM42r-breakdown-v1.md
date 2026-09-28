# Reel B — baby, camera flies around him

2026-09-27 · reverse-engineered from the downloaded file. Facts first; anything that is an inference says **Inference**.

- Link: https://www.instagram.com/reel/DdpRowAM42r/
- Account: @jullyblond ("Михайлова Юлия | Living life") · posted 2026-09-23
- Caption (verbatim, Russian): "Матвею Алексеевичу 7️⃣ месяцев а 🥐" — roughly "Matvey Alekseevich is 7 months old"
- Likes 729,388 · comments 2,627 (at pull time)
- File: 8.2 s · 720×1280 (the version Instagram served) · 24 fps · stereo AAC
- Pictures: `contact-sheet.jpg` (every 0.25 s), `key-frames.jpg` (0 / 2.2 / 3.8 / 7.6 s), `frames-3.5-5.5s.jpg` (8 fps; labels count from 3.5 s), `audio-spectrogram.png`

![contact sheet](contact-sheet.jpg)

## What it is

A baby sits still on a dark rug in a lamp-lit living room. The camera flies around him — face close-up, pull back, low floor level, straight overhead, behind him, across the room past a table — then pushes back into the same face close-up it opened on. No speech; music only.

## Shot list

| Time | Shot | Camera |
|---|---|---|
| 0.00–0.33 | Extreme close-up of the face | pulling back |
| 0.33–1.71 | Low wide, baby seated centre, shelves behind | continues pull-back, then slides right at floor level |
| 1.71–2.33 | Straight down from overhead, baby looking up and reaching | high angle, then whip |
| 2.33–4.33 | Rug level, pushes in to him, then orbits to behind him (ceiling light visible) | floor-level orbit, heavy motion blur |
| 4.33–5.50 | Opposite wall: TV, guitars, lamp; baby side-on | pulls back past a white table in the foreground |
| 5.50–8.21 | Wide from across the room | pushes all the way in to the face; holds 7.0–8.2 s on the same close-up as the open |

Scene-change detection (threshold 0.25): cuts at 0.33, 1.71, 2.33, 4.33, 5.50 s — 6 shots in 8.2 s, average ~1.4 s. Each cut lands inside a fast camera move (whip or blur), so no cut shows as a clean jump.

## Breakdown

| Area | Observed |
|---|---|
| **Hook (0–2 s)** | Starts on a full-frame baby face staring at the lens, then the camera rips backward; by 1.7 s it is already overhead |
| **Camera** | Ultra-wide look with barrel distortion; positions a handheld phone can't easily reach smoothly (rug level, directly overhead, orbiting behind at floor height, backing past furniture); motion blur on every move |
| **Motion** | Baby barely moves: small hand movements (reach at ~1.8 s), same seated pose, same neutral/serious expression in every shot, mouth closed throughout |
| **Identity** | Face, onesie (navy), skin tone and head shape match across all six shots and between first and last frame |
| **Room** | TV, floor lamp, guitars, toy shelves, framed prints and the white table re-appear in consistent positions from different angles |
| **Lighting / grade** | Warm practical lamps, dark room, one look across all shots; no sensor noise visible at this resolution |
| **Sound** | Music only (whisper output: "(upbeat music)"); spectrogram shows a sparse intro, bass/full band entering at ~1.1 s, 0.34 s silence at the very end (7.86–8.2 s) |
| **Text** | None on screen |
| **Pacing** | 6 shots in 8.2 s; bookended — last frame returns to the first frame's close-up (loop-friendly) |
| **Comments (sample, verbatim)** | "AI slop" · "Какой ии можно это сделать?" ("Which AI can do this?") · "This is genuinely frying me" · "get this baby on a Glambot immediately" · "THE boss baby" |

## Real vs generated

- **Stated by the creator:** nothing about how it was made; the caption presents it as her son at 7 months.
- **Viewers:** comments are split between treating it as AI ("AI slop", "Which AI…") and reacting to the baby.
- **Evidence consistent with generation (observed):** identical expression and pose held across every angle for 8 s; every cut hidden inside a blur/whip; camera paths at rug level and overhead that are smooth.
- **Evidence consistent with real footage (observed):** the room layout holds from every angle (TV, lamp, guitars, table); no morphing of the baby between shots in the frames checked.
- **Inference:** two routes fit what's on screen — (a) image-to-video from one or more photos of the baby, one generation per shot with a camera-move instruction, cut together on whips; or (b) a real 360 camera / phone swung on a stick around a still baby, reframed. The file alone doesn't settle it.

## Likely toolchain — Inference

| Step | Route (a): generated | Route (b): real rig |
|---|---|---|
| Subject | 1 photo of the subject in the room | the subject, sitting still |
| Angles | image model makes the same room from overhead / floor / reverse | 360 camera on a stick, reframed in the app |
| Motion | image-to-video per shot with a camera move ("orbit", "crash zoom out", "top-down", "dolly back past foreground") | real camera moves |
| Edit | cut on the whips, bookend the close-up, music drop at ~1 s | same |
| In Damon's setup | **GPT Image 2.5** (angle stills) + **Seedance 2.5** (4 s image-to-video per shot) | film it, or use it as a driving plate for **Genjutsu** to swap subject/room |

## Recreate it with our stack (no generation run)

```
1 hero still (product / person in a room)
   → GPT Image 2.5: same scene from 4 more angles (overhead, rug level, behind, across room)
   → Seedance 2.5: one 4 s clip per angle, each with one camera move
   → edit: cut inside the fast moves, open and close on the same close-up, music drop at ~1 s
```

| Step | Input | Credits (est.) |
|---|---|---|
| 1. Hero still | GPT Image 2.5, or a real photo | ~2.75 |
| 2. Angle stills | 4 × GPT Image 2.5 | ~11 |
| 3. Shots | 5–6 × Seedance 2.5 4 s | ~28 each → ~140–170 |
| 4. Edit | local | 0 |
| **Total** | | **≈ 155–185** (retries not included) |

Alternative with a real move: film the camera path on a phone around any stand-in object, then Genjutsu motion transfer (camera and timing carried over) with the new subject/room as refs: ~88 for 8 s @1080p.

Cost figures: known run costs (GPT Image 2.5 ~2.75, Seedance 4 s ~28, Genjutsu ~44 per 4 s @1080p). Not re-checked with `models_explore` this pass.
