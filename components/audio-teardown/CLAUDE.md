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
| split | `split.py` | voices lifted off the music (Demucs, MIT) | this Mac, `~/.daemn/venvs/demucs` |
| words | `words.py` + `prompts/words-v*-owner.md` | every word, in the language said (Gemini 3.1 Pro → 3.5 Flash) | GEMINI_API_KEY |
| speakers | `speakers.py` | who speaks when (ElevenLabs Scribe v2) | ELEVENLABS_API_KEY |
| lines | `lines.py` | merged by what was said into T1, T2…; every disagreement flagged; a word only Scribe heard (a short "Ew." under music) is kept as its own line, flagged `scribe-only`; every non-word sound (sniffs, sighs, moans) kept as `vocal_sounds` | pure code |
| voices | `voices.py` + `prompts/voice-card-v*-owner.md` | one clip per person; measured (Praat, GPLv3) + heard (Gemini); labels checked | this Mac, `~/.daemn/venvs/audio`; GEMINI_API_KEY |
| music | `music.py` + `prompts/music-read-v*-owner.md` | named (Shazam, then AudD — both asked); tempo, beat grid, key, energy curve, builds and drops, ending measured (librosa, ISC); heard from the music alone, blind: the model is not told the recognised name (it was once wrong and got described instead of the music); it gives the felt tempo next to the measured one | this Mac (`~/.daemn/venvs/shazam`, `~/.daemn/venvs/audio`); AUDD_API_TOKEN; GEMINI_API_KEY |
| effects | `effects.py` + `measure.py events` + `prompts/effects-check-v*` | every sharp onset (top 30%) and every soft stretch the music's loop does not hold (riser, swell, whoosh), timed; moments that are the same added sound grouped by fingerprint, each with its nearest bank sound; ONE whole-track read on the judge model names each group once from `definitions/sound.json` `effect_name`, gives job, category and in-the-edit, and adds what the tool missed; the picture's edit moments are heard against when the caller passes them; the room's quietest second measured | this Mac; GEMINI_API_KEY, then GEMINI_API_KEY_PERSONAL |
| mix | `mix.py` | loudness (EBU R128, ffmpeg), voice over music, how far the music ducks under speech, every silence and the line after it, spoken / music form | this Mac |

`gemini.py` is the one door to Gemini (low thinking — the default stalled 4+
minutes on 3 of 10 swipes). A key out of credit or quota hands over to
GEMINI_API_KEY_PERSONAL (decision 2026-11-12); any other failure goes to the next model. `keys.py` reads keys by name: environment first,
then the Keychain (`daemn-<NAME>`). Nothing is read from a file.

## The contract

In: a video path. Out, all under `--out` and nowhere else:
`transcript.json` (the video chain's shape — id, speaker, start, end, text —
plus `language`, `also`, `flags`), `transcript.md`, `sound-sheet.json`,
`sound-sheet.md`, `words.json`, `speakers.json`, `audio/{mix,voices,music}.mp3`,
`voices/voice-<n>.mp3`, `voices/voice-cards.json`, `effects-machine.json` (every
timed moment and its one-clip check). `sound-sheet.json` carries `vocal_sounds`, `music`,
`effects` and `mix` sections; `sound-sheet.md` renders TRANSCRIPT · VOCAL SOUNDS · VOICES ·
MUSIC · EFFECTS · MIX in that order. `--reuse` keeps the words and voice cards
already in `--out` and adds only music, effects and the mix.

Flags on a line: `scribe-dropped`, `scribe-translated`, `heard-differently`,
`speaker-from-words-model`, `scribe-only` — every place a person should listen.

**The plane it emits:** none of its own — the caller's `--out`. In the video
chain that is `machine/.tmp/audio-teardown/<hash>/`, copied into and filed with
the video-teardown run (`file_run.py`); a person running it standalone points
`--out` at a run folder of their own.

## Definitions (the owner's)

`prompts/` — versioned `-vN-owner.md`, highest wins; a change is a new file on
his word, shown verbatim. `definitions/voice.json` — the voice-card label lists,
`definitions/sound.json` — the music, effect-job and UCS category lists and the
AudioSet → UCS filing rules. Both `status: draft` until he approves. `delivery_style` is NOT listed here: it is
read from the doctrine's own dial (`components/marketing-doctrine/delivery.json`)
so the two cannot drift. A label not on a list is kept and named as unknown.

## Where it is used

`components/video-teardown/machine/transcript.py` runs it before the teardown
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
the market loop (every Sound Sheet filed with the swipe's performance).

Effects (2026-11-15): names now hold across runs (two runs on one swipe gave the
same names, three prompt framings each run twice). What the ear calls ADDED still
moves with how it is asked: on a lo-fi swipe it found nothing at all without the
picture's edit moments, and a per-moment A/B listen heard "spray" and "ding" in
plain drums. Pass `picture=` (the video teardown's frame map cuts and moves) when
it is known; a check of the ear against hand-marked swipes is still to build.

## Tests

`python3 -m unittest tests/test_lines.py tests/test_sound.py tests/test_effects.py` — no network, no spend.
