# Higgsfield Enhance Video

Upscales a video 1:1 to 1080p (or 720p) with Kling 4.0 video-edit, steered by a timed prompt that pins every shot, cut, camera move, line and text, then restores the original sound.

Source files: `higgsfield-enhance-video/SKILL.md`, `higgsfield-enhance-video/references/BRIEF.md`, `higgsfield-enhance-video/scripts/header.txt.md`, `higgsfield-enhance-video/scripts/build_prompt.py.md`, `higgsfield-enhance-video/scripts/prep.py.md`, `higgsfield-enhance-video/scripts/finish.py.md`, `higgsfield-enhance-video/references/examples/ugc_review_15s.txt.md`, `higgsfield-enhance-video/references/examples/car_ad_part2.txt.md`, `higgsfield-enhance-video/references/examples/drama_15s.txt.md`

## Inputs it needs

- One video (draft or finished); its short side must reach 720 px (prep.py scales smaller ones with Lanczos).
- Target resolution: 1080p (default) or 720p.
- Optional: `whisper-cli` ggml model for the dialogue transcript.
- Nothing else: the timed block is written from the contact sheet, cut list and transcript.

## Steps in order

1. **Prepare** - prep.py: Kling-ready parts (>=720 px, CRF 14, constant fps), split at about 15 s, contact sheets, cut list, Whisper transcript, tone measure, credit estimate.
2. **Write the timed block** - One block per part, 1,650 characters or less, in the BRIEF shape: VIDEO / SHOTS / DIALOGUE / TEXT / SOUND.
3. **Build prompts** - build_prompt.py puts the fixed header (with {RES}) before each block; warns past 2,900 characters; writes batch.json.
4. **Upload parts** - `media_upload` every part, PUT, `media_confirm`.
5. **Quote then run** - One `generate_video_batch`, mode `video-edit`, every part at once.
6. **Fetch results** - `jobs_wait`; failed or nsfw jobs are refunded; fetch.sh downloads each.
7. **Join, retime, colour-match, restore sound** - finish.py: retime shots (at most 20 %), match every shot back to the source tone, put source audio back, write qa/report.txt, grid.jpg, compare.mp4.
8. **Deliver** - Upload final.mp4 and compare.mp4; one line with size, SSIM and credits spent.

## Prompt blocks, word for word

**Fixed header (words {RES} replaced per run)** (`higgsfield-enhance-video/scripts/header.txt.md`)

```text
Upscale this exact video 1:1 to native {RES}. Same footage at higher quality: a frame-by-frame recreation of the reference, not a reinterpretation and not a regrade.
KEEP 1:1, FRAME BY FRAME: the same shots, cuts and duration; the same framing, angle, lens, focus and every camera move with the same path, speed and timing; the same people, faces, hair, makeup, wardrobe, props and positions; every expression, glance, blink, gesture and lip movement at the same moment; the dialogue word for word, same voice and lip sync; the same action, light and sound.
SAME COLOUR AND TONE in every shot: the reference's exposure, contrast, black and white levels, saturation, white balance and grade. A flat or log reference keeps its flat tone: no grading, added contrast, deeper blacks or extra saturation. Flat is tone only, never soft detail.
ONLY IMPROVE IMAGE QUALITY: crisp native {RES} detail and texture in every frame (skin pores, hair strands, eyelashes, fabric weave), sharp in-focus edges, accurate faces and hands; no blur, softness, smearing, flicker, morphing or artifacts. Add nothing, remove nothing; no subtitles, captions or watermark not in the reference; dialogue is heard, never written.
```

**Block shape (what Claude writes per part)** (`higgsfield-enhance-video/references/BRIEF.md`)

```text
VIDEO: <length> s, <aspect>, <genre in a few words>; LOOK: <tone exactly as it is: contrast, black level, saturation, palette, e.g. "flat log, lifted grey blacks, dim highlights, very low saturation, beige-grey">; <main people with hair and wardrobe>.
SHOTS (seconds, exactly as in the reference):
0.0–2.3 <shot size + camera position and move with direction and speed> — <who does what, expression, eyeline>.
2.3–6.0 ...
DIALOGUE (heard, never on screen; same voice, word for word, same timing and lip sync): 0.0–2.3 "..." | 6.0–10.4 "..."   (or: DIALOGUE: none, nobody speaks.)
TEXT (crisp, correctly spelled, exactly this and nothing else readable): <every readable text with exact wording, colour, placement and time>; <burned-in captions with their words and times, or: no captions or subtitles>   (or: TEXT: none, no readable text anywhere, no captions or subtitles.)
SOUND: <one line: ambience, effects, music, voices>
```

**Finished block, UGC review 15 s** (`higgsfield-enhance-video/references/examples/ugc_review_15s.txt.md`)

```text
VIDEO: 15 s, 9:16 vertical, UGC phone video; LOOK: soft daylight, mint-and-cream tiled bathroom, natural colour, normal contrast; woman with black shaggy mullet, freckles, hoops, chain, red leopard-print shirt over white black-collar tee.
SHOTS (seconds, exactly as in the reference):
0.00–2.29 handheld selfie close-up — bottle against her cheek at frame left, big smile, eyes on lens.
2.29–2.96 static low wide from the sink — she pushes up one sleeve, then the other, eyes on lens.
2.96–4.29 same frame, she stands closer — pumps foam into her palm, calm gaze to lens.
4.29–5.96 same frame — rubs palms into thick white lather, eyes on hands.
5.96–10.46 same frame — cradles the tilted bottle in foamy hands, talks looking down, presses lips on "um", glances up wide-eyed on "oat", ends with a toothy smile.
10.46–12.83 handheld selfie close-up — mound of foam on her open palm by her face; eyes widen, jaw drops on "Unreal", then a squinting laugh.
12.83–15.04 handheld selfie close-up — her free hand strokes her bare forearm, soft smile.
DIALOGUE (heard, never on screen; same voice, word for word, same timing and lip sync): 0.0–2.3 "This body wash is so creamy." | 6.0–10.4 "Shea and, um, oat, so zero dry skin." | 10.4–12.8 "And the foam? Unreal." | 12.8–15.0 "My skin's been so soft all week."
TEXT (crisp, correctly spelled, exactly this and nothing else readable): pale-pink 500 ml bottle, violet pump; front: purple circle with lowercase "plush" in white; centred below, small purple "creamy body wash" over "shea + oat · 500ml". Stickers stay wordless; no captions or subtitles.
SOUND: her close voice, quiet bathroom tone, pump clicks, lather squelch 4.3–6.0; no music.
```

**Finished block, car ad part 2** (`higgsfield-enhance-video/references/examples/car_ad_part2.txt.md`)

```text
VIDEO: 15 s, 21:9, car ad with smash cuts; LOOK: low warm sun, dust haze, red desert buttes, saturated cobalt and rust, crisp contrast; boxy cobalt-blue SUV, Japanese woman in a slate jacket.
SHOTS (seconds, exactly as in the reference):
0.0–0.88 low front 3/4 — the SUV skids past camera right in a dust burst, sun flare behind.
0.88–2.25 handheld, from the back seat — her gloved hands on the wheel, desert through the windshield; a red dust wall hits the glass 1.7.
2.25–4.38 static wide — the SUV spins donuts on the flat, huge swirling red dust cloud, buttes behind.
4.38–6.08 static, dust haze, backlit — SUV parked side-on; she steps out by the open door and stands looking at the butte, wind in her hair.
6.08–7.96 static ECU of her face — eyes closed, open slowly 6.3, calm direct stare into lens, hair strands blowing.
7.96–8.71 macro — her bare hand rests on the blue hood and slides slowly forward.
8.71–9.58 static macro — the clean chrome "BRAND" badge, light glinting.
9.58–12.08 sunset silhouette wide, slow arc left — she stands facing the parked SUV between two buttes, sun flaring on the horizon.
12.08–14.0 static high aerial wide — the tiny SUV and her in a circle of tyre marks, a tall dust column rising toward the sunlit horizon.
14.0–15.0 black.
DIALOGUE: none, nobody speaks.
TEXT (crisp, correctly spelled, exactly this and nothing else readable): "BRAND" in raised polished-chrome bold capitals on a dark oval badge with a double chrome rim, 8.71–9.58; grille and plate marks stay unreadable.
SOUND: percussion-only music, drum hits and booms on cuts, engine roar, tyre crunch, wind; no voices.
```

**Finished block, drama 15 s** (`higgsfield-enhance-video/references/examples/drama_15s.txt.md`)

```text
VIDEO: 15 s, 21:9, quiet hospital drama, slow handheld drifts; LOOK: soft window light, teal walls, muted cool tones, gentle contrast.
SHOTS (seconds, exactly as in the reference):
0.0–2.08 Top-down close-up of hands on a cream blanket, slow drift left — her hand (silver solitaire ring) rests on his age-spotted hand (ID wristband); his thumb gently strokes her hand.
2.08–4.0 Close-up of the daughter (about 30, brown wavy hair, curtain bangs), his blurred head right — wet eyes look down at him, she lowers her gaze, presses her lips together; a tear runs down her cheek.
4.0–6.29 Low over-the-shoulder past her blurred grey-blue knit — the father (about 80, white hair, nasal cannula) lies back, heavy-lidded eyes half-open, gazing up at her.
6.29–7.54 Low wide from the bed's foot, folded blue blanket foreground, window left — she leans over him holding his hand; he lies still.
7.54–10.04 Close side shot of his head on the pillow, her hair right, blurred monitor with green trace behind — her hand settles on his forehead (7.8 s) and smooths his hair back; his eyes slowly close (8.5 s).
10.04–12.13 Extreme close-up of his eye — her fingers stroke his temple hair, then slide away left; his watery eye opens (10.2 s), gazing up at her.
12.13–13.88 Same low wide — she lifts her hand from his hair, still leaning over him.
13.88–15.0 Same top-down hands close-up — his thumb presses her hand, fingers tighten.
DIALOGUE: none, nobody speaks.
TEXT: none, no readable text anywhere; wristband print and monitor readouts stay illegible; no clock.
SOUND: near-silent room tone, no music, no monitor beeps; soft breaths about 5.0, 7.1 and 12.7 s, sheet rustle 13.9–15.0 s.
```

**Generation request (per part)** (`higgsfield-enhance-video/SKILL.md`)

```text
{
  "index": 1,
  "params": {
    "model": "kling4_0",
    "prompt": "<contents of prompts/full_part_01.txt>",
    "mode": "video-edit",
    "aspect_ratio": "21:9",
    "resolution": "1080p",
    "duration": 15,
    "medias": [{ "role": "video_references", "value": "<media_id>" }]
  }
}
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Enhance (video-edit, 1:1) | `kling4_0` | mode `video-edit`, 1080p or 720p, duration 3-30 s (parts about 15 s), aspect_ratio from source, video as `video_references` |
| Everything else | none | prep, build, retime, colour match, QA run locally in the sandbox (ffmpeg, python) |

## Checks and gates

- Never a bare 'upscale this': the header plus timed block is mandatory.
- Input under 720 px short side fails: prep scales it first; if the source already has 1080 px or more on the short side it says Kling would only re-render.
- Prompt length: warns past 2,900 characters; shorten the block, never the header.
- Fidelity gates in finish.py: part length against source within one frame, each cut within two frames; SSIM under 0.75 alone is a reason to look, not to re-run.
- Retry order: same prompt first (Kling varies), then a shorter split. Look at the grid and full-size faces, hands, text before delivering.
- No camera or lens brands, film titles or real people's names in the block; dialogue is heard, never written, so the TEXT line says no captions when none exist.
- Invoking the skill on a video is the go-ahead to spend; if only the prompt was asked, it stops after step 3.

## Price pattern

Quotes before running; prep.py prints the estimate. From the skill (preflight 2026-11-15, not in `_prices.md`): 1080p 60 credits per 15 s (4 per s), 720p 41.25 per 15 s. A typical 15 s 1080p part is about 60 credits; a 30 s clip is two parts, about 120.

## Cheap swap

- Kling 4.0 Flash video-edit, 720p only: `kling_4_0_flash` reference-to-video quotes 15 credits per 10 s (video-edit itself not quoted). A quarter of Kling 4.0 1080p per second at 720p.
- Gemini edit: `gemini_omni_flash_1_2` mode `edit`, 360p (source 3-15 s, up to 7 image refs): the same 7.5 credits per 10 s tier as its quoted reference-to-video; the edit price itself is not quoted, re-quote first.
- If the goal is only sharper pixels, no re-render: local Real-ESRGAN animevideov3 upscale on this Mac, about 10.6 s of compute per video-second, free (saves 60 credits per 15 s), at the cost of the prompt-guided cleanup.
- The timed block is written by Claude on the plan, free to us.
