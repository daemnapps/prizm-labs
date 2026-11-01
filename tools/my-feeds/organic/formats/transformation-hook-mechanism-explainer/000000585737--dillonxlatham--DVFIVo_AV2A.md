# Transformation hook → mechanism explainer — rebuild sheet

A woman films her own face straight after a needling treatment, covered in fresh puncture dots, under the line "Rejuran healing in 20 seconds" — then the same face in three later, calmer states, then two borrowed pieces of evidence explaining why it works. 585,737 views · 5,653 likes · 22.34s · [@dillonxlatham](https://www.instagram.com/p/DVFIVo_AV2A/), caption: "Comment the word 'Simpletics' for a surprise".

**Why it works.** The worst-looking frame is offered first and the claim is attached to it once, so the viewer spends the rest of the runtime auditing a face against a promise instead of listening to a pitch. The explanation is withheld until the change has already been seen, and when it arrives it is somebody else's footage and a published diagram — evidence the poster clearly did not manufacture.

## The beats

| Time | What happens | On-screen text |
|---|---|---|
| 1.79s | Front camera, close, from below eye level. Woman reclined in a treatment chair, towel round her hairline, whole face in a dense grid of fresh red puncture dots and welts. Clinic headrest behind. | "Rejuran healing in 20 seconds" |
| 5.36s | Cutaway out of an aircraft window — two engine nacelles, cloud deck, blue sky. No face. | none (watermark only) |
| 8.94s | Same woman in an aircraft seat, hair slicked back, cream collared shirt. Dots gone; skin textured and mottled across the cheeks. | none (watermark only) |
| 12.51s | Underwater clip of a salmon in open water, a syringe-like instrument entering at its flank. Carries a **different creator's watermark** — a borrowed source. | none (watermark only) |
| 16.08s | Front camera, very close, warm-lit interior. Marks mostly settled; face calm. | none (watermark only) |
| 19.66s | A published explainer card pasted over the top two thirds of a live shot — human and salmon DNA helices, "70 - 80%" between them. A room and a person's mouth visible below the card. | "HUMAN & SALMON DNA: THE SIMILARITY" · "70 - 80%" · small print, only partly legible |

Two things the frames show that are worth copying deliberately:

- **Every beat is an inset.** The whole video sits as a rectangle over one unchanging background plate — a green-walled room with a person in a black top, blurred at most beats and sharp at 12.51s. That plate never changes and is never cut to on its own. It is a repost wrapper, not part of the argument.
- **Two handles appear.** All the face beats carry `@angeonaplane`; the salmon beat carries `@medmap_en`. The account that posted this shot none of it.

What the frames do **not** show, and I have not guessed at: whether there is spoken narration or a subtitle track between the sampled beats (no captions appear at any of the six), what the treatment or brand actually is beyond the word in the hook line, and how much time really passes between the face beats — the "20 seconds" refers to the video, not the healing.

## What carries the value

The operator's own face across the runtime. The dense grid of fresh puncture dots is volunteered as the first frame, and the same face turns up three more times with the marks gone. The salmon clip and the DNA card do not persuade on their own — they arrive after the change has been seen and give it a reason.

## Shoot it

- **Camera.** Phone front camera, arm's length, vertical. Every "before/after" beat is the same grammar: face filling the frame, no reframe inside a beat, no zoom. Nothing is on a tripod and nothing is composed — it should look like a check-in, not a shoot.
- **Beat 1 is the whole job.** Shoot the worst-looking moment, in the chair, before you clean up. If you do not have a genuinely rough opening frame, this format has nothing to run on.
- **Locations change on purpose.** Chair, then a plane seat, then somewhere warm-lit at home. Different rooms and different light are what make the later beats read as later, since there is no date stamp anywhere.
- **Light.** Whatever is actually there — flat clinic light, a plane window, a warm interior lamp. No fill, no ring light, no colour grade. Uneven light across beats helps.
- **Wardrobe.** Ordinary and different at each beat (towel and gown, then a plain collared shirt, then whatever). Hair off the face throughout so the skin is never hidden. No makeup on any face beat — makeup kills the format.
- **The explainer beats cost nothing.** One clip from an outside source and one published diagram, dropped in full-frame at the end. Do not narrate them on screen; let them sit.
- **One line of text, once.** It lands on the opening beat and never comes back.

## Or generate it

The opening beat — the marked face — is the only shot worth generating; the later beats need the same real person and the last two are borrowed material.

```
vertical 9:16 phone front-camera photograph, {SUBJECT} reclined in a treatment
chair with a towel wrapped around their hairline, face filling the frame shot
from slightly below eye level, skin covered in a dense even grid of fresh red
micro-puncture dots and small raised welts across forehead cheeks and jaw
immediately after {PRODUCT}, no makeup, no retouching, dark padded headrest and
a clinic ceiling fixture just visible behind, flat even indoor clinic light,
slight grain, no on-screen text
```

**Motion.** Held at arm's length close on the face with only small breathing drift — no zoom, no reframe, no cut inside the beat, the marked skin never leaving the centre of frame.

**Text overlay.** `{CLAIM} in {N} {UNIT}` — e.g. "{PRODUCT} healing in {N} seconds" — plain white sans-serif, two centred lines in the lower third. Landed once on the opening beat over the worst-looking frame, never replaced and never restated.

**Reference:** https://www.instagram.com/p/DVFIVo_AV2A/
