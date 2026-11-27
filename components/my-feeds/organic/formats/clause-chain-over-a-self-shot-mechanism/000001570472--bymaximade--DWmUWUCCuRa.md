# Clause-chain mechanism demo — rebuild sheet

A 22.66s piece by **bymaximade**: one woman eating in a tea room, a narration chopped into fragments that never finish a sentence, and two extreme macro cut-ins on her own skin and eye that prove each fragment the second after it lands. **1,570,472 views · 27,037 likes.**

**Why it works** — The sentence is never completed at any beat, so there is no clean place to leave: you read "but your brain", then "was enough", then "see the", and you are still mid-clause when the video ends. Each clause is paid off by a cut to a scale a normal shot cannot reach — pores, peach fuzz, a wet catchlight in the eye — so the claim is shown rather than argued, and the viewer does the concluding themselves.

## The beats

| Time | What happens | On-screen text |
| --- | --- | --- |
| 1.81s | Extreme macro on the lower face — nose, lips filling frame, pale wooden chopsticks resting on the lower lip. Pores, uneven tone, small freckles, fine peach fuzz on the upper lip. Background fully out of focus. | but *your* **brain** |
| 5.44s | Cut wide to chest-up: black scoop-neck tank, thin black cord with an irregular silver pendant, hair pulled back with loose strands, chopsticks held beside the mouth, eyes off-camera. Dark wood shelving with blue-and-white teapots against a white tile wall. | *was* enough |
| 9.06s | Tighter, head and shoulders, same room and wardrobe, facing the lens, slight smile, chopsticks at the lips. | see the |
| 12.69s | Extreme macro cut-in on the eye and brow — separate brow hairs and lashes, brown iris with one hard catchlight, moisture on the lower lid. No room in frame. | **is there** *(bold, yellow)* |
| 16.32s | Back to head and shoulders in the identical room, facing the lens, mouth closed, neutral. | *this* **was made** *(bold, yellow)* |
| 19.94s | An almost entirely white frame with one word in bold red serif at the right. **The still shows nothing else** — no subject, no room; what else is on this card, and whether it is an end card or a title card, cannot be read from the frames. | the |

Two things the frames do not settle, and I have not filled in: **whether the camera moves** inside any beat (six stills cannot show it), and **whether she is speaking on camera** — her mouth is around the chopsticks in three of the six frames, so the narration may well be voiceover rather than sync.

## What carries the value

The macro texture on the subject's own face: pores, uneven tone, freckles, peach fuzz on the upper lip, separated lashes, the wet catchlight in the eye. Nothing is demonstrated and no product does anything — the imperfection *is* the payload, and the clause fragments exist only to point at it a beat before you see it. The post caption confirms the intent: *"natural skin flaws, uneven tone, tiny freckles, even the subtle peach fuzz… your brain reads those imperfections as proof."*

Note the ask lives entirely in the post caption, not on screen: *"Comment 'AI' for the full breakdown + all the prompts used in this video."* No CTA appears in any frame.

## Shoot it

**Camera** — Two scales, nothing else. A chest-up / head-and-shoulders frame at face height, subject centred, and an extreme macro on one feature. Alternate them: macro, wide, tighter, macro, wide. Shoot the macro with a phone macro mode or a clip-on lens close enough that the pores separate — if the skin reads smooth, the format has already failed.

**Light** — Bright, soft, flat and frontal, like a window straight ahead. No hard shadow anywhere in the frames. For the eye macro, the single hard catchlight on the iris is the shot; put one small bright source in front of the subject and check you can see it reflected before you roll.

**Wardrobe and face** — Plain black scoop-neck tank, one thin cord necklace with a single pendant. Hair pulled back with a few loose face-framing strands. Minimal makeup and **no skin retouching at any stage** — the freckles, tone unevenness and upper-lip fuzz are the evidence. A prop in the hand that comes to the mouth (here, chopsticks) gives the macro something to enter frame with.

**Room** — One location, dressed and legible but out of the way: shelving with objects behind, a plain tiled wall. It never changes across the whole runtime.

## Or generate it

The image prompt for the hook beat (1.81s), the shot that has to land:

```
vertical 9:16 extreme macro photograph of {SUBJECT}'s lower face — nose tip,
upper lip and lips filling the frame — with {PRODUCT} entering from the lower
left and resting against the lower lip, visible skin pores, uneven tone, small
freckles and fine peach fuzz on the upper lip and side of the nose, everything
behind the face thrown fully out of focus, soft frontal daylight with no
visible fixture, shallow depth of field, phone-camera look, slight grain, no
retouching and no skin smoothing, no on-screen text
```

**Motion** — Camera held very close and near-still on the mouth; the only movement is {PRODUCT} coming to the lip. The stills cannot tell us whether the source moved, so generate it locked.

**Text overlay pattern** — One fragment of a single continuous sentence per beat, centred just below the middle of frame, lowercase sans-serif with a soft drop shadow, one word italic and the key word bold — the bold word switching to yellow on the later beats. Every fragment stops mid-sentence and none of them completes it:

`but {your} {noun}` → `{was} enough` → `see the` → `{is there}` → `{this} {was made}`

**Reference:** https://www.instagram.com/p/DWmUWUCCuRa/
