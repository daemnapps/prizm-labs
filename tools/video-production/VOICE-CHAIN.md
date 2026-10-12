# The voice chain: how a voice-over is made, as it runs today

the owner, 2026-09-23: *"I think we have a system around generating voice overs normally — can we establish that chain clearly … so we remove all hallucination and variables and can just print."*

**2026-10-03 (the owner): the voice-first workflow is retired** — on-camera lines are now said by Omni inside the clip and turned into the person's cloned voice (ElevenLabs speech-to-speech + the crisp finish); off-camera lines are text-to-speech in the cloned voice; non-word sounds (mm-hmm, uh-huh, hmm, um) are their own track at the edit. See `THE-CHAIN.md` "Voices — where they are made now". The read below still runs at `run.py start` as the storyboard's timing ruler and the line check's reference.

This page describes the chain as the code runs it on 2026-09-23. It changes nothing. Each step lists its input, the one thing it does, what it writes, and the gate after it, with file:line. The song has its own chain beside this one: `SONG-CHAIN.md`.

## The chain

| # | step | input | the one thing it does | output | gate after it |
|---|---|---|---|---|---|
| 1 | **The words** (teardown) | the transformed script + the spoken-copy rules | rewrites each section for the mouth. Prints the SPOKEN paragraph and a SETTINGS line (stability · style · speed) per section | the spice sheet's §4 THE SPOKEN SCRIPT, `video-teardown/prompts/stage-4-loop/4g-spice/stage4g-spice-v5-damon.md:192` (SETTINGS `:248–:259`) | the spoken-copy rules in the same prompt |
| 2 | **The brief** | the spice sheet | copies each SPOKEN paragraph word for word into the scene's `voice`, and its SETTINGS line into `voice_settings` | the brief's block, `stage5-ai-brief-v16-damon.md:726–727`; rules at `:932` | the production gate refuses em-dash, semicolon, parenthesis and bracket by name (`model_inputs.production_gate`) |
| 3 | **lines.json** | `plan.json` (from the brief) | one entry per scene: the scene's `voice` paragraph. Held and silent scenes are left out | `<run>/lines.json`, `machine/run.py:1390–1394` | none. A run with no words skips steps 4–6 |
| 4 | **The one read** | `lines.json`, the character's `voice.json`, the plan's per-scene `voice_settings` | sends each scene's paragraph as one chunk to ElevenLabs `text-to-speech/{voice}/with-timestamps`: the text as prepared in 4a–4c, the settings, and two pins (`apply_text_normalization: "off"`, `seed: 1`, from `model-inputs.json` voice.pins). Each chunk carries the request ids of the previous (up to 3) chunks, so it all sounds like one continuous read | `vo/chunks/NN-<scene>.mp3`; `machine/voice.py:472` (`make_track`), body at `:495`, called from `run.py:1407` | a character with no `voice_id` is a hard stop, dry run included (`voice.py:212`) |
| 4a | · **protected words** (2026-09-23) | the paragraph + `brands/<brand>/brand-identity/voice/pronunciation.json` | every brand, product, ingredient and mechanism word is swapped for its `say_as` — whole word, any case, longest first, one pass. Most rows say themselves (the voice already knows "centella"); a row is respelled only where a clip proved the plain word wrong, e.g. Brand A → `veh-loon`, bisabolol → `bi-sab-o-lol` | the text that gets sent; `machine/lexicon.py` (`apply`, `for_model`); recorded per scene in `vo/timing.json` → `said_as` | the audio gate, step 7 |
| 4b | · **numbers said as words** (2026-09-23) | the paragraph | every figure becomes the words a person says, by one table the team can read: `$29` → twenty-nine dollars, `$29.99` → twenty-nine ninety-nine, `28–40` → twenty-eight to forty, `3×` → three times, `SPF 30` → S P F thirty, `1998` → nineteen ninety-eight … | the text that gets sent; `machine/spoken_numbers.py`, rules + examples in `machine/spoken-rules.json`; recorded in `vo/timing.json` → `numbers` | the audio gate, step 7 |
| 4c | · punctuation for reading | the paragraph | handles each mark the way the doctrine's punctuation map says: a dash becomes a comma, the ellipsis stays. Never changes a word | the text that gets sent; `voice.py:329` (`for_reading`), map `:301`, fallback `:293` | none |
| 4d | · breath | each chunk | cuts every pause longer than the breath (the run's `voiceprint.json` mean, clamped 0.3–0.9 s, otherwise 0.45 s) down to the breath, then re-times the sheet | the chunk, trimmed in place; `voice.py:396` (`breath_of`), `:429` (`tighten_pauses`) | none |
| 5 | **Track and slices** | the chunks | joins them into one track, then cuts each scene's slice from that track | `vo/track.mp3`, `vo/<scene>.mp3`, `vo/timing.json` (every scene and sentence on the track's clock; each sentence keeps the script's spelling as `text` for the captions and the sent words as `said`; each scene keeps `sent_text`, `said_as`, `numbers`, `seed`), `vo/manifest.json`; `voice.py:566–590` | none |
| 6 | **Level** | each slice | brings every slice to −16 LUFS with one linear gain (volume only) | the slice, in place; `voice.py:594–616` (`level_slice`) | none |
| 7 | **The audio gate** | each slice + its line | transcribes the slice with ElevenLabs speech-to-text (scribe_v1) and checks four things: **words** (match ≥ 0.85, figures compared as their spoken words on both sides), **finished** (the line's last 3 words are heard at the end), **protected words** (every word of the brand's list in the line is heard, matched on its real spelling at ≥ 0.85 — `providers.json gates.protected_words` — and every figure is heard as its words, or as the same digits), **sound** (above −50 LUFS, below 0 dBTP). A word of the list nobody has confirmed by ear is a WARNING naming it, never a stop. Volume drift over 6 LU between scenes is a warning, not a stop | `vo/audio-check.json`, `verdicts.json[scene].voice`; `machine/audiocheck.py:66` (`check_slice`), `:82` (`check_run`), called from `run.py:1421` | **a failing slice is remade once, voice only** (`audiocheck.py`, `check_run`), with the next seed. If it still fails, the run stops before any picture is paid for |
| 8 | **Remake paths** | one scene | makes that scene's slice again with the same text (prepared the same way, 4a–4c), voice, model and settings, carrying the same earlier request ids — and seed + n for the n-th remake, so it does not ask for the take that just failed. The old slice is archived to `vo/versions/`. No other slice moves | `voice.py:619` (`remake_scene`); `machine/remake.py:131` (`order`) and `:213` (`voice`), which a clip that stops mid-line triggers | the new slice is heard again; still wrong → stop for a person |

Picture work starts after step 7. A talking clip lip-syncs to its scene's slice. `lineparity.py` then checks the finished clip against the same line (`run.py record`).

## What could change the output, and where it is pinned

| variable | pinned? | where |
|---|---|---|
| the words | **pinned.** Copied from the spice sheet, carried through the brief to `lines.json` unchanged | spice v5 §4 → brief v16 `:726` → `run.py:1390` |
| the voice | **pinned** per character | `brands/<brand>/ai-cast/<name>/voice.json` → `voice_id` (`voice.py:212`) |
| the model | **pinned**: `voice.json` `model_id`, otherwise the contract's house default (read it in `machine/model-inputs.json`) | `voice.py`; `machine/model-inputs.json` |
| the endpoint | **pinned** | `model-inputs.json:882` |
| stitching depth | **pinned** at 3 previous request ids | `model-inputs.json:960`; `voice.py:140` |
| per-scene settings | **pinned** when the brief has a SETTINGS line | brief `voice_settings` → `voice.py:357`, laid over the character's record at `:498` |
| protected words | **pinned** (2026-09-23) | `brands/<brand>/brand-identity/voice/pronunciation.json` → swapped by `lexicon.py` before the call; heard back by the audio gate. Why not an ElevenLabs pronunciation dictionary: its phoneme (IPA) rules only work on `eleven_flash_v2` and `eleven_v3`, not `eleven_multilingual_v2`; its alias rules do, but they live on the account where the team cannot see them, and the music door takes none ([doc](https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries)). Our swap works on every model, the song included, and sits in a file anyone can read |
| how a number is said | **pinned** (2026-09-23) | `spoken_numbers.py` + `spoken-rules.json`, and `apply_text_normalization: "off"` so ElevenLabs does not guess on top (`model-inputs.json` voice.pins; allowed values `auto · on · off`, default `auto` — [doc](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)) |
| seed | **pinned** (2026-09-23) at 1; a remake sends 1 + n | `model-inputs.json` voice.pins. The API calls it "best effort to sample deterministically" — same seed and parameters should return the same take, not guaranteed |
| punctuation | **pinned** | `components/marketing-doctrine/spoken.json` → `punctuation_map` (model `eleven_multilingual_v2`), fallback rows `voice.py:293` |
| breath | **pinned** at 0.45 s in practice | `voice.py:396`. Nothing writes `voiceprint.json` into a run and `spoken.json` has no `breath` key, so the fallback always applies |
| level | **pinned** −16 LUFS, −1.5 dBTP, linear | `voice.py:594` |
| gate thresholds | **pinned** | 0.85 match (`providers.json gates.line_parity`), last 3 words within 4 (`lineparity.py:128`), −50 LUFS / 0 dBTP (`audiocheck.py:39`) |

## Open items: real sources of variance that are not pinned

1. **The character's own voice settings are never sent.** June's `voice.json` keeps the owner's ruled settings ("vo4a is way better": stability 0.45, similarity 0.8, style 0.3, speaker boost off, speed 1.0) nested under a `settings` key. `voice_settings_of` (`voice.py:208`) only reads top-level keys, so it sends nothing. A scene with no brief settings is read with whatever the ElevenLabs account holds for that voice, which can be edited in the app at any time. The fix is one line: also read `rec["settings"]`. It is not applied here because it would change how future reads sound. the owner rules.
2. ~~No `seed` is sent.~~ **Closed 2026-09-23**: seed 1 on every chunk, seed + n on the n-th remake. Whether ElevenLabs returns the same audio for the same seed has not been measured (the API says best effort).
3. ~~`apply_text_normalization` is not pinned.~~ **Closed 2026-09-23**: pinned `off`; our own number rules say every figure first (steps 4a–4b).
4. **Previous request ids expire after 2 hours** (`model-inputs.json`). A remake made more than 2 hours after the read cannot be stitched and restarts the read's tone.
5. **The model decides whether the read is stitched.** `voice.py`'s `stitches()` says which models stitch; a `model_id` in `voice.json` or the contract's default that does not stitch reads each line on its own.
6. **Breath is a fallback, not a measurement** (see the table): the creators' measured pause never reaches the run.

## Protected words and numbers — proof, 2026-09-23

the owner: *"we need to get phonetic spelling for numbers when spoken, as well as make sure brand names, ingredients, mechanisms are never mispronounced through AI."*

- **The lists:** `brands/<brand>/brand-identity/voice/pronunciation.json` (80 words: the brand, every product, every ingredient on both scrubs' labels and the cream's heroes, the mechanisms) and `brands/<brand>/brand-identity/voice/pronunciation.json` (48). Each brand has a plain-English `voice/README.md` beside it. Brand A = veh-loon and Brand B = dudes are confirmed by the owner's ear; the rest wait for his ear, and the gate warns when one is used.
- **Hear them:** `python3 machine/say_it.py <brand>` (dry run) · `--spend` makes one short clip per word in the cast voice, exactly as a run would send it, with a page to play them.
- **The proof** (`runs/video-production/<brand>/<run>`, June's voice, ~380 characters + 26 short transcriptions, well under $__): brand + 4 products + 5 ingredients + 3 number lines. What it taught:
  1. **Capitalised respellings garble** on `eleven_multilingual_v2`: `sen-TEL-uh` → heard "Mohrenko", `nye-uh-SIN-uh-mide` → "New synonym ID", `bih-SAB-uh-lol` → "We serve Ulnall" (kept in `first-pass/`).
  2. **The voice already knows dictionary ingredients**: centella, chamomile, niacinamide, turmeric sent as spelled were all heard 1.0 (`variants/`). So a word goes as spelled unless a clip proves it wrong; each row keeps a lower-case `respelling` as the backup.
  3. **Bisabolol** as spelled came back "Bisayabolol" (an extra syllable); `bi-sab-o-lol` came back "Bisabolol" — the one ingredient respelled.
  4. **Numbers**: "$29" sent as "twenty-nine dollars" was written back "$29"; "seven thirty" and "twenty-eight to forty" came back as words — both are heard by the gate.
  5. **The gate's threshold** (match on the real spelling): right reads scored 0.857 ("Veluna"), 0.895, 1.0; wrong reads 0.30–0.70 and one 0.80 — so 0.85. The brand name's margin is thin; watch it on the first runs.
