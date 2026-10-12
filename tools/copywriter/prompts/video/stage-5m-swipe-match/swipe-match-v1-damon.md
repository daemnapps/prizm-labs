# Swipe match — v1

*v1 (2026-09-24): the last check before a brief can reach production. the owner, after a rewrite moved a swipe's offices to other rooms and turned its selfie opener into a composed shot: "literally this cannot happen again UNLESS I DISCRETELY SAY SO. THE WHOLE POINT IS TO TAKE A SWIPE AND ADAPT, not ruin it" — and, before batching many videos for many brands, "make sure this never happens again, literally."*

You are checking one thing: **does our production brief keep the swipe's structure?** You are not judging the words, the product, the claims, the brand, or whether the ad is good. The words are SUPPOSED to change. Our brand, our product and our people's names are SUPPOSED to replace theirs, and a real business name is SUPPOSED to become an unbranded one.

What must NOT change, shot by shot, compared with the swipe:

1. **Place.** The kind of location. Examples: an exterior outside a business stays one; an office stays an office; a car stays a car; a kitchen stays a kitchen. A different kind of room, or a place the swipe does not have, is a change.
2. **People.** Who is on screen and in what role: the same kinds of people, in the same number. A professional stays that kind of professional; a presenter stays a presenter. Replacing a role with a different kind of person, merging two, dropping one or adding one is a change. Only names and looks may differ.
3. **Camera.** Who holds it and how: a handheld selfie stays a handheld selfie (the speaker holding the phone at arm's length), a mirror selfie stays a mirror selfie, a propped or tripod shot stays propped, a close-up stays a close-up, a two-shot stays a two-shot. A selfie turned into a composed shot, or the reverse, is a change.
4. **Who speaks.** A line the presenter says to camera stays hers; a line a second person says stays that person's role.
5. **Order and story.** The swipe's shots appear in the same order and the story moves through the same steps. A swipe shot with no matching scene in the brief is a change (dropped); a brief scene with no swipe shot behind it is a change (added), EXCEPT a text-free card, screen graphic or endcard standing where the swipe has one.

**The swipe video itself is attached. It is the truth.** The teardown record below is a person's notes on it and can be wrong (notes have mislabelled a propped front-camera shot as a mirror selfie). Watch the video for place, people, camera and order; use the notes only to name the shots by time. Where they disagree, the video wins, and `swipe_has` says what the video shows.

Here is the swipe's teardown record, shot by shot, with each phase's scene contract (Camera · Staging): {teardown_record}

Here is our production brief: {brief}

**Read the brief's own words, never assume.** For `brief_has`, quote the brief scene's words that set the place, the people and the camera (its location, who, composition and camera lines). If a scene's words do not say "selfie" or show the speaker holding the phone, it is not a selfie — and a person with both hands busy is not holding a phone. A different kind of room is a different place, and a different kind of person is a different role. For example, a shop is not an office, and a friend is not a professional. Being stricter than needed costs one question to the owner; being lenient costs an ad.

**Added beats are allowed — but only inside the swipe's world.** An organic swipe has no product, mechanism, proof, offer or close, and our expansion ADDS them. A brief scene whose `source` is tagged [ADDED] (or that plays a beat the swipe lacks, after or between the swipe's shots) is an expansion beat: it is NOT a change as long as its place is one of the swipe's places, its people are the swipe's people (the same roles), and its camera is one of the swipe's camera styles. List it under `added` with `"in_world": true`. It IS a change — `"in_world": false` — when it brings a new kind of place, a new kind of person, or a camera the swipe never uses. The swipe's own shots must all still be there, in order.

**Compare at the grain of the teardown's shot rows.** One row of the teardown's shot table is one swipe shot, and the brief plays it with one scene (or more). Quick cuts or re-framings inside one row — a hand moving closer, a reframe of the same set-up — are that row's texture, not separate shots; a brief scene that plays the row with the row's main camera keeps it. Judge the camera by what dominates the row in the video, and flag a camera only when the kind of shot is different (a selfie against a composed shot, a close-up against a wide), never over a detail of framing.

Go through the swipe's shots in order. For each one, find the brief scene(s) that play it and compare the five things above. Then list any brief scene that no swipe shot stands behind.

Answer with ONE JSON object and nothing else — no prose before or after, no code fence:

{"shots": [{"swipe": "<its time range>", "swipe_has": "<place · people · camera · who speaks, in a few words>", "brief_scenes": ["S1"], "brief_has": "<the same four, QUOTED from the brief's own words>", "keeps": true, "changed": []}],
 "added": [{"brief_scene": "S7", "what": "<what it shows>", "place": "<which swipe place, or new>", "in_world": true}],
 "verdict": "KEEPS" }

- `changed` lists only what changed, each item one of "place", "people", "camera", "speaker", "order", "dropped", each with a few words: for example, "camera: swipe is a handheld selfie; brief is a composed shot".
- `keeps` is false whenever `changed` is not empty.
- `verdict` is "KEEPS" only when every shot keeps and every added scene is in the swipe's world; otherwise "CHANGES".
- When the brief does not say something (e.g. it names no camera for a scene), treat the silence as a change and say so — a brief that does not say the camera cannot promise it.
