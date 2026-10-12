# The banks: music and sound effects, made once

ELEMENTS.md §3 (2026-09-23): the teardown names the sound, the brief carries
it, **production picks it from a bank that was made once**, and the edit lays
it. A missing row is an error, never a silent fallback.

| bank | index | the audio (Drive) | picked by |
|---|---|---|---|
| music | `banks/music/index.json` | `Shared Assets/banks/music/<id>.mp3` | the brief's `music: {energy, tempo_bpm, mood}`: energy and mood exact, then the nearest tempo inside `tempo_tolerance_bpm`, then the id |
| sfx | `banks/sfx/index.json` | `Shared Assets/banks/sfx/<id>.mp3` | the cue NAME in the brief's `sfx: [{cue, at_words, scene}]`: the row's id, else one of its tags. Room tone is here too, as `room-tone-<setting>` (looped beds) |

## A row

`{id, tags, energy, tempo_bpm, mood, seconds, file, source, licence, status, prompt, loop}`

- `status` is `made` or `to make`. Only a `made` row with a `file` is ever
  picked. A `to make` row is the target list: the gate names it when a brief
  needs it.
- `file` is the Drive path, filled in when the row is made.
- `prompt` is what the maker sends, verbatim. `loop` is true on room tone.
- sfx rows leave `energy`, `tempo_bpm` and `mood` empty.

## How it runs

- `run.py start` resolves the brief's music and every sfx cue to a row and
  writes `{bank_id, file}` into `plan.json` beside what the brief said. A cue
  with no made row stops the run before anything is paid for, naming the row
  and the command that makes it. `--banks <folder>` points at another bank
  (the tests use `machine/fixtures/banks`).
- `python3 machine/banks.py status` — made vs to make, per bank.
- `python3 machine/make_bank.py --bank all --dry-run` — every call it would
  make (ElevenLabs Sound Effects `/v1/sound-generation`, ElevenLabs Music
  `/v1/music`, door rows in `machine/providers.json` → `direct.elevenlabs_banks`)
  and its cost. **Nothing has been made yet**; making the rows is a spend
  (≈ $__ for the seeded list at the prices read 2026-09-23) and runs only
  with `--spend` on an approved spend.

To add a row: write it into the index with `status: "to make"` and a
`prompt`, then make it.

## Ruled 2026-09-23: ElevenLabs Music is the music model

Blind test, two rounds (generic beds, then late-90s neo-soul R&B), ElevenLabs Music vs
Google Lyria 3, same prompts, levelled and shuffled (page: "Music Taste Test").
the owner: "Eleven Labs won for me for sure." Music bank rows are made on ElevenLabs Music.
The test ran on `music_v1`; the API now offers `music_v2` and `music_v2_5` (better
vocals, section-by-section composition). ElevenLabs Music also sings written lyrics
through a `composition_plan` (sections → lines, up to 30 lines of 200 characters each,
up to 5 minutes). It returns no lyric timings, so words are timed afterwards with
ElevenLabs speech-to-text, the same way the Lyria song path is timed.
