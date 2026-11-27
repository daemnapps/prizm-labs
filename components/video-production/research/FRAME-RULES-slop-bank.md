# The slop bank

Every rule below was bought with a wrong picture. Each one names the symptom
first, because the symptom is what you actually see on the board — the rule
only makes sense once you recognise what it fixes.

Brand-agnostic: nothing here is about one product or one shoot. Written
2026-09-14/15 across nineteen frames of one ad and the twenty-one corrections
that followed.

---

## A. Before you generate

### 1 · Every identity in the frame gets its element — not just the one the scene is about
**Symptom:** nineteen frames came back with four different women and three
different brushes.
**Why:** the brief attaches the element a scene is *about*. It says nothing
about the woman standing behind, or the device that appears two beats later.
An identity that is not attached is an identity the model invents, every
single time.
**Rule:** scan the scene's prose for each identity's own words and attach its
element whether the brief listed it or not. Print what you added — a silent
fix is a fix nobody can check.

### 2 · A complaint about someone is proof they are in the frame
**Symptom:** the note said "the woman is wrong" and she was not attached to
that scene at all — the prose was about the man, so nothing triggered her.
**Rule:** run the anchor pass over the NOTE as well as the prose.

### 3 · Check the reference by eye. Filenames lie.
**Symptom:** the official stills folder has `..._BACK_i1.jpg` showing the
bristle face and `..._FRONT_i1.jpg` showing the smooth back. Named backwards.
**Rule:** open every reference before you trust it. A wrong reference is worse
than none, because it is confidently wrong.

### 4 · A reference beats a description — but you need the RIGHT view
**Symptom:** six attempts at "the back of the device" while the only banked
reference was a front-on product shot.
**Rule:** if the note asks for an angle you hold no picture of, go and cut one
out of the source material — turntable video, CGI stills, storefront photos —
and bank it. Do not spend another generation guessing.

---

## B. Editing, not re-rolling

### 5 · Two kinds of note, two different calls
**Symptom:** four notes drained as re-rolls; the two about people landed, the
two about products failed identically.
**Why:** a re-roll asks for a whole new photograph and hopes the product lands
inside it. That is the wrong request for a note about one object.
**Rule:**

| The note is about | What runs |
|---|---|
| a thing you own a photograph of | a surgical edit of the finished still |
| staging, a pose, who is in frame | a re-roll carrying the note as a correction |

### 6 · The base image is image one
Position carries meaning to the model, not the filename. Finished still first,
truth references after, in the order you name them.

### 7 · One change per edit
Two changes in one call means neither is specific and the model averages them.
Run it twice.

### 8 · Spell out what is NOT changing
**Symptom:** an edit told only what to change redraws the whole frame.
**Rule:** the HOLD line is half the instruction. Name the faces, the poses, the
room, the crop, the light, the grain — and say "pixel-identical".

### 9 · Never stack edits — go back to the best ancestor
**Symptom:** six passes on one frame turned it to mush.
**Rule:** when a scene needs several corrections, restore the highest-quality
original and make ONE pass carrying all of them. Stacked passes compound every
artefact and every drift.

---

## C. The two failures that cost the most

### 10 · Declare the source frame's aspect and resolution on every edit
**Symptom:** "why is the quality so degraded?" A 1792×2400 plate came back
1024×1024 — square, and a third of the pixels.
**Why:** an edit call with no size asks the model to answer at *its* default.
**Rule:** read the source frame's dimensions, send its nearest supported aspect
ratio, and ask for the top resolution tier. An edit that changes the shape of
the picture is not an edit.

### 11 · Scale needs a ruler that is already in the frame
**Symptom:** "make it two thirds the width" did nothing. Twice.
Then: "no wider than the span of her four gloved fingers, no longer than her
palm" worked on the first try.
**Why:** the model cannot measure the object against itself. It can measure it
against something else in the picture.
**Rule:** express every size note as a comparison to a body part or an object
already in shot.

---

## D. Getting a real product to render

### 12 · Describe the object as well as showing it
A picture tells the model what the thing looks like. Words tell it what the
thing *is*. Give both: silhouette, proportions, materials, controls, and every
mark printed on it.

### 13 · List the marks in physical order, top to bottom, and close the list
**Symptom:** the model invented two diagonal swooshes and put the wordmark on
upside down.
**Rule:** number the marks from one end of the object to the other — (1) shell,
(2) grooves, (3) wordmark, (4) control band, (5) light ring, (6) base — and end
with what is NOT on it. An open description gets decorated.

### 14 · Correct against the observed error, not only against the description
**Symptom:** describing the object harder produced the same invention again.
**Rule:** name what the last take got wrong, as explicit negatives. "It drew
two diagonal slashes; the real marks are four stacked horizontal grooves in the
upper third" beats any amount of positive description.

### 15 · State the orientation
Left alone, a model shows a product's pretty face. If the shot needs the back,
or the thing pressed down out of sight, say so — and say which side the hand is
on.

### 16 · A generic word resolves against what the scene already holds
**Symptom:** "the bottle is wrong" was about to send a WAR shot to the PRIME
reference.
**Rule:** a named product resolves on its own. A generic word — the bottle, the
cap, the device — means whichever one that shot was built with.

### 17 · Three passes with no movement means composite, not generate
If the object has not converged after three surgical passes, the model has
converged on something else. Stop paying for passes. Cut the real packshot in
and marry the light. A near-miss on a brand mark is worse than no product in
frame.

---

## E. Keeping the work

### 18 · Keep every rejected take
It is the record of what the note was about, and the only way to go back to a
clean ancestor when a chain of edits goes wrong. Nothing is deleted.

### 19 · A thumbnail must never outlive its file
**Symptom:** "it does not look like the board is updated."
**Why:** a retouch replaces a still in place, so the filename never changes and
the browser serves its cached copy forever.
**Rule:** rebuild the web copy whenever the master's timestamp moves, and send
`Cache-Control: no-store` on every picture.

### 20 · One board, one address
**Symptom:** two boards up on two ports, one of them showing a run from two
days ago, looking exactly like a board that had stopped updating.
**Rule:** the shelf opens the run; the run always lands on the same address.

---

## The tools these live in

| | |
|---|---|
| `frames.py` | brief → stills. Holds rules 1 and 4 |
| `drain.py` | the board's queue. Holds rules 2, 5, 16 |
| `retouch.py` | the surgical edit. Holds rules 6–15 |
| `elements.json` | the reference bank. Holds rules 3 and 4 |

---

## What one ad cost

A 21.6-second vertical ad: nineteen frames, nineteen motion clips, one
continuous voice-over. Prices marked *measured* came from watching the account
balance move; the rest are published rates. No Higgsfield credits — every call
ran unattended from this machine.

| Step | Model | Calls | Each | Cost |
|---|---|---:|---:|---:|
| The frames — 19 stills, all 19 re-generated with identities anchored, 4 note re-rolls | `gpt-image-2/edit` high | 52 | $0.227 *measured* | $11.80 |
| The retouches — every surgical edit, incl. 4 rebuilt at full resolution | `nano-banana-pro/edit` | 18 | $0.15 / $0.30 *measured* | $3.15 |
| The clips — one per beat, 5s generated then trimmed, 1080×1920 | `grok-imagine-video/v1.5/image-to-video` | 19 | $0.339 *measured* | $6.44 |
| The voice — 71 words, one take | ElevenLabs `eleven_multilingual_v2` | 1 | ~370 chars | <$0.05 |
| **The finished ad** | **21.6 seconds** | **90** | | **$21.44** |
| Abandoned on the way — one Veo test, one Kling clip, both before the routing rule was applied | `veo3.1` · `kling 2.5` | 2 | — | ~$3.20 |

About **a dollar per second of finished video**, and the largest line is frames
— which is what every rule above is for.

## Which model, and why

From the course, adopted whole because it is a routing rule and not a vendor
list. The names rotate; the split does not.

| | |
|---|---|
| A photoreal **person** in a new frame | GPT Image 2 |
| An **edit** to a frame that exists, and anything graphic | Nano Banana Pro |
| A clip where somebody **talks to camera** | Omni |
| A clip where **nobody speaks** — b-roll, product, inserts | Grok |
| Voice, always | ElevenLabs |

A format with nobody talking in it is entirely the fourth row, which is also
the cheap lane. That is why it is the one that scales.

**Artifact:** https://claude.ai/code/artifact/d8cd1d13-e49d-4f19-8e95-c4e9dfbd0e51
