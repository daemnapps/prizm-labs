# Subtitled monologue, angle cuts — rebuild sheet

A 42.68s clip of one seated man telling the story of his brother's death to an off-camera interviewer, carried entirely by white all-caps caption fragments — 1,729,151 views, 103,840 likes, posted by `colesnyder_`.

**Why it works**

Every caption is one clause of a continuous spoken sentence and every clause stops before it resolves, so there is never a frame where the story is finished and the viewer is free to leave. Because the camera never moves and there is nothing else in the frame to look at — no product, no cutaway, no graphic — the only thing changing is the man's body under the words, and his hand going to his temple reads as recall rather than performance.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 3.41s | Medium shot of a man reclined low on a couch — grey Puma t-shirt, blue wristband, forearm tattoos. A black handheld mic stands in the lower centre of frame; a black-and-white plaid cushion fills the bottom edge. Warm vertical wood slat panelling behind, pale green chair back at the left edge. His eyeline is off-camera left, never at the lens. | WHEN MY OLDEST BROTHER DIED |
| 10.24s | Identical framing. He has sat up slightly and turned toward the lens, mouth open mid-sentence, right hand raised near the mic. | THE DOCTOR TELL MY MOM |
| 17.07s | Same frame. He leans forward, hand up beside his temple, eyes wide — the most animated beat in the sample. | I'M CRYIN |
| 23.9s | Same frame. He settles back and sweeps his right hand across the middle of frame, motion-blurred. | MY OTHER BROTHER |
| 30.73s | Same frame. Upright and still, hands lowered out of the caption, jaw set. | YOU THE LAST ONE |
| 37.56s | Same frame, slightly wider read of the wood panelling. Head dropped, eyes down, hands out of shot — the only beat where he is not looking outward. | I TOUCH HIS FEET |

Two things the frames do not show, and I am not filling them in:

- **The end of the third caption.** His raised hand crosses in front of it. What is visible reads `I'M CRYIN` — it may continue.
- **Whether the video cuts between camera angles.** Six stills 6.8s apart all sit in the same position on the same setup, so there is no evidence of a second angle. Interview clips of this kind often cut between two cameras, but nothing in this sample proves it either way. The format name carries "angle cuts" because it is the library's existing id for a subtitled monologue; treat the single locked angle below as the safe rebuild.

**What carries the value**

The unfinished clause. Not the room, not the wardrobe, not the camera — the persuasion is entirely in a real spoken account broken into pieces that each stop early, so the sentence is still open when the video ends. The body under it is the corroboration.

This is the one format on the shelf that **cannot be rebuilt without a person and a true story**. The frame, the light and the caption style are free; the testimony is not. Do not hand this structure to someone reading a script — the format's whole credential is that the speaker is remembering rather than delivering.

**Shoot it**

- **Camera:** one camera, locked on a tripod, and it does not move or reframe for the entire runtime. Seated eye level, medium shot — chest up plus a little room. Frame is near-square (roughly 4:5), not full-height vertical.
- **Blocking:** the speaker sits low and reclined on a soft couch, and talks to a person standing or sitting off-camera left. **Never to the lens.** The off-camera eyeline is what makes it read as an interview instead of a piece to camera.
- **Room:** something with texture behind — the source uses warm vertical wood slats with the pale green back of a chair intruding at the left edge. A visible microphone in the lower centre of frame and a cushion breaking the bottom edge both help; they say "this was a real conversation someone else recorded".
- **Light:** soft, cool daylight from the left mixing with warm bounce off the wall behind. Nothing shaped, no key light look.
- **Wardrobe:** plain — a grey t-shirt, a wristband, whatever the person already wears. Nothing styled, no brand hero, no product in frame at any point.
- **Captions:** white all-caps serif, centred low at about chest height, no box, no outline, no punctuation. One clause per beat, roughly every 6–7 seconds. Cut every clause before it resolves.

**Or generate it**

```
vertical 9:16 photograph, framed near-square inside the frame, {SUBJECT} seated low
and reclined on a soft couch in a plain grey t-shirt, a blue band on one wrist,
forearm tattoos visible, a black handheld microphone standing in the lower centre of
frame, a black-and-white plaid cushion filling the bottom edge, warm vertical wood
slat panelling behind and the pale green back of a chair at the left edge, soft cool
daylight from the left mixing with the warm wood, camera at seated eye level, medium
shot, {SUBJECT} looking off-camera left at an unseen interviewer and never at the
lens, interview-camera look, no retouching, no on-screen text, no {PRODUCT} anywhere
in frame — the source video contains no product at all
```

**Motion:** camera absolutely static in the same position for every beat — generate all six beats from the same seed frame so the room, the microphone and the cushion never shift; only `{SUBJECT}`'s posture, hands and eyeline change.

**Text overlay pattern:**

```
{CLAUSE}
```

One fragment of a single continuous spoken sentence per beat, centred low at about chest height, white all-caps serif, no box, no outline, no punctuation. Every fragment stops before it resolves and the sentence is never completed on screen.

**Reference:** https://www.instagram.com/p/DXK0-aJASmI/
