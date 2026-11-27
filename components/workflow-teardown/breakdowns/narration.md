# Narration

Makes narration audio (numbered takes fitted to fixed video windows, or one continuous long-form read in a locked voice), or puts a consenting person from a photo on screen as the narrator of an existing video. Three modes: A1 per-block takes, A2 continuous, B on-screen presenter.
Source: `narration/SKILL.md`, `narration/references/presenter-mode.md`, `narration/scripts/speech_metrics.sh.md`, `narration/scripts/presenter_composite.sh.md`

## Inputs it needs
- Audio modes: the lines to speak (numbered, in order) and the voice pair `voice_id` + `voice_type` (`preset` or `element`); optional window per line (default 7.8-9.5 s of speech in a 10 s block), delivery direction, mood.
- Mode B: the video, one photo of a consenting non-public person, the locked voice pair, optional authoritative script text. A photo means Mode B at once.
- Missing voice: `list_voices` as the only tool of that turn; empty result locks the pinned default pair.

## Steps in order
1. Write the voice pair to `voice.lock` and re-read it before every call.
2. A1: compose one `{DELIVERY}` phrase for the whole job; send each line in the timecode format at about 20-23 words per 10 s.
3. Submit lines through `generate_audio_batch` (groups of six, stable index); `jobs_wait` with 15 s timeouts; one line alone uses `generate_audio`.
4. Download, convert the MP3 (clip click removed), then gate with `speech_metrics.sh`: `speech=` in window, `pauses=0`, `rate=ok` (not above 2.9 words per second).
5. Out of window, pausey or wrong timbre: rewrite the text and regenerate only the failing indices (at most 3 attempts per line; passed takes are immutable). Never time-stretch.
6. A2: one flowing read with `seed_audio`, script-length target not speed; join chunks (about 1800 characters each) in order with ffmpeg concat; up to two text-rewrite corrections.
7. Mode B: probe the video; make a green-screen reference of the person (`gpt_image_2_6`); generate one 10 s presenter block per 10 s of video; `voice_change` each block; composite per block with `presenter_composite.sh`, concat, QC contact sheet, upload, confirm.
8. Report per line: job id, URL, measured speech, pass/fail, final wording.

## Prompt blocks, word for word
**Per-block take: timecode format sent for every line**  
`narration/SKILL.md`

```
[ {DELIVERY}, {optional line mood}, starts speaking immediately] [00:00-00:09] {line}
```

**Batch item shape (per-line takes)**  
`narration/SKILL.md`

```
Every item is
   `{index, params:{model:"text2speech_v2", variant:"elevenlabs", prompt,
   voice_id, voice_type, count:1}}`; `index` is the stable line number.
```

**Convert each returned MP3 before measuring**  
`narration/SKILL.md`

```
ffmpeg -nostdin -hide_banner -loglevel error -i takeNN.mp3 -ac 1 -ar 24000 \
  -af "areverse,atrim=start=0.030,asetpts=N/SR/TB,afade=t=in:st=0:d=0.060,areverse" \
  -y voiceNN.wav
```

**Speech gate**  
`narration/SKILL.md`

```
sandbox_exec({
  command:"bash ${HF_WORKFLOWS}/narration/scripts/speech_metrics.sh work/voices/voice01.wav --text '<authored line>'"
})
```

**Mode B: green-screen identity reference prompt**  
`narration/references/presenter-mode.md`

```
Edit this photo. Keep the PERSON identical — same face, hairstyle, clothing, skin tone,
pose and framing, copied faithfully, not beautified and not a lookalike. Change one thing
only: replace the background with a perfectly uniform flat chroma-key green screen
(#00B140), evenly lit, no gradient, shadow or vignette, filling everything behind the
person. No green spill on the person; preserve clean hair edges.
```

**Mode B: talking-block prompt template**  
`narration/references/presenter-mode.md`

```
IDENTITY REFERENCE (appearance only, not a start frame): copy the attached person and
solid green background faithfully. The first frame already catches them mid-speech, never
frozen. They look into the front camera and say in <DELIVERY>, in <LANGUAGE>:
"<BLOCK LINE VERBATIM, 31–35 WORDS FOR A FULL BLOCK>". Say every word exactly once at a
brisk steady pace, then hold a calm engaged look. For a partial final window, size the line
to that window even though the provider clip is 10 seconds. Camera locked; small natural head and
shoulder gestures only. Audio is only the clear voice. Keep the background uniformly vivid
green. No repeated or improvised words, captions, watermark, camera motion, beautification,
background change, or frozen opening.
```

**Mode B: composite command (once per block)**  
`narration/references/presenter-mode.md`

```
"$HF_WORKFLOWS/narration/scripts/presenter_composite.sh" \
  blkNN.mp4 talkNN.mp4 outNN.mp4 --style cutout --pos br
```

**Mode B: revoice call**  
`narration/references/presenter-mode.md`

```
4. **Revoice every completed clip.** Call `voice_change` once per block with
   `params:{video_id:"<talking-job-id>",voice_id:"<locked-id>",voice_type:"<locked-type>"}`.
   
```

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Per-block takes (A1) | `text2speech_v2` | `variant:elevenlabs`, locked voice pair, `count:1`, one line per call |
| Continuous read (A2) | `seed_audio` | locked voice pair, no `speech_rate`, prompts up to 2048 characters |
| Green-screen identity picture (B) | `gpt_image_2_6` (fallback `nano_banana_pro`) | 9:16, `1k`, quality medium, photo as image |
| Talking block (B) | `gemini_omni_flash_1_1` | 9:16, 10 s, 720p, `reference-to-video`, green-screen image as `image_references` |
| Replace the talking voice (B) | `voice_change` | `video_id`, locked voice pair; no lip-sync pass |
| Measure, convert, composite, concat | none (sandbox scripts, ffmpeg) | free |

## Checks and gates
- One voice for the whole job; wrong voice, timbre or model/variant is a failed take even if the length is right.
- Speech gate per line: in window (hard reject outside 7.2-9.5 s, soft band 7.2-7.8 only after one retry), no internal pause of 0.8 s or more, rate within the ceiling; unmeasured takes are returned as unverified, never promoted.
- At most 3 attempts per line, a third needs changed text; at most two corrections for a continuous read; failure returns exact slot, attempts, metrics.
- Never voice-clones, never time-stretches, never re-resolves a voice after the lock; personal data in a line is flagged, not voiced.
- Mode B: every block has audio and its duration; QC `PASS` per composite; joined length within 0.1 s of the base video; presenter opaque, inside frame, not covering key content. Declines non-consenting or public persons; discloses when original audio is dropped (mono mix).
- Not for ordinary read-aloud, music, SFX, singing, generic dubbing or a voiceover inside a new ad.

## Price pattern
Not quoted in `_prices.md` for the audio calls (quote with `estimate_audio_cost` first). Reference points: `gemini_omni_flash_1_2` 360p 10 s is 7.5 credits (the 1_1 model Mode B uses is not quoted); a 1k medium picture is under 2 credits (nearest `gpt_image_2_6_flare` 1k low 0.75). A 30 s on-screen narration is 3 blocks: about 3 talking blocks plus 3 voice changes plus 1 picture, not quoted as a total.

## Cheap swap
- Per-block and continuous takes (`text2speech_v2`, `seed_audio`): Kokoro tts locally, free, for drafts and timing tests; ship with the locked paid voice.
- Speech measurement, MP3 cleanup, joining, loudness: already free (ffmpeg, local Whisper stt).
- Green-screen picture: `seedream_5_0_flash` 2k 0.5 or `gpt_image_2_6_flare` 1k low 0.75 instead of `gpt_image_2_6` 1k medium.
- Talking block (`gemini_omni_flash_1_1` 720p): `gemini_omni_flash_1_2` 360p or `wan3_0` 480p, 7.5 credits per 10 s each (both take an image reference; speech on).
- Cut-out matte for compositing: BiRefNet or SAM2 locally instead of chroma-key edges; composite itself is already free.
- Script, density tuning and rewrites after a failed gate: Claude on the plan, free.
