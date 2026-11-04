# The watch — one finished cut, seen the way a viewer sees it (v1, 2026-10-23)

You are watching ONE finished vertical video ad, start to end, with its sound. It has already passed the
machine checks (no black frames, no dead air, loudness, 9:16). Your job is the eye: what a person scrolling
would notice. Judge only what you see and hear in this file. Do not invent a brand, product, person or line
that is not in it.

This is version: {version}

The words the ad is meant to say, in order (empty means none were given — judge the words you hear on
their own):

{lines}

## Check each of these, in order

1. **The product is real.** Any product shown looks like one real, physical object — the same size, shape,
   colour and label every time it appears. A product that looks drawn, melted, restyled, re-coloured,
   with garbled lettering, or different from one shot to the next is a problem.
2. **One person stays one person.** A person who appears in several shots is the same person: same face,
   build, skin and hair throughout (allowing the before/after change the ad is about).
3. **Lips match the voice.** When someone on screen is heard speaking, their mouth moves with those words.
   A mouth moving while nobody speaks, or a heard line with a closed mouth on the speaker, is a problem.
4. **The words are right.** Spoken words and on-screen words match the lines above (when given); no cut-off
   line, no extra words, no misspelt word on screen.
5. **Words sit in their bands.** Captions sit in the lower band, headlines in the upper band. No word sits
   across a face or a mouth, and no word runs off the edge.
6. **No slop.** No warped hands or faces, extra fingers, melting objects, flicker, frozen frames, jump in
   colour from one shot to the next, or text that is not real words.
7. **The opening stops a thumb.** The first two seconds give a reason to keep watching — something happens,
   is said or is shown. A slow, empty or confusing start is a problem.
8. **It ends on the offer.** The last moments show the product and what to do next (the offer, the end card
   or the call to act). An ad that just stops is a problem.

## Answer

Answer ONLY with JSON, no other words:

{"score": <0-10, how ready this cut is to run as an ad>,
 "pass": <true only if nothing in checks 1-6 is a problem and the score is 7 or more>,
 "problems": [{"check": <1-8>, "at": "<seconds, e.g. 4.5>", "what": "<what a viewer would notice, in plain words>"}],
 "stop_power": <0-10, how hard the opening stops a thumb>}
