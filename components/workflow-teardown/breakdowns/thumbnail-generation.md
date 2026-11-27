# Thumbnail Generation
Cinematic YouTube/Instagram thumbnails and video covers: concept framework, casting, scene, 4K render, surgical tweaks, text overlay.
Source: `thumbnail-generation/SKILL.md`, `thumbnail-generation/_files.md`, `thumbnail-generation/references/thumbnail-frameworks.md`, `thumbnail-generation/references/text-overlay-bake.md`, `thumbnail-generation/scripts/bake_text_overlay.mjs.md`

## Inputs it needs
- Scene text (what the video is about).
- 0 to 3 face or character reference photos (identity locked) or an explicit choice of a generated person or no people.
- Optional: a reference thumbnail (style example only, never a face source), a logo, headline text and whether to bake it, ratio, emotions, takes, variant count.
- Defaults: ratio 16:9, one take, emotion shock when a person is in frame.

## Steps in order
1. Collect inputs and apply per-field defaults. Run the character gate (ask once: yourself, a generated person, or people-free) and the variant-count gate.
2. Pick the framework(s) from `references/thumbnail-frameworks.md`; brainstorm at least five and carry the strongest (may combine two).
3. If a reference thumbnail is supplied: ask Match or Unique once, then extract the strict-JSON fields by eye. It never enters `medias`.
4. Upload faces and logo (`media_upload_widget`, or `media_upload` + PUT + `media_confirm`).
5. If a 3D logo is wanted, submit the 3D logo prompt as its own call and wait for it.
6. Assemble one prompt per variant from the 11 house blocks; variants differ only by the Expression phrase and/or one ALTERNATE TAKE line.
7. Submit one `generate_image` per variant in parallel (never `count`).
8. Post-render check every image; re-render the same prompt up to twice; report failures honestly.
9. On request, apply the surgical tweak prompts on `seedream_5_5` i2i, chained.
10. Deliver. Headline supplied and not baked: bake the overlay (`bake_text_overlay.mjs`, style beast/fire/neon-lime/clean-glass/marker) into a flat PNG, upload, confirm.

## Prompt blocks, word for word
All strings below are copied by script from the skill file. Placeholders in angle brackets must be filled before sending; a `<...>` slot never ships.

**House prompt structure, blocks 1 to 11** (`thumbnail-generation/SKILL.md`)
`````
1. **Frame contract** — `Bold, punchy YouTube-thumbnail composite — poster-grade, photoreal and high-impact, NOT a muted cinematic movie still, <ratio note>, single unified frame — no split-screen, no diagonal divide, everything blends smoothly and organically across the same continuous shot.` For 9:16 add `subject framing adapted to the tall canvas, faces in the upper two-thirds`. Framework 8 "Graphical Representation" replaces this with a clean diagram/graphic brief and drops the photoreal + lighting-rig blocks. A non-photoreal faceless Phase-8b handoff makes the same replacement using its supplied render medium and also drops the glossy grade.
2. **Scene brief** (if the user described exact content): `SCENE BRIEF (must be depicted exactly): <text>.`
3. **Text contract** — default: `No text, no readable UI labels, no watermark.` Only when baked text is explicitly wanted: `TEXT: bold thumbnail headline text baked into the image, reading exactly "<TEXT>" — massive, ultra-legible sans-serif with a clean outline/glow treatment, placed where it never covers the subject's face. No other text, no watermark.` When the user EXPLICITLY asked for a text-based framework that carries an in-image UI element (Social UI, News Clip, Day badge, Map/Aerial callout — see the frameworks reference), add instead: `BAKED UI: a <generic chat bubble / DM row / star-review card / breaking-news lower-third / DAY N badge / map callout label> reading exactly "<short text>", clean generic platform styling — NO real brand name, app name or network logo. Keep the text short and truthful to the video.` A text-carrying framework that was only auto-picked (not explicitly requested) renders text-free instead. This is the ONLY sanctioned readable text besides the headline; every other prop stays text-free and wordmark-free.
4. **SUBJECT(s)** — see Identity Lock below. Up to 3 characters; photo characters map positionally onto attached face references. **Render the subject LARGE and dominant — the clear hero, filling roughly 40–60% of the frame, chest-up or medium-close, pushed to the foreground and cleanly separated from the background; NEVER a small subject stuck in the lower third, never a distant video-frame look.** End with `All faces crisply sharp as the anchors of the shot.`
5. **KEY ELEMENTS** — signature props/effects that make it pop.
6. **LOGO** (if any) — 2D: `the attached logo placed into the composition EXACTLY as provided — keep its shapes, colors and proportions untouched, clean 2D placement at a strong focal position, subtle drop shadow for separation, never covering the subject's face.` 3D: `the attached 3D logo render integrated into the scene as a physical volumetric object — glossy dimensional material, catching the scene's key light and rim light, casting a soft contact shadow, composited at a strong focal position without covering the subject's face.`
7. **LOCATION** — place, time of day, weather, atmosphere.
8. **COMPOSITION** — subject LARGE and foreground-dominant (fills ~40–60% of the frame, chest-up / medium-close) on a power third, strong subject-vs-background separation so the subject pops off the background; scale hierarchy, camera angle, depth layering.
9. **BACKGROUND TREATMENT (blended, not divided)** — bold saturated color field, vivid punchy gradients, strong color contrast, texture, blur, edge falloff.
10. **LIGHTING (the YouTube rig — mandatory on people)** — `signature YouTube thumbnail lighting rig on the subject — a strong KEY LIGHT sculpting the face with crisp highlights and controlled falloff, a soft dreamy DREAM LIGHT fill lifting the shadows with a subtle cinematic glow, and a defined BACK LIGHT + HAIR LIGHT tracing a clean bright rim along the hair, shoulders and silhouette, separating the subject sharply from the background.` Colored rim variant: replace last clause with `a defined <color> BACK LIGHT + HAIR LIGHT tracing a vivid colored rim ... with a subtle matching glow.` Rim palette: Ice Blue `#4DA6FF` "electric ice-blue", Neon Magenta `#FF3DBE` "hot neon magenta", Toxic Lime `#C8FF2E` "toxic neon lime", Amber Gold `#FFB63D` "warm amber-gold", Pure White. Key/fill NEVER change color — only back+hair.
11. **GRADE** — `vivid high-impact color grade, punchy high contrast, bright clean exposure, rich saturated colors that pop off the screen, deep blacks and bright highlights, crisp and glossy, poster-punchy, cohesive as one image. <ratio>.` Dial back to a restrained / soft / low-contrast grade ONLY on an explicit calm / premium / muted / aesthetic request.
`````

**Identity Lock (one per photo-referenced person)** (`thumbnail-generation/SKILL.md`)
`````
> CHARACTER N: the person from attached face reference #K — IDENTITY LOCK: reproduce this exact person with a photographic identity match — same bone structure, eye shape, nose, lips, jawline, skin tone, hairline and hair texture as the reference photo. Do NOT beautify, do NOT average with other faces, do NOT restyle the face; it must be recognizably the same person at a glance. Expression: `<emotion phrase>`.
`````

**Emotion casting (Expression slot phrases)** (`thumbnail-generation/SKILL.md`)
`````
**shock** (mouth open gasp, wide eyes), **hype** (ecstatic grin, blazing eyes), **fear** (terrified stare, frozen breath), **confusion** (one brow raised, puzzled), **determination** (locked jaw, laser focus), **smug** (knowing smirk), **charisma** (calm magnetic gaze, relaxed brows, faintest composed half-smile — charismatic leading-man poise, confident but never aggressive; the calm positive option — "determination" alone reads too harsh), **disgust** (recoiling grimace), **awe** (jaw dropped, glittering wonder), **rage** (bared teeth fury), **laugh** (head back).
`````

**Takes per emotion** (`thumbnail-generation/SKILL.md`)
`````
- `ALTERNATE TAKE: reframe as a low-angle hero shot — camera below eye level looking up, the subject towering with extra dominance, background perspective stretching upward, same scene and lighting.`
- `ALTERNATE TAKE: extreme close-up punch-in — the face and expression dominate more than half the frame, background compressed into soft bokeh context, same scene and lighting.`
- `ALTERNATE TAKE: wider dynamic shot with a subtle dutch tilt — more of the environment visible, subject anchored off-center on a power third, stronger motion energy sweeping the frame, same scene and lighting.`
`````

**Split frame contract** (`thumbnail-generation/SKILL.md`)
`````
Replace block 1 with: `SPLIT-FRAME thumbnail, <ratio note>: the frame divided into N
<halves|vertical panels> by clean bold seams, each panel its own complete mini-scene, unified
premium grade across all panels.` — then append exactly ONE mode sentence:

- **plain**: `Each panel shows one facet of the story: <panel 1: desc; panel 2: desc; ...>.`
- **before/after**: `LEFT panel: the BEFORE state — <desc>. RIGHT panel: the AFTER state —
  <desc>. Maximum visual contrast between the two states of the same transformation.`
- **versus**: `Each panel presents one contender lit and framed like a fighter poster:
  <panel 1: contender A desc; panel 2: contender B desc>. Equal visual weight, confrontation
  energy across the seam.`
- **custom**: `<the user's panel-by-panel description>.`

ALWAYS append: `No labels, no captions, no words, no numbers on or between the panels — the
comparison reads purely visually. All panels graded as one premium image.`
`````

**Surgical tweak prompts** (`thumbnail-generation/SKILL.md`)
`````
- **Emotion swap:** `Change ONLY the person's facial expression ... to: <phrase>. Keep identity, face structure, hair, pose, body, clothing, logo, background, lighting and composition EXACTLY unchanged, pixel-faithful — pure expression swap. Keep the YouTube thumbnail lighting rig intact.`
- **Background swap:** `Replace ONLY the background with: <desc>. Keep subject, face, identity, pose, clothing, logo and all foreground elements EXACTLY unchanged. Rebuild the lighting wrap around the subject so the new background's light direction, color and rim light read naturally — keep the YouTube rig.`
- **Background recolor:** `Shift ONLY the background color palette to dominant <color> tones. Keep the background's structure, content and depth exactly — only recolor. Rebuild the subtle ambient color wrap on the subject's edges but keep key light and fill on the face unchanged.`
- **Rim light recolor:** `Change ONLY the back light / hair light (rim light) color on the subject to <phrase> — the bright edge tracing hair, shoulders, silhouette. Do NOT change key light or fill; do NOT change background, pose, identity, clothing, logo, composition.`
`````

**3D logo prompt** (`thumbnail-generation/SKILL.md`)
`````
> Transform the attached 2D logo into a premium 3D logo render: extrude the exact logo shapes into glossy dimensional volumes, keep every letterform, proportion and brand color EXACT, high-end CGI product-render finish with soft studio reflections, subtle bevels, crisp edges, floating on a clean dark neutral studio background with a soft contact shadow. Centered, generous margins, no extra text, no watermark.
`````

**Submit call shape** (`thumbnail-generation/SKILL.md`)
`````
generate_image({ params: {
  model: "nano_banana_pro", prompt: "<variant prompt>", aspect_ratio: "<ratio>",
  resolution: "4k", medias: [ {value: "<face-id-1>", role: "image"},
                              {value: "<logo-id-or-3d-job-id>", role: "image"} ] } })
```
`````

**Reference analysis contract (JSON keys)** (`thumbnail-generation/SKILL.md`)
`````
brief (one dense sentence on the concept), subject (pose/action generically, NEVER a specific
identity), elements, location, composition, background, split (boolean), split_count,
person_count (0-3), emotion (one of the 11 presets or 'other'), emotion_detail (one vivid
sentence covering eyes, brows, mouth, head angle)
```
`````

**Per-field defaults** (`thumbnail-generation/SKILL.md`)
`````
- ratio `16:9` · takes 1 · emotion `shock` when a person is in frame; no person → the Expression
  axis is empty and variants = takes
- BACKGROUND: `bold, vivid saturated color-field gradient with punchy high-contrast tones matching the subject's palette, soft
  vignette, edge falloff`
- COMPOSITION: `the subject rendered LARGE and dominant — chest-up / medium-close, filling ~40–60% of the frame, pushed to the foreground on a power third, camera at eye level, strong separation from the background so the subject pops, shallow depth with a foreground accent element`
- KEY ELEMENTS: the most concrete depictable noun of the user's topic (your judgment),
  oversized, flying toward camera — omit when it would duplicate the SUBJECT
- LOCATION: omit the block
`````

**The 16 frameworks (concept layer)** (`thumbnail-generation/references/thumbnail-frameworks.md`)
`````
| # | Framework | Realize it with |
|---|---|---|
| 1 | Before/After Transformation | Split frames `before/after` mode — max contrast between the two states of one subject |
| 2 | Social UI (tweet / DM / review) | KEY ELEMENTS = a **generic** chat bubble / DM row / star-review card beside the subject; short message via BAKED UI; NO real platform brand |
| 3 | Three-Step Progression | Split frames plain/custom, 3 vertical panels: start → mid story-beat → end; optional per-panel number/Day badge |
| 4 | Compelling Screenshot | NOT a generation — use a real frame from the source video, or a Posed Action Shot that matches the video's first frame. Flag when the user has a source clip |
| 5 | Posed Portrait | The default: SUBJECT rendered LARGE (fills much of the frame) + Identity Lock + YouTube rig + Emotion; very little or nothing in the background — the subject IS the focus |
| 6 | Posed Action Shot | Scene brief = one intriguing action mid-moment; COMPOSITION uncrowded, single hero action |
| 7 | Highlighting a Specific Day | Any framework + a big `DAY N` badge (BAKED UI); pick a day in the last ~20% of the arc |
| 8 | Graphical Representation | Non-photoreal: REPLACE the Frame contract with a clean diagram/graphic brief (bell curve, simple familiar chart); drop the photoreal + lighting-rig blocks |
| 9 | Landscape | Environment is the hero; keep ONE small subject on a power third; lighting rig optional |
| 10 | Map/Aerial | Frame = a map or aerial photo; KEY ELEMENTS = a highlighted route / point (circle, arrow, label via BAKED UI) |
| 11 | Product | Product is the SUBJECT (hero, sharp, its own label exempt per Angle Lock); open the gap by making the product the answer to the title's question |
| 12 | Adding Text | Text policy overlay (default) or baked TEXT; use it as a callout (arrow + word) or as the continuation / answer to the title's question |
| 13 | Repetition of Objects | KEY ELEMENTS = a large quantity of ONE object filling the frame, still legible; add one context element + a subject for scale |
| 14 | Size Difference | COMPOSITION = extreme scale contrast between two elements central to the story (giant vs tiny) |
| 15 | News Clip | Generic "breaking news" lower-third / chyron over the image (BAKED UI, short truthful line); generic broadcaster styling, NO real network |
| 16 | Amplified Reality | Posed Action Shot + exaggerate ONE real element from the story (KEY ELEMENTS oversized); keep it plausible — over-amplification kills trust |
`````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Main thumbnail render | `nano_banana_pro` | resolution 4k always; aspect 16:9 / 4:3 / 9:16 / 4:5; medias = faces then logo; up to 14 refs |
| 3D logo from a flat logo | `gpt_image_2_6` | quality high, resolution 4k, 1:1 |
| Surgical tweaks | `seedream_5_5` (fallback `seedream_v4_5`, quality high) | resolution 2k, i2i from the picked job id; 3:4 instead of 4:5 |
| Text overlay | none | `bake_text_overlay.mjs` in the sandbox |

## Checks and gates
- Default is a CLEAN render with no baked text; text is baked into the generation only on an explicit user text request or a named text framework.
- Character gate: never generate a person as a silent default; with a supplied face, Identity Lock every time; with none and a people-centric concept, stop and ask once.
- Pre-submit checklist: right model; block 1 first and GRADE last; lighting rig + Identity Lock when a person is present; reference thumbnail not in medias; one variant per call; no-text line present when not baking.
- Post-render: identity matches, no stray text (or exact text if baked), expression and hero read at about 120 px wide.
- Retry limit: same prompt twice per variant, then report; faces drift stochastically, the fix is a re-render.
- Truthfulness law: the image may exaggerate but must honestly represent the video; no real brand, app or network names in baked UI.
- Unlim: if 4K is not covered, ask whether to run a covered resolution or pay.

## Price pattern
Not quoted (nano_banana_pro 4K, seedream_5_5, gpt_image_2_6 are absent from `_prices.md`). Cost = variants (emotions x takes, cap 16) x one 4K render each, plus optional 3D logo and tweaks. Quotes before paying.

## Cheap swap
- Concept and framework drafts: `seedream_5_0_flash` 2k at 0.5 credit instead of a 4K nano_banana_pro render; render the picked concept once at full quality.
- 3D logo: skip the paid step and place the flat logo, or `gpt_image_2_6_flare` 1k low at 0.75.
- Tweaks: `seedream_5_0_flash` 2k i2i at 0.5 instead of `seedream_5_5`.
- Concept brainstorm, framework pick, reference analysis, prompt assembly: Claude on the plan, free.
- Headline overlay: already free; local ffmpeg/Pillow does the same. Upscale a 2k pick with Real-ESRGAN (components/local-studio/README.md) instead of paying for 4K.
