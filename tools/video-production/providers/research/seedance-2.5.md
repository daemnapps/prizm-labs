# Seedance 2.5 — three doors compared (MOTION + TALKING BEAT)

Researched 2026-09-17, web only. Confidence flagged per source: **official** (BytePlus/fal/Higgsfield own domains) vs **third-party** (aggregator/community docs, used only where official docs were silent).

## 1. Direct — BytePlus ModelArk (Volcengine Ark, same API)

Official: [Create a video generation task](https://docs.byteplus.com/en/docs/ModelArk/1520757), [Region availability](https://docs.byteplus.com/en/docs/ModelArk/2191806), [Pricing](https://docs.byteplus.com/en/docs/ModelArk/1544106), [Seedance 2.5 prompt guide](https://docs.byteplus.com/en/docs/ModelArk/2607689), model id per [aiseedance25.app](https://aiseedance25.app/seedance-2-5-api) (third-party, unverified against an official model-id page): `dreamina-seedance-2-5-260628`.

- **Access**: Two regions only — AP (`ap-southeast-1`, `https://ark.ap-southeast.bytepluses.com/api/v3`) and EU (`eu-west-1`, `https://ark.eu-west.bytepluses.com/api/v3`, but EU currently only serves `seed-2-0-lite`). No China-residency requirement documented; BytePlus is ByteDance's international arm — open to a non-China business via normal signup, endpoints are region-scoped and can't be called cross-region.
- **Endpoint**: `POST /contents/generations/tasks`, `content` array of typed parts, each with a `role`.
- **Image-to-video, first + last frame**: image parts with `role: "first_frame"` / `"last_frame"`.
- **Audio input (our need)**: audio part, `type: "audio_url"`, `role: "reference_audio"`, formats **wav/mp3**, <15MB each, up to **10 clips / 30s total** (2.5) or 3 clips/15s (2.0). Seedance 2.5 uniquely accepts **audio-only** input (2.0 requires an image/video too). This is the multimodal "omni reference" path, not a separate lip-sync flag.
- **Lip-sync behavior**: not spelled out as a toggle. The prompt guide's dubbing example shows the **video-edit** subtask translating spoken dialogue and instructing the model to "precisely adjust the lip movements to match the translated speech" — i.e. lip-sync-to-provided-audio is real and demonstrated, but documented as an edit-task pattern, not a guaranteed default for image+audio→video.
- **`generate_audio`** (bool, default true): synthesizes audio; **false = silent**. Mono output only.
- **Duration**: 2.5 → `[4,30]` or `-1`; 2.0 → `[4,15]` or `-1` (default 5).
- **Resolution**: 480p/720p/1080p (2.5); 2.0 adds 4K.
- **Aspect ratio (`ratio`)**: 16:9, 4:3, 1:1, 3:4, 9:16, 21:9, adaptive.
- **Other params**: `seed` `[-1, 2147483647]`, `camera_fixed` (bool, default false), `watermark` (bool, default **false**), `output_format`: mp4/mov (2.5 only), `return_last_frame` (PNG, for chaining), `omni_reference_task_type`: auto/reference/edit/extend.
- **Price** (token-based, formula = (in+out duration)×W×H×fps/1024): 2.5 ≈ $0.103/s @480p, $0.231/s @720p, $0.569/s @1080p (1080p at −28% through 2026-09-17). 2.0 ≈ $0.07/$0.15/$0.37/$0.78 per sec at 480p/720p/1080p/4K.
- **Rate limits / concurrency**: not published in any fetched doc — would need console/account page.

## 2. fal.ai

Official model pages fetched today: [seedance-2.5/image-to-video](https://fal.ai/models/bytedance/seedance-2.5/image-to-video/api), [seedance-2.5/reference-to-video](https://fal.ai/models/bytedance/seedance-2.5/reference-to-video), [seedance-2.5/text-to-video](https://fal.ai/models/bytedance/seedance-2.5/text-to-video), plus legacy [v1 pro](https://fal.ai/models/fal-ai/bytedance/seedance/v1/pro/image-to-video/api) and [v1.5 pro](https://fal.ai/models/fal-ai/bytedance/seedance/v1.5/pro/image-to-video/api). Also live: 2.0 family (`bytedance/seedance-2.0/*`, incl. `/us/` variants).

- **`bytedance/seedance-2.5/image-to-video`**: `image_url` (start frame, required), `end_image_url`, `resolution` (480p/720p/1080p), `duration` 4–30 or auto, `aspect_ratio` (currently "auto" only on this endpoint), `generate_audio`, `bitrate_mode`. **No audio input field** — this endpoint cannot take our voice line.
- **`bytedance/seedance-2.5/reference-to-video`** — the door that matters: `image_urls[]`, `video_urls[]`, **`audio_urls[]`** ("audio references for rhythm, timing, and voice"), `resolution` (480p/720p only here), `duration`, `aspect_ratio`, `generate_audio`, `seed`. Docs describe audio as living "in the same latent space" as video, generated jointly — sold as a **timing signal**, not confirmed as verbatim dubbing/lip-sync of the exact input line. Up to 50 references total.
- **v1/v1.5 pro image-to-video**: `image_url`, `end_image_url`, `duration`, `resolution`, `aspect_ratio`, `seed`, `camera_fixed`; **no audio field at all**, no `generate_audio`. Older, silent-only.
- **Price**: v1 pro 1080p/5s ≈ $0.62 ($2.50/M tokens). Seedance 2.5 base ≈ $0.0214/1K tokens at 480/720p (~$0.47/s images-only, ~$0.28/s with a video reference, per fal's own worked numbers).
- **Gap vs direct**: no first+last-frame *and* audio-reference combo in one call; audio support only on the multi-reference endpoint, not the plain image-to-video one; no explicit "this reproduces your track verbatim" claim anywhere in fal's copy.

## 3. Higgsfield

Official: [docs.higgsfield.ai](https://docs.higgsfield.ai/docs) (general API — auth, polling, billing; **no Seedance-specific param page indexed**), [console.higgsfield.ai/explore](https://console.higgsfield.ai/explore) (model catalog, thin on params publicly), [higgsfield.ai/seedance/2.5](https://higgsfield.ai/seedance/2.5), [creator-hub help](https://higgsfield.ai/creator-hub/help-center/ai-models/how-do-i-use-seedance). Field-level detail below is **third-party** (community skill repo [OSideMedia/higgsfield-ai-prompt-skill](https://github.com/OSideMedia/higgsfield-ai-prompt-skill)) — treat as unverified until cross-checked against an actual account/API key.

- **Modes**: `t2v`, `omni_reference`, `video_edit`, `video_extension` (extension needs `extension_mode`: forward/backward).
- **Medias**: reportedly **no `start_image`./`end_image` roles on 2.5** — first/last frame is done by prompt language (`@Image1 is the first frame`), only `image_references`, `video_references`, `audio_references` exist as media roles. This is a real regression vs the direct API's explicit `first_frame`./`last_frame` roles — confirm before building on it.
- **The audio_references trap**: community docs describe `audio_references` as carrying "voice, dialogue, ambience, or music" character/style, with dialogue text instead entered via a separate `{}` bracket syntax in the prompt — i.e. **the audio you attach may be read as a style/character reference, not literally played back and lip-synced**. Higgsfield's own marketing copy says Seedance "generates... lip-synced speech" and dialogue "in double quotes... generates both the lip movement and voice for it" — that's model-generated speech from text, which is a different mechanism than dubbing a pre-made ElevenLabs line.
- **Duration/resolution**: 4–30s (default 5s, ignored in video_edit); 480p/720p only on Higgsfield (no 1080p/4K natively — upscale add-on).
- **Pricing (credits)**: 8s @720p ≈ 52 credits, @480p ≈ 24 credits (higgsfield.ai blog); no official std-vs-fast split or concurrency cap found in official docs.

## Verdict

| Capability | Direct (BytePlus/Ark) | fal.ai | Higgsfield |
|---|---|---|---|
| 2.5 available via API today | Yes, AP+EU | Yes | Yes |
| Open to non-China business | Yes (BytePlus intl) | Yes | Yes |
| First frame + last frame | Yes (`first_frame`./`last_frame` roles) | Yes (`image_url`+`end_image_url`) | No explicit roles — prompt-only (unverified) |
| Accepts our audio for lip-sync | Yes, `reference_audio` role; edit-task dubbing example shown | Only on `reference-to-video` (`audio_urls`), sold as timing signal not confirmed verbatim | Uncertain — `audio_references` may be style-only, not dubbing |
| Silent motion (image→video) | Yes (`generate_audio:false`) | Yes | Yes |
| Duration | 4–30s | 4–30s (varies by endpoint) | 4–30s |
| Max resolution | 1080p (2.5) | 1080p (image-to-video endpoint) | 720p native |

## Ruling
1. Only the **direct BytePlus/Ark API** has a documented case of feeding real audio into a lip-sync result (the dialogue-translation edit example) — treat it as the primary door for the TALKING BEAT until proven otherwise on real footage.
2. fal's plain image-to-video endpoint **cannot** do the talking beat at all (no audio field); only `reference-to-video` takes audio, and fal never confirms it dubs your exact line rather than reinterpreting it — test before trusting.
3. Higgsfield's `omni_reference` audio path is the least documented and carries a real risk of being a style/character reference rather than a lip-sync driver — the user's own suspicion (the "audio_references trap") is corroborated, not resolved, by public docs; needs a direct account test.
4. All three doors do silent MOTION fine — direct and fal both expose explicit first+last-frame roles; Higgsfield reportedly dropped that role in favor of prompt language, worth confirming with a live key before relying on it.
5. Recommended split: **direct API primary for TALKING BEAT** (once account/region access is set up), **fal.ai primary for silent MOTION** (cleanest first/last-frame params, no need for BytePlus account setup), Higgsfield kept as a fallback pending someone actually testing `audio_references` against a real voice line.
