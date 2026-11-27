---
name: remake-clip
description: Surgically remake one scene of a video production run when something in it came out wrong. Today that is mostly a talking clip that stops before its line finishes (the words check says CUT_OFF, or the edit found it). Finds WHICH element broke (the voice slice, a frame, or the clip itself), remakes only that, then rebuilds what depends on it from the same original inputs, and checks the new take finished its line. Use whenever a run has a remake order on it, the edit says a clip was sent back, or someone says "remake scene 5", "that clip cuts her off", "regenerate the cut-off clip", "just fix the audio on scene 3", "same frames, new voice", "redo the clip, same everything, just let it finish".
---

# Remake a clip, surgically

> **Activates component:** `components/video-production` — regenerates one clip of a run.


External dependencies: `components/video-production/machine/remake.py` (the order, the voice step, the record), `machine/voice.py` (`remake_scene`, one scene's slice of the read), `machine/lineparity.py` (the words check, including "did the line finish"), `.claude/skills/frame-edit` (a frame changed by ONE delta), the run's own `batches/`, `media/`, `vo/`, `verdicts.json`, and the Higgsfield connector (`media_upload`, `generate_video`, `jobs_wait`).

the owner, 2026-09-23: *"we need to be conscious of the element that needs to be regenerated. So if it's just the audio then we need to regen the audio, then if the person is speaking we also need to take the same frames used in the original generation and just change the audio track. This is what I mean by surgical edits"*. Also: *"regenerate the clip properly without any slop and just do exactly what's needed."*

## A scene is three elements. Only the broken one is remade.

| Broken element | Remade | Then rebuilt from the SAME originals | Kept exactly |
|---|---|---|---|
| **voice**: the slice itself stops short or says it wrong | the scene's voice slice. Same text, voice and settings, stitched on the same earlier part of the read | the clip, from the **same frames** with the **new slice** | prompt, both frames, model, every setting |
| **frame**: the picture is wrong | the frame, with ONE change (frame-edit) | the clip, from the **new frame** with the **same slice** | prompt, voice slice, model, every setting |
| **clip**: the voice and frames are fine and the clip went wrong | the clip only | nothing | prompt, both frames, voice slice, model, every setting |

For a cut-off clip, `order` finds the element itself. It transcribes the voice slice first. If the slice stops short, the voice is the broken element; if the slice is whole, the clip is.

## The steps. Do them in order and do nothing else.

1. **Read or write the order.**
   ```
   python3 components/video-production/machine/remake.py status <run>
   python3 components/video-production/machine/remake.py order <run> --scene <id> --why cut-off
   python3 components/video-production/machine/remake.py order <run> --scene <id> --why wrong-frame --change "<the ONE change>"
   ```
   The order (`<run>/remakes/<scene>-r<N>.json`) names the element, the steps in order, what is kept, and the exact clip `request` with its `medias` as files. A `STOP` means stop: the scene needs splitting, or it has had two tries. Tell the owner in one line and submit nothing.

2. **Do the element's own step, if it has one.**
   - voice: `python3 components/video-production/machine/remake.py voice <run> --scene <id>`. This remakes the slice, checks the new slice finishes its line, and re-times the clip request to it.
   - frame: run the `frame-edit` skill with exactly the order's one change. Then point the order's frame media at the new take.

3. **Make the clip exactly as the order says.**
   - Upload each file in `medias` with `media_upload`, keeping its role.
   - Call `generate_video` on the order's door model (`seedance_2_5` today, per `providers.json`) with the `request` fields as they are.
   - Wait with `jobs_wait` and download the clip.

4. **File it:**
   ```
   python3 components/video-production/machine/remake.py record <run> --scene <id> --file <downloaded.mp4> --job <job id>
   ```
   The old take is archived, never overwritten. The new take is checked, and the line must FINISH.

5. **Report in one line per scene.** Say what broke, which element was remade, what was kept, and what the new take said. End with `FIXED`, `STILL CUT OFF` or `FLAGGED`.

## No slop. These are the whole job.

- **Only the named element is remade.** Never regenerate the frames to fix a voice, and never re-voice to fix a frame.
- **The prompt is sent word for word.** Don't tidy it, improve it or add a line. The order already carries the one fix.
- **The line is never rewritten or shortened to fit.** If a clip can't hold the line, `order` says STOP (split the scene).
- **Two tries, then a person.** A third try on the same composition is never made (`formats/RUN-PROTOCOL.md`).
- **The words check always decides.** Never mark a take fixed by watching it.
- **A clip made outside the machine** has no original request to remake from, and `order` says so. It goes back through `video-production`.

## What comes back

The new take is at `<run>/media/<scene>.mp4`, and anything replaced is in `media/versions/` or `vo/versions/`. The verdict is in `verdicts.json`, and the order's steps are all marked. The edit picks up the new take the next time it runs.

Reply with the one-line result per scene. No paths, no commands.
