# Stage 5b · Motion QC — v2

*v2 (2026-09-23): a new check 7, **Subject zone** — the first and last
frames are measured inside the centred 4:5 zone at production
(`machine/safezone.py`); what happens BETWEEN them is only visible here.
Everything else is v1 unchanged.*

*v1 (2026-09-17). The motion pass: identity hold, product constancy, anatomy,
camera motivation, lip-sync class. Runs on every generated clip before
anything ships. The session pastes `{generated_clip}`, `{scene_prompt}`,
`{start_frame}` and `{ceilings}` — this model's entries from
`machine/providers.json`.*

Inspect this motion clip against the scene prompt and the start frame. You
are checking what MOVEMENT does, not what the frame contains.

**Every example in this prompt is illustrative only.**

THE CLIP

{generated_clip}

THE SCENE PROMPT

{scene_prompt}

THE START FRAME

{start_frame}

WHAT THIS MODEL CANNOT DO

{ceilings}

Check, in this order:

1. **Identity hold** — does the face hold across the whole clip? Age, build,
   hair, features read against the START FRAME, never against the
   description.
2. **Product constancy** — where the product appears: label legible and
   UNCHANGED across the clip (no garbled text, no weight-flip, no morphing
   cap), shape and colour constant. Compare to the attached packshot.
3. **Anatomy window** — any hand close-up: five fingers, no merging with the
   product, no warping. Flag the moment.
4. **Camera motivation** — is the movement saying something (push-in =
   emphasis, track = journey, hold = gravity) or moving because it can?
5. **One action per cut** — name the single action. Two actions in one clip =
   one blurred action = deviation.
6. **Lip-sync class** — mouth moves with the vocals: FIXABLE (mouth static)
   or CEILING (singing sync approximate — this model cannot do
   phoneme-exact). A ceiling is reported once and never re-rolled.
7. **Subject zone** — the clip is 9:16, and the face, the product and the
   hands doing the beat stay inside the centred 4:5 zone — the middle 70%
   of the height — for the WHOLE clip. The start and end frames were
   measured inside it; a subject that leaves the 4:5 zone mid-clip (a head
   rising into the top 15% on a push-in, a product sinking into the bottom
   15%, hands drifting out of the band) is a deviation. Name the second and
   where it went. It is `fixable`: the camera move or the beat is rewritten
   and the clip made again from the same frames — the edit is never asked to
   crop around it.

Report as JSON, and nothing else:

    {"pass": true}

or

    {"pass": false, "problems": [
      {"what": "<one specific, visible, correctable deviation>",
       "defect_class": "fixable"},
      {"what": "<one specific deviation the model cannot fix>",
       "defect_class": "ceiling"}
    ]}

Each `what` names WHAT is wrong and WHAT it should be, in one sentence.
Report only what you can actually see in the clip.
