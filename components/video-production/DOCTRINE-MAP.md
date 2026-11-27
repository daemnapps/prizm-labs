# Video doctrine map: what exists, and does it reach the clip?

Written 2026-10-26, read-only trace of the code and prompts. Nothing was run; "reaches the clip" means the words are built into the Seedance prompt by `machine/seedance_prompt.py`, read from the code, not from a finished clip.

## 30-second summary

1. **A lot exists:** 29 creative dials, 9 guards, 4 presets, 12 emotions, 43 techniques, the 7 video-spice layers, a 40-row realism index, camera and cutting rules, format and style banks, and the delivery and mood doctrine.
2. **What is connected:** the shot's `face`, `gestures`, camera move, hand-off, spice level (layers), the realism rows and the style sentence all reach the clip prompt. The "absurd, hyper-specific" rule (V24) is written into the brief prompt.
3. **Gap 1, the biggest:** the creative controls (dials, guards, emotions, never-sterile floor) were ruled into every video on 2026-10-23 (V33), but **no video prompt carries them**. Copy and pictures do; video does not. Fix: bind them into the video writing passes and have the brief turn them into face, gestures and camera.
4. **Gap 2:** the emotion word is deliberately never sent to the clip, only what the face and hands visibly do. So emotion reaches the clip only if the brief writes a good `face` and `gestures` for every shot, and nothing checks that. Fix: make those two fields required and filled from the emotion bank's video line.
5. **Gap 3:** the person's own gestures and life marks come from a `character.md` section I could not find in this checkout, and the realism index is 40 rows, all still draft. If the character file is missing, spice layers 2 and 3 quietly send nothing. Fix: a loud warning when a level needs marks and gestures and the file has none.
6. **Also stops at the brief:** humor, register, pacing and absurdity as dials. Only the voice read's delivery tag uses the delivery dials; the clip prompt does not.

## The path a piece of doctrine takes

Teardown (reads the swipe) -> writing 3 injection -> 4 hooks and 4g spice (sets spice level, spice sheet) -> 5 brief (one row per scene, shots with `face`, `emotion`, `gestures`, `camera_move`, `hands_off`) -> clip call plan -> **the Seedance prompt** (assets, summary, timeline, constants).

The last step reads only: the shot's `face` and `gestures` (`seedance_prompt.py:154-159`), camera move and hand-offs (`:30-51`, `:244-257`), `ends_on` (`:268-276`), the style (`:201-205`), two of the person's own gestures (`:162-170`, `:218-220`), marks (`:295-296`), up to 4 realism rows (`:287-294`). Nothing else from the brief gets in.

## The table

| Doctrine piece | Where it lives | Stage that uses it | Reaches the clip? | Gap, one plain line |
|---|---|---|---|---|
| Creative dials (29), guards (9), presets (4), never-sterile floor | `components/creative-controls/controls.json`; rendered to `slices/controls.md` as `{creative_controls}` | Ruled for video by V33 (`VIDEO-RULINGS.md:49`) | **Not bound anywhere in video.** Zero hits in video-teardown, video-writing, video-production. Bound in copywriter (`copy_writer.py:1080,1138`, `copy_set.py:294`) and image-teardown (`tools/run.py:427-432`) | Ruled, built, never plugged into a video prompt. |
| 12 emotions (each has a `video` line, e.g. disgust = "the close-up, the wince") | `controls.json` `emotions` | Meant for writing and brief | **Not bound anywhere in video** | The bank that says how each feeling looks on camera is never shown to the brief writer. |
| 43 techniques (incl. match-cut, jump-cut, smash-cut, deadpan, understatement) | `controls.json` `techniques`; copy techniques also in `marketing-doctrine/slices/techniques.md` | `{techniques}` in teardown 1c, injection, 4g, expansion | Stops at the brief (the doctrine copy slice only; the creative-controls set is unbound) | Techniques shape the script, not the shot; no step turns them into camera or acting. |
| Dial: absurdity, humor, edge, cringe, uncanny, cutting rate, shot scale, eye contact | `controls.json` `dials` | Nowhere in video (see row 1) | No | Video-only dials exist (cutting rate, shot scale, eye contact) with no video prompt that sets them. |
| Absurd + hyper-specific rule (V24) | Written in the brief prompt `video-writing/prompts/v2/stage5-ai-brief-v6-owner.md:423` | Stage 5 brief | Only through what the brief puts in the scene text (`happens`, beats) | Real and live, but it is a prose rule inside one prompt, not a dial; nothing measures it. |
| Taste and delivery dials (humor kind, style, register, pacing) | `marketing-doctrine/slices/delivery.md`, `{delivery}` | Teardown 1c reads it; 4g spice fills it; brief copies it into each scene's `delivery` | Only as the voice read's delivery tag (ElevenLabs). Not in the Seedance prompt | Humor, register and pacing end at the voice; the face and body never get them. |
| Mood (rhythm, register) | `marketing-doctrine/slices/mood.md`, `{mood}` | Teardown 1c, 4g spice (the slice names 4d and 5 as owners; I found it bound only in 1c and 4g) | No | Tone shifts are read and written, never turned into a shot instruction. |
| Emotion per scene and per shot (`emotion`) | Teardown slot (`stage1-teardown-v16:359`); brief shot field (`stage5-ai-brief-v6:770-775, 1093`) | Teardown, 4g, 5 brief | **No, on purpose**: label not sent (`seedance_prompt.py:154-156`; `SEEDANCE-INPUTS.md` table) | Safe against over-acting, but the brief prompt itself still says emotion goes "to the motion model" (`stage5-ai-brief-v6:284`); out of date. |
| Face and gestures per shot | Brief shot fields `face`, `gestures` (`stage5-ai-brief-v6:1092-1094`) | 5 brief -> clip | **Yes, as "face and hands"** (`seedance_prompt.py:154-159, 248-251`) | The only real carrier of emotion; nothing checks that the brief filled them well. |
| Spice layer 1, emotion travels | `VIDEO-SPICE.md`; per-shot `emotion`, `face`, `delivery` | 4g (sets level), 5 | Only as face and gestures | Same as the row above. |
| Spice layer 2, body language (person's own gestures) | `VIDEO-SPICE.md`; the character's `character.md` via `clips_run.life_marks` (`:189-205`) | Clip call (level 3 only) | Yes at level 3, two habits, only if the shot names no gestures (`seedance_prompt.py:218-220`) | Depends on a `character.md` section I could not find in this checkout. |
| Spice layer 3, life marks | Same | Pictures and clip (level 2 and up) | Yes: "Marks kept exactly as in Image 1" (`:295-296`) | Same file dependency; empty file means a silent nothing. |
| Spice layer 4, the senses | Realism rows, family `sense`; a `sense` beat in the script | Level 3 | Yes, as realism rows (`:290-291`), but rows are capped at 4 in total (`:294`) | Sense rows can be crowded out by hand, body and face rows. |
| Spice layers 5 and 6, rhythm and continuity | `VIDEO-SPICE.md`; `hands_off`, `ends_on`; windows of at least 2.5 s | Brief, clip, edit | Continuity yes (`:268-276`); rhythm is the 2.5 s window rule, the cuts themselves are in the edit | Not gated by level in the clip. |
| Spice layer 7, camera and cutting (V10) | Brief shot fields `camera_move`, `hands_off`; `CAMERA`, `HAND`, `END` (`seedance_prompt.py:30-51`) | Brief -> clip | **Yes** (camera phrase and hand-off sentences) | Always sent, even below level 3, so the level table does not fully match the code. |
| Spice level 1 to 3 | `VIDEO-SPICE.md` Levels table; read by `clips_run.py:242-264`; set on the call at `:1070-1071`; piece level from `plan.json` (`:267`) | 4g sets it; clip applies it | **Yes**, gates layers 2, 3, 4 | No level on the piece means every layer is on. |
| Realism index (40 rows: 21 production, 12 writing, 7 editing; 8 formats; all `draft`) | `video-production/spice/realism-index.json`, `REALISM-INDEX.md` | Writing rows to 4g and 5 (`{realism_index}`); production rows to the clip (`clips_run.py:276-296`) | Production rows yes (max 4, by format and level); writing rows stop at the brief; editing rows not drawn yet | A shot with no matching format gets no rows at all; every row is still draft. |
| VIDEO-RULINGS V8, V9, V10 (acting reaches the camera, spice, cutting) | `VIDEO-RULINGS.md:19-21` | All stages | Yes, via the rows above | V8 says emotion goes into the take prompt; V42/`seedance_prompt.py` since removed that (text not updated). |
| VIDEO-RULINGS V33, the controls in every video | `VIDEO-RULINGS.md:49` (also a second V33 about pictures at `:44`; two rulings share the number) | Writing stages | **No** (see row 1) | Ruling says it is wired; the code says it is not. |
| SHOT-ROUTES.md (real / swap / AI) | `SHOT-ROUTES.md`; `machine/shot_route.py` | Brief and budget | Not about feeling; it picks how a shot is made | Motion-first shots go to swap, so acting doctrine only applies to the AI route. |
| Format bank, playbooks, show formats | `formats/bank.json`, `formats/playbooks/*.md`, `show-formats.json` | Production stages 0 | Only the format's realism format and style sentence | Per-format performance notes end at the brief. |
| Style bank | `styles/bank.json` | Stage v1 style formula | **Yes**, one style sentence (`seedance_prompt.py:201-205`) | "Handheld" is stripped when the camera is a propped phone. |
| Cast files: own gestures, life marks | `character.md` "Life marks and gestures" (read at `clips_run.py:189`) | Clip, pictures | Yes if present | I found none in `brands/` or `runs/ai-elements/` here (3 retired ones only); likely on the Drive. Not verified. |
| Teardown reads: mood, delivery, emotion per scene, frame map | `video-teardown/prompts/v2/stage1c-doctrine-v5-owner.md:10-12`; `stage1-teardown-v16:359`; `stage-1f-frame-map` | Teardown | Stops at the brief | The swipe's *dial levels* (how absurd, how edgy) are not read at teardown for video, unlike copy and pictures. |
| Clip judge | `machine/clip_judge.py:7`; prompt `clip-judge-v3` | After the clip | Checks "the acting" against the prompt as sent | Judges the acting that was asked for; never the creative bar. |

## Honest limits

- I read code and prompts; I did not open a finished clip prompt from a real run, so "yes" means the code builds it, not that a given run's brief filled the field.
- I did not check the backup clip prompt (`machine/kling_prompt.py`) beyond noting it uses the same scene fields.
- I did not check `stage-check`'s never-sterile test (`stage_check.py:226-233`) against a video run; it reads `03-injection.md`, the image run's file name.
- Hits for `creative_controls` were searched across `components/` (runs excluded), `.claude`, `platform` and `new-workflow-design`; none are in a video prompt or video machine.
- `SEEDANCE-INPUTS.md` still says the dials number 20; `controls.json` has 29.

## What to build to close the three gaps

1. **Plug the controls in.** Bind `{creative_controls}` into the video writing passes (injection, hooks, spice, brief) the way image-teardown does, using `writing_v2.run_inputs`. Add the brief step "dial effects become face, gestures, camera, ends_on" so the controls reach the only fields the clip reads.
2. **Make emotion visible.** Require non-empty `face` and `gestures` on every shot that has an emotion, filled from the emotion bank's `video` line; add a brief gate that refuses a thin shot.
3. **Make the person's file loud.** At level 2 or 3, warn when a character has no marks or gestures; list which cast files carry the section; promote the realism rows that work out of draft.
