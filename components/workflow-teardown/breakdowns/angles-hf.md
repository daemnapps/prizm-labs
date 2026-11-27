# Multi-Camera Angles (/angles)

Re-shoots a user's one-take clip as a bold multi-camera edit with new lenses and angles, keeping the people, performance, words, timing and original audio.

Source files: `angles-hf/SKILL.md`, `angles-hf/scripts/sheets.py.md`, `commands/angles.md`

## Inputs it needs

- One video, 4-30 s, one continuous take, with its media id and URL.
- Camera directions: from the message note, or spoken/shown in the clip itself; if none, one question (which angle, still or moving, or a multi-camera edit and which moments).
- Resolution: 1080p default, 720p or 480p on request. Aspect ratio is the source's.

## Steps in order

1. **Probe and frame sheets** - sheets.py: a frame every 0.25 s stamped with its second, 20 per sheet, plus speech with times and the aspect ratio.
2. **Read every sheet** - View each sheet through `image_paths`, two per call.
3. **Find the camera directions** - From the note or the clip; ask once if none.
4. **Break the take down, then plan shots** - Story, moments with times, peak, rhythm, space; a shot table with lens, side, height, move, what is behind, and why the cut lands there.
5. **Cost line** - One line: video edit is billed by length at the chosen resolution.
6. **Generate** - `generate_video`, mode `video_edit`, clip as @Video1 and no other media, `generate_audio` false.
7. **Put original audio back** - ffmpeg maps the edit's video with the source's audio, AAC 192k, `-shortest`.
8. **Check from result sheets** - Sheets of the result; find each planned shot; Seedance cuts up to about 1 s early or late.
9. **Deliver** - Video plus the shot plan in a few lines.

## Prompt blocks, word for word

**Multi-camera prompt template** (`angles-hf/SKILL.md`)

```text
Multi-camera re-shoot of @Video1: the same take — the same people, performance, words, sound and timing as @Video1, in real time from 0 to {L} s — covered by many cameras with different lenses around the same {place} and cut together into a bold, dynamic edit. Only the cameras change; nothing in front of them changes. The edit opens on shot 1 from its very first frame. {N} shots, hard cuts at {t1} s, {t2} s, …. Time runs on across every cut: nothing repeats, skips, slows down or speeds up.

@Video1: {one sentence: the place and its landmarks, the people (look, clothes, where they are), the key props, the light}.

Photoreal, cinematic. {aspect_ratio}. {L}s. Same light, colour and sound as @Video1. No music, no extra people.

Shot 1, 0.0–{t1} s, from the first frame — {lens}, {camera position by the set and the people, height}, {move}: {what fills the frame}; {what is now behind or around}. Accent: {the moment this shot catches}.
Shot 2, {t1}–{t2} s — …

{Gaze sentence, when someone talks to or looks at the original camera, written without the word camera.}
Faces, clothes, props and the place stay exactly as in @Video1 in every shot; the sound runs on unbroken across the cuts.
{On-screen text sentence when the clip has captions, titles or logos; otherwise: No text.}
```

**One-angle prompt template** (`angles-hf/SKILL.md`)

```text
Single-camera re-shoot of @Video1: the same take — the same people, performance, words, sound and timing as @Video1, in real time from 0 to {L} s — filmed from one new camera position. One continuous shot from 0 to {L} s with no cuts: the view never switches to another angle. Only the camera position changes; nothing in front of it changes. Time runs on: nothing repeats, skips, slows down or speeds up.

@Video1: {one sentence: the place and its landmarks, the people (look, clothes, where they are), the key props, the light}.

Photoreal, cinematic. {aspect_ratio}. {L}s. Same light, colour and sound as @Video1. No music, no extra people.

The camera, 0.0–{L} s — {lens}, {camera position by the set and the people, height}, {move; a static camera: completely still for the whole shot, no pan, tilt, zoom or shake}: {what fills the frame, and how much of the face turns to us}; {what is now behind or around}.

{Gaze sentence, when someone talks to or looks at the original camera, written without the word camera.}
Faces, clothes, props and the place stay exactly as in @Video1 for the whole shot.
{On-screen text sentence when the clip has captions, titles or logos; otherwise: No text.}
```

**Generation request** (`angles-hf/SKILL.md`)

```text
{"params":{"model":"seedance_2_5","mode":"video_edit","prompt":"<the shot-list prompt>","count":1,"duration":<L>,"resolution":"1080p","aspect_ratio":"auto","generate_audio":false,"medias":[{"value":"<clip media id>","role":"video"}]}}
```

**Audio restore command** (`angles-hf/SKILL.md`)

```text
     && ffmpeg -v error -y -i edit.mp4 -i src.mp4 -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
        -shortest -movflags +faststart final.mp4 \
     && curl -f -X PUT -H 'Content-Type: video/mp4' -H 'If-None-Match: *' --upload-file final.mp4 
```

**Frame-sheet command** (`angles-hf/SKILL.md`)

```text
 ~/angles/<MEDIA_ID> && curl -sfL '<SRC_URL>' -o src.mp4 \
     && python3 "$HF_WORKFLOWS/angles-hf/scripts/sheets.py" src.mp4 -o ~/angles/<MEDIA_ID>/sheets
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Re-shoot from the shot list | `seedance_2_5` | mode `video_edit`, duration L (source rounded to whole s), resolution 1080p (720p/480p on request), aspect_ratio auto, generate_audio false, clip as role `video` |
| Sheets, speech, remux | none | sheets.py (Pillow, ffmpeg, faster-whisper) in the sandbox |

## Checks and gates

- Rejects a clip outside 4-30 s (reports the duration; trims only on request); a photo is declined with an offer of `/product-angles`.
- Stops and asks once when neither the note nor the clip gives any camera direction.
- Pre-generation checklist: shots cover 0 to L exactly, cut times match, peak gets the strongest angle, at least four kinds of angle, original framing at most once and never first, something new behind the subject in every shot, no invented action, people or props, no camera gear named.
- Post-generation: every planned shot is located on the result's own sheets; a drift (changed face, invented action, original framing throughout) is reported with its time and one retry is offered.
- One retry only for a failed job with the same request; never resubmit a pending one.

## Price pattern

Quotes by length at the chosen resolution. `seedance_2_5` video_edit is not quoted in `_prices.md`; its nearest quote is the omni_reference draft (480p, 10 s) at 30 credits and 1080p at 160. Treat a 10 s 1080p re-shoot as likely near 160: re-quote before running.

## Cheap swap

- Test run at 480p first (the workflow allows 480p for a quick test), then 1080p once the shot list is right.
- Gemini edit: `gemini_omni_flash_1_2` mode `edit`, 360p (source 3-15 s, up to 7 image refs): the same 7.5 credits per 10 s tier as its quoted reference-to-video; the edit price itself is not quoted, re-quote first.
- The breakdown and the shot list are written by Claude on the plan (free to us); frame sheets, Whisper and the audio remux are local and free.
- Not a swap: Wan 3.0 has no edit mode (only reference video as a style input), so it cannot re-shoot the same take.
