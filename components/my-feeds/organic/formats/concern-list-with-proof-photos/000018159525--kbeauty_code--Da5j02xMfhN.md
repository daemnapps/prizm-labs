# Concern list with proof photos — rebuild sheet

Two people in white clinical coats stand in one hospital corridor and run through six body concerns — one big label and one unretouched close-up photo per concern — in 13.7 seconds: 18,159,525 views, 393,170 likes (@kbeauty_code).

**Why it works**

Each beat hands the viewer a two-word label and a tight photo of the actual problem, so recognition happens before any claim is made — the person who has dark underarms or cracked heels stops on their own frame. The white coats and the real clinic corridor are what make showing those photos feel like diagnosis instead of shock content, and the fixes themselves sit mostly in the caption, so the video indexes problems and the caption pays them off.

**The beats**

| Time | What happens | On-screen text |
|---|---|---|
| 1.1s | Woman in an open white coat over black, in a grey stone clinic corridor with metal double doors and a Korean wall sign. One arm raised above her head, baring the underarm. A white-bordered macro photo of a dark underarm is composited over the lower half. | Dark Armpits |
| 3.29s | Man in an open white coat over a black tee, small badge on the lapel, same corridor and framing, hand raised toward his own jaw. Inset photo: pink skin dense with ingrown hairs. | Ingrown Hair |
| 5.48s | Woman standing centre, coat open, smiling to camera, one leg forward. Inset photo: an upper thigh with strawberry-legs texture. | Strawberry Legs |
| 7.67s | Both presenters in frame together — woman left, man right holding a small dark object at chest height and gesturing. Inset photo: a hand holding a PanOxyl Acne Foaming Wash bottle, label readable. This is the one beat where the label is **white, not yellow**, and names the ingredient instead of a concern. | Benzoyl Peroxide |
| 9.86s | Woman raises one arm again, other hand toward her side. Inset photo: a grey t-shirt underarm with a sweat mark. | Body Odor |
| 12.06s | Framing slightly tighter on the man alone in his white coat, facing camera. Inset photo: a cracked, callused heel. | Callused Heels |

Where the frames don't tell us:

- There is no audio in the stills, so nothing here says what is spoken. The caption implies they talk through each pairing.
- Six stills across 13.7s can't prove the cut rhythm. The stills land 2.19s apart and five of six show a concern while one shows an ingredient, which reads like each concern is actually two half-beats — concern photo, then answer photo — and the sample caught one answer half. Treat that as a read of the pattern, not a measured fact.
- Stills can't distinguish a locked tripod from a very steady handheld. What is certain is that the framing, the corridor and the subject position are effectively identical across all six.
- The caption is truncated at "The Ordinary G", so the last pairing is incomplete in the record.

**What carries the value**

The composited macro photos of the real problems — the dark underarm, the ingrown hairs, the cracked heel. They are cropped tight, unretouched and unglamorous, and they sit under a plain label with nothing else competing. The presenters, the coats and the corridor are not doing the persuading; they are the permission slip that lets those photos be shown as clinical rather than gross.

**Shoot it**

- **Camera.** Phone vertical on a tripod at chest height, subject about two metres away, framed mid-thigh up. Do not change the framing between concerns — the repetition is the format. One take per concern, or one long take with the presenter resetting between labels.
- **Location.** A plain hard-surfaced corridor: flat walls, a door, a wall sign, nothing decorative. Any lobby, stairwell landing or office hallway works. What matters is that it looks institutional and stays identical every beat.
- **Light.** Whatever the ceiling gives you. Flat, even, slightly cool overhead light, no window, no lamps, no colour grade. Trying to make it pretty breaks it.
- **Wardrobe.** Open white coat over a plain black top. Nothing branded, nothing patterned. In the source there is a small badge on the man's lapel.
- **The insets.** These are the job. Source or shoot one tight close-up per concern, crop hard so the problem fills the panel, and drop it in over the lower half of the frame with a white border. No smoothing, no filter — the moment it looks retouched it stops being evidence. Never let a panel cover the presenter's face.
- **Labels.** Two or three words, same position every beat, heavy bold title case with a black outline, yellow for a concern and white when you name the fix.
- **The honest limit.** In the source the authority is real — the caption says a dermatologist and a pharmacist, siblings. The coat is making a claim, not just a look. If your presenters aren't credentialed, rebuild the structure without the clinical costume: the photos and the labels carry it, and a false credential is the one part of this that will cost you.
- **Talent.** No performance needed. Nobody is being charismatic in these frames — they stand, gesture at the body part, and let the panel do the work.

**Or generate it**

Image prompt for the opening beat, the one that has to land:

```
vertical 9:16 photograph, {SUBJECT} in an unbuttoned white clinical coat over a
plain black top, standing centred in a hospital corridor — pale grey stone walls,
brushed-metal double doors, a small wall sign, recessed ceiling lights and a
ceiling dome camera — one arm raised above the head baring the underarm, the other
hand relaxed at the side, facing camera, framed from mid-thigh up at chest height
about two metres from the lens, flat even overhead fluorescent light with no window
light and no colour grade, phone-camera look, slight compression, no retouching,
no on-screen text, and the lower half of the frame kept clear and uncluttered so a
white-bordered close-up panel — the body concern itself, or {PRODUCT} held in a
hand on the answer beats — can be composited in afterwards
```

**Motion:** camera holds still at chest height with the same framing as every other beat — only the subject's raised arm and speaking move; no push, no drift, no zoom.

**Text overlay:** one label per beat, same position mid-frame every time, heavy bold sans in title case with a black outline: `{CONCERN}` in yellow on the problem beats, swapping to white for `{INGREDIENT}` on an answer beat — never more than two or three words, and never overlapping the face or the composited panel.

Generate the corridor plate once and reuse it for every beat so the room matches exactly; the close-up panels are composited in the edit, not generated into the frame.

**Reference:** https://www.instagram.com/p/Da5j02xMfhN/
