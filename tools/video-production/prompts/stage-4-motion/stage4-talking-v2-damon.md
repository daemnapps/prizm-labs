# Stage 4 · Talking shot — v2

**Superseded 2026-10-03 (the owner) — the talking clip is made on the Omni route (`THE-CHAIN.md` 4.5,
`machine/omni_clips.py`):** Omni Flash on fal at 1080p animates the approved picture as the first
frame, says the on-camera line written in the prompt (no audio attached — the voice-first workflow
is retired), and ElevenLabs speech-to-speech turns it into the person's cloned voice. A person's
clip always starts from the approved picture, never a clip's last frame. The recipe below is the
2026-09 legacy door's, kept as the record.

*v2 (2026-09-17, the owner's ruling): the recipe for a talking beat on this
stage — the approved still as the start image, the ElevenLabs line attached
as audio, `mode: omni_reference`. The v1 instruction that a talking beat
needs no start image and no audio is removed; it described the live Cinema
chain's own two-call route (`cinematic_studio_3_0` + `voice_change`,
documented in `THE-CINEMA-LINE.md`), which is a different route and
untouched by this change. This file governs this stage's own talking beat,
not that one. The no-cut line, verbatim, is also added to the prompt — every
video prompt this machine ships carries it, without exception (the course
write-up, the owner 09-14, §7).*

**Every example in this prompt is illustrative only.**

---

Inputs: the approved scene still, attached as the start image. The
ElevenLabs line for this beat, attached as audio. `mode: omni_reference`.

Prompt text:

    Single continuous take, no cuts or scene changes.

The still is the framing; the audio is the performance. `omni_reference`
animates the still to the audio without re-planning the frame — it does not
need, and must not be given, a description of what the still already shows.

---

~4s per talking beat, ~6s for b-roll. Re-roll on the same (still, take)
pair until the motion lands — the pair is the asset, the roll is cheap.
