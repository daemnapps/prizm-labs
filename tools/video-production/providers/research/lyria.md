# Lyria research, one level deeper (web only, 2026-09-17)

## 1. Gemini API (direct)

Two APIs both cover Lyria; **`generateContent` is the recommended production path**, Interactions is beta:
> "The Interactions API is currently in Beta. For stable production deployments, the generateContent API is recommended." — [interactions/music-generation](https://ai.google.dev/gemini-api/docs/interactions/music-generation)

**Request shape**
- `generateContent`: `"contents":[{"parts":[{"text":"..."}]}]`, images via `inline_data:{mime_type, data}`, output format via `"generationConfig":{"responseFormat":{"audio":{"mimeType":"audio/wav"}}}`. — [music-generation](https://ai.google.dev/gemini-api/docs/music-generation), [generate-content/music-generation](https://ai.google.dev/gemini-api/docs/generate-content/music-generation)
- Interactions: `client.interactions.create(model=..., input=..., response_format=...)`. `input` can be a list mixing `{"type":"text","text":...}` and `{"type":"image","mime_type":...,"data":...}`.
- **Structure/timing tags** (both APIs, same prompt syntax): section tags `[Verse]`, `[Chorus]`, `[Bridge]`; timestamp ranges like `[0:00 - 0:10] Intro: ...`. `instrumental` is not a discrete field — it's prompted in text ("Instrumental only, no vocals").
- Lyria 3 Clip is fixed 30s; Lyria 3 Pro / 3.5 default output is MP3, **WAV is selectable for Pro** via `response_format`.

**Response shape**
- `output_audio` (base64/binary audio, MP3 or WAV) and `output_text`. `steps[].content[]` holds ordered blocks tagged `type: audio|text`.
- Docs explicitly warn ordering isn't fixed: **"You should not assume the lyrics are always the first part."** — [music-generation](https://ai.google.dev/gemini-api/docs/music-generation)
- **On the timed-lyric-sheet question — not confirmed as a documented feature.** The docs describe `output_text`/the text content block only as *"the generated lyrics or a JSON description of the song structure"* — never as containing per-line timestamps. Nothing in either music-generation page or the `lyria-3-pro-preview` model page documents a `[0.0:5.3] lyric line` format. **Treat the timed sheet you saw on 3 Sep as an observed behaviour to verify per run, not a guaranteed output.**

**Duration / languages / safety / pricing**
- Lyria 3 Clip: fixed 30s. Lyria 3 Pro / 3.5: "a couple of minutes," up to **3 minutes**, steerable by prompt + timestamp tags.
- Lyria 3.5 "generates lyrics in the language of your prompt" and adapts vocal style/pronunciation to it.
- Safety: **"All prompts are checked by safety filters. Prompts that trigger the filters will be blocked. This includes prompts that request specific artist voices or the generation of copyrighted lyrics."** All output carries a SynthID audio watermark.
- Pricing (per generation, not token-based): **Lyria 3 Clip Preview $0.04/song, Lyria 3 Pro Preview $0.08/song, Lyria 3.5 $0.08/request** (no free tier). — [OpenRouter Lyria 3 Pro](https://openrouter.ai/google/lyria-3-pro-preview), [OpenRouter Lyria 3 Clip](https://openrouter.ai/google/lyria-3-clip-preview)
- Rate limits: not published on the model/guide pages I could reach; only generic tier-based Gemini API rate-limit docs exist, with no Lyria-specific numbers surfaced.
- `lyria-3-pro-preview` model card: input types Text+Image, output Audio (MP3) + Text (Lyrics), 131,072 input-token limit; **Lyria 3.5 is positioned as the preview's replacement**, no other new claims documented on that page. — [lyria-3-pro-preview](https://ai.google.dev/gemini-api/docs/models/lyria-3-pro-preview)

**Vertex AI** adds `negative_prompt` and `seed` (GA) on the underlying `lyria-002` music-generation model — `seed` gives deterministic regen but **cannot be combined with `sample_count`** in the same request. This is on the base Lyria model reference, not confirmed to extend to Lyria 3/3.5 on Vertex. — [Vertex Lyria model reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/lyria-music-generation), [prompt guide](https://cloud.google.com/vertex-ai/generative-ai/docs/music/music-gen-prompt-guide)

## 2. fal.ai

Both `fal-ai/lyria3/pro` and `fal-ai/lyria3` share the **same minimal schema** (confirmed via the live OpenAPI spec, `fal.ai/api/openapi/queue/openapi.json?endpoint_id=...`):

```json
// Input (Lyria3ProInput / Lyria3Input — identical shape)
{
  "prompt": "string, required, 1-5000 chars — genre/mood/instrumentation/tempo/vocal style; supports vocals, lyrics, multi-language",
  "negative_prompt": "string, default '', DEPRECATED — 'Negative prompting is not supported by Lyria 3.'",
  "image_url": "string|null, optional — mood/theme inspiration"
}
// Output
{
  "audio": { "url": "string", "content_type": "string|null", "file_name": "string|null", "file_size": "integer|null" },
  "lyrics": "string|null — generated or provided lyrics, if applicable"
}
```
- **No `lyrics`, `instrumental`, `seed`, or `duration` input fields exist on either fal endpoint.** You steer vocals/lyrics/instrumental purely through the free-text `prompt`. `negative_prompt` is present only as a deprecated no-op.
- `lyrics` output is confirmed **plain text, no timestamps** — matches the original finding.
- Price: **$0.08 per audio on `/pro`** (page-quoted: "Your request will cost $0.08 per audio"). The plain `/lyria3` endpoint's price wasn't separately surfaced but shares the schema; treat as effectively the same tier unless fal's pricing page says otherwise.
- No queue-limit specifics were published on the model pages beyond fal's general async-queue behavior.

## 3. Alignment options for a timing sheet

| Option | Timestamps | Sung-vocal reliability | Price |
|---|---|---|---|
| **ElevenLabs Scribe** (direct `elevenlabs.io`, or fal `fal-ai/elevenlabs/speech-to-text`) | **Word-level**, confirmed in schema: output `words` = "Word-level transcription details" with timestamps | Benchmarks show Scribe **beats Whisper on non-studio audio** (background music, reverb, overlapping vocals) and on non-English languages (e.g. Indonesian WER ~2.4% vs Whisper's 7.7%); on clean studio English both are strong, edge still to Scribe | Direct: **$0.22/hr** (Scribe) or $0.39/hr (Scribe realtime). Via fal: **~$0.03/min** (~$1.80/hr) |
| **Whisper / fal `fal-ai/wizper`** | **Chunk-level only** (schema returns `chunks` with start/end, not per-word) — weaker fit for a per-line lyric sheet | Handles clean studio vocals well; degrades vs Scribe on noisy/heavily-produced mixes typical of a full song mix | fal: **~$0.03–0.05/1000 audio-seconds ≈ $0.50/1000 min** — far cheaper than Scribe, but coarser timing |
| **Gemini audio understanding** (`generationConfig.audioTimestamp`) | MM:SS granularity via `audio_timestamp` config flag — coarser than word-level, and a tracked bug exists against the public endpoint for this exact param | Not benchmarked against sung vocals specifically in docs | Standard Gemini token pricing, not per-minute |

**For sung vocals specifically, ElevenLabs Scribe is the most reliable of the three** — it's the only one with documented word-level timestamps plus benchmark evidence of holding up under music/reverb, which is exactly the condition a mixed song track presents. Wizper's chunk-level timestamps are too coarse to safely rebuild a per-line cut sheet without manual adjustment.

## Verdict table

| Capability | Gemini API (direct) | fal.ai |
|---|---|---|
| Sings our written lyrics | Yes, via prompt + `[Verse]`./`[Chorus]`/timestamp tags | Yes, via free-text prompt only (no structured lyric field) |
| Duration 30–180s | Clip=30s fixed; Pro/3.5 up to ~3min, prompt-steered | Not documented; likely same underlying model limits, unconfirmed on fal |
| Explicit mix direction | Prompt text only, no structured mix params | Prompt text only |
| Per-line timed lyric sheet | **Not documented** — `output_text` described only as lyrics/structure JSON, ordering not guaranteed | **Confirmed absent** — `lyrics` output is plain text, no times |
| Negative prompt / seed | Not on Gemini API pages; **Vertex AI's base Lyria model** has both (GA) | Present but deprecated/no-op |
| Image-guided mood | Yes (`image_url`/inline image part) | Yes (`image_url`) |
| Price per song | $0.04 (Clip) / $0.08 (Pro, 3.5) | $0.08 (`/pro`) |

## Plain ruling

1. **Primary door for the song stays the Gemini API** (`generateContent`, not Interactions — that's still beta) — it's the only door with structural prompt tags (`[Verse]`, timestamp ranges) and WAV output for Pro.
2. **The timed lyric sheet is NOT a documented feature of `output_text`** — nothing in the music-generation guide, the Interactions guide, or the `lyria-3-pro-preview` model page describes per-line timestamps in the text output. Our 3 Sep result was real but is an **observed behaviour, not a guaranteed contract** — verify it lands on every run, don't build a pipeline that assumes it.
3. **fal's `/lyria3/pro` is strictly worse for our use** — same $0.08 price, but the `lyrics` output is confirmed plain text with zero timing, and there's no way to feed structured lyrics in.
4. **When Gemini's text output doesn't carry usable timestamps, run the audio through ElevenLabs Scribe** (fal `fal-ai/elevenlabs/speech-to-text` is the cheap, easy door at ~$0.03/min; direct API at $0.22/hr if volume favors it) — it's the only alignment option with documented word-level timestamps and the best track record on music-laden, non-studio audio like a finished ad mix.
5. **Don't reach for Whisper/Wizper for this** — its timestamps are chunk-level, not word-level, so it can't reliably drive a per-line video cut without hand-adjustment; keep it as a cheap fallback only, not the alignment tool of record.

## Sources
- https://ai.google.dev/gemini-api/docs/music-generation
- https://ai.google.dev/gemini-api/docs/interactions/music-generation
- https://ai.google.dev/gemini-api/docs/generate-content/music-generation
- https://ai.google.dev/gemini-api/docs/models/lyria-3-pro-preview
- https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/lyria-music-generation
- https://cloud.google.com/vertex-ai/generative-ai/docs/music/music-gen-prompt-guide
- https://openrouter.ai/google/lyria-3-pro-preview
- https://openrouter.ai/google/lyria-3-clip-preview
- https://fal.ai/models/fal-ai/lyria3/pro
- https://fal.ai/models/fal-ai/lyria3/pro/api
- https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/lyria3/pro
- https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/lyria3
- https://elevenlabs.io/docs/overview/capabilities/speech-to-text
- https://elevenlabs.io/pricing/api
- https://fal.ai/models/fal-ai/elevenlabs/speech-to-text
- https://fal.ai/models/fal-ai/elevenlabs/speech-to-text/api
- https://fal.ai/models/fal-ai/wizper
- https://fal.ai/models/fal-ai/wizper/api
- https://ai.google.dev/gemini-api/docs/audio
