# Cast sheets — v4 (2026-11-10)

*v4: de-slop is step 2, inside this process (owner ruling 2026-11-10). The master is made as `full/master-raw.png`; the `deslop` section re-textures it from two real texture photos (skin, hair) out of `runs/ai-elements/_texture-refs/`, named in the spec's `texture`; the take becomes `full/master.png` and every sheet is made from it. The headshot now takes its face from the de-slopped master only, with the skin photo as its texture reference: v3 sent the real person's frame with it, and a blindfolded master let that real face through. Everything else in v3 stands.*

*v2: the REAL BODY rides with the face. the owner, on a real person drawn too short: "you need to index her body directly from her tiktok and ig." v1's turnaround and looks were drawn from a chest-up master alone, so every body came out average. Now the full-body sheets also carry up to three full-body frames of the real person, and the prompt says so. And no product ever appears in a cast sheet (the tool refuses one) — v1 let a detail panel draw an invented tube. Everything else in v1 stands.*

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
Every visible bit of skin at the exact realism of the headshot (when it is given as a reference). Real unretouched photograph of a real human being: visible pores, peach fuzz (fine vellus hair) on the cheeks, jaw and upper lip, fine lines and creases with shadow in them, natural asymmetry, a faint natural sheen, real eyes with feeling in them, wet lid lines, individual lashes and catchlights, stray hairs. No beauty filter, no airbrushing, no smoothing, no waxy or plastic skin, no AI glow (the owner, 2026-10-28: "truly real ... zero plastic look"). Identical person in every panel — same face, bone structure, hair, age as the reference. Pure white seamless studio background, soft even diffused light, no shadows on the backdrop. Exactly one person per panel, no other people, no props, no products, no text, no labels, no numbers, no watermark, no logos, no frame borders.

## master
Portrait photograph of a NEW person built from the real person in image 1 (the other images are the same real person or the same role). Keep from the reference: their age, build, skin texture and realism, the register of their clothes and their presence. Change, exactly: {adjustments}. The result: {who}. Chest-up, facing the camera straight on, calm neutral expression with a slight closed-mouth smile, against a plain warm off-white wall, soft even window light. Wearing {base}. Only this one person in the picture. Real phone-camera photograph, natural skin texture, no retouching, no beauty smoothing. No text, no logos, no watermark.

## turnaround
Image 1 is the person's face and identity; any further images are full-body photos of the SAME real person — match her height, build, leg length and proportions to those exactly, never an average body. Character turnaround model sheet, four full-body views of the same person evenly spaced in one row — front, three-quarter, side profile, back — standing upright, neutral relaxed pose, arms at sides, whole body head to toe with both feet visible, not cropped, not sitting. The person: {who}. Wearing {base}. {real}

## angles-expressions
Character head-and-shoulders reference sheet, a grid of 10 portraits of the same person, 5 across and 2 down. Top row, neutral expression: front, three-quarter left, three-quarter right, full profile, head tilted slightly up. Bottom row, facing camera: warm natural smile, mid-word talking with the mouth open on an 'ah' sound, mid-word with lips rounded on an 'oo' sound, concerned frown, genuine laugh. The person: {who}. Wearing {base}. {real}

## details
Macro detail reference sheet of the person in image 1, a 2x2 grid of close-ups. {details}. Their exact age in every panel — no younger stand-in hands or skin. The person: {who}. {real}

## light-test
Lighting test sheet, the same person three times side by side, chest-up facing camera, neutral expression: left in soft natural window daylight, centre in warm indoor tungsten lamp light, right in flat overcast outdoor light. Only the light changes. The person: {who}. Wearing {base}. Real unretouched photograph: visible pores, fine lines, matte skin, no beauty filter, no plastic skin. Plain neutral backgrounds. Exactly one person per panel. No text, no labels, no watermark.

## headshot
THE ONE FACE REFERENCE. A real, unretouched photograph of the person in image 1, the same face exactly — same bone structure, eyes, eyebrows, nose, mouth and hairline; image 2 is a skin texture photo only, never a face to copy; head and shoulders filling the frame, shot on a 100mm macro lens at f/8 in soft side daylight with a little light behind them, every detail resolved. THE EYES: a real feeling in them, the muscles around the eyes engaged, wet and clear with catchlights, the wet line of the lower lid, individual lashes, stray eyebrow hairs. THE SKIN, unmistakably real at this distance: individual pores across the nose, cheeks and forehead; peach fuzz on the cheeks, jaw, upper lip and temples catching the side light; the skin's own micro-texture for their age; every line with soft shadow inside it; a faint natural sheen; the skin's own marks only as the person really has them. No smoothing, no retouching, no beauty filter, no waxy or plastic skin, no airbrush, no AI glow. Plain grey background. {real}

## hands-closeup
A real, unretouched macro photograph of the hands of the person in the first reference, both hands resting palms down, then one turned palm up, filling the frame, shot on a 100mm macro lens at f/8 in soft side daylight, the skin at the exact realism of the headshot: individual pores, fine hair on the backs of the hands and wrists, the skin's own texture for their age, veins and tendons, knuckle creases with shadow in them, natural nails, and their own marks exactly as the details sheet shows them. No smoothing, no retouching, no waxy or plastic skin, no AI glow. Plain grey background. {real}

## look
Costume continuity sheet: the person in image 1 (the other images are real photos — of this outfit, or of this same person's full body: match her height, build and proportions to them exactly), full body head to toe in two views side by side — front and back — standing upright, arms relaxed, both feet visible, not cropped. Outfit, exact: {outfit}. Every garment, fastening, sleeve roll and piece of jewellery exactly as described. The person: {who}. {real}

## deslop
Image 1 is the character: keep this exact person, same face, bone structure, eyes, expression, hair shape, hairline, wardrobe, framing and background. Change only the surface texture. Take the skin texture from Image 2 ({skin}) and apply it to the face, forehead, nose and neck, keeping the character's own skin tone and redness{keep}. Remove any over-etched or plastic AI skin. Take the hair texture from Image 3 ({hair}) and apply it to the {hair_on}, keeping its shape and color. Real fabric weave on the clothes. Unretouched phone photo, soft window light, slight grain. Do not copy any face or person from Images 2 or 3.
