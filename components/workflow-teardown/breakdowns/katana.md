# Katana

Remixes a reference edit (a viral cut) into a finished new video for your subject: same visual language, rhythm, text and effects, new scenes. Also edits supplied footage from a brief.
Source: `katana/SKILL.md`, `katana/references/{generation,stills,budget,analysis,routing,compositing,qa-delivery,genjutsu-routing,creative-quality}.md`, `commands/katana.md`, `commands/katana-bold.md`, `katana/scripts/*`

## Inputs it needs
- A reference video (or a brief; with neither it finds a reference itself) plus the subject: photo(s) of the hero or product. Explicit `/katana` with a video and an image is enough, no text brief.
- Optional: source footage, audio, locks (wording, song, opening shot, clothing). The hero always wears the clothing from the user's photo.
- Never asks questions, fonts or credit approval; it sets its own spend cap and states it.

## Steps in order
1. Pick the task: reference remix, creative edit of supplied media, named preset (`/katana/<slug>`), or analysis only.
2. Upload media (`media_upload`, PUT, `media_confirm`); all processing in the Higgsfield sandbox only.
3. Read the reference frame by frame (`analyze_ref.py`, `energy.py map`, `viewproof.py stamp` log); write per-second notes, `analysis/breakdown.json`, motion reviews.
4. Write `analysis/task-contract.json` (locks vs freedoms) and `plan/creative-plan.json` (concept, output target, shots, text, sound, energy).
5. Route each shot: supplied footage, graphics, a still, new Seedance footage, or Genjutsu motion transfer only where a performance is required.
6. Quote every paid job (`estimate_*_cost`), set one finite cap (`ledger.py cap`), then submit through the guard. Canary first, batch the rest (up to 12).
7. Stills: one hero keyframe first, then secondary stills from it; one environment-only location plate per distinct location; judge each still before any video.
8. Seedance plates (`seedance_2_5`, `omni_reference`, audio off) with the location plate, identity reference and keyframe as images.
9. Logic check on every clip (`prodcheck.py logic`), pick in-points from real frames, assemble the EDL (camera work, grade, text overlay, real music/SFX), render.
10. Verify the whole output (energy, ranges, identity, text, audio), `deliver.py`, show with `show_result`/`show_katana_result`.

## Prompt blocks, word for word
**G1 identity sheet prompt (only when a measured identity problem needs it)**  
`katana/references/generation.md`

```
    "prompt": "Prepare only the planned identity reference views. Image 1 supplies <assigned material/style ownership> only, never its performer or outfit; image 2 supplies the identity and the exact clothing the person wears in every view. Preserve <explicit locks> without importing the portrait background."
```

**G4 reference-frame + user-character still (the keyframe)**  
`katana/references/generation.md`

```
  "prompt": "The first reference owns the composition, pose, camera angle, framing and <assigned style, texture, light and setting>. Place the person from the second reference in <the hero's position>, with the same face and identity and wearing exactly the clothing from the second reference, rendered in the first reference's style. Do not blend their face with the first reference's performer and do not use that performer's clothes. Do not copy the second reference's background. Keep the first reference's face visibility and occlusions; a hidden face stays hidden. <Planned changes to setting, props, other people and text, or: keep them unchanged.>"
```

**Location plate, photoreal look (soul_cinematic params)**  
`katana/references/stills.md`

```
{ "model": "soul_cinematic", "quality": "<from plan line: 1.5k | 2k>", "aspect_ratio": "<from plan line>", "count": 1,
  "medias": [ { "role": "image", "value": "<location evidence media_id: source frame or location photo>" } ],
  "prompt": "<environment only, no people; architecture, landmarks, materials, palette, time of day>" }
```

**Location plate, stylised look (gpt_image_2_6_flare params)**  
`katana/references/stills.md`

```
{ "model": "gpt_image_2_6_flare", "quality": "<from plan line: high>", "resolution": "<from plan line: 2k>",
  "aspect_ratio": "<from plan line>", "count": 1,
  "medias": [ { "role": "image", "value": "<accepted keyframe job_id, or the style frame media_id>" },
              { "role": "image", "value": "<location evidence media_id: source frame or location photo>" } ],
  "prompt": "<the first reference owns the art style only; the second owns the layout, landmarks and materials; environment only, no people, no text or lettering>" }
```

**G7 Seedance plate params**  
`katana/references/generation.md`

```
{
  "model": "<from plan line: seedance_2_5>",
  "mode": "<from plan line: omni_reference>",
  "duration": "<from plan line: sum of the shot slots>",
  "resolution": "<from plan line>",
  "aspect_ratio": "<from plan line>",
  "bitrate_mode": "high",
  "generate_audio": false,
  "medias": [
    { "role": "image", "value": "<composition/style frame or accepted keyframe id>" },
    { "role": "image", "value": "<identity + clothing reference id: photoreal look = the user photo media_id as supplied or a G1 character-sheet job_id, never a generated hero still; stylised look = the accepted stills.md keyframe job_id; omit this entry if unnecessary>" },
    { "role": "image", "value": "<accepted location plate job_id or media_id (a soul_cinematic or location_plate line)>" }
  ],
  "prompt": "<below>"
}
```

**G7 prompt shape (clip prompt order)**  
`katana/references/generation.md`

```
- **Prompt shape**: use the optional ownership/causal/spatial structure above, then the required shot
  slots. Leave technical specs in params; keep separately composed effects in the layer plan.
  1. **Header**: what each `@image` is, plus an exhaustive inventory of identity items to keep "in
     every shot", including every garment from the user's photo. Use HEADER-FULL for body shots and HEADER-CU for close-ups.
  2. **Prop line** (when needed): preserve the prop reference's material, colour and shape; solve keying in compositing without changing the prop.
  3. **Style and scene line**: planned set, light, camera behaviour and selected reference grammar.
  4. **`Shot n (a-bs): …`**: only the necessary shots, each with its role, framing and action. The timecodes are the slots
     above.
  5. **Closing line**: preserve explicit locks and planned details. Authored wording/graphics are
     composed later as overlays. Never exclude required final content without its documented later layer.

```

**Selfie gesture-pool plate skeleton**  
`katana/references/generation.md`

```
  - Skeleton, in this order:
    1. Capture device.
    2. The hero from the identity reference, wearing the clothing from the user's photo.
    3. Location.
    4. Light.
    5. Planned camera, framing and subject placement.
    6. Action routine.
    7. Timestamped beat list.
    8. Planned expression and cut structure; a text exclusion only when the plan composes the text as a later layer.

```

**Genjutsu motion-transfer prompt (40 words max)**  
`katana/references/genjutsu-routing.md`

```
A motion-transfer prompt can be: "Apply the source video's motion to the character in the reference image, keeping their clothing, the framing and the timing." For a fully specified preset, omit the prompt or use an empty string only when its actual contract permits it. An extra phrase is justified only to resolve a concrete ambiguity, such as which of two subjects' motion transfers. This rule does not limit the image-editing prompt or Seedance shot instructions.
```

Example plate prompts quoted in `katana/references/examples.md` carry the previous project's hero and room; per the source they are structure only.

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| New footage plates (only video model allowed) | `seedance_2_5` | `omni_reference`, 4-30 s, `generate_audio:false`, `bitrate_mode:high`, 480p/720p/1080p by delivery frame, 24 fps |
| Environment plate, photoreal | `soul_cinematic` | 1.5k or 2k, one image in, people check, 2 takes |
| Environment plate, stylised; keyframe; secondary stills | `gpt_image_2_6_flare` (or `gpt_image_2_6`; `nano_banana_2_1` fallback) | quality high, 2k |
| Identity sheet, look change, stickers | `seedream_5_5` | per plan line |
| Fictional hero selfie | `soul_2` | 2k 3:4 |
| Re-perform a specific move or camera path | `hf_mult_motion_control` | billed per driving second |
| Matte | `remove_background` / `sam_3_video` | about 1 credit |
| Chant or voice-over | `seed_audio` / `elevenlabs_v4` | per 30 characters |
| Motion preview | `seedance_2_5` with `draft:true` | 480p |
| Everything else | none (sandbox ffmpeg, code, bundled CC0 SFX) | free |

## Checks and gates
- Free analysis first: `viewproof.py status` must pass before the ledger allows any paid step; the reference is read first frame to last.
- Ledger gates: finite cap, current quote per setting, guard pass, at most three attempts per still, one corrective retry per failed video; `seedance_2_5` plate refused without a location plate line; photoreal look refuses a generated hero still as identity input; stylised keyframe must come from the style owner frame.
- Every location plate is checked for people (`faces.py detect` plus eyes); a still gets a `match`/`rewrite` verdict before any video uses it.
- Never changes a face with code (no paste, warp, swap, restore); never switches video model to dodge a refusal; never buys credits; no questions, ends with a declarative result.
- Final: `energy.py check`, `prodcheck.py ranges`, full-output review, size-capped delivery file.
- Bare `/katana` only opens the preset catalog; analysis-only requests stay analysis-only.

## Price pattern
Quotes before every paid job (no-submit `estimate_*_cost`), one cap for the run. From `_prices.md`: Seedance 2.5 480p draft 30 per 10 s, 720p 70 (7 per second), 1080p 160. Pictures 0.5 to 2.75 each, matte about 1, hero image about 0.12. A typical 10 s remix at 720p is one plate plus stills: about 75 to 150 credits (the logged 10.5 s run used 71.12). Genjutsu moves add 7 to 11 per driving second.

## Cheap swap
- Plate video `seedance_2_5` 70 per 10 s at 720p: `wan3_0` 480p 7.5 per 10 s (up to 10 image refs) saves about 90 percent, but Katana locks Seedance for new scenes, so this is a draft route outside the workflow; `gemini_omni_flash_1_2` 360p is the same 7.5.
- Seedance 1080p 160: shoot at 480p/720p and upscale locally with Real-ESRGAN (free) instead of paying for 1080p.
- Stills at 2k high (about 2.75): `seedream_5_0_flash` 2k 0.5 or `gpt_image_2_6_flare` 1k low 0.75: saves 2 to 2.25 each.
- Matte (`remove_background` 1): BiRefNet or SAM2 locally, free.
- Chant/VO (`elevenlabs_v4`): Kokoro tts locally, free.
- Motion transfer (7 to 11 per second): skip it, or drive a still with ffmpeg camera moves; RIFE interpolation locally for smoother frames, free.
- Reference analysis, planning, EDL, text, grade, QA: already free (sandbox, Claude on the plan).
