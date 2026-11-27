# Video Montage

Joins existing clips into one finished video, swaps or mixes a soundtrack, and burns timed speech captions on it, with no generation.

Source files: `video-montage/SKILL.md`, `video-montage/references/subtitles.md`, `video-montage/references/ugc-captions.md`, `video-montage/references/faceless-captions.md`, `video-montage/references/website-captions.md`, `video-montage/references/caption-clearance.md`, `video-montage/scripts/audio_to_captions.py.md`, `video-montage/scripts/subtitle_paper_burn.py.md`

## Inputs it needs

- Clips (media ids) in the order wanted, or one finished master to caption.
- For captions: the finished video's real audio, the authored script text (`script_manifest.json` with `vo_line` blocks) and the spoken language code.
- A look for captions if the caller did not set one: TikTok caps, Heavy impact caps, Clean geometric caps or Handwritten torn paper.
- Optional music file for a soundtrack change.

## Steps in order

1. **Probe every source** - ffprobe each clip: duration, streams, size, fps.
2. **Assemble** - Ordered concat manifest with stream copy when codecs match; normalize only what differs; hard cuts unless asked.
3. **Soundtrack** - Keep speech intelligible, duck and trim music; add none unless asked.
4. **Transcribe real audio** - Per-block voice files if present, else `--mixed` with the language code; `--script` keeps the authored words.
5. **Verify transcript (gate)** - similarity at least 0.90, caption_words equals words, spot-check three cues.
6. **Clean-frame evidence and protected regions** - Standalone/UGC captions: caption_evidence, inspect frames, caption_regions map of faces, hands, labels, existing text.
7. **Burn one look** - subtitle_paper_burn.py (bold / paper) or burn_caps_clean.sh; one font size for the whole video.
8. **Verify the burn** - duration within about 1 s, audio tail intact, two cue-midpoint frames inspected, receipts returned.

## Prompt blocks, word for word

**Whisper timing, UGC and website captions** (`video-montage/references/ugc-captions.md`)

```text
python3 "${HF_WORKFLOWS}/video-montage/scripts/audio_to_captions.py" output/final.mp4 \
  --mixed --language '<spoken-language-code>' --script script_manifest.json \
  --srt caps.srt --json caps.json --max-words 5 --max-chars 32
```

**Faceless caption burn (fixed look)** (`video-montage/references/faceless-captions.md`)

```text
python3 "${HF_WORKFLOWS}/video-montage/scripts/subtitle_paper_burn.py" \
  --in final.mp4 --srt caps.srt --out final_subbed.mp4 \
  --style bold --no-caps --font-key montserrat --stroke-frac 0.045 \
  --profile faceless
```

**Per-block timing on clean voice files** (`video-montage/references/subtitles.md`)

```text
python3 ${HF_WORKFLOWS}/video-montage/scripts/audio_to_captions.py final.mp4 --srt caps.srt --per-block final.mp4.assembly.json --voice-dir . --script script_manifest.json --language '<narration-language-code>'
```

**Mixed-audio timing** (`video-montage/references/subtitles.md`)

```text
python3 ${HF_WORKFLOWS}/video-montage/scripts/audio_to_captions.py video.mp4 --srt caps.srt --mixed --language ru
```

**Burn: paper or bold** (`video-montage/references/subtitles.md`)

```text
python3 ${HF_WORKFLOWS}/video-montage/scripts/subtitle_paper_burn.py --in video.mp4 --srt caps.srt \
    --out final_subbed.mp4 --style paper|bold [--no-outline] \
    [--font-key tiktok|caveat|patrick|marker|montserrat|anton]
```

**Burn: clean** (`video-montage/references/subtitles.md`)

```text
bash ${HF_WORKFLOWS}/video-montage/scripts/burn_caps_clean.sh --in video.mp4 --srt caps.srt --out final_subbed.mp4
```

**UGC-natural variant (flags)** (`video-montage/references/subtitles.md`)

```text
add `--no-caps --single-line --stroke-frac 0.045` to
the `bold` burner and pair it with `audio_to_captions.py --max-words 4`.
```

## Models it calls

| Job | Higgsfield model id | Settings |
|---|---|---|
| Assembly, soundtrack, captions | none | ffmpeg and a Whisper model run in the Higgsfield sandbox (`sandbox_exec`); nothing is generated |

## Checks and gates

- The caller supplies the master and the authored script; the workflow does not re-ask resolved choices.
- Never claims an assembly from an exit code: duration, streams, first and last frames and every join are checked.
- Transcript gate: similarity under 0.90 with `--script` means re-run per block or with model `medium`; a non-zero exit burns nothing.
- No stand-in for missing speech: no speech means the clean video comes back with that said.
- Caption placement protects the moving face, hands, product labels, existing hooks and tutorial text on every cue; it returns `caption_incomplete` with the clean master and the failing interval if placement cannot pass.
- Faceless profile is the exception: one fixed bottom-center baseline, no region maps.
- Excluded from this workflow: text-only subtitle translation, transcription or SRT delivery, analysis, native Higgsedit authoring, generative edits.

## Price pattern

No credits: it runs in the sandbox and calls no generation model. Nothing quoted in `_prices.md` applies.

## Cheap swap

- Already free in the Higgsfield sandbox; on this Mac the same jobs are free local tools: ffmpeg for concat and mixing, Whisper stt (components/local-studio) for the word clock, Demucs stems to pull speech from music. Saving: 0 credits either way, plus no sandbox round trip.
