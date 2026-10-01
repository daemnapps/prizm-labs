# Reel A — "Turning into people to prove I'm using AI"

2026-09-27 · reverse-engineered from the downloaded file. Facts first; anything that is an inference says **Inference**.

- Link: https://www.instagram.com/reel/DdrtGPgIzXA/
- Account: @tiktoktitans_tts ("TikTok Titans") · posted 2026-09-24
- Caption (verbatim): "More proof AI really is crazy good. #ai #aisocialmedia #content"
- Likes 496 · comments 90 (at pull time)
- File: 48.9 s · 1080×1920 · 30 fps · stereo AAC
- Pictures: `contact-sheet.jpg` (every 0.5 s), `key-frames.jpg` (1 / 17 / 23.5 / 26 / 33 / 42 / 44.5 s), `audio-spectrogram.png`

*(The pictures stay with the downloaded file — not published here.)*

## What it is

A creator in a red hoodie says commenters think he uses actors. He takes three commenters' profile pictures plus "a couple more reference images", then "meets" each of them in a hallway: they walk in, shake his hand, wave, look at camera. Each "person" is presented as AI.

## Shot list

| Time | Shot | On screen |
|---|---|---|
| 0.0–3.9 | Selfie close-up, talking head | Burned-in caption "Turning into people to prove i'm using AI" (0–~2.5 s); comment screenshots stack in from 2.0 s |
| 3.9–6.5 | Talking head continues | — |
| 6.5–8.0 | Three fast flashes of his earlier videos (older woman in a store, shirtless man in an office, a floor clip) | Under the line "these are the type of videos that I do" |
| 8.0–10.7 | Talking head | Comment overlay: "Tell this is literally him just making it look like someone commented…" |
| 10.7–15.0 | Rapid cuts: screen recordings of the three commenters' profiles and posts, interleaved with talking head | Profiles: mentzsamantha, gardenlikeaviking, emotionally.intelligent.parent |
| 15.0–20.8 | Wide, full body, hallway. He steps back from the phone and sets up | Framing then stays fixed |
| 20.8–28.2 | Contender 1 (woman, floral dress) walks in from left, handshake, waves, looks at camera | Comment overlay 21.5–23 s; profile-photo PiP 24–26.5 s |
| 28.2–36.5 | Contender 2 (shirtless, red beard) walks in, handshake, he puts a hand on the man's shoulder, man exits right | Comment overlay 29.5–31.5 s; PiP 33.5–35 s |
| 36.5–46.8 | Contender 3 (doll-like blonde, green knit set) walks in; tighter framing 41.5–43 s | Comment overlay 39–40 s; PiP 44–45.5 s |
| 46.8–48.9 | Selfie close-up outro | "comment below, maybe I'll do you next" |

Scene-change detection (threshold 0.25) found 23 cuts; 15 of them fall in the first 15 s. From 15 s to 46.8 s the hallway plays as long unbroken takes.

## Spoken track (transcribed locally, whisper small.en)

> All right, let's prove some more people wrong. So I got three of the top comments from my last video. I'm gonna be turning myself into them using AI. If you don't know, these are the type of videos that I do, and people think that I'm using actors and paying people off. I went to their TikToks and Instagram. I've taken their profile picture and a couple more reference images. So I'm gonna be doing this one a little bit different. I'm actually gonna be meeting the person, okay? I'm not gonna turn into them. I'm just gonna meet him. So come on, contender number one, nice to meet you. Go ahead and look at the camera and show them that it's AI. Give them a little friendly wave. Nice, okay. Person number two, come on in. What's up? Go ahead and look at the camera. Check out this one. Nice, lovely. All right, and last but not least, look at this. Oh my gosh, look at the skin. This is a very pretty Barbie doll right here, okay? [To] comment below, maybe I'll do you next.

## Breakdown

| Area | Observed |
|---|---|
| **Hook (0–2 s)** | Face close-up, mid-sentence start ("All right, let's prove some more people wrong"), caption states the premise; comment screenshots arrive at 2.0 s |
| **Camera** | Talking-head parts: handheld/selfie close-up. Hallway: fixed frame, phone-height, slight wide-angle, no camera move for ~30 s |
| **Motion** | People walk in and out of frame, handshake, wave, turn to camera; he touches contender 2's and 3's shoulder. Feet on the floor, hand contact and clothing movement read continuous in the frames |
| **Identity** | Each contender stays the same person through their segment. Contender 3's face matches the doll profile photo in the PiP (proportions of a doll) |
| **Lighting / grade** | One hallway, flat indoor daylight + overheads; no visible grade change between contenders and host |
| **Sound** | Voice throughout; a continuous low-frequency bed under the voice across the whole file (see spectrogram) — not identified. A small black round object is clipped at his hoodie neckline (visible at 1 s) |
| **Text** | One burned-in caption line at the open; the rest is proof overlays: comment screenshots, profile screen recordings, source-photo PiPs |
| **Pacing** | 15 cuts in the first 15 s; then three long takes (~7–10 s each) |
| **Comments (sample, verbatim)** | "Are you going to share what ai you used to make this?" · "Can you match the voice too?" · "Maybe show the software?" · "😂😂this is a great hook" · "Me please" / "Do me pls!!" |

## Real vs generated

- **Stated by the creator:** the three contenders are AI, built from each commenter's profile picture + a few reference images.
- **Observed:** the host and the contender share one continuous frame with physical contact (handshakes, hand on shoulder), with no visible seam or cut at the contact.
- **Inference:** the contenders' body motion comes from a real stand-in performer filmed with the host, and the stand-in's identity was replaced from the reference images (video-to-video character replacement). A real performer would supply the contact, weight and floor contact that the "reads fake" sources list as hard for pure generation.
- **Inference:** the neckline object is a wireless lav mic.
- **Not determinable from the file:** whether the host himself is generated; which tool was used (no credit in caption or comments from the creator).

## Likely toolchain — Inference

| Step | Likely | In Damon's setup |
|---|---|---|
| Driving plate | Phone on a stand, host + one stand-in walking in | Film on phone |
| Identity refs | Profile photo + 2–3 more photos of the person | Same, or GPT Image 2.5 for a made-up person |
| Replace stand-in | A replacement-mode model: Wan 2.2 Animate "Replacement", Kling Motion Control, Luma Ray3 Modify, Runway Act-Two class | **Genjutsu motion transfer** (`hf_mult_motion_control`, up to 30 refs, clip 4–30 s); fal Wan 2.2 Animate Replace as the replacement-mode alternative |
| Keep the host untouched | Mask/composite the replaced person back over the original plate | Local tracking + compositing (SAM 3 Remove Background in connector for mattes) |
| Edit | Proof overlays, PiP, comment cards | Local edit |

## Recreate it with our stack (no generation run)

```
Phone plate (host + stand-in, 8 s per person)
   → refs of the new person (photos, or GPT Image 2.5 stills)
   → Genjutsu motion transfer on the plate, refs = new person
   → matte the new person, comp over the original plate so the host stays real
   → edit: talking-head open, proof overlays, PiP of the ref photo, outro CTA
```

| Step | Input | Credits (est.) |
|---|---|---|
| 1. Film the plate | 3 × ~8 s walk-ins with a stand-in | 0 |
| 2. Identity stills | 1–2 GPT Image 2.5 stills per person (only if not using real photos) | ~2.75 each → ~5.5 per person |
| 3. Motion transfer | 8 s @1080p per person (Genjutsu ≈44 per 4 s) | ~88 per person |
| 4. Matte + comp | local | 0 |
| 5. Edit | local | 0 |
| **Total, 3 people, one take each** | | **≈ 280** (retries not included) |

Cost figures: known run costs from Damon's clone test (Genjutsu ~44 per 4 s @1080p; GPT Image 2.5 ~2.75). Not re-checked with `models_explore` this pass.

Platform disclosure rules for realistic AI people are in the main findings page, section 5.
