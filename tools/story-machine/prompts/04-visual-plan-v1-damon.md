# Stage 4 — Visual Plan (v1)

Decides what's on screen under the voice. Two looks, set by `{look}`.

- **broll** — the reference channel's look: a fast stream of satisfying
  process footage that has nothing to do with the story. The eyes are kept
  busy; the ears get the story.
- **animated** — AI-animated scenes of the story itself, one consistent
  character, built shot by shot.

---

You are planning the visuals for a story narration. You are given the
finished narration with its beat marks.

## What you are given

- `{narration}` + `{beat_marks}` — from Stage 2 or 3 (any length; the plan covers the whole narration)
- `{look}` — `broll` or `animated`
- `{footage_lane}` — **broll only.** What satisfying footage this brand owns
  or has licensed (e.g. a product being poured, pressed, cut, applied;
  a craft process; a machine). Never footage the brand doesn't have rights to.
- `{character}` — **animated only.** The one character reference to keep
  consistent.

## Always (both looks)

- **9:16, 1080×1920.**
- **Captions: one word at a time**, dead centre, heavy rounded white font,
  thick black outline, no box. A word lands on the beat it's spoken. Quoted
  dialogue keeps its quote marks on screen.
- **First 2 seconds: the title card** — the title set as a social post
  (avatar, handle, the title as the post text), floating over the first clip.
- **A cut every 2–4 seconds.** Never hold a shot longer than 5.
- **No faces telling the story.** The voice is the only narrator.
- **Last 2 seconds** (ad lane): end card — product, price, one button.
  Organic lane: no end card; the last word just ends.

## broll look

- List clips in order, one per 2–4 seconds, enough to cover the whole narration.
- Each clip must be **visually complete in itself** (a pour finishes, a cut
  lands, a mould releases) — the micro-satisfaction is what holds the eyes.
- Raise intensity at the turn: the most satisfying clip in the set lands on
  the turn's first word.
- Colour: bright, saturated, clean backgrounds. Nothing dark or muddy.

## animated look

- One shot per beat line, 3–5 seconds each.
- Every shot description starts with the `{character}` reference name so
  the image model keeps them consistent.
- Write the image prompt and the motion prompt separately for each shot.
- Mix in at least one real-footage shot every 30 seconds (a real place, a
  real object) — channels that are 100% AI-generated get flagged as mass
  produced.

## Return

```
LOOK: <broll | animated>
RUNTIME: <seconds>
TITLE CARD: handle "<handle>" · post text "<title>"

SHOTS:
<n> | <start s>–<end s> | <beat> | <what's on screen> | <image prompt (animated)> | <motion prompt (animated)>

TURN SHOT: <shot number that lands on the turn, and why it's the strongest>
CAPTION STYLE: one word · centre · white heavy rounded · black outline 8px
END CARD: <ad lane: product · price · button text | organic: none>
```
