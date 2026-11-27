# Pinned quote, interview clip — rebuild sheet

A 3:50 podcast cut-down: one quoted line of money advice pinned in a branded band over multicam studio footage of the man who said it, closing on a shop card. 941,928 views · 59,798 likes.

**Why it works** — The band states a flat, arguable claim and attributes it to a named person, so the viewer opens with a position they can agree or disagree with and stays to hear it defended. Because the quote never changes and no speech captions compete with it, every angle change reads as the same argument continuing rather than a new scene.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 18.4s | Brand band across the top quarter; a horizontal interview shot letterboxed below it. Locked medium close-up, near-frontal, of the guest — dark teal crewneck with a bold multicoloured Africa-map graphic, panelled wood and brown curtain behind, soft key from camera left. He looks slightly off-lens at an unseen interviewer. Small "ONE 54" bug bottom right. | DAVID'S MONEY ADVICE: "GET OUT OF DEBT." |
| 55.21s | Hard cut to a second locked angle, three-quarter from his left, tighter, mid-speech. Same man, same wardrobe, same set. | DAVID'S MONEY ADVICE: "GET OUT OF DEBT." |
| 92.02s | Third locked angle, wider three-quarter from the front right. Another person's hands are just visible at the bottom edge — a second participant is in the room. | DAVID'S MONEY ADVICE: "GET OUT OF DEBT." |
| 128.83s | Tightest angle of the run, from his right. He is animated mid-sentence, a hand rising into the bottom of frame. | DAVID'S MONEY ADVICE: "GET OUT OF DEBT." |
| 165.64s | Cut to a second man in another corner of the same set — black zip jacket, grey sofa, chin on his fist, listening, not speaking. White painted brick, slatted wood cabinet, a plant. The listener cutaway. | DAVID'S MONEY ADVICE: "GET OUT OF DEBT." |
| 202.45s | Band and letterbox both drop away for a full-frame brand card: hosts' names and logo on white, a white-seamless studio portrait of the two hosts, the shop URL over an Africa silhouette. | HOSTED BY GODFREY & AKBAR / ONE 54 PODCAST / SHOP NOW AT ONE54AFRICA.COM |

**What carries the value** — The pinned attributed quote. A named person's short, arguable piece of advice is held word-for-word on screen for the entire runtime while the footage underneath is that person actually saying it. The band is the claim; the unedited conversation is the receipt. Nothing is demonstrated and no product appears until the last beat.

## Shoot it

- **Camera.** Shoot horizontal and crop into the lower three-quarters — the vertical frame is a band plus a letterboxed 16:9 shot, not a vertical shoot. You need at least three fixed positions: two on the speaker (a near-frontal medium and a tighter three-quarter from the other side) and one on the listener. Every angle is locked — no pans, no pushes, no handheld anywhere in the six frames. Coverage changes only by hard-cutting between angles. On phones: two on tripods running on the speaker, one on the listener, then cut between them. One phone repositioned between takes will not work — the conversation has to be continuous.
- **Light.** Soft key from camera left, warm, with a practical glowing in the background; shallow depth so the set reads as a room rather than a backdrop. Warm and domestic, not clinical.
- **Wardrobe.** Plain dark crewneck with one bold graphic across the chest — the only colour in the frame. The listener is in plain black. Nothing patterned, nothing that competes with the band.
- **Set.** A built living-room set with two usable corners: one warm and enclosed (panelled wood, heavy curtain) for the speaker, one bright (white painted brick, slatted cabinet, plant) for the listener. The two corners are what make the cutaway read as a different place in the same room.
- **What you cannot fake.** This needs a person whose name in the band is itself a reason to watch, and a second person for the reaction cut. Filed `replicable_without_talent: false` for that reason — the structure is cheap, the casting is not.

**What the frames do not show:** the audio, so nothing here can say what is actually being argued. There are no burned-in speech captions at any of the six sampled beats — all four speaking frames are mid-sentence with nothing under the band — but six stills across 230 seconds cannot rule out captions in the gaps. Nothing shows whether the two men ever appear in frame together, whether any camera moves inside a shot, or what happens between 0s and 18.4s before the first sample.

## Or generate it

```
vertical 9:16 composite: the top quarter is a flat patterned brand band in two
colours with a headline reversed out of it; the lower three-quarters is a
horizontal studio-interview frame letterboxed in — medium close-up, chest up, of
{SUBJECT} seated in a warm built podcast set, near-frontal but looking slightly
off-lens at an unseen interviewer, wearing a plain dark crewneck sweater with one
bold graphic across the chest, panelled wood wall and a heavy curtain behind,
soft key light from camera left with a warm practical in the background, shallow
depth of field, broadcast-camera look rather than phone grain, small square
channel bug bottom right, no on-screen text. {PRODUCT} is not in this shot at
all — it appears only on the end card.
```

**Motion.** The camera does not move: one locked broadcast angle, only {SUBJECT} talking and gesturing — coverage changes by hard-cutting to a different locked angle of the same person in the same seat, never by moving the camera. Generate each angle from the same seed so the wardrobe and set stay identical.

**Text overlay.** `{NAME}'S {TOPIC} ADVICE: "{SHORT QUOTE}."` — pinned in the top band, word-for-word identical from the first frame to the last, with two words inside the quote reversed out in a coloured box. Nothing else on screen at any point. The final beat replaces the whole frame with a brand card: `{SHOW}` / `SHOP NOW AT {URL}`.

**Reference:** https://www.instagram.com/p/DZle7NitHD5/
