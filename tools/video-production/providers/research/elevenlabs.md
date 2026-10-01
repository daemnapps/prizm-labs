# ElevenLabs: three doors compared (direct API / fal.ai / Higgsfield)

## 1. Direct — ElevenLabs API

**Custom voice**
- Instant clone: `POST /v1/voices/add` — required: `name`, `files` (list of audio files); optional: `remove_background_noise`, `description`, `labels`. Returns `voice_id`, `requires_verification`. ([Create IVC voice](https://elevenlabs.io/docs/api-reference/voices/ivc/create))
- Professional clone (PVC): needs 30 min minimum audio (2–3 hrs optimal), single speaker, MP3 192kbps+; trains 3–6 hrs (up to 24). Slots by plan: Free/Starter 0, Creator/Pro/legacy Scale 1, Scale/legacy Business 3, Business 10, Enterprise custom. ([Professional Voice Cloning](https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning))
- Voice Design (text→voice): `POST /v1/text-to-voice/design` — `voice_description` (required), `model_id` (`eleven_multilingual_ttv_v2` or `eleven_ttv_v3`), `text`./`auto_generate_text`, `loudness`, `seed`, `guidance_scale`, `reference_audio_base64` (v3 only), `prompt_strength`, `output_format`. Returns `previews[]` with `generated_voice_id`. mp3_192 needs Creator+; PCM 44.1kHz needs Pro+. ([Design](https://elevenlabs.io/docs/api-reference/text-to-voice/design))

**The line, full control**
- `POST /v1/text-to-speech/{voice_id}` and `.../with-timestamps` — body: `text`, `model_id` (default `eleven_multilingual_v2`; also `eleven_v3`, `eleven_turbo_v2_5`, `eleven_flash_v2_5` — full list via `GET /v1/models`), `voice_settings{stability, similarity_boost, style, use_speaker_boost, speed}`.
  - `stability` 0–1 (default 0.5), `similarity_boost` 0–1 (default 0.75), `style` v2+/v3 only, `use_speaker_boost` default true **but not available on eleven_v3**, `speed` 0.25–4.0 (default 1.0). ([voice-settings.md](https://github.com/elevenlabs/skills/blob/main/text-to-speech/references/voice-settings.md))
  - Timestamps response: `{"audio_base64", "alignment": {"characters", "character_start_times_seconds", "character_end_times_seconds"}, "normalized_alignment": {...same...}}`. ([Create speech with timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps))
  - Audio tags (`[laughs]`, `[whispers]`, `[sighs]`, `[curious]` etc.) work **only on eleven_v3**. ([Audio tags](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-do-audio-tags-work-with-eleven-v3-alpha))
  - Output formats: all tiers get `mp3_44100_32/64/96`, `opus_48000_*`, `alaw/ulaw_8000`; `mp3_44100_192` needs Creator+; `pcm_*`./`wav_*` at 44.1/48kHz need Pro+. ([Convert](https://elevenlabs.io/docs/api-reference/text-to-speech/convert))

**Multi-speaker dialogue**: `POST /v1/text-to-dialogue` — `inputs[]{text, voice_id}` (max 10 unique voices, ~2000 chars total), `model_id` (default `eleven_v3`), `settings{stability}`, `pronunciation_dictionary_locators[]`, `seed`. ([Text-to-dialogue](https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert))

**Speech-to-speech (recast a take)**: `POST /v1/speech-to-speech/{voice_id}` — `audio` file + `voice_id`, optional `model_id`, `voice_settings`, `remove_background_noise`, `output_format`, `seed`. ([Speech-to-speech](https://elevenlabs.io/docs/api-reference/speech-to-speech/convert))

**Sharing the asset out**: any `voice_id` (cloned, designed, or professional) is usable across every endpoint, and the raw audio/`voice_id` can be handed to any other tool. **Nothing here is locked to ElevenLabs' own front end.**

**Cost/limits**: TTS overage ≈$0.10/1,000 chars (multilingual), $0.05/1,000 (Flash/Turbo) — Creator ($22/mo) includes 220,000 chars. Concurrency (Speech Engine API): 4 calls (Starter) up to 40 (Business). ([Pricing](https://elevenlabs.io/pricing/api))

## 2. fal.ai — `fal-ai/elevenlabs/*`

Confirmed endpoints: `tts/eleven-v3`, `tts/turbo-v2.5`, `tts/multilingual-v2`, `text-to-dialogue/eleven-v3`, `voice-changer`, `dubbing`, `speech-to-text` / `speech-to-text/scribe-v2`, `music`, `forced-alignment` (11 total per fal's own count). ([Explore ElevenLabs on fal](https://fal.ai/explore/elevenlabs), [fal.ai/elevenlabs](https://fal.ai/elevenlabs))

- **No clone or Voice Design endpoint exists on fal for ElevenLabs** — only Qwen3-TTS and MiniMax have fal-hosted "voice-design"/"clone-voice" slugs; ElevenLabs' own clone/design API is not mirrored. ([fal search](https://fal.ai/models/fal-ai/qwen-3-tts/voice-design/1.7b))
- **No BYO voice_id passthrough**: both `tts/eleven-v3` and `voice-changer` take a `voice` field (default `"Rachel"`), i.e. picking from fal's bundled preset-voice list, not a caller-owned ElevenLabs `voice_id`. There is no API-key-passthrough mechanism documented. ([tts/eleven-v3 API](https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3/api), [voice-changer API](https://fal.ai/models/fal-ai/elevenlabs/voice-changer/api))
- `voice_settings` exposed on `tts/eleven-v3`: just `stability` and a `timestamps` boolean flag — no `similarity_boost`./`style`./`speaker_boost`./`speed`, no audio-tag documentation, no pronunciation dictionaries.
- Timestamps: `timestamps: true` returns a `timestamps` list (word-level), not the full character-level `alignment`./`normalized_alignment` object direct gives.
- Pricing: TTS $0.10/1k chars (v3/multilingual), $0.05/1k (turbo); voice-changer $0.30/min; dubbing $0.90/min; scribe-v2 $0.008/min.
- **What's lost vs. direct**: your own cloned/designed voice, full `voice_settings`, audio tags reliability, dictionaries, character-level timestamps, dialogue voice limits control.

## 3. Higgsfield

- `text2speech_v2`: `--prompt`, `--variant` (`elevenlabs`, `minimax`, `seed_speech`, `vibe_voice`, `cozy_voice`), `--voice_id`, `--voice_type` (`preset`|`element`) — ElevenLabs is one selectable **engine**, and `element` means a voice registered inside Higgsfield's own voice library (not an imported ElevenLabs `voice_id` — no import mechanism is documented). Char cap for the elevenlabs/vibe_voice/cozy_voice variants: 5,000. ([higgsfield-ai/cli MODELS.md](https://github.com/higgsfield-ai/cli/blob/main/MODELS.md))
- `voice_change`: `--video`, `--voice_type` (`preset`|`element`), `--voice_id` — swaps the speaker on an existing video without touching visuals. ([CLI](https://github.com/higgsfield-ai/cli))
- `seed_audio` (Seed Audio 1.0): optional `--voice_id`./`--voice_type`, must be provided together; "a voice allows at most 2 additional audio references"; a voice can't combine with an image reference.
- Video models take audio as a reference, not a `role: audio` field: `cinematic_studio_3_0` → `--audio-references`./`--audio` (repeated), `seedance_2_0` → same (0–3), `wan2_7` → single. Workflow per Higgsfield's own blog: generate in Seed Audio first, then attach as a reference into Cinema Studio / Seedance 2.0 / Kling 3.0. ([Higgsfield Audio blog](https://higgsfield.ai/blog/higgsfield-audio))
- Voice cloning UI: record/upload up to 2 min, "Clone Voice," saved to account voice library, reusable across tools. ([Higgsfield voice cloning](https://higgsfield.ai/voice-cloning), [X thread](https://x.com/higgsfield/status/2028918606709572088))
- **`voice_clone_limit_reached`, exact per-account element caps, and any ElevenLabs-voice-import path are not documented anywhere in Higgsfield's public docs, CLI repo, or `openapi.json`** (their own docs note the OpenAPI file is not the authoritative catalog) — this is an undocumented account ceiling you're hitting in practice, not a published limit. ([docs.higgsfield.ai](https://docs.higgsfield.ai/docs))

## Verdict table

| Capability | Direct | fal.ai | Higgsfield |
|---|---|---|---|
| Custom voice (clone/design) | Full — IVC, PVC, Voice Design | None | Own clone only, in-house, no ElevenLabs import |
| Full `voice_settings` control | Full (stability/similarity/style/boost/speed) | `stability` only | Not exposed |
| Audio tags ([laughs] etc.) | v3 only, documented | Undocumented | Undocumented |
| Timestamps | Character-level `alignment` | Word-level only | Not exposed |
| Multi-speaker dialogue | Full, up to 10 voices | Single dialogue endpoint, limited | Not exposed |
| Speech-to-speech | Full | Voice-changer, presets only | `voice_change`, in-house voices only |
| BYO voice_id elsewhere | Yes — portable everywhere | No passthrough | No import |

## Ruling
1. All custom voices — instant clone, professional clone, Voice Design — get made **only through the direct ElevenLabs API**; neither fal nor Higgsfield can create or import one.
2. The actual line — with `voice_settings`, audio tags, dictionaries, character-level timestamps — gets **generated only through the direct API** too; fal strips settings down to `stability`, Higgsfield exposes none.
3. The finished audio (a file, or a `voice_id` reference) then gets **handed to Higgsfield/fal as a plain reference file** — `--audio-references` on Higgsfield's video models, or as an uploaded asset for fal video pipelines — never regenerated inside either.
4. If we tried to do voices "on fal": we'd lose our own cloned voice, most `voice_settings`, dialogue control, and precise timestamps — we'd be stuck on fal's bundled presets.
5. If we tried "on Higgsfield" only: same loss, plus we'd be capped by an undocumented voice-element ceiling with no way to bring in an ElevenLabs voice we already built.
