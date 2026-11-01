# Cast sheets — v1 (2026-09-23)

The prompts `machine/make_character.py` sends, one section per picture. Every
character starts FROM A REAL REFERENCE (a real photo or real video frame) and
the ADJUSTMENTS that make them our own person (the owner, 2026-09-23: "we always
need realistic references so we can build for real … all characters need to
follow this principle when generating"). The master is an edit of the real
references; every sheet after it is an edit of the master only (plus the real
references for looks and details). Standard: `PRODUCTION-ELEMENTS.md`.

Variables: {who} the identity words · {adjustments} what we change from the
real person · {base} the neutral sheet outfit · {outfit} one look's outfit ·
{details} the detail panels · {real} the realism block below.

## realism
Real unretouched photograph: visible pores, fine lines, natural asymmetry, matte skin with no glare, naturally muted catchlights in the eyes, no beauty filter, no airbrushing, no plastic skin. Identical person in every panel — same face, bone structure, hair, age as the reference. Pure white seamless studio background, soft even diffused light, no shadows on the backdrop. Exactly one person per panel, no other people, no props, no text, no labels, no numbers, no watermark, no logos, no frame borders.

## master
Portrait photograph of a NEW person built from the real person in image 1 (the other images are the same real person or the same role). Keep from the reference: their age, build, skin texture and realism, the register of their clothes and their presence. Change, exactly: {adjustments}. The result: {who}. Chest-up, facing the camera straight on, calm neutral expression with a slight closed-mouth smile, against a plain warm off-white wall, soft even window light. Wearing {base}. Only this one person in the picture. Real phone-camera photograph, natural skin texture, no retouching, no beauty smoothing. No text, no logos, no watermark.

## turnaround
Character turnaround model sheet, four full-body views of the same person evenly spaced in one row — front, three-quarter, side profile, back — standing upright, neutral relaxed pose, arms at sides, whole body head to toe with both feet visible, not cropped, not sitting. The person: {who}. Wearing {base}. {real}

## angles-expressions
Character head-and-shoulders reference sheet, a grid of 10 portraits of the same person, 5 across and 2 down. Top row, neutral expression: front, three-quarter left, three-quarter right, full profile, head tilted slightly up. Bottom row, facing camera: warm natural smile, mid-word talking with the mouth open on an 'ah' sound, mid-word with lips rounded on an 'oo' sound, concerned frown, genuine laugh. The person: {who}. Wearing {base}. {real}

## details
Macro detail reference sheet of the person in image 1, a 2x2 grid of close-ups. {details}. Their exact age in every panel — no younger stand-in hands or skin. The person: {who}. {real}

## light-test
Lighting test sheet, the same person three times side by side, chest-up facing camera, neutral expression: left in soft natural window daylight, centre in warm indoor tungsten lamp light, right in flat overcast outdoor light. Only the light changes. The person: {who}. Wearing {base}. Real unretouched photograph: visible pores, fine lines, matte skin, no beauty filter, no plastic skin. Plain neutral backgrounds. Exactly one person per panel. No text, no labels, no watermark.

## look
Costume continuity sheet: the person in image 1 (the other images show this outfit on real people), full body head to toe in two views side by side — front and back — standing upright, arms relaxed, both feet visible, not cropped. Outfit, exact: {outfit}. Every garment, fastening, sleeve roll and piece of jewellery exactly as described. The person: {who}. {real}
