# The Video Machine — the production process (model-agnostic)

> **⚠ STALE — the four-generation-stations overview, written 2026-08-30.** It predates the edit-first finding (`frames-by-edit.md`) and the worked song-ad run (`formats/song-ad/`). Its station model still describes how the machine is shaped, but the way a frame is actually made is no longer what this file says.
>
> Live method docs: `frames-by-edit.md` (how a frame is made), `building-the-cast.md` (how a character is built — its own process), `formats/song-ad/` (a format, proven end to end).


v3, 2026-08-30. The process that turns a finished brief into finished clips.
**Four generation stations**, each a **slot** any model can fill — cloud,
local, or open-source. The edit (cut sheet + rendering) is deliberately OUT
of scope: it needs a different level of detail and runs as its own process
(separate build). This machine's job is done when every
beat of the brief has a clip that works.

Proven across 328 real generations on one full ad production;
the fully-specific proven run (every model name, every setting, every
verbatim prompt) is the evidence record: `evidence-record.md` +
`evidence-run.json`. Artifact: **The Video Machine**
(team page) —
republish over that link on every change. Stage-by-stage detail lives in
`stages/`.

The models are swappable. The process is the machine.

## The line at a glance

```
BRIEF ──► 1 CAST ──► 2 VOICES ──► 3 SCENES ──► 4 MOTION ──► (hand-off)
          identity    base take +   one still    talking /     clips + takes
          images      chained lines  per beat    cinematic /   to the edit
                                                 product clips  process
```

House standard, locked once and never touched: one aspect ratio (vertical
9:16 for feed ads), stills at full quality, video at delivery quality.
Nothing is upscaled afterward — quality is set at generation time.

## Station 1 — Cast: make each character once

One clean identity image per character; it is the face used in every scene,
so it's made carefully and never remade.

- **From reference photos**: 1–2 real photos in, one straight portrait out.
- **From a written description**: a split-screen **character sheet** — full
  body left, close-up right, plain studio background, seed locked so the
  face is reproducible.

**The slot** — any image model that can: take reference images (or hold a
detailed identity from text), render natural skin without a beauty-filter
look, and lock a seed.

**Prompt pattern — character sheet:**

> Split-screen character sheet composition, left side a full-body shot of
> the character standing upright in a neutral pose facing the camera,
> head-to-toe framing, right side a tight close-up chest-up portrait of the
> same character, identical original character on both sides, exactly one
> person in frame, pure white seamless studio background.
> [IDENTITY — age, ethnicity, face, skin texture, build, in concrete
> physical detail] [WARDROBE — every garment and accessory, named]
> Visible fine skin texture with natural pores, no digital smoothing, no
> beauty filter, no AI-airbrushed look, natural anatomy, unretouched
> commercial photography style, soft diffused studio lighting, sharp focus
> on skin detail.
> NEGATIVES: no other people, no duplicate figures, no props, no furniture,
> no text, no watermark, no frame borders, original character not resembling
> any real celebrity.

## Station 2 — Voices: a paragraph is the voice

No voice presets. Every voice is a written description of a person, then
cloned from its own best take, line after line.

1. **Base take.** Describe the person in prose — age, accent, texture,
   mood — and give them their first line. A real uploaded recording works
   as the seed voice too.
2. **Chain every next line.** Feed the base take back as the reference:
   "this recording is the SAME speaker — generate their next line in the
   identical voice." Never re-describe a voice from scratch mid-project.
3. **Lock a drifting accent.** Stack the two best takes as references and
   spell out the phonetics — name the vowels, the consonants, the melody,
   and what it must never slide into.

Findings that hold regardless of model: slower-than-neutral speaking rate
reads dramatically better; hard lines take up to ~14 takes; punctuation in
the line is the pacing direction.

**The slot** — any voice model that can: generate speech from a text
persona, clone from reference recordings (same-speaker continuity), and
control rate and expressiveness.

**Prompt pattern — base take:**

> [PERSONA — age, accent, vocal texture, temperament, how they speak],
> speaking slowly and steadily. [He/She] says: [THE LINE, written the way
> it should be performed — punctuation is pacing]

**Prompt pattern — chaining / accent lock:**

> @Audio1 and @Audio2 are recordings of the SAME speaker: [PERSONA restated]
> with [THE ACCENT, in caps, phonetics named — vowels, final consonants,
> prosody] — never [what it must not slide into]. Generate the next
> recording in the identical voice and identical accent. [He/She] says:
> [THE LINE]

## Station 3 — Scenes: compose, don't describe

One still per beat of the script. Faces and product stay consistent because
every scene is built by **stacking banked images** — 1–6 references per job
(cast images + product photo + wardrobe boards) — addressed by position:
"the woman from the first reference, the product from the second." The
setting, light, and framing are written out; the identities are never
re-described.

Optional prep that pays off: studio turnarounds and wardrobe boards per
character, generated once, reused as references everywhere. Banked stills
are durable — in the proven run a product shot was still being wired into
new scenes three weeks later.

**The slot** — any image model that can: accept multiple reference images
in one job and keep each identity faithful, be addressed by reference, and
hold a product's label and shape exactly.

## Station 4 — Motion: three shot types, one station

Every clip comes from the video model. What changes is what you feed it:

- **A. Talking shot** — scene still + voice take, **no prompt at all**. The
  still is the framing, the audio is the performance; the model animates
  and lip-syncs to the track. ~4s per beat, ~6s for b-roll. The volume
  mode: most of a story ad ships this way.
- **B. Cinematic shot** — 0–2 references + a full written shot direction,
  with the sound described in words and the model generating the ambience
  itself. 8–15s single takes. Works with no image at all for establishing
  shots.
- **C. Product hero** — product photo + motion direction. "Exactly matching
  the reference image… label crisp and legible… no hands, no text
  overlays." Silent, slow, label-first. 8–9s.

**The slot** — any video model that can: animate from a start frame,
**lip-sync to a supplied audio track** (mode A — the one capability that
cannot be faked), follow a written shot direction with or without a
reference (modes B/C), and optionally generate its own ambient audio (B).

**Prompt pattern — cinematic shot:**

> Cinematic drama, [SETTING + LIGHT]. [The character from the first
> reference image] [ONE physical action, described beat by beat]. [The
> emotional reaction, in one sentence]. [SOUND — what is heard, and what is
> NOT: no music / no dialogue / room tone only].

**Prompt pattern — product hero:**

> Cinematic product photography in motion, 9:16. [ONE camera move, slow] on
> the [PRODUCT] exactly matching the reference image, [SURFACE + set
> dressing + LIGHT], the label coming into crisp focus. NEGATIVES: [known
> render errors of this product], no hands, no text overlays. Silent clip,
> no audio.

## Where this machine ends

Output: a bank of finished clips and voice takes, named per story beat,
handed to the edit process (separate build — cut sheet,
timing, text on screen, rendering). That process has its own design and its
own level of detail; it is not a station of this machine.

## The rules that make it scale

1. **Bank everything upstream.** Cast, voices, product shots, scene stills
   are permanent assets. An asset that works is never regenerated.
2. **One base take per voice, then chain.** Clone the take, not the
   description.
3. **The pair is the asset.** Keep the same still + voice line and re-roll
   the motion until it lands. Iterate the cheap end, never the banked end.
4. **Short beats, long singles.** ~4s talking beats cut well and fail
   cheap; save 8–15s takes for cinematic singles.
5. **Lock a house standard.** One aspect ratio, one still quality, one
   video quality — decided once. Spend the thinking on prompts.
6. **Write the negative space.** Every shipped prompt says what must NOT
   happen: no music, no hands, no text overlays, no beauty filter, no
   celebrity likeness.
7. **Expect takes.** ~100 voice takes and ~90 video rolls became one film.
   Retries are the economics; scale comes from never redoing stations 1–3.

## Swapping a model in — the auditions

A candidate earns a slot by passing the audition, not by its name:

| Slot | The audition | Status |
|---|---|---|
| Cast | Same face, twice, from the same seed — skin not airbrushed | proven in cloud · local slot open |
| Voices | Ten chained lines that still sound like one person, accent intact on line ten | proven in cloud · local slot open |
| Scenes | Two known faces + the product in one frame, all faithful, label legible | proven in cloud · local slot open |
| Motion | A 4s lip-synced talking beat from a still + a voice take — mouth matches the words | proven in cloud · local slot open |
