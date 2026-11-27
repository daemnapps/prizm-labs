# Content Factory (what-if shorts)

Makes a 9:16 "what if..." short (about 60 s) where every frame is drawn by code in the Higgsfield sandbox (Higgsedit, GLSL for 3D looks) with one directed ElevenLabs v4 voiceover. No generated images or video.
Source: `commands/content-factory.md`, `commands/content-factory-references-what-if-reference.md`, `commands/content-factory-references-what-if-voiceover.md`, `commands/content-factory-references-higgsedit.md`, `commands/content-factory-references-glsl-3d.md`

## Inputs it needs
- A topic (the user's message after `/content-factory`). Bare command opens the style gallery; a style without a topic gets one question.
- Optional: a style (one of 56 listed with reference videos), a pasted/attached reference video or link, length (`duration_seconds`), `episode_count`, language, own characters or props as images.
- Language of the voiceover follows the user's typed words.

## Steps in order
1. Pick the reference: attached/linked video, else the chosen style's reference video, else design the style yourself.
2. Study it (`what-if-reference`): save it, sample 12-16 frames plus text crops into contact sheets, write `refs/style.md` (palette hex, type, captions, UI, how characters/sets are built, 3D material and light, shot rhythm).
3. Write the story in the reference's format and pacing, never its wording, premise or characters. Series: plan all episodes first, one line each.
4. Voice one ElevenLabs v4 take (`what-if-voiceover`): pick a table voice, one bracketed direction, caps for stress, about 160 words for 60 s.
5. Wait for the job, download, `voice.json`, check length (within 25 percent) and transcribe with faster-whisper; re-voice the whole take once if it does not match.
6. Build the Higgsedit project (`edit.jsx`): one compose, one timed full-canvas frame per scene; 2-4 reusable sets; captions from word times; GLSL shader for 3D references.
7. Preview 3-4 frames at 540x960, fix, then render (XL sandbox, background, ranges if over about 12 minutes).
8. Loudness to about -14 LUFS by plain gain, `ffprobe` check (1080x1920, audio), PUT, `media_confirm`, `register_what_if_result`, `show_result` with `content_factory_video`.

## Prompt blocks, word for word
**Style notes the reference study must produce (`refs/style.md`)**  
`commands/content-factory-references-what-if-reference.md`

```
3. Before any story, write `refs/style.md`:
   - palette as hex, sampled with ffmpeg from a few frames:
     `ffmpeg -i <frame> -vf "palettegen=max_colors=8:reserve_transparent=0:stats_mode=full" pal.png`,
     then `ffmpeg -v error -i pal.png -f rawvideo -pix_fmt rgb24 - | od -An -v -tu1 -w3 | awk '{printf "#%02X%02X%02X\n",$1,$2,$3}' | sort -u`;
   - type: the look, weight and case of each text role, and the closest
     Higgsedit font;
   - captions: position, size, case, and how words appear (one by one, greyed
     until spoken, highlighted);
   - recurring UI (HUD panels, tags, cards, counters) and where it sits;
   - how characters, sets and props are built: 2D or 3D, outline, shading,
     proportions, level of detail, and the hero's face (eyes, brows, mouth,
     nose), hair, costume details and hands;
   - for a 3D render: the material (matte clay, satin or glossy toy, faceted
     low-poly, voxel or brick, knit, polished metal), the key light's direction
     and softness, the fill colour, the lens, the camera height and how blurred
     the background is;
   - shot sizes, camera moves, cut rhythm and the end card.

```

**Voice and take rules (ElevenLabs v4)**  
`commands/content-factory-references-what-if-voiceover.md`

```
Set `stability` from the table and leave `similarity_boost` unset.

| Name     | `voice_id`                             | `stability` |
| -------- | -------------------------------------- | ----------- |
| Kevin    | `f1373f24-3b96-433f-9a68-e595810ef608` | 0.45        |
| Kiki     | `2d51d9d0-b2a4-5e8b-9c63-f310adafd5f7` | 0.45        |
| Desmond  | `563f728c-e249-5a85-97ab-8461e8c09da6` | 0.45        |
| Alexey   | `7c2133e5-68ab-511f-9aed-9a67664382b1` | 0.40        |
| Grady    | `e2a2d2e6-9ed2-59cd-82af-feaa27f8a678` | 0.45        |
| Barrett  | `d603a8cd-3fe1-55e0-9245-617a2589131e` | 0.45        |
| Andre    | `f1e8226e-2248-4d5f-b43c-0a79e9949dbf` | 0.45        |
| Miles    | `e18664a7-ee4f-5273-acf8-533eb24cd366` | 0.45        |
| Jasper   | `a7b8abe9-47f1-553e-a9df-87945a7e5bc8` | 0.45        |
| Ainsley  | `731b4ffe-e95e-59f4-8c00-81608936091f` | 0.45        |
| Holden   | `3c9d6053-6334-592c-8997-4e325286af3f` | 0.45        |
| Alistair | `d9d5c263-f84e-4752-97b5-3750fcc6fd2f` | 0.45        |
| Caspian  | `ef70cc83-3015-4bad-9359-0ea968c43ec0` | 0.45        |
| Gideon   | `1ad38ba4-9cc4-4f2f-9fde-b0fefdf67ae5` | 0.40        |
| Zoe      | `d0374db1-44b9-4f05-939e-0a9ae9dbbe6a` | 0.40        |

## Text of the take

The whole script is ONE take: every spoken line, in order, joined with single
spaces into one text.

- Open the text with one bracketed direction naming voice quality, energy and
  pace, such as `[dry, punchy storyteller, brisk pace]`.
- Add a new bracketed tag only where the delivery turns: `[leaning in]`,
  `[deadpan]`, `[building tension]`. Use `...` for a held beat and `[pause]`
  before a punchline.
- CAPS on at most one word per sentence, for stress.
- Never ask for "slow" or "unhurried": the take runs about 20% longer.
- Tags are never spoken. Leave them out of captions and on-screen text. Use no
  other square brackets.
- Spell numbers out and write symbols as words ("percent", "dollars").
- Length: about 160 words for 60 s in English (about 2.7 words per second) and
  about 2.5 words per second in Russian and other languages. It is a soft
  target: never pad or cut to hit it.
- At most 10,000 characters in total.


```

**Take text rules**  
`commands/content-factory-references-what-if-voiceover.md`

```
## Text of the take

The whole script is ONE take: every spoken line, in order, joined with single
spaces into one text.

- Open the text with one bracketed direction naming voice quality, energy and
  pace, such as `[dry, punchy storyteller, brisk pace]`.
- Add a new bracketed tag only where the delivery turns: `[leaning in]`,
  `[deadpan]`, `[building tension]`. Use `...` for a held beat and `[pause]`
  before a punchline.
- CAPS on at most one word per sentence, for stress.
- Never ask for "slow" or "unhurried": the take runs about 20% longer.
- Tags are never spoken. Leave them out of captions and on-screen text. Use no
  other square brackets.
- Spell numbers out and write symbols as words ("percent", "dollars").
- Length: about 160 words for 60 s in English (about 2.7 words per second) and
  about 2.5 words per second in Russian and other languages. It is a soft
  target: never pad or cut to hit it.
- At most 10,000 characters in total.


```

**Voiceover request**  
`commands/content-factory-references-what-if-voiceover.md`

```
{"params": {"model": "elevenlabs_v4", "prompt": "<the whole take>", "stability": <stability>, "batch_size": 1,
  "dialogue": [{"text": "<the whole take>", "voice_id": "<voice_id>", "voice_type": "preset"}]}}
```

**Higgsedit project skeleton**  
`commands/content-factory-references-higgsedit.md`

```
export default async ({ project }) => {
  const p = await project({ dir: ".", size: "1080x1920", fps: 30, background: "<hex>" });
  const voice = await p.add("../voice.mp3");
  p.compose(
    <frame width={1080} height={1920} layout="none">
      {/* one full-canvas child per scene: <frame at={t0} duration={t1 - t0} width={1080} height={1920} layout="none">…</frame> */}
    </frame>,
    { at: 0, dur: <video seconds> }
  );
  p.cut(voice, { at: 0 }); // the take on the audio spine; its length is the default dur
};
```

**Render and upload command lines**  
`commands/content-factory-references-higgsedit.md`

```
Start
  the final render with `sandbox_exec` `size: "xl"` and `background: true`:
  `cd ~/what-if/<slug>/edit && higgsedit render . --bitrate 8M --out ~/what-if/<slug>/edit/renders/final.mp4`
```

**Loudness and upload rule**  
`commands/content-factory-references-higgsedit.md`

```
- **Loudness and upload.** The render plays a mono take about 3 dB quieter.
  Call `media_upload` with `filename: "<slug>.mp4"` first. Then, in one
  foreground command: measure the final's integrated loudness
  (`ffmpeg -i final.mp4 -af ebur128 -f null -`), bring it to about -14 LUFS
  with a plain gain
  (`ffmpeg -i final.mp4 -c:v copy -af volume=<-14 minus measured>dB out.mp4`),
  keeping the true peak under -1 dB, and append
  `&& curl -f -X PUT --upload-file out.mp4 '<upload_url>'`. Never compress or
  limit the voice harder: it flattens the intonation.
```

Style slugs (each has a published reference video in `commands/content-factory.md`): haze-countdown, pixel-night, heatwave-park, night-scan, toy-planet, lowpoly-skyline, shard-pixel, ink-gold, astro-hud, mannequin-commute, cutaway-lab, grain-poster, frost-lowpoly, wash-atlas, offline-grid, grain-primary, night-ledger, phosphor-vector, crowd-sim, speed-run, toon-mission, oval-office-toon, iso-diorama, gas-giant, ops-console, rubber-hose, canyon-crowd, knit-sky, brick-toy, park-skyline, bold-flat, sepia-silhouette, poly-captcha, retro-poly-jungle, botanical-plate, peach-scale, violet-flat, blueprint-line, gold-studio, pop-desk, woodblock-wave, ranger-lowpoly, signal-room, slow-drip, dusk-anime, voxel-city, noir-panels, cube-planet, quiet-lowpoly, swiss-grid, night-flat, candy-diner, paper-atlas, sitcom-mini, retro-poly-cosmos, pastel-clay.

The GLSL helper library written once per 3D video (signed-distance shapes, camera ray, march, normal; code, not a prompt) is in `commands/content-factory-references-glsl-3d.md`.

## Models it calls
| Job | Higgsfield model id | Settings |
|---|---|---|
| Directed voiceover, one take | `elevenlabs_v4` | `stability` 0.40-0.45 from the voice table, `batch_size:1`, one `dialogue` turn, `voice_type:preset` |
| Revoice one or two lines | `elevenlabs_v4` | same voice and stability, original bracketed direction |
| Reference style study (YouTube fallback) | `video_analysis_create` (tool) | only if `yt-dlp` fails on YouTube |
| Frames, 3D, captions, render | none (Higgsedit and ffmpeg in `sandbox_exec`) | free; never image or video generation |

## Checks and gates
- Stops if `command -v higgsedit` is missing; never `pip install`, never Pillow for frames or text.
- Never fetches the reference and requests the voice in the same step; never generates images or video for this format.
- Voice check: take length within about 25 percent of the word estimate, whisper transcript matches the script, no tag read aloud; one whole-take re-voice, then it ships with a note.
- Failures: preflight errors fixed and resent; failed/canceled job resent once; `nsfw` or `ip_detected` reword and resend once; never resubmit a take that has a job id otherwise.
- Render checks: 3-4 preview frames, 1080x1920, duration, audio stream, 2-3 final frames inspected; true peak under -1 dB; voice never compressed harder.
- Several episodes: made in order, each delivered when its own check passes, never re-voiced afterwards.
- A language other than English or Russian gets a table voice and an accent note.

## Price pattern
The voiceover is the only paid call. Not quoted in `_prices.md`; the Katana notes put speech at about 0.23 credit per 30 characters, so a 60 s take (about 900 characters) is roughly 7 credits (inferred). A whole-take re-voice doubles it; a line patch is a few credits.

## Cheap swap
- Voiceover (`elevenlabs_v4`, about 7 per 60 s): Kokoro tts on this Mac, free; saves the 7 but loses the directed performance, so use for drafts.
- Reference reading and `style.md`: already free; Claude reads the frames. Story and script: Claude on the plan, free.
- Transcript and word timings: local Whisper stt instead of the sandbox faster-whisper.
- Render: already free in the sandbox; a local ffmpeg/HyperFrames build could replace Higgsedit but the workflow is tied to Higgsedit.
- No picture or video model is used, so `wan3_0`, `gemini_omni_flash_1_2` and the 2k picture swaps do not apply.
