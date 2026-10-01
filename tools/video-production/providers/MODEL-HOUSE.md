# The model house — which door for each model

**2026-09-17.** Damon's rule: a sub-par access to a model quietly neuters the
process, so every model we use was researched at each of its doors — the
maker's own API, fal, Higgsfield — with the field names quoted from the
official docs, before deciding where it is called from. This page is the
ruling and the evidence. The five full dossiers are in `research/`.

## The ruling

| Station | Model | Primary door | Why the other doors are sub-par |
|---|---|---|---|
| cast · still | **GPT Image 2** (`gpt-image-2`) | **direct — OpenAI API** | `input_fidelity: "high"` ("faces are preserved far more accurately") and `moderation: "low"` (the setting that stops clean frames being blocked) exist **only** on the direct API. fal (`openai/gpt-image-2/edit`) and Higgsfield (`gpt_image_2`) expose neither. Direct also has the batch API. |
| edit | **Nano Banana Pro** (`gemini-3-pro-image`) | **direct — Gemini API** (fal acceptable) | direct: per-category `safety_settings`, batch mode at 50% off ($0.067 a 2K edit). fal (`fal-ai/nano-banana-pro/edit`): same model, same references, one safety scalar — a fair backup. Higgsfield: the reference `medias` shape silently no-ops when wrong and 9:16 was ignored on a real run. |
| motion (silent) | **Seedance 2.5** | **Higgsfield** (the editors' hand) — fal alternate, direct BytePlus equal | at 720p Higgsfield costs the same as direct for motion, so it is the editors' door (Damon's 2026-09-17 "we scale tomorrow" ruling); fal (`bytedance/seedance-2.5/image-to-video`) and direct BytePlus remain equal alternates — explicit first + last frame, 1080p, 4–30 s, `generate_audio: false`. |
| talking | **Seedance 2.5** on Higgsfield · **OmniHuman 1.5** on fal | **both proven live 18 Sep** on the same still + line. Higgsfield: 6 s 720p 9:16, 39 credits (≈ $1.30–1.70). fal OmniHuman: $0.16/s ≈ $0.77, clip = the line's length, editor crops to 9:16. fal **Google Omni Flash 1.1**: 44 s, $0.10/s, lip-synced beautifully — **to words it made up** (10% match to the line by transcription). It has no audio input at all (the field was silently dropped). **But it can be controlled:** write the line into the prompt — it speaks it 100% — then swap the voice to the character's with ElevenLabs speech-to-speech, timing intact (100% again). Proven live on fal ($0.10/s, 43 s) and direct on Google (`gemini-omni-1.1-flash`, Interactions API, 41 s, price to be read from the first bill). **Line parity is now a gate**: every talking clip is transcribed (ElevenLabs Scribe) and must say its line ≥ 85%. fal's Seedance 2.5 refuses photoreal people — OmniHuman is fal's talking door. Direct BytePlus stays the one-command upgrade for Seedance | Only BytePlus documents feeding real audio into a lip-synced result (`reference_audio` role; the dubbing example). fal only takes audio on `reference-to-video`, sold as a timing signal, unproven for verbatim lines. Higgsfield's docs call `audio_references` a style reference — but the 16 Sep run held the voice, so it stays the proven door until BytePlus is set up and tested on one line. |
| voice | **ElevenLabs** | **direct — ElevenLabs API** only | custom voices (`/v1/voices/add`, Voice Design), full `voice_settings`, audio tags on v3, character-level `alignment` timestamps, 10-voice dialogue, speech-to-speech. fal: presets only, `stability` only, no clone/design. Higgsfield: cannot import a voice; undocumented element cap. |
| song | **Lyria 3 Pro** (`lyria-3-pro-preview`; `lyria-3-clip-preview` for 30 s; `lyria-3.5` newest) | **direct — Gemini API** only | `generateContent` with `[Verse]/[Chorus]` and time tags, image mood, WAV. fal (`fal-ai/lyria3/pro`): prompt + image in, plain lyrics out, no times, no lyric field. The timed sheet in Lyria's text part is observed behaviour, not documented — check with ElevenLabs Scribe (word timestamps; best on music-laden audio). |

**What this means.** Four of the five models are called **directly** — the
aggregators strip exactly the controls this process depends on. fal keeps
one job it is a fair alternate at (silent motion, and a backup for edits).
Higgsfield keeps both proven motion jobs (silent and the talking beat)
until a direct door is opened and tested. The audio (voice line, song) is
always made first and travels to whichever door makes the pictures as a
plain file.

**The two hands** (Damon's 2026-09-17 ruling): the machine — cast, still,
edit, voice, song — runs direct, one command, nobody at a keyboard; the
editors — motion, talking — run on Higgsfield, from the submit sheet the
machine writes.

## What has to exist for this to run

| | Status |
|---|---|
| OpenAI API key (`daemn-OPENAI_API_KEY`) | in the Keychain (18 Sep) — direct door proven live |
| Gemini key | in the Keychain |
| ElevenLabs key | in the Keychain |
| fal key | in the Keychain |
| BytePlus ModelArk account (AP region, `ark.ap-southeast.bytepluses.com`) | **not opened** — Damon's call; unlocks Seedance direct for the talking beat |
| Direct clients in the runner (OpenAI images, Gemini image, Gemini Lyria) | built and proven live 18 Sep |
| Higgsfield API key pair (`daemn-HIGGSFIELD_KEY_ID` / `_SECRET`) | in the Keychain (18 Sep) — 91 endpoints answer; **$0 balance** — nothing prints until the console wallet is funded |

## The cost per door (read 2026-09-17, official price pages)

**Images, voice, song — no difference.** GPT Image 2 ~$0.18 an image on fal
vs ~$0.15–0.21 direct; Nano Banana Pro $0.15 on fal vs $0.134 direct
($0.067 in batch); ElevenLabs $0.10 per 1,000 characters at both; Lyria
$0.08 a song at both. Direct is equal or cheaper, and has the controls.

**Motion is the whole difference, and it runs the other way:**

| Seedance 2.5, per second of clip | 480p | 720p | 1080p |
|---|---|---|---|
| BytePlus direct | $0.10 | **$0.23** | $0.57 |
| Higgsfield, Ultra plan (6.5 credits/s at 720p; 23–30 credits per $) | $0.10–0.13 | **$0.21–0.28** | not published |
| fal | $0.22 | $0.47 | not sold (2.5 is 480/720p only on fal) — **and refuses any photoreal person** (live 18 Sep: the identical presenter still was blocked twice as a 'real-person likeness'); b-roll with nobody in frame only |

**One 30-second ad at 720p**, line by line:

| | Direct | Higgsfield (Ultra) | fal |
|---|---|---|---|
| Stills — GPT Image 2 × 9 | $1.71 | ~$0.30–0.40 (credit rate unclear) | $1.60 |
| Edits — Nano Banana Pro × 3 | $0.40 ($0.20 in batch) | ~$0.25 | $0.45 |
| **Motion — Seedance 2.5, 40 s incl. the talking beat** | **$9.24** | **$8.70–11.30** | **$18.92** |
| Voice — ElevenLabs, 600 characters (direct at every door) | $0.06 | $0.06 | $0.06 |
| **Total** | **≈ $11.4** | **≈ $9.5–12.0** | **≈ $21.0** |
| + the song, if a song ad (Lyria, direct) | +$0.08 | +$0.08 | +$0.08 |

Direct and Higgsfield are a wash at 720p, so between them the choice is
control and hands (direct = one command, nobody at a keyboard; Higgsfield =
the editors' door). fal is ~$10 more per ad on the motion line alone — and, tested live 18 Sep, it will not animate a person at all: the same still Higgsfield turned into the talking beat was refused twice on fal's Seedance 2.5 ("likenesses of real people", partner validation). fal keeps product and scene b-roll on Seedance — and the talking beat on OmniHuman 1.5, which took the same still ($0.16/s ≈ $0.77 a line, about half Higgsfield's price). 1080p on the direct door is 2.5× the
motion line — about $25 an ad — so 720p is the print resolution unless a
hero clip earns more.

**A correction.** The 16 Sep receipts priced a Higgsfield credit at 18 per
dollar; on the Ultra plan it is 23 (monthly) to 30 (annual). Every
Higgsfield figure on The Road to $10 was about 1.5× too pessimistic.

## The fourth door — the Higgsfield API (re-run 2026-09-18)

The 17 Sep ruling was made with three doors: the maker's API, fal, and
Higgsfield **through the MCP / web app** (Ultra plan credits, a person or a
session at the keyboard). On 18 Sep Damon minted a Higgsfield **API** key
pair at console.higgsfield.ai — a fourth door that did not exist for us
when the ruling was made. Same analysis, run again with it in.

**What it is.** Plain HTTP at api.higgsfield.ai, `Authorization: Key
<id>:<secret>`. Pay per generation in USD from its own prepaid wallet —
**separate from the Ultra plan**; the Ultra credits do not reach it. 20
concurrent requests. `POST /estimate/<model>` prices a job before it runs;
failed and `nsfw` results are not charged; outputs are kept 7 days (the
client downloads on completion). Model list is `GET /models` — 78 live,
91 endpoints answered our key on the 18 Sep probe. Tooling:
`~/devel/daemn/tools/higgsfield/hf_client.py` (pull · probe · show · run ·
poll). Page: Higgsfield Control.

**Which of our five models it carries.** Checked two ways: the 78 in
`GET /models`, then 617 slug guesses derived from the MCP's 96 model names
POSTed at the API (anything but 404 is a real route). That turned up
unlisted doors — GPT Image **1.5**, Nano Banana Pro (disabled), Cinema
Studio image, FLUX.2 Pro.

| Station | Model we use | On the Higgsfield API? | What you'd get instead |
|---|---|---|---|
| cast · still | GPT Image 2 / 2.5 | **no** | `openai/gpt-image-1.5` (unlisted, older). It validates `moderation: low` ✓ — but `input_fidelity` is not validated (passes through, presumed dropped) and aspect ratios are **1:1 / 3:2 / 2:3 only — no 9:16**. |
| edit | Nano Banana Pro | **exists, disabled** | `/nano-banana-pro` and `/edit` answer `503 model_disabled` (18 Sep); Nano Banana 2 the same |
| motion · talking | Seedance 2.5 | **yes** | text/image/reference-to-video, video-edit, video-extend; 480p/720p only |
| voice | ElevenLabs | **no** — the API serves no audio model at all (the MCP's six TTS/music models are not on it) | — |
| song | Lyria 3 Pro | **no** | — |

So four of the five stations are untouched: the direct ruling stands as
written. The only station the fourth door changes is **Seedance 2.5**.

**Seedance 2.5 on the API — the fields.** `reference-to-video` takes
`image_urls` (1–30) + `audio_urls` (1–10) + explicit `aspect_ratio` incl.
`9:16` + `generate_audio` — the same shape as the MCP talking recipe that
was proven 18 Sep (still as start image, the ElevenLabs line as audio
reference, omni). `image-to-video` takes `image_url` + `end_image_url`
(first + last frame, which the MCP door did not expose). 4–30 s. No 1080p.

**Price — the estimate endpoint is authoritative.** Seedance 2.5 on the
API is token-metered: `ceil(seconds × W × H × 24 / 1024)` tokens at
**$0.0214 per 1,000** (480p and 720p). That is the identical rate fal
charges. At 720p 9:16 (720×1280) it is 21,600 tokens a second:

| Seedance 2.5, one second at 720p | $/s | 6 s talking beat | 40 s of motion (one ad) |
|---|---|---|---|
| BytePlus, direct (account not opened) | **$0.23** | $1.39 | **$9.24** |
| Higgsfield MCP / app, Ultra credits (6.5 cr/s, 23–30 cr/$) | $0.21–0.28 | $1.30–1.70 | $8.70–11.30 |
| **Higgsfield API**, list | $0.46 | $2.77 | $18.49 |
| **Higgsfield API**, 15% default discount | $0.39 | $2.36 | $15.72 |
| **Higgsfield API**, Seedance picked in the 7-day launch offer (30%) | $0.32 | $1.94 | $12.94 |
| fal (Seedance; refuses people) | $0.47 | — | $18.92 |
| fal OmniHuman 1.5 (talking only) | $0.16 | $0.77 | — |

(The marketing page shows Seedance 2.5 at "$0.1234 / sec"; the estimate
endpoint's own formula gives $0.46 at 720p. The endpoint is what bills —
the first funded run settles it.)

**One 30-second ad at 720p, four doors:**

| | Direct | Higgsfield MCP (Ultra) | **Higgsfield API** (15% / 30%) | fal |
|---|---|---|---|---|
| Stills, edits, voice — all direct | $2.17 | $2.17 | $2.17 | $2.17 |
| Motion — Seedance 2.5, 40 s incl. talking | $9.24 | $8.70–11.30 | $15.72 / $12.94 | $18.92 |
| **Total** | **≈ $11.4** | **≈ $10.9–13.5** | **≈ $17.9 / $15.1** | **≈ $21.1** |

**What the fourth door buys, and what it costs.**

- **It collapses the two hands into one.** The 17 Sep ruling put motion and
  talking on Higgsfield *because* that was the proven door and it needed an
  editor at the keyboard (or a Claude session on the MCP). The API is the
  same backend with nobody at a keyboard: one command, 20 in parallel,
  webhooks, estimate-before-spend, cancel. That is the control direct was
  chosen for — on the one model where direct is not open yet (BytePlus).
- **It is the most expensive Seedance door.** ~1.4–1.7× direct after
  discounts, ≈ fal at list. On a 40 s motion line that is +$3.7 to +$6.5
  an ad over direct BytePlus, and about +$4 over Ultra credits.
- **It is a wallet, not a plan.** Ultra credits cannot be spent here; the
  API wallet is prepaid and its credits expire in a year.
- **It opens the cheap-motion lever.** The same door serves Kling 3.0
  std ($0.107/s list, $0.091 after 15%), Kling 3.0 turbo ($0.095), Wan 3.0
  ($0.10 at 720p), MiniMax H3 ($0.11), LTX 2.5 ($0.09–0.12) — read from
  the estimate endpoint, 18 Sep. If the 34 s of *silent* motion per ad ran
  on Kling 3.0 std and only the 6 s talking beat stayed on Seedance, the
  motion line is ≈ $5.45 and the ad ≈ $7.6 — under the $10 goal on this
  door alone. Whether those models hold our formats is Damon's call and a
  bake-off, not a ruling.
- **Not yet verified, because the wallet is empty:** that the API accepts
  a photoreal presenter still (the MCP did; fal's Seedance did not), that
  `audio_urls` dubs the line (the MCP's `audio_references` did), and that
  9:16 is honoured. One talking-beat run (~$2.40) answers all three.

**The re-run ruling, for Damon to confirm.**

| Station | 17 Sep | 18 Sep, with the API |
|---|---|---|
| cast · still · edit · voice · song | direct | **direct — unchanged**; the API does not carry these models |
| motion (silent) | Higgsfield, editors' hand | **Higgsfield API** from `run.py`, nobody at a keyboard — at a premium over direct/Ultra; bake Kling 3.0 / Wan 3.0 on the same door for the cheap line |
| talking | Higgsfield MCP, editors' hand → BytePlus | **Higgsfield API** (same recipe shape) from `run.py` → BytePlus direct still the price upgrade (halves the motion line) |
| fal | alternate | unchanged — OmniHuman for a cheap talking line, b-roll only on Seedance |

Net: the fourth door does not change *where* any model is called for
control reasons — it removes the last reason a human had to be in the
loop. The price of that, today, is about $4–6 an ad until BytePlus opens.

## The talking beat ruled — the Omni door (2026-09-18, 15:05)

Damon watched the same still + line through three doors — Higgsfield
Seedance 2.5, Google Omni direct (controlled recipe), fal Omni (controlled
recipe) — and ruled: **"fal Omni came out the best for what I need and
obviously it's cheaper."**

**The door:** `google/gemini-omni-flash/v1.1/image-to-video` on fal, via
the controlled-Omni recipe, now one call — `machine/omni.py talk` — on the
machine hand: the line written into the prompt → Omni performs it → line
parity → ElevenLabs speech-to-speech into the character's voice → ffmpeg
remux → parity again. **Proven as one command 2026-09-18:** 63 s wall
clock, 100% parity before and after the swap, 720×1280, 6 s.

**Price:** $0.10/s at 720p on fal + speech-to-speech on the clip's seconds
— about $0.65 a 6-s beat, against $1.30–1.70 on Higgsfield credits and
$2.36 on the Higgsfield API. Hands-off, US card, no wallet to fund beyond
the fal and ElevenLabs keys already in the Keychain.

**BytePlus, for the record:** key minted and verified (the account
answers), the door wired (`machine/direct_byteplus.py`, tests green) —
but Seedance 2.5 cannot be activated without a paid balance and BytePlus
takes no online payment from a US company ("Online payment is not supported
in your country/region"; sales form only). Wired and waiting.

**Silent motion** stays on Higgsfield through the MCP (Ultra credits) for
now; fal's Seedance for b-roll with nobody in frame.

## The evidence, per model

`research/gpt-image-2.md` · `research/nano-banana-pro.md` ·
`research/seedance-2.5.md` · `research/elevenlabs.md` · `research/lyria.md`
— each with the three doors' quoted fields, prices and limits, and the URLs.

Prices, as read 2026-09-17: GPT Image 2 ~$0.01–0.21 per image by quality
(direct); Nano Banana Pro $0.134 per 1K/2K image direct, $0.15 on fal;
Seedance 2.5 ~$0.23/s at 720p, ~$0.57/s at 1080p direct, similar on fal;
ElevenLabs ~$0.10 per 1,000 characters; Lyria 3 Pro $0.08 a song.

## Ruling 2026-09-18 — one image door

Damon: "we'll just do gpt for all image work both initial reference gen and edits." Every still — the first frame (generation with the cast sheet as the identity reference) and every edit (the last frame, `images/edits`, `input_fidelity: high`, two references: the previous frame first, the cast sheet second) — runs on GPT Image 2.5 direct, then is colour-matched to the first frame. Nano Banana Pro stays in the registry as an alternate: measured the same day, it held the face with the second reference but under-delivered a push-in.

## Ruling 2026-09-18 evening — motion and talking

Damon: "let's just do the higgsfield seedance frame." Motion and the talking beat run on Seedance 2.5 through Higgsfield: `start_image` (first frame) + `end_image` (last frame) + `audio_references` (the scene's slice of the one voice track), mode omni_reference, up to 30 s. Proven live on Pigment Memory scene 1. fal Omni (the 15:05 ruling) and BytePlus direct stay as alternates.
