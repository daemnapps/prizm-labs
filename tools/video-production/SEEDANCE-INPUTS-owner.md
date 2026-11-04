# Seedance Inputs (the owner's page)

Mirror of the artifact page. Standing rules: `SEEDANCE-INPUTS.md`.

- Average clip prompt: 677 words before, 208 after (12 Yai clips).
- One 11-step list was pasted four times into a single 10 s clip.
- The plan priced Seedance at the Omni rate: $2.64 shown, $24.89 real for the same 88 s.

## How one scene becomes one clip

1. **The brief** — One row per scene: who is in it, the line, what happens, the shots. It is the prompt for everything after it. *(makes: scene fields (below))*
2. **The voice** — Each line is read once by ElevenLabs v3 with its delivery tag, heard back word for word, locked. Read again only if the words fail. *(makes: vo/<scene>.mp3)*
3. **The storyboard** — Scenes are grouped into sections (one camera set-up each). It decides which pictures get made: a start picture per section, an end picture only where the scene ends somewhere new. *(makes: section list)*
4. **The picture** — GPT Image 2.5 makes the start picture from the cast sheet and real references. One version. A judge reviews it (up to 2 remakes); the real product is pasted in; every face is checked against the cast master. *(makes: approved start picture)*
5. **The call plan** — Each section is cut at line boundaries into calls of 4 to 10 seconds. A person on screen always starts from the approved picture, never from a clip's last frame. *(makes: clips/plan.json)*
6. **The clip** — ONE call to Seedance 2.5: Image 1 = the approved picture, Audio 1 = that line's locked read, plus the prompt. 480p, 9:16, length = the read + 0.6 s. *(makes: raw clip)*
7. **The checks** — Words heard back (Scribe), face lock, frame-by-frame check, clip judge. Up to three attempts on Seedance, then the Kling backup as the last rung; every attempt is scored; the best-scoring one is kept (a tie goes to the later) and marked `below_criteria` with the failed checks if it did not pass. *(makes: the best attempt, flagged or not; V34)*
8. **The upscale** — Only the kept take is upscaled on this Mac to 1080x1920. Free. *(makes: final clip)*
9. **The hand-off** — The clip, its ledger and its word times go to the edit, which sets captions and cuts on them. *(makes: clips/ledger.json, clips/calls/<call>/transcript-words.json)*

## What Seedance is told, and from where

| Brief field | Lands in | Why |
|---|---|---|
| who / the cast member | Image 1 line + Audio 1 line | who the picture shows and whose voice it is; the face itself comes from the picture, never a description |
| voice (the line) | Audio 1, the locked read | NEVER typed in the prompt: typing it triggers burnt-in subtitles |
| delivery tag ([softly] …) | the voice read, not the prompt | it is sent to ElevenLabs; the audio already carries it |
| happens / beats[do] | the summary sentence and the timeline windows | one visible action per window of 2.5 s or more, two at most; extra steps are dropped by name and the scene is flagged to split |
| shots[face, gestures] | 'face and hands:' in the window of that shot | what the face and hands visibly do |
| emotion (the label) | not sent | a strong emotion word can make Seedance light the eyes or overact |
| shots[camera_move] | the camera phrase | push-in · pan · tilt · arc · handheld · hold; else the swipe's camera kind (selfie · mirror · held · still) |
| hands_off, ends_on | a hand-off sentence and 'At the end of the take: …' | how one moment joins the next, and what the take ends on |
| the style (format profile) | the style sentence | one look for the piece, by name; 'handheld' is removed when the camera is a propped phone |
| after the routine (even skin) | one skin sentence | the spots are not asked for when the picture no longer has them |
| life marks (spice layer 3) | 'Marks kept exactly as in Image 1' | from the character file |
| own gestures (spice layer 2) | two of them, only if the shot names none | from the character file; never the whole list |
| realism rows | up to 4 'real detail' sentences | from the realism index, by format and spice level (the senses join at level 3) |
| off-camera lines and sound nods | 'listens in silence, lips closed' / 'nods slightly' | the listener never speaks; a murmur becomes a nod |
| swipe motion clips | 'Video N is a motion reference only' | blurred pieces of the swipe's own shot, for sections that copy its movement |
| the last picture (silent clips) | 'Image 2 is the last frame' | only when different from the first; never beside a voice |

## The settings we hold

| Setting | Value | Note |
|---|---|---|
| Resolution | 480p | upscaled on this Mac; the price at 480p is an estimate until priced |
| Aspect | 9:16 | the start picture is centre-cropped to 9:16 before sending |
| Duration | read + 0.6 s, 4 to 10 s | the model allows 4 to 30 |
| Audio | on for talking clips, off for silent | generate_audio |
| Takes | 1, up to 3 on failure | VIDEO-RULINGS V34 |
| Calls in parallel | 6 (12 checks in flight) | providers.json clip_route |
| Face tolerance | eye drift 0.06, one remake | face lock |
| Swipe motion refs | up to 3 pieces of 2 to 8 s, blurred | providers.json clip_route.refs |
| Seed, strength, genre | none | we send none; a third-party Higgsfield guide says the model has none, so the prompt and the inputs are the whole control |

## The creative controls above the clip

| Control | What | How it reaches the clip |
|---|---|---|
| Creative dials (29) | intensity, valence, absurdity, humor, specificity, dramatisation, metaphor, edge, realism, ad likeness, stopping power, relevance, rhyme, coherence, anchorage, borrowedness, shot scale, eye contact, density, scale distortion, uncanny, degradation, cutting rate, camera, status, irony, cringe, parody marks, cultural casting | bound in the writing passes (injection, hooks, spice, brief) as the video dials; the brief turns them into `face`, `gestures`, `angle`, `camera_move` and timing, which are all the clip prompt reads |
| Guards (9) | relevance, legibility, benign, claim-safe, receipt, never-sterile, reads-cold, one-idea, parody-not-copy | bound in the same passes; checked on the writing |
| Presets (4) | maxed, native-unaware, problem-aware, product-proof | a whole set of dial levels |
| Video spice level | 1 clean · 2 lived-in · 3 fully lived | decides which of the seven layers reach the clip: 1 = emotion, rhythm, continuity; 2 adds life marks; 3 adds own gestures, the senses and camera work |
| Camera and cutting (V10) | push-in, pan, tilt, arc, handheld, hold; hand-offs continuous, action, match, whip | per shot, in the brief |

## Controls Seedance has that we do not use yet

| Control | What it does | Where we stand |
|---|---|---|
| Video extension | continue or prepend a clip so two clips join with no seam; needs mov for best continuity | would replace our 'no hand-offs for people' workaround |
| Keyframes (several pictures in order) | 'Use Images 1 to 7 in order as keyframes'; follows the pictures closely | we send one picture per clip; a 15 s scene could run on 3 keyframes |
| Extra reference pictures | face, product, room, look, each bound by job (up to 30; 1 to 8 subjects stable) | the chain sends one; the bench can test adding the face |
| Several views of one subject | supported on 2.5 as separate images | the cast sheet's turnaround could ride as references |
| Longer takes | up to 30 s in one call | we cap at 10 |
| Sound tags | music ( ), sound effects < >, dialogue { } | we send no music and no effects; the edit lays them |
| Dialogue language and accent | named before the line | the read already carries it |
| Video editing mode | replace a subject or object in an existing clip, keep the camera and timing | the Genjutsu swap does this today |
| Style reference | a picture or clip for look only | the style sentence does this today |

## Eleven places we fought the model

| Fault | What we did | What Seedance rewards | Now |
|---|---|---|---|
| The prompt was written for another model | The Omni-era paragraph was wrapped inside a second wrapper. 520 to 1,130 words a clip. | Seedance wants the shortest prompt that fully says the shot. | A 4-block prompt, about 210 words. |
| The picture was never called the first frame | It said “the person in image 1”, and elsewhere “ends on the second picture” when no second picture was sent. | Name each file by number and job: “Image 1 is the first frame”. | Image 1 and Audio 1 are bound by job. A last frame is named only if one is sent. |
| The line was typed beside its own audio | The words sat in the prompt and in the voice file. | Repeating dialogue is a known trigger for burnt-in subtitles. | The words live in Audio 1 only. |
| One step list pasted four times | Steps with no shot label matched every shot. One 10 s clip carried the same 11 steps four times. | One change per window; too much gives extra cuts or skipped action. | Each step said once, in a timed window. |
| Eleven steps in ten seconds | No limit on actions per clip. | At most two per window of 2.5 s or more. | Extra steps are dropped by name and the scene is flagged to split. |
| Emotion words | “feels intent, a little grim, then a flicker of satisfaction”. | Strong emotion words can make Seedance light the eyes or overact. | Only what the face and hands visibly do. |
| The same stock gestures in every clip | “Small slow nods, head bobble, hand to chest, lean in as if telling a secret”, whatever the scene. | Observable, specific direction. Generic acting reads as slop. | The shot’s own face and gestures only. |
| A long list of negatives | Five “no” phrases plus “no cinematic grade” (it named the word it feared). | Negatives are honoured for subtitles and music; “cinematic” is vague. | Two: no subtitles, no background music. |
| A paragraph describing the face | 120 words of face, marks and clothes beside a picture that already shows them. | When the reference is accurate, point to it; do not re-describe. | “Keep this exact person, face, clothing, props, room and light.” |
| The camera argued with the style | Style said “handheld front camera”, the camera line said “phone set down and still”. | One dominant camera behaviour per shot. | Contradicting words are removed. |
| The price on the plan was ten times too low | Seedance clips were priced at the retired Omni 360p rate: $0.03 a second. | n/a | Priced at the measured $0.283 a second (720p). This 88 s plan: $2.64 shown, $24.89 real. |

## Old prompt next to new, every clip

### G01-C1-1 · scene S1 · 5 s · 579 → 231 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "You didn't know this, but believe it or not,". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

It ends exactly on the second picture: the same people, place and light, in the positions that picture shows.

The phone is set down and still: the frame does not move.

The woman holds the split skin model to the lens and clears the spot off one half with the paste. Shown step by step, one after another: smears the paste onto the left-half spot with the tablespoon; then drags her thumb across the paste. The woman feels intent, a little grim, then a flicker of satisfaction, and it shows in the eyes and the whole face. The woman's face: eyes on the lens over the model, brows lifting on 'believe it or not', nose wrinkling slightly as the clump shows. The woman's hands and body: eyebrow-flash, disgust-wrinkle. Shown step by step, one after another: smears the paste onto the left-half spot with the tablespoon; then drags her thumb across the paste; then the brown spot peels up in one wet flake like wet tissue paper; then the coffee-ground clump under it shrinks to a pale speck; then tilts the split toward the lens. The woman says it matter-of-fact, her lips moving with every word: "You didn't know this, but believe it or not,"

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman holds the split skin model to the lens and clears the spot off one half with the paste, static phone frame, propped and not moving.

0-2s: The woman smears the paste onto the left-half spot with the tablespoon; then drags her thumb across the paste. The woman's face and hands: eyes on the lens over the model, brows lifting on 'believe it or not', nose wrinkling slightly as the clump shows; eyebrow-flash, disgust-wrinkle. The woman starts speaking Audio 1.
2-5s: The brown spot peels up in one wet flake like wet tissue paper; then the coffee-ground clump under it shrinks to a pale speck. At the end of the take: the model's left half is clean tan skin, its spot gone and the clump beneath it pale and shrunk, a smear of yellow paste on it; the right half still spotted; the tan identical on both halves.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G01-C1-2 · scene S1 · 7 s · 565 → 231 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "85% saw their facial dark spots visibly fade with this simple kitchen paste.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

The phone is set down and still: the frame does not move.

The woman feels intent, a little grim, then a flicker of satisfaction, and it shows in the eyes and the whole face. The woman's face: eyes on the lens over the model, brows lifting on 'believe it or not', nose wrinkling slightly as the clump shows. The woman's hands and body: eyebrow-flash, disgust-wrinkle. Shown step by step, one after another: smears the paste onto the left-half spot with the tablespoon; then drags her thumb across the paste; then the brown spot peels up in one wet flake like wet tissue paper; then the coffee-ground clump under it shrinks to a pale speck; then tilts the split toward the lens. The woman says it matter-of-fact, her lips moving with every word: "85% saw their facial dark spots visibly fade with this simple kitchen paste." The take ends on the model's left half is clean tan skin, its spot gone and the clump beneath it pale and shrunk, a smear of yellow paste on it; the right half still spotted; the tan identical on both halves.

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman holds the split skin model to the lens and clears the spot off one half with the paste, static phone frame, propped and not moving.

0-4s: The woman smears the paste onto the left-half spot with the tablespoon; then drags her thumb across the paste. The woman's face and hands: eyes on the lens over the model, brows lifting on 'believe it or not', nose wrinkling slightly as the clump shows; eyebrow-flash, disgust-wrinkle. The woman starts speaking Audio 1.
4-7s: The brown spot peels up in one wet flake like wet tissue paper; then the coffee-ground clump under it shrinks to a pale speck. At the end of the take: the model's left half is clean tan skin, its spot gone and the clump beneath it pale and shrunk, a smear of yellow paste on it; the right half still spotted; the tan identical on both halves.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G02-C1-1 · scene S2 · 10 s · 1129 → 239 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "Add one tablespoon of turmeric to the blender, a thumb of fresh ginger, a teaspoon of moringa, and two spoons of chamomile tea,". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

It ends exactly on the second picture: the same people, place and light, in the positions that picture shows.

The phone is set down and still: the frame does not move.

The woman blends the four ingredients one at a time and scrapes the paste into a dish. The woman feels focused, easy authority, and it shows in the eyes and the whole face. The woman's face: eyes on the lens, dropping to her hand as the spoon tips, back up. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels focused, and it shows in the eyes and the whole face. The woman's face: eyes down on the drop, then up to the lens. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels focused, and it shows in the eyes and the whole face. The woman's face: eyes on the spoon. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels easy, sure, and it shows in the eyes and the whole face. The woman's face: eyes on the spoon, a slight smile. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Without a cut, the phone carries straight on into the next moment. Then, in the same take: The woman feels settled, and it shows in the eyes and the whole face. The woman's face: eyes down at the lid, then up to the lens. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. The woman says it matter-of-fact, her lips moving with every word: "Add one tablespoon of turmeric to the blender, a thumb of fresh ginger, a teaspoon of moringa, and two spoons of chamomile tea,"

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman blends the four ingredients one at a time and scrapes the paste into a dish, static phone frame, propped and not moving.

0-2s: The woman tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar. The woman's face and hands: eyes on the lens, dropping to her hand as the spoon tips, back up; eyes-down-to-hands. The woman starts speaking Audio 1.
2-5s: The woman tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar.
5-8s: The woman dips the tablespoon into the cup; then tips the second spoonful in.
8-10s: The woman presses the black lid down with both hands; then runs the blender. At the end of the take: the small glass dish full of thick gritty paste on the counter, the jar set aside, a dab of paste between her right fingertip and thumb, her eyes on the lens.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G02-C1-2 · scene S2 · 10 s · 1261 → 239 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "and blend everything together. Scrape it into a little dish and use it today, because it won't last a day in the fridge.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

The phone is set down and still: the frame does not move.

The woman feels focused, easy authority, and it shows in the eyes and the whole face. The woman's face: eyes on the lens, dropping to her hand as the spoon tips, back up. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels focused, and it shows in the eyes and the whole face. The woman's face: eyes down on the drop, then up to the lens. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels focused, and it shows in the eyes and the whole face. The woman's face: eyes on the spoon. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels easy, sure, and it shows in the eyes and the whole face. The woman's face: eyes on the spoon, a slight smile. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Without a cut, the phone carries straight on into the next moment. Then, in the same take: The woman feels settled, and it shows in the eyes and the whole face. The woman's face: eyes down at the lid, then up to the lens. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. Then, in the same take: The woman feels matter-of-fact, and it shows in the eyes and the whole face. The woman's face: eyes down on the scrape, up to the lens on 'because'. The woman's hands and body: eyes-down-to-hands, feel-it. Shown step by step, one after another: tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar; then tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar; then dips the tablespoon into the cup; then tips the second spoonful in; then presses the black lid down with both hands; then runs the blender; then scrapes the paste into the small glass dish; then sets the jar down beside the dish; then rubs a dab of paste between fingertip and thumb. The woman says, her lips moving with every word: "and blend everything together. Scrape it into a little dish and use it today, because it won't last a day in the fridge." The take ends on the small glass dish full of thick gritty paste on the counter, the jar set aside, a dab of paste between her right fingertip and thumb, her eyes on the lens.

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman blends the four ingredients one at a time and scrapes the paste into a dish, static phone frame, propped and not moving.

0-2s: The woman tips the heaped tablespoon of turmeric into the jar; then drops the ginger thumb into the jar. The woman's face and hands: eyes on the lens, dropping to her hand as the spoon tips, back up; eyes-down-to-hands. The woman starts speaking Audio 1.
2-5s: The woman tips the teaspoon of moringa onto the yellow; then tips the tablespoon of tea into the jar.
5-8s: The woman dips the tablespoon into the cup; then tips the second spoonful in.
8-10s: The woman presses the black lid down with both hands; then runs the blender. At the end of the take: the small glass dish full of thick gritty paste on the counter, the jar set aside, a dab of paste between her right fingertip and thumb, her eyes on the lens.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G03-C1-1 · scene S3 · 4 s · 550 → 175 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "Rub it on for sixty seconds, twice a week.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

It ends exactly on the second picture: the same people, place and light, in the positions that picture shows.

The phone is set down and still: the frame does not move.

The woman rubs the paste onto her cheekbone and explains what it does on top and underneath. Shown step by step, one after another: dips two fingers into the dish; then rubs small circles on her left cheekbone. The woman feels earnest, authoritative, and it shows in the eyes and the whole face. The woman's face: eyes on the lens throughout, brows level, mouth firm. The woman's hands and body: her flat left palm marks the top, then lowers to mark underneath. Shown step by step, one after another: dips two fingers into the dish; then rubs small circles on her left cheekbone; then holds; then lays her flat left palm level at chest height; then lowers the palm a hand's depth; then holds. The woman says it matter-of-fact, her lips moving with every word: "Rub it on for sixty seconds, twice a week."

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman talks to the camera, static phone frame, propped and not moving.

0-4s: The woman dips two fingers into the dish; then rubs small circles on her left cheekbone. The woman's face and hands: eyes on the lens throughout, brows level, mouth firm; her flat left palm marks the top, then lowers to mark underneath. The woman starts speaking Audio 1. At the end of the take: a small smear of yellow paste on her left cheekbone, the dish still at her chest, her left palm lowered and still at waist height.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G03-C1-2 · scene S3 · 10 s · 546 → 198 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "This scrubs the dead brown skin off the top and works on the stain underneath, so 85% saw it visibly fade.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

The phone is set down and still: the frame does not move.

The woman feels earnest, authoritative, and it shows in the eyes and the whole face. The woman's face: eyes on the lens throughout, brows level, mouth firm. The woman's hands and body: her flat left palm marks the top, then lowers to mark underneath. Shown step by step, one after another: dips two fingers into the dish; then rubs small circles on her left cheekbone; then holds; then lays her flat left palm level at chest height; then lowers the palm a hand's depth; then holds. The woman says it matter-of-fact, her lips moving with every word: "This scrubs the dead brown skin off the top and works on the stain underneath, so 85% saw it visibly fade." The take ends on a small smear of yellow paste on her left cheekbone, the dish still at her chest, her left palm lowered and still at waist height.

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman talks to the camera, static phone frame, propped and not moving.

0-3s: The woman dips two fingers into the dish; then rubs small circles on her left cheekbone. The woman's face and hands: eyes on the lens throughout, brows level, mouth firm; her flat left palm marks the top, then lowers to mark underneath. The woman starts speaking Audio 1.
3-7s: The woman holds; then lays her flat left palm level at chest height.
7-10s: The woman lowers the palm a hand's depth. At the end of the take: a small smear of yellow paste on her left cheekbone, the dish still at her chest, her left palm lowered and still at waist height.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G03-C2-1 · scene S4 · 8 s · 562 → 217 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "Think about what you've already spent on creams and lasers that only touched the top.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

It ends exactly on the second picture: the same people, place and light, in the positions that picture shows.

The phone is set down and still: the frame does not move.

The woman dismisses the creams and lasers, then shows the clean half of the model again. The woman feels skeptical, then confident, and it shows in the eyes and the whole face. The woman's face: lips pressed, a sceptical narrowing of the eyes on 'creams and lasers', then settled and certain on 'the last thing'. The woman's hands and body: breath-before-line, lip-press, lean-in-secret, counter-tap. Shown step by step, one after another: leans toward the lens; then raises her open left palm; then drops the palm; then taps two fingers on the counter; then sets the dish down on the counter; then studies the clean half up close; then turns the split to the lens; then taps the clean half twice with her index finger. The woman says it serious, her lips moving with every word: "Think about what you've already spent on creams and lasers that only touched the top."

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman dismisses the creams and lasers, then shows the clean half of the model again, static phone frame, propped and not moving.

0-3s: The woman leans toward the lens; then raises her open left palm. The woman's face and hands: lips pressed, a sceptical narrowing of the eyes on 'creams and lasers', then settled and certain on 'the last thing'; breath-before-line, lip-press, lean-in-secret, counter-tap. The woman starts speaking Audio 1.
3-5s: The woman drops the palm; then taps two fingers on the counter.
5-8s: The woman sets the dish down on the counter; then studies the clean half up close. At the end of the take: the split model held square to the lens at chest height, her index finger resting on the clean left half, the right half still spotted, skin colour identical.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G03-C2-2 · scene S4 · 7 s · 665 → 200 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "This works on the stain itself, and 85% saw their spots visibly fade.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

The phone is set down and still: the frame does not move.

The woman feels skeptical, then confident, and it shows in the eyes and the whole face. The woman's face: lips pressed, a sceptical narrowing of the eyes on 'creams and lasers', then settled and certain on 'the last thing'. The woman's hands and body: breath-before-line, lip-press, lean-in-secret, counter-tap. Shown step by step, one after another: leans toward the lens; then raises her open left palm; then drops the palm; then taps two fingers on the counter; then sets the dish down on the counter; then studies the clean half up close; then turns the split to the lens; then taps the clean half twice with her index finger. The next moment starts in the middle of that movement. Then, in the same take: The woman feels confident, settled, and it shows in the eyes and the whole face. The woman's face: eyes close on the clean half, then up to the lens on 'gone'. The woman's hands and body: look-close. Shown step by step, one after another: leans toward the lens; then raises her open left palm; then drops the palm; then taps two fingers on the counter; then sets the dish down on the counter; then studies the clean half up close; then turns the split to the lens; then taps the clean half twice with her index finger. The woman says, her lips moving with every word: "This works on the stain itself, and 85% saw their spots visibly fade." The take ends on the split model held square to the lens at chest height, her index finger resting on the clean left half, the right half still spotted, skin colour identical.

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman dismisses the creams and lasers, then shows the clean half of the model again, static phone frame, propped and not moving.

0-4s: The woman leans toward the lens; then raises her open left palm. The woman's face and hands: lips pressed, a sceptical narrowing of the eyes on 'creams and lasers', then settled and certain on 'the last thing'; breath-before-line, lip-press, lean-in-secret, counter-tap. The woman starts speaking Audio 1.
4-7s: The woman drops the palm; then taps two fingers on the counter. At the end of the take: the split model held square to the lens at chest height, her index finger resting on the clean left half, the right half still spotted, skin colour identical.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G04-C1-1 · scene S5 · 8 s · 548 → 203 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "My granddaughter's Brilliance Face Scrub... the same four, in one tube, ready every time.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

It ends exactly on the second picture: the same people, place and light, in the positions that picture shows.

The phone is set down and still: the frame does not move.

The woman shows her granddaughter's tube, gives the offer, counts the three tubes and quotes the guarantee. The woman feels warm, and it shows in the eyes and the whole face. The woman's face: eyes on the lens, a half-smile starting before 'ready every time' ends. The woman's hands and body: small-wai-nod, half-smile. Shown step by step, one after another: gives a small polite nod over the tube; then taps the tube with her right index finger; then holds; then lifts the empty tablespoon; then taps each tube in turn with her left index finger; then looks up to the lens; then glances to her right; then looks back to the lens. The woman says it warmly, her lips moving with every word: "My granddaughter's Brilliance Face Scrub... the same four, in one tube, ready every time."

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman shows her granddaughter's tube, gives the offer, counts the three tubes and quotes the guarantee, static phone frame, propped and not moving.

0-3s: The woman gives a small polite nod over the tube; then taps the tube with her right index finger. The woman's face and hands: eyes on the lens, a half-smile starting before 'ready every time' ends; small-wai-nod, half-smile. The woman starts speaking Audio 1.
3-5s: The woman holds; then lifts the empty tablespoon.
5-8s: The woman taps each tube in turn with her left index finger; then looks up to the lens. At the end of the take: her eyes on the lens, the tube at her chest, her right hand starting to lift off it.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G04-C1-2 · scene S5 · 6 s · 523 → 184 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "Buy two, get one free, plus a free travel pouch.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

It ends exactly on the second picture: the same people, place and light, in the positions that picture shows.

The phone is set down and still: the frame does not move.

The woman feels warm, and it shows in the eyes and the whole face. The woman's face: eyes on the lens, a half-smile starting before 'ready every time' ends. The woman's hands and body: small-wai-nod, half-smile. Shown step by step, one after another: gives a small polite nod over the tube; then taps the tube with her right index finger; then holds; then lifts the empty tablespoon; then taps each tube in turn with her left index finger; then looks up to the lens; then glances to her right; then looks back to the lens. The woman says it matter-of-fact, her lips moving with every word: "Buy two, get one free, plus a free travel pouch."

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman shows her granddaughter's tube, gives the offer, counts the three tubes and quotes the guarantee, static phone frame, propped and not moving.

0-3s: The woman gives a small polite nod over the tube; then taps the tube with her right index finger. The woman's face and hands: eyes on the lens, a half-smile starting before 'ready every time' ends; small-wai-nod, half-smile. The woman starts speaking Audio 1.
3-6s: The woman holds; then lifts the empty tablespoon. At the end of the take: her eyes on the lens, the tube at her chest, her right hand starting to lift off it.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G04-C1-3 · scene S5 · 9 s · 667 → 203 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "A big tablespoon, three tubes, sixty days. It says it right on the page... Less Spots, Guaranteed.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

The phone is set down and still: the frame does not move.

The woman feels matter-of-fact, and it shows in the eyes and the whole face. The woman's face: eyes down to the tubes, up to the lens on 'days'. The woman's hands and body: eyes-down-to-hands. Shown step by step, one after another: gives a small polite nod over the tube; then taps the tube with her right index finger; then holds; then lifts the empty tablespoon; then taps each tube in turn with her left index finger; then looks up to the lens; then glances to her right; then looks back to the lens. The woman says it matter-of-fact, her lips moving with every word: "A big tablespoon, three tubes, sixty days." Then, in the same take: The woman feels assured, and it shows in the eyes and the whole face. The woman's face: a glance aside toward the page she is quoting, then back to the lens. The woman's hands and body: glance-away-think. Shown step by step, one after another: gives a small polite nod over the tube; then taps the tube with her right index finger; then holds; then lifts the empty tablespoon; then taps each tube in turn with her left index finger; then looks up to the lens; then glances to her right; then looks back to the lens. The woman says it matter-of-fact, her lips moving with every word: "It says it right on the page... Less Spots, Guaranteed." The take ends in the middle of a movement, so the next clip picks the movement up. The take ends on her eyes on the lens, the tube at her chest, her right hand starting to lift off it.

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman shows her granddaughter's tube, gives the offer, counts the three tubes and quotes the guarantee, static phone frame, propped and not moving.

0-3s: The woman gives a small polite nod over the tube; then taps the tube with her right index finger. The woman's face and hands: eyes on the lens, a half-smile starting before 'ready every time' ends; small-wai-nod, half-smile. The woman starts speaking Audio 1.
3-6s: The woman holds; then lifts the empty tablespoon.
6-9s: The woman taps each tube in turn with her left index finger; then looks up to the lens. At the end of the take: her eyes on the lens, the tube at her chest, her right hand starting to lift off it.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

### G04-C2 · scene S6 · 4 s · 528 → 178 words

**Old**

```
The person in image 1 speaks the line in audio 1, word for word, lips exactly on the words: "Tap the button below, or I can't get it to you.". Keep the first frame as it is: the same person, face, glasses, clothes, props, place, framing and light. Only the speaker's mouth moves with the words; anyone else on screen listens with lips closed. One continuous take, no cuts, no music, no added words. The look, exactly: native phone-camera footage: handheld front camera, available room light, true unretouched skin texture, slight noise and compression, nothing styled. Hold this look in every picture.

The image is the first frame: keep it exactly as it is, the same framing and distance from the lens, the same people, faces, clothes, place, signs and light. Nothing is re-staged or re-framed; the camera moves only as the camera line below says.

The woman stays exactly the same person in every frame: Yai, <brand>'s grandmother: a Thai woman in her late eighties from Isaan, deeply weathered sun-worn brown skin with deep wrinkles, age spots and visible pores, small round face, narrow dark kind eyes, thin white hair pulled into a tight small bun, small slightly stooped wiry frame with strong forearms and hands; fingertips and nails faintly stained yellow from decades of turmeric; age spots and fine scars on the backs of her hands; a thin old burn mark on her left wrist from a cooking pot; jade bangles worn smooth. No one's eye colour, face shape, skin marks or hair ever changes.

The phone is set down and still: the frame does not move.

The woman points down to the button, then straight at the lens on the condition. Shown step by step, one after another: points down; then points at the lens. The woman feels warm, commanding, and it shows in the eyes and the whole face. The woman's face: eyes locked on the lens to the last word, a warm but commanding smile. The woman's hands and body: points down on 'below', points at the lens on 'I can't'. Shown step by step, one after another: points down; then points at the lens. The woman says it matter-of-fact, her lips moving with every word: "Tap the button below, or I can't get it to you." The take ends on her right index finger pointing straight at the lens, the tube in her left hand at her chest, the warm commanding smile.

Small, slow nods as the point lands. A gentle side-to-side head bobble of agreement. A small polite nod, hands briefly brought together near the chest. Two fingers tap the counter as they make the point. A hand comes to their chest on the sincere line. They lean toward the lens, voice lowered, as if telling a secret.

After the last word, everyone holds still, no laughing, nothing else is said.

One continuous take from the first frame to the last: no cuts, no jumps, no change of set-up; anything held stays in the same hand. Never write any words on the picture: no subtitles, no captions, no speech text, no titles. No music. Real footage, natural skin, no cinematic grade.
```

**New**

```
Image 1 is the first frame and shows the woman: keep this exact person, face, clothing, props, room and light.
Audio 1 is the woman's voice: the woman speaks Audio 1 word for word, lips matching every word.

Native phone-camera footage: available room light, true unretouched skin texture, slight noise and compression, nothing styled. The woman points down to the button, then straight at the lens on the condition, static phone frame, propped and not moving.

0-4s: The woman points down; then points at the lens. The woman's face and hands: eyes locked on the lens to the last word, a warm but commanding smile; points down on 'below', points at the lens on 'I can't'. The woman starts speaking Audio 1. At the end of the take: her right index finger pointing straight at the lens, the tube in her left hand at her chest, the warm commanding smile.

Constant throughout: one continuous take, static phone frame, propped and not moving; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.
```

## Test cost (needs the owner's OK)

3 clips × 2 prompts = 28 s: about $3.52 at 480p (estimate), $7.92 at 720p (measured $0.283 a second).

## 18 October learnings

| Learning | Today | What is true | Where it lands |
|---|---|---|---|
| Build the subject inside the shot’s own first picture | partial | Only swipe-edit pieces do. The edit prompt says nothing about light, rim light or contact shadows. | Hand-over to picture prompts. Rule V38. |
| One recast per shot, never a whole multi-cut clip | mostly | Swaps already run one shot at a time. Nothing handles a shot under the 4 s minimum. | V39 |
| Choose the frame rate; do not default to 30 | not built | The edit hard-codes 30 while every generated clip is 24. That is the choppy cut. | V40, video-edit |
| Cut a generated pass at its own cuts | not built | Only the frame-control tool detects cuts. | V40, video-edit |
| Real in-between frames (RIFE), never blends or holds | not built | The tool exists in local-studio; the edit never calls it. | V40, video-edit |
| Machine checks before the owner sees it (cut frames, jumps, held frames, leftover person or wardrobe colour) | not built | The edit checks lip slip and loudness only. | V41, video-edit |
| Always 9:16; name every accessory to remove; scale, not crop, motion-control output | partial | 9:16 is centre-cropped at the clip door. The rest is written nowhere. | V38, V41 |

## Sources

- [BytePlus ModelArk: Dreamina Seedance 2.5 prompt guide (official)](https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide)
- [Dreamina: Seedance 2.5 prompt guide (ByteDance, formula and camera)](https://dreamina.capcut.com/seedance/seedance-2-5-prompt)
- [ClipDance: Seedance 2.5 prompt rules (summary of the official guide)](https://clipdance.ai/blog/seedance-2-prompts-guide)
- [RunDiffusion: Seedance 2.0 prompt guide (reference modes and limits)](https://www.rundiffusion.com/seedance-2-0-prompt-guide)
- [Magic Hour: how to use Seedance 2.0 without drift](https://magichour.ai/blog/how-to-use-seedance-20)

## Prompt changes, 26 Oct 2026 (old next to new, verbatim)

Why: the creative controls were ruled into every video (V47, first numbered V33) but no video prompt carried them, and the brief prompt still said the emotion label goes to the motion model. Four writing prompts are new versions (the old files stay as they were, V19). The clip model still never receives a dial, a level or an emotion word; the controls reach it through the shot's `face`, `gestures`, `angle`, `camera_move` and timing.

### Stage 5 brief, v6 → v7

**OLD (v6), one line of the "where it goes" table:**

```text
| a shot's **face · emotion · gestures · angle · camera_move** | the motion model, as the acting and the camera of that take |
```

**NEW (v7):**

```text
| a shot's **face · gestures · angle · camera_move** | the motion model, as the acting and the camera of that take (the `emotion` label is not sent: it is the source `face` and `gestures` are written from) |
```

**OLD (v6), three lines of the shot template:**

```text
"face": "⟨what the face does in this shot: eyes, brows, mouth — or `listens in silence, lips closed`⟩",
"emotion": "⟨the actor's feeling in this shot⟩",
"gestures": ["⟨this person's own small movements in this shot⟩"],
```

**NEW (v7):**

```text
"face": "⟨visible actions of the face in this shot: eyes, brows, mouth — or `listens in silence, lips closed` — never an emotion word; `n/a: reason` if it truly does not apply⟩",
"emotion": "⟨the actor's feeling in this shot, one of the twelve by id — a label for the reader, not sent to the clip model⟩",
"gestures": ["⟨visible movements of the head and hands in this shot — or `n/a: reason`⟩"],
```

**OLD (v6): nothing. NEW (v7), added section:**

```text
## THE CREATIVE CONTROLS BECOME WHAT THE CLIP CAN SHOW (VIDEO-RULINGS V47, V46)

Every video is made against one set of dials, guards and a never-sterile floor, the same set copy and pictures use. Here are the video dials, each with its scale and what it does on camera, then the guards and the floor: {creative_controls}

Here are the levels this video aims for: {controls_target}

Here are the twelve emotions and how each one looks on camera: {emotion_video_lines}

The clip model is never sent a dial, a level or an emotion word (a strong label is what lights the eyes or overacts). It is sent only what the shot's `face`, `gestures`, `angle`, `camera_move`, `ends_on` and beat lengths say. So this brief turns the controls into those fields, shot by shot:

| A control | Becomes, in the shot |
|---|---|
| the chosen **emotion** of the shot (one of the twelve, by id) | `face` and `gestures`, written from that emotion's camera line above in your own visible detail |
| **intensity**, **dramatisation** | how big the performance is: how far the head, shoulders and hands move; how sharp the first movement is. The peak lands in the first three seconds |
| **eye contact**, **shot scale** | `angle` and `face`: where the eyes go (lens, away, down to the hands) and how close the camera is |
| **camera**, **cutting rate** | `camera_move` and the number and length of shots in a scene (a beat is never under 2.5 s) |
| **humor**, **irony**, **cringe**, **edge** | the timing and the face: the held beat before the line, the look at the lens, the wince; stated as a visible action |
| **absurdity**, **specificity**, **scale distortion**, **uncanny** | `happens` and the beats: the one impossible or hyper-specific thing that is seen |
| **realism**, **degradation**, **ad likeness** | the style and the realism rows already above; never contradicted by a polished face or gesture |

Rules for the two fields the clip reads:
- Every shot that shows a person to camera has `face` AND `gestures` filled with **visible actions** (eyes, brows, mouth, head, hands, shoulders). An emotion word alone ("shocked", "skeptical") is not an action and counts as empty.
- If a field truly does not apply to a shot, write `n/a: ⟨the reason⟩` in it. It is never left blank and never filled with "natural".
- `emotion` stays in the brief as a label for the people who read it; it is the source the `face` and `gestures` are written from. It is not sent to the clip model.
- If an input above reads `[UNFILLED]`, write on without it and say so in one line.
```

### Stage 3 injection, v5 → v6 (new section; v5 had none)

```text
## THE CREATIVE CONTROLS FOR VIDEO (VIDEO-RULINGS V47, V46)

Every video is made against one set of dials, guards and a never-sterile floor, the same set copy and pictures use. Here are the video dials, each with its scale and what it does on camera, then the guards and the floor: {creative_controls}

Here are the levels this video aims for: {controls_target}

Here are the twelve emotions and how each one looks on camera: {emotion_video_lines}

How every pass uses them:
- The floor holds on every awareness level, offers included: nothing below it, and a real mark or face is never kept or blanked.
- A dial is a level of something the viewer can see or hear. Write each one into the words, the faces and the timing, never as the label.
- If any input above reads `[UNFILLED]`, write on without it and say so in one line.
- THIS PASS: set the script's humor, absurdity, valence arc (open low, close high), dramatisation and borrowedness at the levels above, in the words the lines use. The dial must be audible in the line itself.
```

### Stage 4ab reading and hooks, v3 → v4 (the same section, plus this line)

```text
- THIS PASS: write each hook version to reach the stopping-power and intensity levels in its first three seconds. For each version name the emotion it opens on (by id from the twelve) and, in a few visible words, what the opening face and hands do.
```

### Stage 4g spice, v5 → v6 (the same section, plus this line)

```text
- THIS PASS: choose the emotion of every beat from the twelve (by id). Put that emotion's camera line into the spice sheet's EMOTION TRAVELS layer as what the face and hands visibly do, in visible actions, never as the emotion word. The emotion label itself is never sent to the clip model; only the face and the hands are.
```

### How the clip prompt reads the shot (code, not a prompt)

- OLD: a blank or emotion-word-only `face` / `gestures` was sent as nothing, silently.
- NEW (`machine/acting.py`): such a field is filled from the emotion bank's camera line for the shot's emotion, or marked `not applicable` with the reason; each call records it (`acting`) and the clip plan lists it (`acting_notes`). A person with no character-file section 'Life marks and gestures' is named in the plan. The Kling backup prompt now carries the same face, gestures, own-habits and marks lines as the Seedance prompt.
