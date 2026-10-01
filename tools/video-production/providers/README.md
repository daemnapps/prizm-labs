# Providers — the doors (current: 2026-09-18)

**Every station is a direct door since 2026-09-18.** The ruling per model
and door, with the evidence: `MODEL-HOUSE.md`; the dossiers: `research/`.

| Station | Door | Code |
|---|---|---|
| voice | ElevenLabs, direct | `machine/voice.py` |
| cast · still | OpenAI, direct — GPT Image 2.5 sunburst | `machine/direct_openai.py` |
| edit | Google, direct — Nano Banana Pro | `machine/direct_google.py` |
| song | Google, direct — Lyria 3 | `machine/direct_google.py` |
| talking | fal Omni + ElevenLabs speech-to-speech (controlled recipe) | `machine/omni.py` |
| motion | fal Omni, sound stripped | `machine/omni.py` |
| — wired, blocked | Seedance 2.5 on BytePlus, direct (US billing) | `machine/direct_byteplus.py` |

The table below is the older picture — **one model per station, per
house** — kept because `--provider` can still force a run into a house.
`higgsfield.md` (house rules) and `EDITOR-SHEET.md` moved to `../archive/`.

---

# Providers — the house rules per generation house

One file per provider the video machine can run on. Each holds what was
learned at that house — the exact call shapes, the parameter traps, the
misfires and the rule each one bought. **A note learned on one format
applies to every format on that provider**, which is why these live here
and not under a format.

| Provider | File | Switch |
|---|---|---|
| fal — API, key in the environment | [`fal.md`](fal.md) | `--provider fal` (detected when Claude Code has a fal key; never asks) |
| Higgsfield — through the MCP connector, or by hand in the web app | `higgsfield.md` (team-only, not in this repo) | `--provider higgsfield-mcp` / `higgsfield-ui` (shows the models, asks once) |

The switch itself, the model each station gets on each provider, the
rates and each model's ceilings: `../machine/providers.json`, read by
`../machine/platform.py` and `../machine/preflight.py`. A new provider is
a block in that file and a page here.

Both files were written from the song ad's runs (2026-09-03 on fal,
2026-09-04 on Higgsfield) and still carry that piece as their worked
example — the calls are the provider's; the piece is illustrative.

## The seven stations (2026-09-17; talking recipe updated with the course write-up)

**One primary model per station per provider, at most one named fallback,
and never a bare model name — a station.** Damon: "we have many providers
and many models — streamline the models used so any tool, fal or
Higgsfield, can do what's necessary." Full rulings, ceilings and evidence
per pick: `../machine/providers.json`'s `_house` key and each model's
`why`./`ceilings`. The principle layer behind every pick in that file is
`GENERATION-METHOD.md` (the reference carries the material;
generate what must be photographic, composite what must be exact; never
name the camera; judge by measurement, not taste). The course write-up
(Damon, 09-14) corroborates the ruling and confirms the same model split:
realism of a person → GPT Image; edits → Nano Banana Pro.

**Hand column added 2026-09-17** (Damon's "we scale tomorrow" ruling — the
two hands, full detail in `../formats/RUN-PROTOCOL.md`). The one page an
editor reads before touching Higgsfield: [`EDITOR-SHEET.md`](EDITOR-SHEET.md).

| Station | Hand | What this station does | fal | Higgsfield (both doors) |
|---|---|---|---|---|
| cast | machine, direct | the character, once, from a reference photo | `fal-ai/gpt-image-2` *(candidate — slug unconfirmed, no run yet)* | `gpt_image_2` |
| still | machine, direct | every frame, seeded from the cast sheet | `fal-ai/gpt-image-2` *(candidate; fallback `fal-ai/bytedance/seedream/v4/edit`)* | `gpt_image_2` *(fallback `nano_banana_2`, on an NSFW/IP misfire)* |
| edit | machine, direct | one discrete change to an approved frame | `fal-ai/nano-banana-pro/edit` | `nano_banana_pro` |
| motion | editor, Higgsfield | animate an approved still into a moving clip | `fal-ai/bytedance/seedance/v2.5/pro/image-to-video` | `seedance_2_5` |
| talking | editor, Higgsfield | motion where the person speaks the line | `fal-ai/bytedance/seedance/v2.5/pro/image-to-video` *(candidate — same recipe below, unconfirmed on fal's endpoint)* | `seedance_2_5` *(fallback `cinematic_studio_3_0`, if sync drifts)* |
| voice | machine, direct | the spoken line as audio, made first with ElevenLabs | `elevenlabs`, direct API — custom voice per character, generated before any picture *(alternates `fal-ai/elevenlabs/tts/multilingual-v2`, `fal-ai/elevenlabs/tts/eleven-v3`, `fal-ai/elevenlabs/voice-changer` — library voices only)* | `elevenlabs`, direct API, same recipe *(alternate `voice_change`, for re-voicing an existing clip)* |
| audio | machine, direct | the song, for sung formats — otherwise the editor's | `fal-ai/lyria3/pro` *(alternates `lyria` — Gemini direct, returns timings natively — and `fal-ai/minimax-music/v2.6`; fallback `fal-ai/stable-audio`, effects only)* | `fal-ai/lyria3/pro`, same call *(same alternates)* |

**The talking recipe** (proven 16 Sep on Higgsfield, Damon's 2026-09-17
ruling; `mode` confirmed by the course write-up, Damon 09-14, §6):

1. the approved still, uploaded, as media role `start_image`
2. the ElevenLabs line, uploaded, as media role `audio`
3. `mode: omni_reference`

**The voice recipe** (Damon's 2026-09-17 ruling — the same on every provider,
because ElevenLabs is called directly on neither):

1. one custom ElevenLabs voice per character, bound in
   `brands/<brand>/ai-cast/<name>/voice.json` (`voice_id`)
2. every line is generated FIRST, from here, direct on the ElevenLabs
   account — before any picture
3. piped into the provider: uploaded to Higgsfield as the media a talking
   beat lip-syncs to (role `audio`), or attached on fal as the item's own
   `audio` media
4. fal's own ElevenLabs endpoints see library voices only and cannot reach
   an account-private voice id — no key passthrough, no clone/design
   endpoint — so the call is always direct, never through a provider
   wrapper

**The song recipe** (Damon's 2026-09-17 ruling):

1. `fal-ai/lyria3/pro` makes the song — up to 3 minutes, sings written
   lyrics, ~$0.08
2. `fal-ai/elevenlabs/speech-to-text` runs on the finished song for word
   timestamps — the timing sheet the cut is built to, since fal's Lyria
   returns none
3. the song is uploaded to whichever provider is generating the picture,
   as the audio the sung clips carry

**Superseded, stated honestly.** THE-CINEMA-LINE.md's 2026-09-12 ruling —
"never marry audio to video," `cinematic_studio_3_0` as the whole
architecture for a talking beat — is superseded on the talking beat only.
The 16 Sep run proved the recipe above on Higgsfield, with the locked-voice
rule holding. `cinematic_studio_3_0` is now the talking FALLBACK if sync
drifts, not the primary route. Everything else THE-CINEMA-LINE.md rules —
element injection, the receipts — still stands. This table's own cast/still
row is superseded too: `soul_2` and Seedream-for-identity (ruled
2026-08-31) gave way to GPT Image from reference on Damon's 2026-09-17
ruling; `soul_2` is now retired in `machine/providers.json`.

**Audition, not yet in a station cell.** The course write-up (Damon, 09-14)
proposes a routing rule — talking beats to Omni, silent shots to Grok. Both
`gemini_omni_flash_1_1` and `grok_video_v15` carry `status: audition` in
`machine/providers.json` on that strength alone; neither has a run against
`seedance_2_5` on the same still. Seedance stands as the motion/talking
primary until one of them beats it on a measured comparison.

**Gaps, named rather than hidden:** fal's cast/still slug
(`fal-ai/gpt-image-2`) is a candidate — no fal OpenAI-image
endpoint has ever been named or run in this repo; confirm on first run.
fal's talking recipe is the same shape proven on Higgsfield but unconfirmed
on fal's own seedance image-to-video endpoint. The audio slot
(`fal-ai/lyria3/pro`, on every provider) is a candidate, not a proven pick,
until a run files a ledger row naming the model that made its song.
