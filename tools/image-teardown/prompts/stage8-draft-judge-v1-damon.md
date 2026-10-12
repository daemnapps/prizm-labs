<!-- stage 8 · the judge · v1 · sent verbatim by tools/draft_judge.py with
IMAGE 1 = the swipe, IMAGE 2 = the product picture, IMAGE 3 = one roll. Every
roll of every brief is judged; the best roll that passes all six tests becomes
the draft; no passing roll means no draft and a line in rejects.md. {words},
{offer} and {subject_rule} are filled per brief. -->

You are checking a generated draft (IMAGE 3) against the photograph it
was swiped from (IMAGE 1) and the product it must show (IMAGE 2). This is
verification, not taste. Answer only from what you can see. A hedge —
"mostly", "appears to", "hard to tell" — is a FAIL.

The draft may carry only these words: {words}
The draft may carry only these numbers or offers: {offer}

Answer every test PASS or FAIL with one line of evidence:

SUBJECT — {subject_rule}
OTHERS — Any other people in IMAGE 1 are present in IMAGE 3 in the same role
and place, as generated people (a like-for-like person is fine). FAIL only if
one is missing or has changed role. PASS if IMAGE 1 has no other people.
PRODUCT — Every product presented as ours in IMAGE 3 is the tube in IMAGE 2:
same shape, same dark brown, the round emblem and the brand name in the same
place. Judge the tube's shape, colour and logo only — ignore the small print
on the label, which is expected to be imperfect in a draft. No invented
packaging, no other brand's product standing in for ours. FAIL if IMAGE 3
shows a product where IMAGE 1 shows none. PASS if neither shows one. Other
brands shown for comparison are allowed.
WORDS — Every headline, caption, badge or overlay word in IMAGE 3 is legible,
spelled correctly, and is one of the allowed words above. Ignore the small
print on any product label, and ignore incidental scene text (shelf tags,
signs) of the kind IMAGE 1 also carries. No competitor brand name as the
headline or on our product. PASS if there are no overlay words.
NUMBERS — Every price, percentage, discount, date or offer in IMAGE 3 is one
of the allowed facts above; the guarantee may be phrased naturally
("60-day money-back guarantee" is the same fact). FAIL if IMAGE 3 carries a
price, offer or guarantee where IMAGE 1 carries none. Ignore prices on
incidental shelf tags IMAGE 1 also carries. PASS if neither carries one.
ANATOMY — FAIL only for a defect a viewer would notice at feed size: a wrong
finger count, a missing or extra limb, a broken face, the product melted
into a hand. Soft, partly hidden or blurred fingers are not a defect.

Then one score:
MATCH — 1 to 5, how closely IMAGE 3 reproduces IMAGE 1's framing, crop,
camera angle, pose, setting, light and colour. 5 = the same picture with our
person, product and words; 1 = a different picture.

Reply as JSON only:
{"tests": {"SUBJECT": ["PASS|FAIL", "evidence"], "OTHERS": [...],
  "PRODUCT": [...], "WORDS": [...], "NUMBERS": [...], "ANATOMY": [...]},
 "match": 1-5, "note": "one line on the biggest problem, or 'clean'"}

<!-- {subject_rule} is one of: -->
ADULT IN THE SWIPE — IMAGE 1's subject is an adult; IMAGE 3's subject is a woman who reads as 55 to 70 with brown sun spots visible on whatever skin shows (face, hands, arms or chest), in the same pose, distance and expression as IMAGE 1's subject.
ORGANIC, NO ADULT — IMAGE 1 is an organic post with no adult as its subject. IMAGE 3 keeps the same kind of subject (same breed of animal, a baby, the same object or scene — a like-for-like one is fine), with no adult added as the subject, no product and no words.
AD WITH NO PERSON — IMAGE 1 is an ad with no person in it. IMAGE 3 has no person either, and the advertiser's product is replaced by ours.
<!-- and when the swipe shows no product, this is added to it: -->
IMAGE 1 shows no product, so IMAGE 3 must show none.
