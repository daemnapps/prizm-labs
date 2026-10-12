# The Sound Sheet — research (2026-09-25)

Mirror of the **Sound sheet** tab on *Swipe Batches*
((team page)).
the owner: "there's already some level of foundational elements and models that these
industries have used for decades … similar to how we build our casting sheet, I
want to get ultra nuanced here too."

The audio equivalent of the casting sheet: one record per swipe, every field from
an established industry vocabulary, each filled by **measured** (a tool — stable
number), **heard** (a model listening to the isolated track) or **identified**
(a database lookup).

## Where the vocabulary comes from

| World | What it gives us |
|---|---|
| Film sound | Dialogue / music / effects kept as separate stems; spotting to the frame; UCS effect naming (82 categories, 753 subcategories, v8.2); Chion's audio-vision — empathetic vs anempathetic music, diegetic vs laid over, synchresis |
| Music industry | Production-music / supervision tags — genre, mood, energy, tempo, key, instrumentation, vocals, era, valence–arousal; Essentia measures tempo/key and classifies 400+ genres and moods |
| Voice & casting | VO read styles (announcer, conversational, real person, peer-to-peer) and direction terms (billboard, beat, pace); GRBAS voice quality (grade, roughness, breathiness, asthenia, strain); Laver's Vocal Profile Analysis; eGeMAPS — 88 standard acoustic voice parameters (openSMILE) |
| Advertising | Sonic logos, music fit; audio-ad testing's four drivers — sonic branding, music, voice, message |
| Machine listening | AudioSet ontology (632 sound classes); source separation (Demucs); diarization (pyannote); age/gender/emotion/accent models (wav2vec2, emotion2vec) |

## The sheet

**1 · The mix** — sound form (spoken/sung/rapped/music only/silent, share of runtime) · voice-over-music balance in dB and ducking · loudness (LUFS) and dynamic range · every silence and what it lands on · sound-off test (are the words on screen).

**2 · Each voice** — language per line and switch points · accent and region · age and gender as presented · pitch mean, range, movement, uptalk · texture (warm, bright, nasal, raspy, breathy, fry, strain) · read style · pace in wpm and pause pattern · billboarded words · emotion and energy per line · fillers, laughs, catchphrases · mic and space · who they talk to · talk share, line count, longest line.

**3 · The music** — track, artist, which part of the song (identified) · source (licensed / trending sound / stock / original) · BPM, meter, key, mode · energy curve with every build/drop/switch · valence–arousal · genre, sub-genre, era · instruments and vocals · in the scene or laid over · with the mood or against it · cuts on the beat · how it ends.

**4 · Effects & room** — every effect with exact time, UCS name and what it lands on · its job (transition, emphasis, caption pop, reveal, joke) · real product sounds (pump, squeeze, click, spray) · room tone, echo, street, silence.

**5 · Sonic brand** — sound logo or sung brand name · sounds/lines that repeat within and across the brand's ads · when the brand is first spoken and how often.

## The loop

Every swipe gets a Sound Sheet → joined to how it performed (views, clones, spend, market, sub-avatar) → patterns per market → written into casting calls, voice prompts, music and effects lists.

## What the research says moves buying (store, radio and lab studies — to be re-tested on our own winners)

- Music fit beats liked-but-off music — MacInnis & Park, 1991.
- French music sold more French wine, German music more German — North, Hargreaves & McKendrick, 1997.
- Slower background music, slower shopping, higher supermarket sales — Milliman, 1982.
- Sonic branding lifted audio-ad recall; music, voice and message the other drivers — Audacy × Veritonic, 2023.

## Tools

Demucs + ElevenLabs isolation (split) · Gemini 3.1 Pro (words, every language; everything "heard") · Scribe v2 / pyannote (who speaks when) · openSMILE eGeMAPS (voice numbers) · wav2vec2 age-gender, emotion2vec · Essentia (tempo, key, genre, mood) · a music-ID service (needs one sign-up) · onset detection + AudioSet models, named in UCS (effects).

## Song recognition (2026-09-25) — CORRECTED: already built with Shazam

Another session built fix L at 17:33 the same day: Demucs splits the music off, **Shazam** names it (free, no account, via the unofficial shazamio library — the owner chose it over signing up), Gemini describes the isolated music when no song is named (`machine/music.py`, wired into `deepen.py`). AudD stays a backup only if a key is added. The comparison below is kept for reference.


**AudD** — the pick. Enterprise endpoint scans the whole file in 12-second slices and returns the offset of every match (catches mid-video switches). 300 free requests, no card; then ~$__ per 1,000 slices ≈ 2–3¢ per one-minute swipe. Run on the isolated music track.
**ACRCloud** — backup: broadcast-monitoring grade, larger catalog, price by quote, 14-day trial.
**Shazam** — no public API (Apple developer program only).
Unknown for both: sped-up / remixed TikTok sounds — the test page measures it. Sign-up is the owner's (email only).

## Models, lined up

| Field | Main | Check / fallback | Runs |
|---|---|---|---|
| Split | Demucs v4 | ElevenLabs voice isolation | Mac + key |
| Words, every language | Gemini 3.1 Pro | Gemini 3.5 Flash → Scribe v2 (flagged) | keys |
| Who speaks when | Scribe v2 | Gemini speaker labels | key |
| Language per line | Gemini 3.1 Pro | VoxLingua107 (107 languages) | key + Mac |
| Accent | Gemini on the person's clip | CommonAccent (English accents) | key + Mac |
| Age · gender | audEERING wav2vec2 age-gender | Gemini + cast sheet | Mac |
| Pitch · texture · strain | Praat + openSMILE eGeMAPS | Gemini interprets | Mac |
| Emotion · energy | emotion2vec+ | Gemini per line | Mac + key |
| Pace · pauses · share | computed from Scribe timings | — | Mac |
| Read style · emphasis · tics | Gemini on the voice track | element-library check | key |
| Song | AudD | ACRCloud | sign-up |
| Tempo · key · beats | Essentia | librosa | Mac |
| Genre · mood · instruments | Essentia models (Discogs 400, Jamendo mood/instrument, valence–arousal) | Gemini | Mac + key |
| Loudness · balance · silences | ffmpeg loudness (LUFS) per track | — | Mac |
| Cuts on the beat | beat grid × shot times | — | Mac |
| Effects: when | onset detection on the effects track | — | Mac |
| Effects: what | PANNs AudioSet tagger + CLAP → UCS name | Gemini against the frame | Mac + key |
| Room · product sounds | AudioSet tagger | Gemini | Mac + key |

## Connected like the doctrine

1. **`components/marketing-doctrine/sound.json`** beside `delivery.json` — every audio value with what it does, when it fits (awareness, section, format), risk, source; rendered to `slices/sound.md`, bound as `{sound}`; draft until the owner approves.
2. **Element lists** in `components/elements` — read style, voice texture, music role, music source, UCS effect names, language; teardown labels checked, unknowns recorded.
3. **Crosswalks** — read style ↔ `delivery_style`; pace ↔ `pacing`; voice card ↔ `spoken.json` voice-model settings; voice card ↔ cast sheet.
4. **Down the chain** — 1b/1c get the Sound Sheet; stage 3 keeps the swipe's sound structure under the structure lock; the brief carries music/effects list and casting call with voice; the manifest checks sound carried; video-production builds the voice from the card.
5. **Market loop** — Sound Sheets × performance (views, clones, market, sub-avatar).

Build order: free tools on the Mac → draft sound.json + element lists for approval → test page on 8–10 swipes → chain only on the owner's word.

## Wiring map (2026-09-25) — nothing installed or built yet

**One new tool: `components/audio-teardown/`** — one command, a video in, the Sound Sheet out; built to hand off.
Files: `run.py` (entry) · `split.py` (Demucs) · `words.py` (Gemini 3.1 Pro, every language, fallbacks) · `speakers.py` (Scribe v2) · `lines.py` (T-lines; today's transcript logic moves here) · `voices.py` (per-person clip, Praat, voice card) · `music.py` (today's Demucs+Shazam move here; + librosa tempo/key/beats, CLAP mood words) · `effects.py` (onsets + PANNs + CLAP → UCS names) · `mix.py` (LUFS, balance, silences) · `sheet.py` (assemble + element-library check) · `setup.sh` (installs tools, checks business-safe licences) · `prompts/` (four audio prompts, `-damon`) · `definitions/` (label lists, UCS 82/753) · `tests/` (no network) · `CLAUDE.md`, `README.md`.

**Chain:** new stage **1a Audio teardown** before the teardown → teardown v15 fills Sound form / Music / Sound column / Voice from the sheet → deep passes: voice cards join the cast sheet → 1b/1c see language, accent, age by ear → spec v5 numbers sound elements → rewrite v15 keeps sound structure under the structure lock → 4a–4g read `{sound}` → brief v24 carries a Sound block (music/effects list, casting call with voice); manifest checks sound → video-production builds voices from cards. Prompt changes only on the owner's word, shown verbatim.

**Edited:** video-teardown `run.py`, `transcript.py` + `music.py` (become pass-throughs), `deepen.py`, `manifest.py`, `elements_check.py`, `file_run.py`, `board.py`, `batch.py`; `marketing-doctrine/sound.json` (new, beside delivery.json); `elements/` (sound label lists); `swipe-organic` + `intake` (each swipe keeps its sound and languages); `video-production` (later).

**Files:** Mac run folder = split tracks (large, never git) · Drive `…/video-teardown/machine/runs/<run>/audio/` = voices/music/effects tracks and one clip per person · repo `runs/video-teardown/<brand>/<run>/` = Sound Sheet + transcript (text) · `platform/data/sound/` = one row per swipe with market, sub-avatar, performance (the market loop).

**Keys:** GEMINI_API_KEY (have) · ELEVENLABS_API_KEY (have) · APIFY_TOKEN (have, button only, credit out) · TikTok login via Higgsfield (optional, the owner's click) · Shazam (no key) · AUDD_API_TOKEN (not needed).

**Mac tools:** Demucs, Shazam installed; to install ≈3 GB: Praat (parselmouth), librosa, PANNs, CLAP, VoxLingua107. Disk has ~18 GB free.

**Handoff:** definitions (sound.json, label lists, audio prompts) stay the owner's; the engine goes to whoever runs it; Runs by: both; through /system-fit → /system-ready → /system-review before others depend on it.

**Build order:** 1 words in every language → 2 voices → 3 music + effects + mix → 4 doctrine + labels + prompts → 5 pools + market loop. Each step on the test page before the next.
