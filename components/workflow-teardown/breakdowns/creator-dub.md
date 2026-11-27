# Creator Dub

Dubs a creator's own video into other languages with the speakers' lips synced: per language the same video with new audio and lip sync, an audio track, styled per-speaker captions, and a translated title and description (YouTube: plus a Studio guide). Default 9 languages: German, Spanish, French, Italian, Portuguese, Japanese, Korean, Turkish, Arabic (plus English when the source is not English).
Source: `creator-dub/SKILL.md`, `creator-dub/references/{languages,qa,translation_brief,youtube}.md`, `creator-dub/scripts/*`

## Inputs it needs
- Voice stems, one per on-camera speaker, plus music/effects beds and any clip-dialogue stem, all full length from 0:00. A final mix alone is accepted only as a lower-quality fallback (voice split).
- The published video file (picture for the synced versions and the check against the stems).
- Original language, target languages if not the default, the script if any, terms (names, products, mishear risks), exact title and description, optional brand colour.
- Your yes on cost: every language is a paid dub plus a paid lip-sync; adding languages or re-dubbing a whole language needs a new OK.

## Steps in order
1. Map stems (`prepare_stems.py`) and check them against the published video (`patch_stems.py`); estimate reverb room if a reverb return exists.
2. Transcribe (`transcribe.py`, large-v3-turbo) and fix spelling, speakers, deleted lyrics and line length; `build_lines.py`.
3. Write the translation brief, then per language `translations_<code>.json` and `youtube_meta_<code>.json`; `budget.py` and `validate_meta.py` must pass.
4. Upload the voice once; `dub_job.py request` per language; submit `audio_dubbing`; estimate and tell the total first; wait for all jobs in the same turn.
5. QA each language (`qa_lang.sh`), read flags with `references/qa.md`, reword shorter and re-dub only a window, splice the better take.
6. Mix each language over the original stems (within 0.2 LU of the master), encode m4a, build `.ytt`/`.srt` captions.
7. Lip-sync each language with `sync_so` over the whole video (one segment per dubbed line), restore the original frames, put the language mix back on the picture.
8. Upload the videos, zip captions + metadata + `HOW_TO_UPLOAD.md`, report per language.

## Prompt blocks, word for word
**Translation brief template (filled once per video)**  
`creator-dub/references/translation_brief.md`

````
# Translation brief: "<video title>"

<2–4 sentences: what the video is, who hosts it (and any co-host), the creator's tone, what is being made or shown, the story of
any film or clip inside it, and who each character is (role, relationship).>

## Input

`lines.json` holds all lines in time order. Each line has:

- `key`;
- `speaker`;
- `dubbed`: true means it's voiced in your language; false means subtitles only, and the clip audio stays in the original language;
- `seconds`: the original length;
- `text`: the original line.

## Output

1. `translations_<code>.json`: one JSON object `{"<key>": "<translation>"}` covering **every key** with non-empty text. UTF-8, `ensure_ascii=False`.
2. `youtube_meta_<code>.json`: `{"title": ..., "description": ...}`, translated from `youtube_orig.json`:
   - keep every URL, emoji and timestamp;
   - translate the chapter names;
   - title ≤ 100 characters.

## This episode

- **Jokes / double meanings:** <line → what it means and how it must land>
- **Repeated lines** (translate identically every time): <list>
- **Insults / slang:** <list>
- **Names:** <every person/character and how it is written per script, see references/languages.md>
- **Products and on-screen labels:** <anything beyond the standard list that must stay in Latin script>

## Rules

Follow `references/languages.md` (read it with `get_workflow_bundle_file`) for your languages: tone, address, names, numbers, length caps.

## Check before you finish

Run from the episode's `multi/` folder:

```
python3 $HF_WORKFLOWS/creator-dub/scripts/budget.py segments_final.json translations_<code>.json --lang <code> --keys dubbed_keys.json
python3 $HF_WORKFLOWS/creator-dub/scripts/validate_meta.py youtube_orig.json <a file with {"<code>": meta}>
```

Fix every flagged line, or leave a flag only when it can't get shorter without losing meaning (a name or a number).

Report back:

- the budget summary line;
- the lines you shortened;
- any flags you left and why;
- the title.
````

**Shared translation rules (all languages)**  
`creator-dub/references/languages.md`

```
## Shared rules

- Translate the meaning, not word for word, in the creator's tone (the brief describes it). Clip/film characters keep their own voice. Subtitle-only lines (clips that stay in the original language) are translated too.
- Keep jokes, double meanings and insults working (the episode brief lists them).
- Repeated film lines must be translated identically every time.
- **Product and channel names stay in Latin script exactly:** everything in the glossary's `keep_latin`, plus whatever the brief adds.
- **On-screen labels** (buttons like "Generate") may stay in English when the viewer sees them on screen.
- **Numbers:** keep 480p/1080p/2.5 as digits; spell units the native way; "21 by 9" → 21:9 in the local form.
- **Length:** dubbed lines fit the original timing. Check them with `budget.py` (cap = characters ÷ original characters; lines under 2 s get 0.87 × cap). Cut filler until no line is flagged. Subtitle-only lines have no hard cap but stay concise.
- **No quotation marks** inside lines unless the language needs them (Japanese 「」 is fine).
- **Title/description:** same meaning as the original. A title should read like a native creator wrote it, keeping its hook and its length close to the original. Keep every URL, emoji and timestamp; translate chapter names; title ≤ 100 characters; no < or >.


```

**Dubbing request per language**  
`creator-dub/SKILL.md`

```
python3 $SK/dub_job.py request <code> <target_language> <orig>
```

**audio_dubbing submit**  
`creator-dub/SKILL.md`

```
{"params": {"model": "audio_dubbing", "prompt": "<video> – <Language> dub",
            "medias": [{"role": "audio", "value": "<voice media_id>"}],
            ...every key of req_<code>_r1.json}}
```

**Lip-sync submit (sync_so)**  
`creator-dub/SKILL.md`

```
{"params": {"model": "sync_so", "sync_mode": "cut_off",
            "medias": [{"role": "input_video", "value": "<video media_id>"}, {"role": "input_audio", "value": "<voice media_id>"}],
            "segments": [{"start_time": 1.2, "end_time": 4.9, "active_speaker_detection": {"auto_detect": true}}, ...]}}
```

**Mix and caption commands**  
`creator-dub/SKILL.md`

```
mkdir -p deliver out
python3 $SK/mix.py ../stems_v2 "" dub_<code>_<round>.wav host_segments.json ../reverb_ir.npy|none "deliver/<video> - <CODE>.wav" --voices voices.json --bus-gain <bus_gain_db>
ffmpeg -v error -y -i "deliver/<video> - <CODE>.wav" -c:a aac -b:a 256k "out/<video> - <CODE>.m4a"
python3 $SK/srt.py segments_final.json words_by_segment.json "out/<video> - <ORIG>.ytt" [--first <co-host id>] [--palette "#hex"]
python3 $SK/srt.py segments_final.json words_by_segment.json "out/<video> - <CODE>.ytt" --text translations_<code>.json --lang <code> [--first ...] [--palette ...]
```

**Window re-dub commands (QA fix)**  
`creator-dub/references/qa.md`

````
2. **Dub the window.** Collect the bad lines of one language that are close together into one window:
   ```
   python3 $SK/dub_job.py request <code> <tag> <source> --round r2 --keys s064 s065
   ```
   It writes `req_<code>_r2.json` (only the lines in the window, shifted to start at 0) and `win_<code>_r2.wav` (that stretch of the voice, at least 30 s so the voice still clones). Upload the WAV, run `audio_dubbing` with the request, download the result, then put it back on the timeline:
   ```
   python3 $SK/dub_job.py place <code> r2 dubwin_<code>_r2.wav
   ```
   which writes the full-length `dub_<code>_r2.wav` (silent outside the window).
3. **Check the re-render.** Run `bash $SK/qa_lang.sh r2 <code>` and compare the flags on the window's lines only (everything outside the window is silent in r2 and gets flagged; ignore it).
4. **Splice the better takes:** `assemble.py host_segments.json choices.json dub_<code>_r3.wav` with `{"renders": {"r1": "dub_<code>_r1.wav", "r2": "dub_<code>_r2.wav"}, "base": "r1", "swaps": [[["s064","s065"], "r2"]]}`.
   - It only splices where both renders are silent. If the only clean splice points bracket the whole window, swap the whole window's lines.
   - Pick the take with clean words over the one with better timing (narration 1–2 s late over B-roll is fine; a garbled word is not).

````

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Dub each language from our transcript and translations (voice only) | `audio_dubbing` (ElevenLabs Dubbing v2) | `source_language`, `target_language`, `keyterms`, `transcript`, `translations`, voice stem as audio media |
| Lip-sync each language over the video | `sync_so` | `sync_mode:cut_off`, one segment per dubbed line (auto speaker detection) |
| Voice/background split (fallback only) | `separate_stems` tool | `mode:two` |
| Spelling, translation, brief, metadata | none (Claude on the plan) | subagents for 3 languages each if available |
| Transcription, mix, QA, captions, zip | none (sandbox scripts, ffmpeg, faster-whisper) | free |

## Checks and gates
- Asks before starting because of cost; stops if the transcript/translation dubbing mode is rejected (needs ElevenLabs Enterprise).
- `budget.py` length caps per language (1.15 most Latin, ja 0.55, ko 0.75, ar 0.95); `validate_meta.py` keeps URLs, emoji, timestamps, title at most 100 characters.
- QA flags: cut-off endings, garbled words, babble, dub speech over film dialogue; brand-name mismatches and about 1 s early starts are accepted.
- Subtitle-only lines for clip audio stay in the original language; the mix must keep music bit-identical (YouTube rejects changed music).
- Frames restored after Sync so cuts stay where they were; captions stay separate files unless asked; no free regeneration, only paid window re-dubs.
- Not for voice swapping (`voice_change`) or localizing an ad into new footage (ad-multiplier).

## Price pattern
Not quoted in `_prices.md`. The workflow quotes first with `estimate_audio_cost` on one language and tells the total. Billing: dub by the voice track's length, lip-sync by the video's length, per language, plus short window re-dubs. Nine languages means nine of each.

## Cheap swap
- Lip-sync (`sync_so`, per language): skip it for audio-only YouTube tracks; keep it only for the Reels/TikToks you post as video. Saves the whole sync bill.
- Fewer languages: dub the top 2 to 3 markets first (each language is an independent paid job).
- Stem split: local Demucs on this Mac, free, instead of the paid `separate_stems` call.
- Transcription: local Whisper stt (the sandbox already uses faster-whisper, free).
- Translation, brief, metadata, QA reading: Claude on the plan, free.
- Draft dub: Kokoro tts locally (free) for the languages it covers, as a listen-test before paying for ElevenLabs Dubbing.
- No picture model is used, so the `wan3_0`, `gemini_omni_flash_1_2` and 2k picture swaps do not apply.
