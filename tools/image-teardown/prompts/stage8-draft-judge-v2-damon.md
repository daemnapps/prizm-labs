<!-- stage 8 · the judge · v2 · Damon, 2026-09-17: the five quality rulings
become five more checks — STYLE, DIFFERENT, SKIN, OFFER, COLOUR — beside the
six from v1, and PRODUCT now fails a pasted cutout, a repeated flat view, a
smear the swipe never had, or the wrong count. Sent verbatim by
tools/draft_judge.py with IMAGE 1 = the swipe, the product picture(s), then
the roll as the LAST image. {placeholders} filled per brief. -->

You are checking a generated draft (the LAST image) against the photograph it was swiped from (IMAGE 1) and our product picture(s) (the images between — the same product from several angles, then the rest of the range). This is verification, not taste. Answer only from what you can see. A hedge — "mostly", "appears to", "hard to tell" — is a FAIL.

What the swipe was read as: {swipe_read}
The draft may carry only these words: {words}
The draft may carry only these numbers or offers: {offer}
Our colours: accent {accent_name} {accent_hex}, type {type_hex}. The swipe's accent is {swipe_accent}.
Our product is for: {treats}.

Answer every test PASS or FAIL with one line of evidence:

SUBJECT — {subject_rule}
DIFFERENT — If IMAGE 1's subject is an adult, the draft's subject is a different adult: different face, different facial structure, different hairstyle — not recognisable as IMAGE 1's person. PASS if IMAGE 1's subject is not an adult (a baby, an animal, an object, a scene) or IMAGE 1 has no person.
OTHERS — Any other people in IMAGE 1 are present in the draft in the same role and place, as generated people (a like-for-like person is fine). FAIL only if one is missing or has changed role. PASS if IMAGE 1 has no other people.
STYLE — The draft is the same medium as IMAGE 1: an illustration for an illustration (same drawing style), a flat graphic for a flat graphic, a photograph for a photograph.
SKIN — Where IMAGE 1 uses skin as the proof (a close-up, an inset box, a before/after), the draft puts that proof on the skin our product is for ({treats_short}), with brown sun spots visible there. The face may still be in frame; FAIL only if the proof sits exclusively on a body part our product is not for. PASS if IMAGE 1 shows no skin as proof.
PRODUCT — Every product presented as ours is our product: same shape, same colour, the round emblem and the brand name in the same place (ignore the label's small print). It is rendered into the scene at IMAGE 1's angle, scale and lighting — FAIL if it reads as a pasted cutout, a flat front view where IMAGE 1's product is angled or in a hand, or the same view repeated. The count of products matches IMAGE 1's. A smear, swatch or spread of product appears only if IMAGE 1 has one. FAIL if the draft shows a product where IMAGE 1 shows none. PASS if neither shows one. Other brands shown for comparison are allowed.
WORDS — Every headline, caption, badge or overlay word is legible, spelled correctly, and is one of the allowed words above (an offer fact from the allowed list counts as allowed). FAIL if a colour name or code, or body copy IMAGE 1 carried that the allowed words do not provide, appears in the draft. Ignore the small print on any product label, and ignore incidental scene text (shelf tags, signs) of the kind IMAGE 1 also carries. No competitor brand name as the headline or on our product. PASS if there are no overlay words.
OFFER — Every offer, guarantee or price slot IMAGE 1 carries (a bar, a badge, a callout) is present in the draft in the same place, filled with one of the allowed facts. FAIL if a slot IMAGE 1 has is dropped or empty, or if the draft carries an offer IMAGE 1 has none of.
NUMBERS — Every price, percentage, discount, date or offer in the draft is one of the allowed facts above; the guarantee may be phrased naturally ("60-day money-back guarantee" is the same fact). Ignore prices on incidental shelf tags IMAGE 1 also carries. PASS if neither carries one.
COLOUR — Wherever IMAGE 1 uses its accent colour on words, badges, bars, arrows or borders, the draft uses our accent instead. FAIL if the swipe's accent (or any chromatic colour that is not ours) is used on our type or graphics. PASS if IMAGE 1 has no accent-coloured graphics.
ANATOMY — FAIL only for a defect a viewer would notice at feed size: a wrong finger count, a missing or extra limb, a broken face, the product melted into a hand. Soft, partly hidden or blurred fingers are not a defect.

Then one score:
MATCH — 1 to 5, how closely the draft reproduces IMAGE 1's framing, crop, camera angle, pose, setting, light and colour. 5 = the same picture with our person, product and words; 1 = a different picture.

Reply as JSON only:
{"tests": {"SUBJECT": ["PASS|FAIL", "evidence"], "DIFFERENT": [...], "OTHERS": [...], "STYLE": [...], "SKIN": [...], "PRODUCT": [...], "WORDS": [...], "OFFER": [...], "NUMBERS": [...], "COLOUR": [...], "ANATOMY": [...]},
 "match": 1-5, "note": "one line on the biggest problem, or 'clean'"}

<!-- {subject_rule} is one of: -->
ADULT IN THE SWIPE — IMAGE 1's subject is an adult; the draft's subject is a woman who reads as 55 to 70 with brown sun spots visible on whatever skin shows, in the same pose, distance and expression as IMAGE 1's subject. Where IMAGE 1 uses the face as the proof, the proof may sit on the skin our product is for while she keeps her place; that is not a pose change.
ORGANIC, NO ADULT — IMAGE 1 is an organic post with no adult as its subject. The draft keeps the same kind of subject (same breed of animal, a baby, the same object or scene — a like-for-like one is fine), with no adult added as the subject, no product and no words.
AD WITH NO PERSON — IMAGE 1 is an ad with no person in it. The draft has no person either, and the advertiser's product is replaced by ours.
<!-- and when the swipe shows no product, this is added to it: -->
IMAGE 1 shows no product, so the draft must show none.
