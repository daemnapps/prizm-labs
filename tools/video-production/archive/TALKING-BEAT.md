# The talking beat — SUPERSEDED 2026-09-12

**Read `THE-CINEMA-LINE.md` instead.**

This file documented a day spent marrying an audio file to a video: which
model consumes `audio_references`, how to pad a take to a whole second, how to
measure a mouth against a voice envelope. All of it solved a problem that does
not exist in Cinema Studio, which generates the speech and the picture
together and then gets revoiced.

Kept because the traps it records are real and still bite — figures spoken
literally, gestures held as poses, cameras named into frame, the scene count
exploding — and because it is the record of how long the wrong road was.

---

# The talking beat

How a scene where the presenter speaks becomes a clip. Settled 2026-09-12 after
a day of getting it wrong in four different ways.

**Everything here happens in Higgsfield. Nothing else.**

---

## The five steps

### 1. Read the scene before you generate anything

What is she **saying**, and what is she **doing** while she says it? These are
different questions and the second one has an answer.

> "Number one: drugstore bump products…" → **one** finger.
> "Number two: pre-shave oil." → **two**.
> "It reaches 4x deeper than your hands." → the hand moves *down*.
> "The neck stops feeling like braille." → her fingertips go to her own jaw.

Write the gesture for every beat before a single plate is made. Eighteen beats
built off one plate is eighteen shots of a woman holding up three fingers while
she says "number one", and that is exactly what happened.

### 2. The plate carries the gesture AND the expression

Edit from the scene's own reference. Change **only** the gesture and the face;
never re-describe the room, the wardrobe, the crop or the light — naming them
again invites the model to reinvent them.

**A flat plate gives the video nothing to animate.** This is the one that is
easy to miss. A neutral still produces a clip of someone reciting, no matter
what the motion prompt says. The plate itself has to be a person mid-explanation:

- eyes **into the lens**, alive, with light in them — not a stare
- eyebrows slightly raised and **active**
- head turned very slightly, not square-on
- a faint knowing tension at the mouth

### 3. Duration comes from her take, never from the script

The brief's timing is the *source* video's timing. Her read is shorter —
usually by two to six seconds. Ask for the script's length and the job fails.

    duration = ceil(length of her mp3), clamped 4–15

### 4. Generate on `wan2_7`, with her voice attached

    model             wan2_7
    start_image       that scene's plate
    audio_references  her ElevenLabs take
    aspect_ratio      9:16      resolution  1080p

**Not seedance.** Seedance takes `audio_references` as a *style* reference and
returns a silent clip — the mouth is then the model's own invention and the
voice gets laid under in the edit, which is the definition of out of sync. Wan
consumes the audio and returns the clip **with her track already inside it**.
Same parameter name, two completely different meanings. That cost most of a day.

Two things the prompt must always say:

**The gesture is a beat, not a pose.** It lands on the word and *resolves* —
the hand comes down inside the first second and stays down. Written as "stays
up through the line", she holds one finger aloft for seven seconds like a
statue, long after the word has passed.

**Direct the face explicitly.** Brows lift on the number, draw in on the
product names, flicker on the dismissal. Eyes stay on the lens and keep moving
in small natural shifts. Say it, or it does not happen.

### 5. Verify before showing it to anyone

Three measurements, all cheap, none of them "it looks right to me":

| check | how | pass |
|---|---|---|
| Is it **her** voice? | RMS-envelope correlation, returned track vs her mp3 | ~1.000 |
| Is the mouth **synced**? | frames at her three loudest vowels and her silences | open on loud, shut on quiet |
| Does the gesture **resolve**? | eight frames tiled across the clip | up at the start, down after |

---

## What this replaces

`sequence.py` and `sound.py` ran on fal and are retired in place. The clips
they produced for the first run came off `kling3_0` with `sound: "off"` — a
model this repo had already written down as RETIRED — and no audio attached at
all. Nothing recorded which model made a clip, so it went unnoticed through an
entire finished ad.

**Record the model on every clip.** A wrong model that leaves no trace is a
wrong model that gets used twice.

---

## The brief emits too many scenes

**the owner, 2026-09-12: "we don't need 33 scenes."**

Stage 5 mapped one scene to every beat of a 203-second source and emitted
**33**. That is a transcript of the swipe, not an ad. It is also the real cost
driver: every scene is another generation, another gesture to get wrong,
another chance for the sync to drift, and eighteen of them were the same
woman at the same crop saying consecutive sentences.

Consecutive talking beats in the same setup are **one scene**, not four. The
cut can find its own edit points inside a longer take. Splitting them up front
buys nothing and pays for it three times over.

Before generating anything, collapse the scene list: adjacent type-A beats
with the same setup merge, and the target is the smallest number of scenes
that still carries the structure — not one per line of script.

## Also settled that day

- `seedance_2_5`, `mode: omni_reference`, her take attached as `audio`.
  Not `wan2_7`, not `seedance_2_0`, and never fal.
- The prompt must *instruct* the sync in words. Attaching audio does nothing
  on its own.
- Never describe what she does during silence — it breaks the sync.
- Duration is her take rounded up. The trailing tail is harmless.
- Figures and marks belong in the ON-SCREEN text, never the spoken line:
  `4x` is read aloud as "four x".
