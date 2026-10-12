# The song chain: how a sung piece's song is printed

the owner, 2026-09-23: *"if we trigger a song to be made, we have a specific protocol / chain to do that as well, so we remove all hallucination and variables and can just print."* The model was ruled the same day, after a blind test against Lyria 3: *"Eleven Labs won for me for sure."* The song is ElevenLabs Music `music_v2_5` (`machine/providers.json` → `doors.audio`, with Lyria kept as the alternate).

It sits beside the voice chain (`VOICE-CHAIN.md`). The script drives the video. On a sung piece the song is the voice, so it is made and heard before any picture is paid for.

## The chain

| # | step | input | the one thing it does | output | gate after it |
|---|---|---|---|---|---|
| 1 | **The words** (brief v16) | the lyrics in WHAT TO SAY | puts each lyric line on the scene it plays over as `lyrics` (and `voice: ""`), then writes the `song` block: `{style_id, vocal, bpm?, sections: [{name, scene, seconds, lines}]}`, with every line copied from the scenes' lyrics | the brief's block; `video-teardown/prompts/stage-5-brief/ai-lane/stage5-ai-brief-v16-damon.md:728` (`lyrics`), `:1582` (`song`), `:1596` (rules) | — |
| 2 | **Carried to the plan** | the brief | `song` goes into `plan.json` untouched, and each scene keeps its `lyrics` | `machine/run.py:308` (`PIECE_ELEMENTS`), `machine/scenes.py:338` | — |
| 3 | **The words check** | `song` + the scenes' lyrics | every sung line must be a script line, and every script line must be sung. Case and punctuation are ignored; the words are not | nothing, or a refusal naming the line; `machine/song.py:155` (`check_words`) | **refused by name**, dry run included |
| 4 | **The style** | `song.style_id` | looks up ONE row of `banks/music-styles/index.json`. The row must be `approved` (rule 6; `ruled` until 2026-10-07), its vocal must match the brief's, and it must have a line for each section name | `song.py:185` (`style_row`) | an unknown id, a draft row, a vocal mismatch, or an unknown section is **refused by name** |
| 5 | **The request** | block + row + door | builds it mechanically: one chunk per section, text = the section's lines **as they are sung** — each line through the same step the voice takes (`lexicon.for_model`: the brand's protected words swapped for their `say_as`, every figure in words by `spoken-rules.json`; 2026-09-23) — joined with newlines, `duration_ms` = seconds × 1000, positive styles = the row's + "`<bpm>` BPM" + the row's line for that section, negative styles = the row's. Model, url, format, seed and adherence come from `providers.json direct.elevenlabs_song` | `<run>/song/request.json` (its `said` lists every line that was changed and how; the brief's lines are never touched), written on `--dry-run` too; `song.py` (`sent_block`, `build_plan`, `build_request`) | the door's limits (3–120 s a section, ≤30 lines, ≤200 characters a line, ≤10 min) are refused by name |
| 6 | **The call** | the request | POST `https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192`, `model_id: music_v2_5`, `seed: 1` | `<run>/song/song.mp3`, never overwritten: a remake first moves the old take to `song/versions/song-vN.mp3`; ledger row; `song.py:274`, `:448` | — |
| 7 | **The song gate** | song.mp3 + the sections | transcribes the song with ElevenLabs speech-to-text (scribe_v1, word times). Every line of every section must be heard in order, each at a match of 0.75 or more (`providers.json gates.song_lines`), and the last line must finish (`lineparity.ending_heard`). `[bracketed]` sound tags are not words, and every figure is compared as its spoken words on both sides (`spoken_numbers`). **Protected words (2026-09-23):** every word of the brand's list in the lyrics is heard (real spelling, ≥ 0.85, `gates.protected_words`) and every figure heard as its words; an unconfirmed word is a warning | `song/transcript.json`, `verdicts.json[SONG].song`; `song.py:316` (`transcribe`), `:342` (`gate`) | **fails → made ONCE more** (the same request with seed + 1, written to `song/request-remake.json`). Still failing, the run **stops**, naming the missing line |
| 8 | **Timing** | the transcript | puts every line's start and end, and its words, on the song's clock. Each section gets its heard window and its planned window | `song/timing.json`, for captions and cuts; `song.py:478` | — |
| 9 | **Level** | song.mp3 | levels a copy to −14 LUFS with one linear gain. The original is never touched | `song/song-14lufs.mp3`; `song.py:399` | — |

**Wiring.** `run.py start` runs this after the voice and its audio gate, and before any frame. It only runs when the plan's `song` has `sections` and the song door is song.py's own (`run.py:1428–1450`, `song.door_closed`). By hand: `python3 machine/song.py <run> [--dry-run]`. A legacy song block with only a `prompt` still goes to the Lyria alternate on the machine hand (`run.py:808`, `:1103`).

## What is pinned

How brand words and figures are sung (the brand's `voice/pronunciation.json` and `spoken-rules.json`, applied to the text sent — the music door has no text-normalisation switch and takes no pronunciation dictionary, so the text itself is the only lever) · the words (the brief's lines only, checked both ways) · the sound (one ruled style row, no free text) · model `music_v2_5`, url, `mp3_44100_192`, `context_adherence: high`, `seed: 1` (`providers.json direct.elevenlabs_song`) · section lengths (from the brief) · gate threshold 0.75 · the remake rule (once, seed + 1) · level −14 LUFS.

## Still variable / open

1. **The model's own interpretation.** A fixed seed makes the request identical every time. Whether ElevenLabs returns identical audio for the same seed has not been measured.
2. **The brief writer cannot yet see the style ids.** No `{music_styles}` variable is bound into the brief stage, because the binding lives in `video-teardown/machine/extra-stages.json`, outside this lane. Until it is bound, the writer takes the id from the production route or the injection, or writes `[UNFILLED]`, and production stops and lists the rows.
3. **Only one style is ruled** (`neo-soul-90s`, from the Nova proof). Four neutral rows are `draft` and refused until the owner hears and rules them.
4. **Sung clips and their audio.** timing.json gives each section its window, and the storyboard is clocked from it — one section per sung line (`storyboard_plan.py` `build_song`, 2026-10-10; the song-ad rulings are in `formats/song-ad.md`). Slicing the song per scene for the motion door, and lip-sync on sung clips, is not wired here yet.

## Proof, 2026-09-23

One real call, from `machine/fixtures/song/nova-song-plan.json` (the Nova lyrics, style `neo-soul-90s`): `runs/video-production/<brand>/<run>`. The gate passed first take: all 6 lines at match 1.0, in order, the last line finished. Levelled copy at −14.1 LUFS. $__. The request it sent matches the earlier hand-made proof plan chunk for chunk (plus the pinned seed and adherence).
