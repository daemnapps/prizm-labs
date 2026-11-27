# Ad Multiplier

Takes one 4-30 s source ad and makes N independent versions: edit mode swaps named people, products, objects, clothes, backgrounds or text inside the same footage; recreate mode re-shoots the same ad as new footage for another market, language or cast.
Source: `ad-multiplier/SKILL.md`, `ad-multiplier/references/prompt-writer.md`, `ad-multiplier/references/recreate.md`, `ad-multiplier/references/media-pipeline.md`, `ad-multiplier/ui.yaml.md`

## Inputs it needs
- One source video, 4.0-30.0 s inclusive (never trimmed or looped; outside the range it stops).
- The change: what to replace/add/remove/modify, and the ordered list of outputs or a number N (N counts final videos).
- Replacement images (all, some or none) for each person/product; missing adult people are generated.
- Final size: 720p (recommended) or 1080p.
- Recreate mode only: target market/audience, spoken language, new product facts, up to 20 images.

## Steps in order
1. Pick the mode: Edit (default, keep footage), Recreate (re-shoot), or Hook/CTA only. One question if it fits two.
2. Intake once: edit, N, references, 720p/1080p.
3. Upload source once; `ffprobe` in the sandbox (duration, display aspect, audio stream and offset).
4. `video_analysis_create` once, poll `video_analysis_status`; the scenes become the timed caption. Derive a two-axis casting profile (look + hairstyle) for every person to be replaced.
5. Plan ordered outputs (zip lists by position, never a product of lists). Person replacement covers every appearance.
6. Missing adult people: one `soul_2` image each (3:4, 2k), 140-190 word prose prompt, studio background. Ask for approval of each generated person.
7. Write one prompt per output (COMPACT or DETAILED template below, max 3900 chars); validate and rewrite once if invalid.
8. Submit each output one at a time to `ad_multiplier` (`video_edit`, silent, `count` 1); retry a failed position once.
9. Finalize in one sandbox call: pull the source audio, trim and remux, check duration/aspect/size/audio, PUT to reserved upload slots, confirm.
10. Recreate mode skips 3-9: one `ad_multiplier_v2` request per output with the whole request in plain words; a finished job is the deliverable.

## Prompt blocks, word for word
**Missing-person image prompt example (Soul 2.0 call, prose form only)**  
`ad-multiplier/SKILL.md`

```
{"params":{"model":"soul_2","prompt":"A straight-on, eye-level full-body portrait features a strikingly beautiful 24-year-old Afro-Caribbean woman with supermodel facial features, symmetrical features, a well-proportioned figure, warm deep-brown skin with natural texture, and long dark softly waved hair. She stands poised with shoulders back, one foot angled outward, arms relaxed, and a direct camera gaze. She wears a structured matte-black blazer, opaque high-neck top, tailored wide-leg trousers, pointed-toe heels, thin gold chain, and small stud earrings. Her complete outfit and both feet are visible. A seamless matte-white studio backdrop and matching floor contain no props, furniture, text, logos, or clutter, leaving generous negative space around her centered figure. Soft, evenly diffused high-key natural studio lighting creates gentle grounded shadows, authentic skin detail, and controlled highlights without harsh contrast or overexposure. A crisp black, white, and subtle gold palette supports the modern fashion-editorial mood. Captured on a professional high-resolution digital camera with balanced vertical framing, deep depth of field, ample dynamic range, minimal noise, and razor-sharp focus from face to footwear, the image preserves realistic anatomy, natural hands and limbs, and a photogenic unretouched editorial finish without distortion or exaggerated traits.","count":1,"aspect_ratio":"3:4","quality":"2k"}}
```

**Source-text preservation block (appears once in every edit prompt)**  
`ad-multiplier/references/prompt-writer.md`

```
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
```

**Person-replacement exclusion line (once per replaced person)**  
`ad-multiplier/references/prompt-writer.md`

```
The original source person identified as [target] in @Video1 must never appear in any frame of the output. Replace that person completely with [ALIAS] from [@ImageN] in every appearance, transferring the complete reference-defined look and retaining only the original performance, pose, blocking, interactions, and timing.
```

**COMPACT edit template**  
`ad-multiplier/references/prompt-writer.md`

```
TASK - VIDEO EDIT:
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
<start>-<end>s: keep everything exactly the same
<start>-<end>s: <one operation sentence>. Keep every unrequested element, camera motion, lighting treatment, and overall color grading from @Video1 exactly the same.
```

**DETAILED edit template**  
`ad-multiplier/references/prompt-writer.md`

```
[@ImageN] — [ALIAS], the complete replacement look for [TARGET]: [complete visible identity, optional visible build/stature when discernible, hair, outfit, footwear, headwear, eyewear, jewelry, and accessories]. Transfer this entire look from @ImageN, including the full outfit and all worn accessories.
Preserve every caption, subtitle, and other untargeted on-screen text element from @Video1 exactly as it appears, including its wording, styling, placement, animation, and timing. Text physically attached to a replaced target follows that replacement.
Video edit. Keep this @Video1 clip exactly as it is — the same shots and cuts, camera moves, framing, composition, unmapped performers, setting, untargeted held and environmental props, lighting, pacing, and timing. Change only [complete scope], keeping source blocking, poses, motion, position, screen placement, and timing while rendering each replacement person's complete image-defined look.
1. [REPLACE | MODIFY | REMOVE | ADD] — [mapped target and operation, complete-look @ImageN binding when present, resolved clothing override when present, temporal scope, source-person exclusion when required, and interaction/reflection handling].
[IDENTITY | REFERENCE | EDIT] lock: [every mapping, untouched-content protection, anti-bleed rules, and generated two-axis profile when present].
Render [one imperative summary transferring each replacement's complete reference-defined look, including clothing and accessories, while inheriting only source performance and timing].
Everything else — [untouched people, objects, untargeted wardrobe, text, environment, lighting, the camera moves and all timing] — stays exactly the same.
```

**Edit submission (silent video edit)**  
`ad-multiplier/SKILL.md`

```
{"params":{"model":"ad_multiplier","prompt":"<validated prompt verbatim>","count":1,"duration":8,"duration_policy":"strict","aspect_ratio":"auto","resolution":"720p","mode":"video_edit","generate_audio":false,"medias":[{"value":"<source media id>","role":"video"},{"value":"<@Image1 confirmed user media id>","role":"image"},{"value":"<@Image2 approved generated-person job id>","role":"image"}]}}
```

**Recreate submission**  
`ad-multiplier/references/recreate.md`

```
{"params":{"model":"ad_multiplier_v2","prompt":"Recreate this ad for the German market in German, with the presenter in the image replacing the main presenter.","count":1,"resolution":"720p","medias":[{"value":"<source media id>","role":"video"},{"value":"<presenter image media id>","role":"image"}]}}
```

**Hook-only submission (hook / cta / both)**  
`ad-multiplier/references/recreate.md`

```
{"params":{"model":"ad_multiplier_v2","mode":"sections","section":"hook","prompt":"New hook: open on a close-up of the product with the question \"Still tired at 3 pm?\"","count":1,"resolution":"720p","medias":[{"value":"<source media id>","role":"video"}]}}
```

**Asset manifest entry shape**  
`ad-multiplier/SKILL.md`

```
[
  {"tag":"@Image1","asset_key":"uploaded_product","role":"product","target_id":"product_1","target":"the can held by the woman","state":"whole clip","complementary_of":null},
  {"tag":"@Image2","asset_key":"output_1_replacement_person_1","role":"person","target_id":"person_1","target":"the woman in the gray jacket","state":"whole clip","complementary_of":null,"appearance_authority":"complete_look","clothing_override":null,"replacement_casting_profile":{"apparent_racial_ethnic_presentation":"<positive fictional casting description>","hairstyle":"<positive length, texture, cut, and shape description>"}}
]
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Edit a person/product/background in the source | `ad_multiplier` | `mode:video_edit`, `generate_audio:false`, `duration_policy:strict`, duration `ceil(source s)`, `aspect_ratio:auto`, 720p or 1080p, `count:1` |
| Generate a missing adult replacement person | `soul_2` | 3:4, `2k`, `count:1`, no medias, prose prompt |
| Read the source (scenes, timing) | `video_analysis_create` (analysis tool, not a model) | once per source |
| Recreate the ad as new footage | `ad_multiplier_v2` | `count:1`, `resolution` 720p default, no duration/aspect/audio fields; `mode:sections` + `section` for hook/CTA |
| Audio restore, trim, QC | none (sandbox ffmpeg) | free |

## Checks and gates
- Refuses a source outside 4-30 s; stops before spend if analysis fails twice or the target is ambiguous (one bundled mapping question).
- Asks you to approve each generated person before any edit is paid; never offers a person that fails the two-axis (look + hairstyle) or quality check.
- Prompt gate: non-empty, at most 3900 chars, every `@ImageN` present, no ids or URLs, the preservation block exactly once, no conditional wording.
- Final gate (edit): duration within max(1/fps, 0.10 s), aspect within 1.5 percent, short edge within 8 px of 720/1080, AAC audio present when the source had audio. Raw silent widget output is never the deliverable.
- Never changes untargeted captions or text; `unlim_choice` is asked, never chosen for the user.
- Recreate: refuses source outside 4-30 s; 403 on plans below Pro; `nsfw`/`ip_detected` are not resubmitted; no `use_unlim`.

## Price pattern
Quotes before paying through the model's own estimate. Edit is billed by the source's duration at the Seedance 2.5 per-second rate; from `_prices.md`: `ad_multiplier` 10 s 720p = 70 credits per output. Each missing person adds one `soul_2` image (about 0.12 credit, per the Katana notes). Recreate costs `ceil(source s)` at the same rate (about 70 for a 10 s source at 720p, inferred, not quoted: `ad_multiplier_v2` cannot be quoted without a source video). A hook/CTA run reserves its longest length (hook 15 s, CTA 5, both 20) and refunds the unused seconds. Typical run, 3 outputs of a 10 s ad at 720p: about 210 credits.

## Cheap swap
- Edit (`ad_multiplier` 70/10 s): `wan3_0` 480p 7.5/10 s as a reference-to-video draft (up to 10 image + 5 video refs): saves about 90 percent, but it regenerates instead of editing, so source motion is not preserved. Use it only to test the idea, not to ship.
- Recreate (`ad_multiplier_v2`): `wan3_0` 480p draft with the source and cast images as refs and a Claude-written prompt: 7.5 vs about 70.
- Replacement person: `soul_2` is already the cheap door (about 0.12); `seedream_5_0_flash` 2k (0.5) is not cheaper.
- Source reading: replace `video_analysis_create` with local Whisper plus ffmpeg frames read by Claude: free.
- Audio restore, trim, QC: already free (ffmpeg); upscale a 480p draft with local Real-ESRGAN instead of paying for 1080p (saves about 150 per 10 s).
- Prompt writing: done by Claude on the plan, free.
