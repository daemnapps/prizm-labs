# Word-per-beat procedure — rebuild sheet

A fully CGI kitchen loop: six ingredient characters take turns fixing a close-up of bad skin, one bold word on screen per beat — @realhealthschool, 37.15s, 3,386,104 views, 159,056 likes.

## Why it works

Only one word is ever on screen, it changes every beat, and the sixth one is the bare conjunction **AND** — so at 32.69 seconds of a 37-second video the sentence still hasn't finished, and you can't leave mid-line. The composition never resets either: the bowl sits dead centre and the afflicted skin is pinned to the right edge the whole way through, so every new character reads instantly as another answer to a problem that never left the frame.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 2.97s | Sunlit kitchen counter. An animated tomato slice with cartoon eyes and limbs stands on a glass bowl of coarse white granules, arms up, a puff of grains in the air. Right edge: extreme close-up of a nose and cheek, pores and blackheads visible. | ACNE |
| 8.92s | A ginger/turmeric-root character presses white paste onto an acne-covered cheek with its own hand. Below it, a bowl of thick white cream, a spoon, yellow-orange powder spilled on the wood. | INFLAMMATION |
| 14.86s | A lemon-slice character, eyes wide and mouth open, dusted with white grains, over the same bowl of granules. Close-up of a spotted nose and cheek at the right. | OIL |
| 20.8s | A green spiked aloe-leaf character over a bowl of clear green gel, laying a hand across the closed eye of the face — framing has moved up from cheek to brow. | PUFFINESS |
| 26.75s | An amber honey-drop character on a bowl of dark coffee grounds, holding a handful of them. The skin at the right is now visibly dry and flaking. | CELLS |
| 32.69s | A white egg character with oil running down it, standing in a bowl of olive oil, lifting a hand to the lips of the face. | AND |

**What the frames don't show.** Six stills across 37 seconds is one sample per beat — there are almost certainly more words on screen between them, and "AND" is proof of it: a conjunction only exists inside a longer running line. I can't hear whether there's narration, can't confirm whether the camera drifts inside a beat (the framing is the same setup at every sample, and nothing moves between them), and can't see the ending — the caption promises "The last skin mix blew my mind 🤯", so a final pairing lands after the last frame I have. The face is not one continuous person either; each beat cuts to a close-up that matches that beat's complaint.

## What carries the value

The running one-word line that never closes. Each beat pins a single complaint on screen and a new ingredient character steps up as its answer, so you stay to collect the list — and the bare AND on beat six proves the list is still going. The characters are the delivery; the unfinished line is the retention.

## Shoot it

The source is fully generated — there is no shoot behind it. To do the live-action version on a phone:

- **Camera.** Phone vertical on a tripod at counter height, lens roughly level with the bowl. Lock it and do not move it between beats — same distance, same height, same bowl position every time. All the change must come from what's in the frame, never from the camera.
- **The frame.** Clear glass bowl of the ingredient centred in the lower third, the ingredient itself scattered loose on the wood beside it, and the person's face entering hard from the right edge in extreme close-up — close enough that only nose, cheek or eye is in shot. Two thirds product, one third skin, every beat.
- **Light.** One window to the left of frame, daylight, nothing else. Skin unretouched and unfiltered — the visible condition is the evidence, so no soft light, no smoothing, no makeup.
- **Wardrobe.** None to plan for; nobody is dressed in shot, only a face at close range. Hands should be bare — no rings, no polish, no sleeves in frame.
- **Beats.** One ingredient per beat, ~6 seconds each, six of them, and the ingredient makes contact with the skin (a touch, a dab, a press). Change the framing slightly per beat to match the complaint — cheek for acne, brow and eye for puffiness, lips for dryness.
- **Text.** One word, held for the whole beat, replaced on the cut.

## Or generate it

The image prompt for the beat that has to be right — the one where the character actually touches the skin:

```
vertical 9:16, a 3D-animated character made from {PRODUCT} — large cartoon eyes,
a mouth, slim limbs — standing on the rim of a clear glass bowl filled with
{PRODUCT}, on a sunlit wooden kitchen counter; the character reaches one hand
across the frame and presses it against the cheek of {SUBJECT}, whose face fills
the right half of the frame in extreme close-up, photo-real and unretouched with
the untreated skin condition plainly visible; behind them a real kitchen —
multi-coloured tiled backsplash, a window with morning daylight at the left, a
potted herb, a crock of wooden spoons, glass jars; loose {PRODUCT} scattered on
the wood beside the bowl; glossy Pixar-style rendering for the character against
photographic skin and room, shallow depth of field, warm side light from the
window, no on-screen text
```

**Motion.** Camera holds one static composition for the whole beat — no push, no pan, no rack — and only the character moves, reaching across to touch the face.

**Text overlay.** One word per beat, bold white all-caps with a heavy black outline, centred at mid-frame height, replaced on every ingredient: `{CONCERN}` → `{CONCERN}` → `{CONCERN}` → … → `AND`, so the line is still running when the last beat lands and the list never visibly closes.

**Consistency note.** Generate every beat from the same kitchen seed so the backsplash, window, herb and counter match exactly — the fixed room is what makes the character swap read as a list rather than six unrelated clips.

**Reference:** https://www.instagram.com/p/DWUTvzuCpHs/
