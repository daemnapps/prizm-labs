# Split-screen mechanism verdict — rebuild sheet

A 22.9s post by wyatthwkns: a young man talks to his phone in a dim room in the top band while borrowed footage of an industrial meat-processing floor runs underneath him for the entire runtime — 1,457,882 views, 52,547 likes, post caption "Haters will say it's fake".

**Why it works**
The frame is split for every single second, so the viewer sees the ugly evidence and the person explaining it in the same instant — there is no cut where they can decide the claim was asserted rather than shown. Because the top band never changes at all (same seat, same room, same light, same shirt), the only thing moving on screen is the evidence, and the running caption keeps the sentence unfinished so there is never a clean place to leave.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 1.83s | Composite established: top band, locked mid-close of the man — moustache, short curly light hair, dark top, dim room with warm hallway light behind and dark garments hanging to his right. Bottom band: a heap of pale pink minced meat on an industrial floor beside a metal machine. | `ts` |
| 5.5s | Top band identical, still talking. Bottom band cuts to metal pipework and equipment legs over the same pink meat heap. | `be like` |
| 9.16s | Top band identical. Bottom band cuts to a mass of intestines/offal piled against a whitewashed concrete wall. | *nothing legible at this frame* |
| 12.82s | Top band identical. Bottom band: the same offal mass framed wider, with machinery, a blue bottle and a red container at the top of the band. | `so` |
| 16.49s | Top band identical. Bottom band: dark, out-of-focus brown texture — **too dark to identify from this frame; do not guess it.** | `like` |
| 20.15s | Top band identical to the opening frame. Bottom band: almost entirely black with a faint reddish smear — **not identifiable.** | `about` |

What the frames do not show, and is not being invented here: the audio. The caption fragments are the only evidence of what is being said, so the actual argument of the monologue is unknown — only that it runs continuously and is chopped one clause per beat. The frames also cannot show whether the split ever drops away between the six samples; in every sampled beat it is still a split.

**What carries the value**
The borrowed processing footage in the lower band. The face above it never changes, never demonstrates anything and never holds a product — it is the meat and the offal doing the persuading, and the presenter is there to make it an argument instead of a clip.

**Shoot it**
Two pieces, shot separately, composited into fixed bands.

- *Top band* — phone on a stand or propped, front camera, chest-up, square-on. Set it once and do not touch it for the whole take: same seat, same room, same distance, same shirt. One unbroken take to camera. No handheld drift, no reframe, no second angle.
- *Light* — whatever ordinary light the room has. The reference is genuinely dim, lit by a warm practical behind the subject, and that is part of why it reads as unstaged. Do not add a ring light or clean it up.
- *Wardrobe* — plain dark top, no branding, nothing that draws the eye. The top band is meant to be the flat half.
- *Bottom band* — evidence footage you did not shoot, in a visibly different place, with a visibly different camera and grade. It changes on each beat; it is never explained by the top band, only talked over.
- *The seam* — burn the speech caption in at the join between the bands, same position every beat. One clause per cut, never a complete sentence.

**Or generate it**

```
vertical 9:16 composite, upper third a locked mid-close of {SUBJECT} in their own dim
room talking straight to a phone camera, warm practical light spilling from a doorway
behind them, dark clothes on a wall to one side, phone front-camera look, slight grain,
no retouching; lower two-thirds a full-bleed frame of borrowed evidence footage relating
to {PRODUCT}, plainly shot on someone else's camera in a different place and light, both
bands locked and identical in position every beat, no on-screen text
```

*Motion:* both bands absolutely static — regenerate the presenter band from the same seed on every beat so the room, framing and wardrobe never change, and let only the footage inside the lower band cut to a new source.

*Text overlay:* one line of the spoken narration on the seam between the bands, identical position every beat, changing to the next fragment on each cut and never completing a sentence — `"{clause of what the speaker is saying right now}"`.

**Reference:** https://www.instagram.com/p/DUvvfhvEYCJ/
