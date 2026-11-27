# UGC Video

Makes a finished 9:16 creator-style ad video in one of six formats: review (creator speaks, product optional), product (off-screen voiceover), unboxing, try-on, tutorial (Step N labels), website tour (real screenshots).
Source: `ugc-video/SKILL.md`, `ugc-video/references/formats/{review,product,unboxing,try-on,tutorial,website}.md`, `ugc-video/references/{boards,duration,ugc-character,ugc-board,ugc-clip,monologue-craft,product-intake,product-product-intake,website-capture,saas-clip-prompt}.md`, `ugc-video/scripts/plan_duration.py.md`

## Inputs it needs
- Format (default review). Duration as an integer of at least 4 s (offer 10/15/30/45); clip length 4-15 s each (planner: 16 s = 12+4, 31 s = 15+12+4).
- Creator photo (consenting adult, authorized) or a requested gender; a generated adult 21+ is used otherwise.
- Product photo or URL (required for product/unboxing/try-on/tutorial; optional for review; website needs the site URL).
- Optional: approved claims (the complete allowlist), language/accent (default English, American), location, outfit, mood, music, on-video text.

## Steps in order
1. Safety and truth gate (creator authorization, allowed promotion, claims allowlist, no fake testimonials) before anything is spent.
2. Intake: one bundled question for missing duration, creator and product.
3. Normalize the product once (`product_reference`, canonical description, tier, mechanics, scale, label treatment, `approved_claims`).
4. Lock the creator: `soul_2` 3:4 2k image (or the supplied photo); website format also de-slops it with `seedream_5_5`.
5. Plan durations with `plan_duration.py`; write the monologue / voiceover (hook, one idea per beat, no AI-tell phrases) and split it per board.
6. Boards one at a time (`gpt_image_2_6`, 21:9 strip of 8 or 4 vertical slots), each cleaned with `seedream_5_5`, inspected, and only the cleaned board seeds the next board and the video.
7. Write every clip prompt, then submit clips in batches of at most 6 to `seedance_2_5` (`omni_reference`, native speech, audio on).
8. Inspect clips (identity, product, duration, speech, text); retry only failed indices once.
9. Assemble and caption in video-montage (opt-in text/post package); deliver the checked MP4.
Website format: capture real mobile screenshots with headless Chromium, no boards, one continuous talking-head clip per beat, screenshots overlaid as cards.

## Prompt blocks, word for word
Per-format board and clip prompt files hold the same skeleton with format changes: product (`ugc-product-boards.md`, `ugc-product-clip-prompt.md`), unboxing (`ugc-unboxing-board.md`, `ugc-unboxing-clip.md`, `unboxing-ugc-character.md`), try-on (`ugc-try-board.md`, `ugc-try-clip.md`, `try-on-ugc-character.md`), tutorial (`ugc-tutorial-boards.md`, `ugc-tutorial-clip-prompt.md`), website (`saas-clip-prompt.md`, `saas-monologue.md`, `saas-ugc-character.md`); all in `ugc-video/references/`. The review set is quoted below.

**Creator (Soul 2.0) prompt structure, review format**  
`ugc-video/references/ugc-character.md`

```
A [age band from Variety pool] [man/woman], [expression — pick one from the Approved mid-action expressions list], [hair color + length from Variety pool], [build vibe], with high model facial features, symmetrical features, well-proportioned figure, natural skin texture, standing in a [specific location with architectural details].
[Light direction and quality — MUST be cool/neutral daylight, NEVER golden hour, NEVER warm sunset, NEVER orange/amber cast] falls across her face — neutral, clean, no warm cast, no retouched glow. Skin texture is real, with visible pores and natural unevenness.
[He/She] wears [outfit matching category × tier from the matrix — pick a non-default option from the matrix's list; a dressed option realizes as the Wardrobe Bank recipe — layered with the Universal modesty triplet and any per-garment specifics]. Body in a calm neutral pose — relaxed standing, one hand resting naturally.
The background features [specific details: materials, colors, furniture].
Color palette dominated by [space colors — keep neutrals; avoid amber/orange dominance].
Casual handheld iPhone selfie taken by [her/him] at arm's length — head and shoulders fill the frame, slight natural tilt, slightly off-center, intuitive composition, captured mid-moment. Subject in clear focus with the background naturally falling out as in any phone photo.
Shot on iPhone front-facing camera. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. No fisheye lens, no ultra-wide distortion. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

**Creator closing block, appended verbatim to every creator prompt**  
`ugc-video/references/ugc-character.md`

```
Self-portrait selfie shot on iPhone front-facing camera held by the subject at arm's length — head and shoulders fill the frame, casual handheld framing, slight natural tilt, slightly off-center, slightly imperfect, not posed. Phone-sensor grain and realistic skin texture preserved, no retouch, no smooth-skin filter. No fisheye lens, no ultra-wide distortion. Authentic UGC creator phone selfie, NOT editorial portrait, NOT fashion magazine.
```

**Storyboard sheet prompt template (8 slots, review)**  
`ugc-video/references/ugc-board.md`

```
[@Image1 product reference + ANGLE LOCK if product is present.] [@Image2 character reference, or @Image1 if no product.] [@Image3 previous-board reference if K > 1, with explicit instruction to preserve identity / location / lighting / wardrobe / product from this reference.] The same person appears in every slot with identical face, hair, body, and identity — no changes to features, hair, or proportions between slots.

A single horizontal storyboard sheet composed of exactly EIGHT equal-size 9:16 vertical slots arranged in ONE HORIZONTAL ROW, separated by thin white gutters on a clean white background, total sheet aspect 21:9. Do NOT make two rows and do NOT make a grid — exactly eight panels in one row, never ten, never twelve. All eight slots are active photorealistic UGC iPhone-style stills that tell one continuous [clip_duration]-second video clip as eight sequential beats — slot 1 is beat 1 (opening), slot 8 is beat 8 (closing). There are no placeholder slots. Each adjacent pair of slots is a DIFFERENT camera setup — a different POV (selfie vs static camera), a different distance band (tight/macro vs medium vs wide), and a different action — so every beat boundary reads as a crisp hard cut, never a morph.

Setting and lighting in all eight slots default to the same environment, time of day, and light direction visible in the character reference image (and previous-board reference if provided), unless the story requires a different location. Outfit stays identical across slots within the same location.

Product (if present) appears at realistic real-world scale, approximately [X cm] in real size, fitting naturally in the character's hand without enlargement. Exactly one [product] appears in frame in every slot where it is visible — never a duplicate, never a look-alike clone. Product placement in every slot is clean: either fully visible held in one hand, fully hidden inside a closed bag/box/pocket, or absent from the frame — never half-sticking out, never balancing awkwardly, never partial.

The character has exactly two hands. In selfie POV slots, one hand is occupied by the phone (off-frame or visible at edge), so only one hand is available for action — never two objects in selfie POV. Every slot names what EACH hand is doing — one role per hand, the idle hand parked explicitly (holding the phone, resting at her side, flat on the counter) — never more than two simultaneous hand-roles. Slots requiring two free hands are static camera POV with the phone not in frame. POV may change between slots — every POV change aligns with a hard cut between slots, never a smooth transition.

Slot 1 — exact 9:16 vertical photorealistic UGC iPhone still, [selfie/static camera POV], [distance band]: [camera framing, character action, product placement (visible in hand / hidden inside X / absent), explicit hand allocation naming BOTH hands' roles (e.g. "left hand holds phone off-frame, right hand holds product"; an idle hand is parked — resting at her side, flat on the counter), micro-behavior, light/setting note].

Slot 2 — exact 9:16 vertical still, [POV — different framing from slot 1], [distance band — different from slot 1]: [...].

Slot 3 — exact 9:16 vertical still, [POV/band different from slot 2]: [...].

Slot 4 — exact 9:16 vertical still, [POV/band different from slot 3]: [...].

Slot 5 — exact 9:16 vertical still, [POV/band different from slot 4]: [...].

Slot 6 — exact 9:16 vertical still, [POV/band different from slot 5]: [...].

Slot 7 — exact 9:16 vertical still, [POV/band different from slot 6]: [...].

Slot 8 — exact 9:16 vertical still, [POV/band different from slot 7]: [...].

Rendering rules: every slot is an exact 9:16 vertical rectangle, all eight slots identical in size, arranged in ONE HORIZONTAL ROW (do NOT make two rows or a grid — exactly eight panels in one row, never ten, never twelve) with thin white gutters on a clean white background, total sheet aspect 21:9. All eight slots are active — there are no placeholder slots. No two adjacent slots share both their POV and their distance band. Active slots are photorealistic iPhone-style UGC stills with natural light and casual real-life feel. The character's identity is identical across all eight panels. The character has exactly two hands; selfie POV occupies one hand with the phone, leaving one hand for action; two-handed actions are static camera POV; every slot names each hand's single role, the idle hand parked explicitly, and the total simultaneous hand-roles never exceed two. POV may change between slots; every POV change aligns with a hard cut, never a smooth transition. The product (if present) appears at realistic real-world scale relative to the character's hand and body, never enlarged for visibility, and keeps the same visible angle from the reference image across all appearances. Product placement is always clean: fully held in hand, fully hidden inside a closed container, or absent — never partial, never sticking out, never balancing awkwardly. Exactly one product in frame wherever it appears — never duplicated. Each prop holds exactly one state per slot — a cap is on or off, never both. No on-image text of any kind: no header, no metadata, no captions, no pop-text, no badges, no numbers, no subtitles, no watermarks. No legible text or numbers on any prop beyond the product's own label and the garment's own large fictional print. No shallow depth of field, no bokeh, no lens flare, no beauty filter, no cinematic color grade [omit these negatives when user_request explicitly asks for a cinematic look]. No fisheye lens, no ultra-wide distortion. No mirror or reflection shots (unavoidable mirror = partial reflection only, matching the subject exactly). No deformed hands. No third arm, no extra hands, no duplicated limbs. No additional brands or logos beyond the user's product. No invented product claims.
```

**Board cleanup prompt (seedream_5_5, shared by every board)**  
`ugc-video/references/boards.md`

```
KEEP EXACTLY the framing, composition, slot layout, camera distances, poses,
identity, body, product geometry and real label. Change only micro-realism:
natural skin/material texture, gentle daylight and fine sensor noise, authentic
phone photo, deep focus. Preserve face proportions exactly. Avoid waxy skin,
beauty filters, oversaturation, HDR glow, oversharpening and cinematic bokeh.
No added watermark or text. Preserve existing tutorial Step N headings exactly.
```

**Seedance clip prompt structure (review)**  
`ugc-video/references/ugc-clip.md`

```
Style & Mood: UGC iPhone aesthetic, [light description matching the board], [SELFIE: front-facing camera, intimate handheld feel | STATIC: locked-off static camera, completely static, frozen frame | MIXED: starts SELFIE handheld, hard-cuts to STATIC locked-off, hard-cuts back to SELFIE handheld — POV alternates per cut], social media vertical format.

Narrative Summary: [1 sentence stating what happens in this clip — references the arc_role and the throughline of the 8 cuts. Close it with a register calibration phrase, gated THREE ways by `user_request`: NATURAL (DEFAULT — no signals needed) — close with `performed by a natural, engaged creator — genuine reactions, lively but human, never staged screaming energy` (or near-equivalent). HYPED (opt-in ONLY) — when `user_request` carries an explicit energy signal (`hyped` / `hype` / `energetic` / `explosive` / `high-energy` / `viral energy` / `insane energy`), close with `performed by an INSANELY hyped creator with explosive screaming energy throughout` (or near-equivalent). CALM — skip the calibration phrase entirely when `user_request` signals a calm-tone aesthetic (`goth` / `vampire` / `cinematic noir` / `cold` / `passive` / `deadpan` / `clinical` / `refined` / `luxury-passive` / `minimal` / `somber` / `serious` / `dark` / `shadowy` / `quiet` / `GRWM` / `routine` / `process-led`). The explicit `user_request` word always wins].

Dynamic Description:
Cut 1 (0-Xs) — [framing distance per board slot 1, e.g. MEDIUM CLOSE-UP, TIGHT CLOSE-UP, MACRO, WIDER, PRODUCT-EXTENDED] [POV per slot 1]: [action from slot 1, explicit hand allocation (role of EACH hand, ≤ 2 simultaneous hand roles), 2+ micro-behaviors, expression, and — only when present — product placement]. Hard cut to.
Cut 2 (...) — [framing distance / POV per slot 2, a DIFFERENT framing from cut 1]: [action from slot 2, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 3 (...) — [per slot 3, different framing from cut 2]: [action from slot 3, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 4 (...) — [per slot 4, different from cut 3]: [action from slot 4, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 5 (...) — [per slot 5, different from cut 4]: [action from slot 5, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 6 (...) — [per slot 6, different from cut 5]: [action from slot 6, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 7 (...) — [per slot 7, different from cut 6]: [action from slot 7, hand allocation, 2+ micro-behaviors, expression, and optional product placement]. Hard cut to.
Cut 8 (Ys-end) — [per slot 8, different from cut 7]: [action from slot 8, hand allocation, 2+ micro-behaviors, expression, and optional product placement].

Static Description: [1-2 sentences: setting, ambient details, props, light direction — match the board image's environment].

Audio: She speaks to camera, iPhone microphone audio with natural room tone[, IF K==1 AND non-verbal cues used: include bracketed sounds at the start of Cut 1, e.g. [*small bright laugh*] [*soft gasp*] [*delighted 'oh!'*] (HYPED register only: [*explosive gasp*] [*hyped yelp*])]: "[monologue_segment, distributed across the 8 cuts at natural phrase boundaries]"

[ONLY when user_request explicitly asks for music or names a genre/mood — Music: [genre/mood], low in the mix under the voice, swells at [the peak beat], returns under the closer.]

Facial features clear and undistorted, consistent clothing throughout. Shot on iPhone, natural lighting, social media aesthetic. [SELFIE-only: slight natural handheld micro-shake from her grip | STATIC-only: locked-off static camera, absolutely static, zero camera movement of any kind, no shake, no drift, no breathing wobble | MIXED: handheld micro-shake during selfie cuts, locked-off frozen frame during static-camera cuts]. No on-screen text, no subtitles, no captions, no watermarks, no legible text on any object except [when a product exists: the product's own label and] the garment's own large fictional print, no real brand logos anywhere, no cinematic grade, no film grain, no bokeh, no lens flare, no fisheye lens, no ultra-wide distortion, no slow motion, no beauty filter, no third arm, no extra hands, no duplicated limbs, no deformed hands.
```

**Seedance quality suffix (end of every clip prompt)**  
`ugc-video/references/ugc-clip.md`

```
Facial features clear and undistorted, consistent clothing throughout. Shot on iPhone, natural lighting, social media aesthetic, [POV-matched movement language]. No on-screen text, no subtitles, no captions, no watermarks, no legible text on any object except [when a product exists: the product's own label and] the garment's own large fictional print, no real brand logos anywhere, no cinematic grade, no film grain, no bokeh, no lens flare, no fisheye lens, no ultra-wide distortion, no slow motion, no beauty filter, no third arm, no extra hands, no duplicated limbs, no deformed hands.
```

**Website format: creator de-slop prompt (seedream_5_5)**  
`ugc-video/references/formats/website.md`

```
KEEP EXACTLY the framing, composition, pose, subject and identity of this
vertical portrait — no reframe, no zoom, no crop, no change to the person's
face / hair / body / clothing. CHANGE ONLY micro-realism: true-to-life
pore-level skin with natural texture and fine vellus hair, real material
detail, even natural daytime light with gentle highlight roll-off and faint
true sensor noise, a flat authentic iPhone selfie, deep focus. PRESERVE the
face's exact shape / width / proportions 1:1 — do NOT squeeze / narrow / slim /
stretch the face. AVOID AI-slop: waxy plastic skin, airbrushed poreless skin,
beauty-filter smoothing, over-saturation, HDR glow / bloom / halos,
oversharpening, teal-orange grade, shallow depth of field, bokeh, cinematic /
DSLR look. No added text, no watermark.
```

**Website format: no-UI ban line (every clip)**  
`ugc-video/references/saas-clip-prompt.md`

```
_No website, no web interface, no app UI, no screen / monitor / browser / rendered content on any
phone or device screen anywhere in the shot._
```

**Review clip request (params)**  
`ugc-video/references/formats/review.md`

```
{
  "index": 1,
  "params": {
    "model": "seedance_2_5",
    "prompt": "<clip prompt>",
    "count": 1,
    "aspect_ratio": "9:16",
    "resolution": "1080p",
    "duration": 15,
    "mode": "omni_reference",
    "generate_audio": true,
    "medias": [
      { "value": "<clean_board_job_id>", "role": "image" },
      { "value": "<character_media_id>", "role": "image" },
      { "value": "<product_reference>", "role": "image" }
    ]
  }
}
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Creator image | `soul_2` | 3:4, 2k, count 1 |
| Storyboard sheet | `gpt_image_2_6` | 21:9, 2k, quality high, product + creator + previous cleaned board as images |
| Board cleanup | `seedream_5_5` | 21:9, 2k, raw board as image |
| Creator de-slop (website) | `seedream_5_5` | 3:4, 2k |
| Clip with native speech | `seedance_2_5` | 9:16, 1080p, 4-15 s, `omni_reference`, `generate_audio:true` |
| Voice, TTS, dubbing | none (`generate_audio` is never called) | native Seedance speech only |
| Assembly, captions | video-montage workflow | opt-in |
| Duration plan, site capture, probes | none (sandbox scripts) | free |

## Checks and gates
- Refuses public figures, minors, impersonation, political/adult/gambling/drug/weapons/financial promotion; try-on also refuses intimate apparel.
- Claims come only from the user's allowlist; no invented purchase, results or reviews; product output is framed as a brand demo, not a customer review.
- No generation until creator input and duration are resolved; one later ask for text/post package.
- Cleanup is mandatory: never continue from a raw board; stop dependent generation if cleanup or the visual check fails.
- No baked text (except tutorial Step N labels); no greeting after board 1; a timeout is polled, never resubmitted; moderation stops the path; a locked model is never swapped.
- Website: real captured pixels only; a capture failure asks for screenshots or a talking-head-only version.

## Price pattern
Quotes before paying. From `_prices.md`: `seedance_2_5` 10 s 1080p 160 (16 per second), 480p 30; pictures 1.75 to 2.5 each. A 15 s review video at 1080p is 0.12 (creator) + 2 pictures (about 5, board and cleanup) + 240 (clip): about 245 credits. At 720p the clip is about 105. Nothing in `_prices.md` quotes `gpt_image_2_6` or `seedream_5_5` directly (nearest figures used).

## Cheap swap
- Clip (`seedance_2_5` 240 for 15 s at 1080p): `wan3_0` 480p 7.5 per 10 s (about 11 for 15 s; takes image and audio refs, speech on) or `gemini_omni_flash_1_2` 360p 7.5 per 10 s (7 images max, 10 s with refs): saves about 95 percent, quality lower. The workflow locks Seedance, so this is a draft route; upscale with local Real-ESRGAN.
- Boards and cleanup (about 2.5 each): `seedream_5_0_flash` 2k 0.5 or `gpt_image_2_6_flare` 1k low 0.75: saves up to 2 per picture.
- Creator image: `soul_2` is about 0.12 already.
- Script, monologue, product intake, claims check: Claude on the plan, free.
- Voiceover for the product format: Kokoro tts locally (free) over a silent Wan clip instead of native speech.
- Duration planning, site screenshots, probes, assembly, captions (local Whisper): already free.
