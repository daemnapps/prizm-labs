# Real Motion — findings v1

2026-09-27 · research only. This page reports what was found, with sources. Where a line is an inference and not a finding, it says **Inference**.

---

## 1. The reference: @lutherlongford

| What | Found |
|---|---|
| Bio | "Standing on business with immaculate manners." |
| Followers | 6,768 (profile fetch, 2026-09-27) |
| Link in bio | a pump.fun link; bio also names an "Official LONGFORD coin" with a Solana contract address |
| How it's made | **Nothing published.** No interview, tutorial, tool credit or agency credit found on the profile or on the open web (searches for "lutherlongford" and "Luther Longford" AI returned nothing about the account). |
| Reel DdsA5QXIZ-i | Not pulled: the Instagram scraper on the Apify account hit its monthly usage limit. |

Source: https://www.instagram.com/lutherlongford/

For comparison, one AI-character account whose process *is* documented: Aitana López (The Clueless agency, Barcelona) — reported as built on Stable Diffusion with custom LoRAs, by a team of creative directors, art directors, editors and writers; reported at 300K followers in 6 months and €10K/month by Jan 2024.
Sources: https://www.theclueless.ai/project/aitana-lopez · https://make-influencer.ai/examples/aitana-lopez/ · https://en.wikipedia.org/wiki/Aitana_L%C3%B3pez

---

## 2. Tools — what goes in, what comes out

### A. Real motion → new person (motion transfer from a "driving" video)

| Tool | In | Out | Length / res | Price (published) | Source |
|---|---|---|---|---|---|
| **Higgsfield Genjutsu — Motion Transfer** (`hf_mult_motion_control`) — *in your Higgsfield connector* | 1 driving video + up to 30 reference images; presets or short text (no full prompt) | the same motion, camera and timing, with the people/place/look rebuilt from the refs | clip 4–30 s; up to 1080p (480/720/1080) | 15 s @1080p = 144 credits (~$7.20); 15 s @480p = 40 credits (~$2.00). Your own run: ~4 s @1080p = 44 credits | https://higgsfield.ai/blog/higgsfield-genjutsu · connector `models_explore` |
| **Kling Motion Control (2.6 / 3.0)** | 1 character image + 1 motion reference video (+ text up to 2,500 chars) | character performing the video's body motion + facial expressions | ref video 3–30 s; "image" orientation max 10 s, "video" orientation max 30 s; 720p (std) / 1080p (pro) | fal: v3 Pro $0.168/s, v3 Std $0.126/s, v2.6 Std $0.07/s | https://kling.ai/feature/ai-motion-control · https://kie.ai/kling-3-motion-control · https://fal.ai/kling-motion-control |
| **Runway Act-Two** | driving performance video (face, body, hands) + character image *or* video | character with the performance, speech and expression | driving video 3 s min; outputs up to ~10 s; 1080p 16:9 (per third-party summaries — Runway's help page returned 403) | under 3 s = 15 credits; scales with length | https://help.runwayml.com/hc/en-us/articles/42311337895827-Performance-Capture-with-Act-Two · https://aiwiki.ai/wiki/runway_act_two |
| **Wan 2.2 Animate** (open weights, Apache 2.0) | 1 character image + 1 reference video | *Animation mode*: the image moves like the video. *Replacement mode*: the person in the video is swapped for the character, matching scene light and colour | 720p, clips ~6 s typical | fal: $0.08 per video-second @720p (Move and Replace) | https://wan.video/blog/wan2.2-animate · https://huggingface.co/Wan-AI/Wan2.2-Animate-14B · https://fal.ai/models/fal-ai/wan/v2.2-14b/animate/replace |
| **Luma Ray3 Modify** | source video (max 10 s) + 1 character reference image + optional start/end keyframes; strength slider Adhere ↔ Reimagine | same performance, new look ("variable appearance, invariant performance") | 10 s max; 1080p recommended | not found on the guide | https://lumalabs.ai/learning-hub/ray3-modify-user-guide · https://lumalabs.ai/news/ray3-modify |
| **Viggle (Mix / Viggle-Animate)** | 1 character image + a driving video (5–15 s for Animate) | character placed into / replacing the motion | under 15 s; no audio | from $6.99/mo (third-party report) | https://viggle.ai/developers · https://viggle.ai/pricing |

### B. Identity locks (the same face every time)

| Tool | In | Out | Source |
|---|---|---|---|
| **Higgsfield Soul ID** | 20+ photos of one person, varied angles/expressions, one full-height shot; trains in ~3–5 min | a reusable identity, usable in Soul 2.0 images and saved as a Reference Element for Cinema Studio, Marketing Studio, Seedance 2.0, Kling 3.0 | https://higgsfield.ai/blog/sould-id-best-character-consistency |
| **Veo 3.1 "Ingredients to Video"** | up to 3 reference images (character, product, location) | video keeping all three consistent; native 9:16; upscale to 1080p/4K | https://blog.google/innovation-and-ai/technology/ai/veo-3-1-ingredients-to-video/ |
| **Seedance 2.0 / 2.5, Wan 3.0, MiniMax H3** (in your connector) | image + video + audio references | reference-driven video; 2.5 has video_edit and video_extension modes, up to 30 s | Higgsfield connector `models_explore` |
| **Custom LoRA** (e.g. Stable Diffusion / Flux) | a training set of one face | an image model that draws that face | Aitana López sources above |

### C. Talking / lip sync

| Tool | In | Out | Limits / price | Source |
|---|---|---|---|---|
| **HeyGen Avatar V** | a 15-second video of yourself (+ voice clone) | a digital twin with "your specific gestures, expressions, and mannerisms", full upper body | videos up to 3 min | https://help.heygen.com/en/articles/14602974-avatar-v-is-now-available-on-heygen |
| **HeyGen Avatar IV** | photo or video look + script | talking avatar with head motion, hand gestures | 16 credits/min (photo), 31 credits/min (video look); Creator plan $29/mo | https://www.heygen.com/avatars/avatar-iv · https://www.ezugc.ai/blog/heygen-review |
| **Hedra Character-3 / Omnia** | 1 image + audio (+ text) | upper-body talking video with blinks, gaze shifts, micro-expressions; Omnia (Feb 2026) adds full body | up to 10 min reported | https://www.hedra.com/models/video/hedra/character-3 |
| **sync.so sync-3** (also in your connector as `sync_so`) | an existing video + new audio | the same video with the mouth re-synced | native 4K, handles profiles and obstructions, 95+ languages; ~$0.133/s | https://sync.so/sync-3 · https://sync.so/pricing |
| **Kling Motion Control** | — | Kling's own page: motion control "focuses on movement and expressions"; for speech use Video 3.0 | — | https://kling.ai/feature/ai-motion-control |

### D. Finishing (skin, upscale, grain)

| Tool | In | Out | Source |
|---|---|---|---|
| **Topaz Starlight (2.5 / Precise 2.6)** — Topaz also in your connector (`topaz_video`) | a video | diffusion upscale to 1080p/4K, up to 4×, optional frame interpolation | https://www.topazlabs.com/starlight |
| **Bytedance Video Upscale** (connector) | a video | 1080p/2K/4K, 24–60 fps, presets incl. `aigc` and `ugc` | connector `models_explore` |
| **FPS Boost / Video Deflicker** (connector) | a video | frame interpolation to 16–120 fps / flicker removal | connector `models_explore` |
| **Grain + blur in the edit** | the finished clip | order given by one guide: upscale → blur & grain → grade → review; grain after upscale "sits at the correct pixel scale" | https://invideo.io/blog/ai-video-post-production/ |

### E. Status change worth knowing

**Sora is discontinued.** OpenAI announced it 2026-03-24; the app and web closed 2026-04-26; the Sora 2 API was scheduled to close 2026-09-24.
Source: https://help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation · https://the-decoder.com/openai-sets-two-stage-sora-shutdown-with-app-closing-april-2026-and-api-following-in-september/

---

## 3. The typical real-motion pipeline (as documented across the sources above)

```
[1 Real driving footage]  →  [2 Identity refs / Soul ID / LoRA]  →  [3 First frame / still in new look]
         ↓                                                                    ↓
                     [4 Motion transfer: Genjutsu · Kling MC · Act-Two · Wan Animate · Ray3 Modify]
                                              ↓
                          [5 Lip sync if talking: sync-3 · HeyGen · Hedra]
                                              ↓
                  [6 Finish: upscale → blur/grain → grade → export 1080p]
```

Documented shooting guidance for step 1: record on a phone framed medium or wide so the full body stays in frame, camera on a tripod for a static reference (HackerNoon, https://hackernoon.com/ai-motion-capture-turns-your-phone-into-a-mocap-studio-heres-the-workflow-i-run); "Use clear videos with visible facial movement … ensure the character's facing direction matches your input image" (Kling, https://kling.ai/feature/ai-motion-control).

A run of steps 1, 3, 4: a real clip (3.2 s) → GPT Image 2.5 stills in three outfits → Genjutsu at 1080p → 1080×1920, 24 fps, 4.04 s each; first 3.2 s follow the real clip 1:1, last ~0.8 s is the model continuing; it copied the camera move too. 140.25 credits total.

---

## 4. What reads fake vs what reads real (practitioner descriptions)

| Factor | What's described | Source |
|---|---|---|
| **Weight / contact** | "Slides without weight or contact settling"; "Limbs float, steps land without weight" | https://creatide.ai/blog/why-ai-video-motion-looks-unnatural-and-how-to-fix-it · https://www.atlabs.ai/blog/why-your-ai-videos-look-fake-(and-how-to-fix-them-step-by-step) |
| **Too smooth** | real people fidget and shift weight; AI motion described as "slightly too fluid" | https://www.nemovideo.com/blog/why-ai-videos-look-fake-how-to-fix |
| **Physics / gravity** | "Path ignores gravity, mass, or solid contact" | creatide (above) |
| **Hands & fine detail** | "Fingers, rings, hair edges, and facial micro-shapes can morph or vanish"; hands on products especially | creatide (above) |
| **Cloth** | "Limbs or cloth bend past natural limits" | creatide (above) |
| **Eyes** | normal blink rate 11.6/min (13.5/min attentive); eyes make small saccades, not just blinks; gaze is "predominantly unconscious" and mis-timed gaze reads as uncanny | https://www.mimicminds.com/post/uncanny-valley-explained · https://www.uni-bamberg.de/fileadmin/cg/publications/canales23/Canales23_Gaze.pdf |
| **Face drift** | "even a small drift in eye spacing or jawline registers as wrong" | atlabs (above) |
| **Skin** | "Plastic skin usually means you asked a stylized model for realism" | atlabs (above) |
| **Lips vs audio** | "A talking character with a wandering mouth breaks the illusion instantly" | atlabs (above) |
| **Light / shadow** | "shadows that fall in two directions" | atlabs (above) |
| **Camera** | "Camera move fights subject"; handheld phone shake described as the UGC look | creatide (above) · https://morphic.com/ai-glossary/camera-shake |
| **Sensor texture** | AI frames have "no sensor noise"; one guide gives 30–40% grain in Soft Light for phone-look, plus subtle motion blur and chromatic aberration | https://invideo.io/blog/ai-video-post-production/ |
| **Overloaded clips** | unnatural motion attributed to one short generation carrying subject action + camera + environment + contact at once | creatide (above) |
| **Export** | 1080p export described as surviving platform compression more naturally than 4K | invideo (above) |

**Inference (labelled):** the transfer tools in section 2A take their body timing, weight shifts and camera shake from a real recording rather than inventing them, which is the mechanism the sources describe for the "weight/too smooth/physics" row. Hands, cloth, eyes and skin are still generated.

---

## 5. "Clone of a real person" ads + platform rules

**Documented clone workflows**
- HeyGen: a 15-second video of yourself → Avatar V twin (above).
- One pattern described: a founder or employee records a 2-minute consent video once; the platform clones face and voice for later ads (https://aiavatar.tech.blog/2026/05/07/how-to-create-ai-ugc-ads-using-your-ai-twin-complete-guide/).
- Arcads: 300+ / ~1,000+ licensed actors (figures differ by source), each reported as having consented to licensing face and voice (https://www.wireflow.ai/blog/arcads-vs-creatify).
- Sora "Cameos" (a consent-gated likeness feature) — product now discontinued (above).

**What the rules say**

| Platform | Rule (as written by the source) | Source |
|---|---|---|
| **Meta — all ads** | Meta applies an "AI info" label when its own gen-AI ad tools make a significant edit; "When these tools result in the inclusion of an AI-generated photorealistic human, the label will appear next to the Sponsored label (not behind the three-dot menu)." Meta said it would begin "automatically detecting ads created or edited using third-party AI tools through industry-standard signals." Reported start of automated third-party detection for ads: 2026-06-01. | https://about.fb.com/news/2025/02/gen-ai-transparency-metas-ads-products/ · https://www.digitalapplied.com/blog/ai-content-labeling-rules-advertisers-2026-reference |
| **Meta — political / social-issue ads** | advertiser must disclose photorealistic image/video or realistic audio made or edited with AI that shows a real person saying/doing something they didn't, a realistic person that doesn't exist, or an event that didn't happen; undisclosed ads are rejected | https://transparency.meta.com/policies/ad-standards/SIEP-advertising/SIEP/ |
| **Meta — organic posts** | users must disclose photorealistic video or realistic audio that was digitally created or altered, via the AI disclosure tool | https://about.fb.com/news/2024/04/metas-approach-to-labeling-ai-generated-content-and-manipulated-media/ |
| **TikTok** | creators must label realistic AI-generated content, incl. entirely AI-generated videos of real or fictional people, people shown doing/saying what they didn't, and AI speech; TikTok reads C2PA Content Credentials to auto-label (since May 2024). TikTok is quoted: "the AIGC label is a disclosure mechanism, not a distribution signal." | https://www.tiktok.com/tns-inapp/pages/ai-generated-content · https://www.cinerads.com/blog/tiktok-ai-content-policy |
| **YouTube** | disclose AI that "Makes a real person appear to say or do something they didn't do", "Alters footage of a real event or place", or "Generates a realistic scene that didn't actually occur". Not required: colour tweaks, beauty filters, voice cloning for your own voiceovers, clearly unrealistic content. YouTube auto-labels its own-tool content, C2PA content, and detected AI. "Disclosing AI content won't limit a video's audience or impact its eligibility to earn money." | https://support.google.com/youtube/answer/14328491 |
| **US FTC — reviews & testimonials rule** (effective 2024-10-21) | bans reviews/testimonials that misrepresent they are by someone who does not exist or who didn't actually use the product; FTC: "AI-generated reviews are covered by the final rule"; civil penalties apply | https://www.ftc.gov/news-events/news/press-releases/2024/08/federal-trade-commission-announces-final-rule-banning-fake-reviews-testimonials |

---

## 6. Already in your setup

- **Higgsfield connector (Ultra plan):** Genjutsu motion transfer + object replace, Kling 3.0 / Omni Edit, Seedance 2.0 / 2.5, Wan 3.0 / Prime, MiniMax H3, Veo 3.1, Gemini Omni Flash 1.1 (edit mode, 4K), FLUX 3 Video, Sync Lipsync 3, Topaz, Bytedance Upscale, FPS Boost, Deflicker, Remove Background (SAM 3), Depth Anything Video. Kling Motion Control and Wan Animate are **not** listed there as their own models.
- **fal account** (`tools/fal`): fal hosts Kling Motion Control (v2.6 / v3) and Wan 2.2 Animate Move/Replace — not yet run from this repo (no such rows in `tools/fal/runs.jsonl`).

---

## 7. Reels, reverse-engineered

Three reels Damon sent as inspiration (2026-09-27). Full breakdowns, contact sheets and frames in `reels/<id>/`. Method: `playbooks/reverse-engineer-a-reel.md`. The @lutherlongford reel (DdsA5QXIZ-i, section 1) has not been broken down.

| | Reel A — @tiktoktitans_tts | Reel B — @jullyblond | Reel C — @paolo0.o |
|---|---|---|---|
| Link | https://www.instagram.com/reel/DdrtGPgIzXA/ | https://www.instagram.com/reel/DdpRowAM42r/ | https://www.instagram.com/reel/DdntUJEOUL6/ |
| What | Creator "meets" three commenters rebuilt with AI from their profile photos; they walk in, shake hands, wave | Baby sits still; camera flies around him (overhead, rug level, behind, across the room) and back to his face | "2 hours of sleep be like": shot / reverse-shot of a man and a golden retriever walking upright; paw to lens ↔ hand to lens, dog selfie, dog walks off, man rubs his eyes |
| Length / cuts | 48.9 s · 23 cuts, 15 of them in the first 15 s, then three ~7–10 s takes | 8.2 s · 6 shots, cuts at 0.33 / 1.71 / 2.33 / 4.33 / 5.50 s, each hidden in a whip or blur | 18.7 s · 7 shots alternating man / dog, cuts at 0.93 / 2.65 / 4.13 / 7.23 / 9.18 / 15.12 s, clean cuts |
| File | 1080×1920 | 720×1280 served · 24 fps | 1080×1920 · 60 fps |
| Likes / comments | 496 / 90 | 729,388 / 2,627 | 204,979 / 874 |
| Hook 0–2 s | face close-up, mid-sentence, caption "Turning into people to prove i'm using AI" | full-frame baby face, camera rips backward, overhead by 1.7 s | caption over a man walking; at 0.93 s the reverse shot is a dog walking on two legs |
| Sound | voice + a low continuous bed | music only; full band in at ~1.1 s | music only; soft piano (commenters: "Zelda music", "Clash royale sound?") |
| Stated method | "I've taken their profile picture and a couple more reference images" | none | hashtag "#ai" in the caption; nothing else |
| Comments on method | "Are you going to share what ai you used to make this?" | "AI slop" · "Какой ии можно это сделать?" ("Which AI can do this?") | "Woah 🤯 is this real?" |
| **Inference:** how | real stand-in performer filmed with the host, identity replaced from refs (video-to-video replacement), host kept real | either image-to-video per shot with a camera move, or a real 360 camera swung around a still baby — the file doesn't settle it | man shots real; dog shots generated — either motion transfer from the creator acting the dog's moves (poses mirror his own shots), or image-to-video per shot — the file doesn't settle it |
| Our stack (est.) | phone plate → Genjutsu per person (~88 / 8 s) + optional GPT Image 2.5 stills → matte + comp → edit · ≈280 for 3 people | GPT Image 2.5 hero + 4 angles (~14) → 5–6 × Seedance 2.5 4 s (~140–170) → edit · ≈155–185 | phone takes (real side + "character" side) → GPT Image 2.5 character still (~2.75) → Genjutsu on 3 character takes (~176) → edit · ≈180; image-to-video only ≈115 |

**Damon's ad idea, as he said it (recorded, not assessed):** open as an ad, then cut to "turn on the music — we made this song just for you" — the brand owns every asset, the song included. Reels B and C carry no speech; both run on music alone.
