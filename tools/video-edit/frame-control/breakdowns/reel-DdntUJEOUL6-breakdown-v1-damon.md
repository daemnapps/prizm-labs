# Reel C — "2 hours of sleep be like" (man meets a dog walking upright)

2026-09-27 · reverse-engineered from the downloaded file. Facts first; anything that is an inference says **Inference**.

- Link: https://www.instagram.com/reel/DdntUJEOUL6/
- Account: @paolo0.o ("ALi PAOLO") · posted 2026-09-23
- Caption (verbatim): "2 hours of sleep be like. #viralcontent #alipaolo #pov #sleep #ai"
- Likes 204,979 · comments 874 (at pull time)
- File: 18.7 s · 1080×1920 · 60 fps · stereo AAC
- Pictures: `contact-sheet.jpg` (every 0.5 s), `key-frames.jpg` (0.3 / 1.8 / 5.5 / 7.1 / 8.6 / 10.5 / 13.5 / 16.5 s), `frames-6.5-9.5s.jpg` (8 fps across the paw → hand exchange), `audio-spectrogram.png`

![contact sheet](contact-sheet.jpg)

## What it is

Shot / reverse-shot in a sunny car park. A man in a cream tee, check cap and tote bag faces the camera; the reverse shots show a golden retriever walking toward the camera on its hind legs like a person. The dog reaches a paw to the lens, the man reaches his hand to the lens, the dog ends up in a selfie-style framing, turns and walks away along a wall; the man walks off rubbing his eyes. On-screen text: "2 hours of sleep be like". No speech; soft piano only.

## Shot list

| Time | Shot | Who | Camera | Caption on screen |
|---|---|---|---|---|
| 0.00–0.93 | Man walking toward camera, car park, vans behind | man | handheld, eye level | yes |
| 0.93–2.65 | Dog walking upright toward camera beside a white brick wall, red barriers behind | dog | handheld, eye level | yes |
| 2.65–4.13 | Man standing, looking into the lens | man | handheld | no |
| 4.13–7.23 | Dog walks closer, lifts one front leg and reaches it to the lens until it fills the frame | dog | handheld, subject walks into lens | yes |
| 7.23–9.18 | Man reaches his right hand to the lens; frame pushes in; his arm then extends to lower-left as if holding the camera (selfie framing) | man | handheld | no |
| 9.18–15.12 | Dog in the same selfie framing (front leg extended to lower-left), smiling, tongue out; then turns and walks away upright along the wall | dog | handheld | yes |
| 15.12–18.73 | Man turns away, rubs his eyes with one hand, walks off past camera | man | handheld | no |

Scene-change detection (threshold 0.25): cuts at 0.93, 2.65, 4.13, 7.23, 9.18, 15.12 s — 7 shots, alternating man / dog. At a lower threshold (0.08) the extra hits all sit inside shots 4 and 6 (fast paw reach, dog close-up moving), not new cuts.

## Breakdown

| Area | Observed |
|---|---|
| **Hook (0–2 s)** | Caption "2 hours of sleep be like" over a plain shot of a man walking; at 0.93 s the reverse shot is a dog walking on two legs toward the viewer |
| **Structure** | Strict alternation man → dog → man → dog; each reverse shot answers the last action (dog reaches paw → man reaches hand; man in selfie framing → dog in the same selfie framing) |
| **Camera** | Handheld phone look in every shot, eye level, no whips; each shot is one continuous take |
| **Motion (dog)** | Upright bipedal walk with human-like weight shift and hip sway; front legs swing and reach like arms; the paw reach at 6.5–7.2 s comes straight into the lens with motion blur; turns and walks away upright |
| **Motion (man)** | Ordinary walking, standing, reaching, eye-rub; small fidgets |
| **Identity** | Dog: same golden retriever, same fixed smile in every dog shot; tongue appears from 9.25 s. Man: same person, outfit and bag across all four of his shots |
| **Look** | Man shots: pale sky, phone sensor texture, flat daylight. Dog shots: deeper blue sky, warmer and more saturated, fur rendered smooth with a soft painterly texture; different spot (white brick wall, red barriers, power pole) |
| **Sound** | Music only (whisper output: "(soft piano music)"); spectrogram shows a continuous tonal bed, chord changes around 3.9 / 8.1 / 10 / 12.2 / 15.5 / 16.4 s, and brighter broadband swells at ~7.5–8.2 s (the hand-to-lens moment) and from ~13.5 s to the end |
| **Text** | "2 hours of sleep be like" in white with a dark outline, upper-centre, on the opener and every dog shot; absent from man shots 2–4 |
| **Pacing** | 7 shots in 18.7 s, average ~2.7 s; the longest shot (5.9 s) is the dog close-up and walk-away |
| **Comments (sample, verbatim)** | "Woah 🤯 is this real?" · "Sounds like Zelda music in the background 🔥" · "Clash royale sound?" · "Nab this is me after being awake for 26hours+" · "Bro say like this but me who sleep only 1 hour😭" |

## Real vs generated

- **Stated by the creator:** the caption carries the hashtag "#ai". Nothing further on method.
- **Viewers:** "Woah 🤯 is this real?" is the only method-related comment in the sample pulled (10 comments).
- **Observed:** the man shots carry phone sensor texture and a paler sky; the dog shots have a different grade and smooth, painterly fur. The dog's poses mirror the man's (paw to lens ↔ hand to lens; selfie arm to lower-left in both).
- **Inference:** man shots are real phone footage. Dog shots are generated. Two routes fit what's on screen:
  - (a) **motion transfer** — the creator (or a stand-in) performed the dog's part himself at the brick wall: walk up, reach to lens, selfie, turn and walk away; that take was then rebuilt with a golden retriever as the character. The human gait, the arm-like reach and the selfie pose matching his own shot point this way.
  - (b) **image-to-video** — a dog still animated with a text prompt per shot ("golden retriever walks upright toward camera, reaches paw to the lens"). The file alone doesn't settle which.

## Likely toolchain — Inference

| Step | Route (a): motion transfer | Route (b): image-to-video |
|---|---|---|
| Real side | film yourself in location A (4 short takes) | same |
| "Dog" side | film yourself acting the dog's moves in location B, same phone | none |
| Character | 1 still of the dog standing upright in location B | 1 still of the dog in location B per shot |
| Generation | video-to-video: the takes → the dog (Genjutsu / Kling Motion Control / Wan Animate class) | image-to-video with a move per shot |
| Edit | alternate shots, answer each action with the reverse, caption on dog shots, piano bed | same |
| In Damon's setup | **GPT Image 2.5** (dog still) + **Genjutsu** on each "dog" take | **GPT Image 2.5** + **Seedance 2.5** 4 s per shot |

## Recreate it with our stack (no generation run)

```
phone: film the real side (you) + the "character" side (you acting it), same light, same phone
   → GPT Image 2.5: the character (animal / mascot / product-person) standing in location B
   → Genjutsu: each character take → the character, motion and camera kept
   → edit: shot / reverse-shot, each action answered, caption over the character shots, music bed
```

| Step | Input | Credits (est.) |
|---|---|---|
| 1. Phone takes | 3 real + 3 "character" takes | 0 |
| 2. Character still | GPT Image 2.5 | ~2.75 |
| 3. Character shots | Genjutsu: 1.7 s + 3.1 s (one 4 s clip each) + 5.9 s (8 s) | ~44 + 44 + 88 → ~176 |
| 4. Edit | local | 0 |
| **Total** | | **≈ 180** (retries not included) |

Alternative, image-to-video only: GPT Image 2.5 still (~2.75) → 4 × Seedance 2.5 4 s (~112) → edit: **≈ 115**.

Cost figures: known run costs (GPT Image 2.5 ~2.75, Seedance 4 s ~28, Genjutsu ~44 per 4 s @1080p). Not re-checked with `models_explore` this pass.
