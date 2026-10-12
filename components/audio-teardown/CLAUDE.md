# components/audio-teardown — the sound of a swipe, read properly

**audio-teardown** — takes **a video**, makes **its Sound Sheet**: every word in
the language it was said, who said it and when, one voice card per person, the
music (named, measured, heard), every sound effect (timed, confirmed, named) and
the mix (loudness, balance, ducking, silences).
Does not **write, cast or generate anything**. Triggered by
`python3 run.py <video> --out <dir>`.

**Owner: the owner** · built 2026-09-25 · run by a person by hand, or by the video
chain inside a batch — same code.

Runs by: person

(the developer, 2026-10-07, triage action 3 (definition lines and registry rows); SI-6 (intent line). The line read `both` until then.)

Why it exists (the owner, 2026-09-25): speech-to-text alone turned a Korean
mother's lines into "[laughs]" and, on a second run, translated her into
English without a word. "We need the ability to transcribe ALL language." Then:
"we can make really really really powerful avatar, sub avatar, casting calls …
and when we generate voice, we know exactly what to generate."

## How it runs

| Step | File | What | Where it runs |
|---|---|---|---|
| split | `split.py` | voices lifted off the music (Demucs, MIT) | this Mac, `the venv named by DEMUCS_PYTHON` |
| words | `words.py` + `prompts/words-v*-damon.md` | every word, in the language said (Gemini 3.1 Pro → 3.5 Flash) | GEMINI_API_KEY |
| speakers | `speakers.py` | who speaks when (ElevenLabs Scribe v2) | ELEVENLABS_API_KEY |
| lines | `lines.py` | merged by what was said into T1, T2…; every disagreement flagged | pure code |
| voices | `voices.py` + `prompts/voice-card-v*-damon.md` | one clip per person; measured (Praat, GPLv3) + heard (Gemini); labels checked | this Mac, `the venv named by AUDIO_PYTHON`; GEMINI_API_KEY |
| music | `music.py` + `prompts/music-read-v*-damon.md` | named (Shazam, then AudD — both asked); tempo, beat grid, key, energy curve, builds and drops, ending measured (librosa, ISC); heard from the music alone | this Mac (`the venv named by SHAZAM_PYTHON`, `the venv named by AUDIO_PYTHON`); AUDD_API_TOKEN; GEMINI_API_KEY |
| effects | `effects.py` + `prompts/effects-check-v*`, `effects-name-v*` | every sharp sound timed (onsets) and tagged (PANNs AudioSet tagger, MIT code / CC-BY weights in `~/panns_data`); each moment confirmed on its own 1.2 s clip; named, given its job and UCS category | this Mac; GEMINI_API_KEY |
| mix | `mix.py` | loudness (EBU R128, ffmpeg), voice over music, how far the music ducks under speech, every silence and the line after it, spoken / music form | this Mac |

`gemini.py` is the one door to Gemini (low thinking — the default stalled 4+
minutes on 3 of 10 swipes). `keys.py` reads keys by name: environment first,
then the Keychain (`daemn-<NAME>`). Nothing is read from a file.

## The contract

In: a video path. Out, all under `--out` and nowhere else:
`transcript.json` (the video chain's shape — id, speaker, start, end, text —
plus `language`, `also`, `flags`), `transcript.md`, `sound-sheet.json`,
`sound-sheet.md`, `words.json`, `speakers.json`, `audio/{mix,voices,music}.mp3`,
`voices/voice-<n>.mp3`, `voices/voice-cards.json`, `effects-machine.json` (every
timed moment and its one-clip check). `sound-sheet.json` carries `music`,
`effects` and `mix` sections; `sound-sheet.md` renders TRANSCRIPT · VOICES ·
MUSIC · EFFECTS · MIX in that order. `--reuse` keeps the words and voice cards
already in `--out` and adds only music, effects and the mix.

Flags on a line: `scribe-dropped`, `scribe-translated`, `heard-differently`,
`speaker-from-words-model`, `scribe-only` — every place a person should listen.

**The plane it emits:** none of its own — the caller's `--out`. In the video
chain that is `machine/.tmp/audio-teardown/<hash>/`, copied into and filed with
the video-teardown run (`file_run.py`); a person running it standalone points
`--out` at a run folder of their own.

## Definitions (the owner's)

`prompts/` — versioned `-vN-damon.md`, highest wins; a change is a new file on
his word, shown verbatim. `definitions/voice.json` — the voice-card label lists,
`definitions/sound.json` — the music, effect-job and UCS category lists and the
AudioSet → UCS filing rules. Both `status: draft` until he approves. `delivery_style` is NOT listed here: it is
read from the doctrine's own dial (`components/marketing-doctrine/delivery.json`)
so the two cannot drift. A label not on a list is kept and named as unknown.

## Where it is used

`tools/video-teardown/machine/transcript.py` runs it before the teardown
read (cached by video content in `machine/.tmp/audio-teardown/`, as its own
process), copies the Sound Sheet, voice clips and cards into the run, and
appends voices, music, effects and the mix to the teardown record; `deepen.py`
hands them to the cast sheet; `music.py` takes the song, tempo, key and composer
brief from the sheet instead of reading the music a second time; `file_run.py`
files the sheet. A cached run made before music, effects and the mix existed is
topped up with `--reuse`, not redone.
Off: `VT_NO_AUDIO_TEARDOWN=1` (falls back to Scribe only, and says so).

## Still to build

UCS subcategories; the sound doctrine (`components/marketing-doctrine/sound.json`);
the market loop (every Sound Sheet filed with the swipe's performance). Effect
NAMES can differ between runs on the same moment (typewriter / click); the
times are stable and every effect carries how sure the check was.

## Tests

`python3 -m unittest tests/test_lines.py tests/test_sound.py` — no network, no spend.
