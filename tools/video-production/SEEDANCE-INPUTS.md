# What we send Seedance, and why (2026-10-26)

The standing contract for a Seedance 2.5 clip. Which model does the job is `components/generative-model-house/MODEL-HOUSE.md`; this page is how the inputs are shaped so that model gives its best result. Built by `machine/seedance_prompt.py`, sent by `machine/seedance.py`. The audit behind it, with the old and new prompts side by side and the clips: `SEEDANCE-INPUTS-owner.md` (the same text as the owner's page).

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

## What the model rewards (BytePlus, Seedance 2.5 prompt guide)

Source: https://docs.byteplus.com/en/docs/modelark/seedance-2-5-prompt-guide (read 2026-10-26). Third-party guides agree where noted.

| Input | What it rewards | Our rule |
|---|---|---|
| Reference files | Each image, audio and video is named by its upload number and its job ("Image 1 is the first frame", "Audio 1 is the voice"). Upload in the order the subjects first appear. A mapping that lives only inside the picture ("John") confuses who is who. | Image 1 = the approved first picture, always bound as the first frame. Audio 1 = the locked read of the line, bound as the speaker's voice. Nothing else is attached unless a test proves it helps. |
| How many | Up to 50 files; 1 to 8 image subjects and 1 to 5 audio or video subjects is the stable range; 5 to 10 s of audio or video per subject. | One person per clip, one picture, one audio slice of 2 to 15 s. We are far inside the range. |
| First and last frame | Setting the picture's role to first/last frame locks the output to that picture's aspect and cannot sit beside audio on Higgsfield (the 422 of 2026-09-22). A picture sent as a plain reference and called "the first frame" in words is allowed, but the model follows it approximately, not exactly. | A talking clip is reference mode, so the prompt says "Image 1 is the first frame" and holds the picture with words. A silent clip may carry a different last picture; the same picture is never sent as both ends. |
| Prompt shape | Bind the files; one summary sentence (subject, place, event, style, camera); a timeline in whole-second windows or "Shot N"; then what stays constant. Positive wording. The shortest prompt that fully says the shot. | Four blocks: assets, summary, timeline, constants. About 200 words, down from 520 to 1,130. |
| Timeline | Whole-second windows that touch, no gaps. Too little in a window and the model improvises; too much and it adds cuts or skips the action. Do not time fast repeated actions. | One visible change per window of at least 2.5 s, two at most. Anything over that is dropped by name and reported, and the scene is split at the storyboard. |
| Camera | Name the shot size and ONE move per shot; replace "dynamic camera" with a specific move. | One camera sentence, from the shot's own `camera_move`, repeated once in the constants. The style words never contradict it (a propped phone is not "handheld"). |
| Dialogue | Speaker, language and delivery named before a line. Repeating the dialogue words in the prompt, or adding separate tone notes to words, is a known trigger for burnt-in subtitles. | The words are in Audio 1 only. The prompt never types the line. |
| Performance | Replace an emotion label with a trigger and a visible response. Strong emotion words can make the eyes glow. | The shot's `face` and `gestures` go in; the `emotion` label does not. |
| Negatives | Supported for subtitles and audio ("no subtitles", "no BGM"). Long blacklists compete with the scene; "cinematic" and "emotional and beautiful" are vague. | Two negatives only: no subtitles, no background music. The word "cinematic" is never used. |
| Text on screen | Misspells letters; give the exact words as a reference picture if they must be right. | Words are never in a picture or a clip (V28); they are laid on in the edit. |
| Length | 4 to 30 s a call on 2.5; about 6 to 8 s per beat. | The clip is the line's own length, 4 to 10 s in practice. |
| Look | Concrete place, practical light, texture. | The style words from the brief stand; phone-camera footage where the swipe is phone footage. |

Also from the third-party guides (Luma, RunDiffusion, Scenario, Dreamina's own page), lower weight: say whether a reference video is for motion only and exclude everything else it carries; match cuts and whip pans have to be asked for; blur and warping come from vague identity rules and conflicting references. Sources are listed on the page.

## Every input Seedance 2.5 takes, and what we do with each (2026-10-26)

| Input | Limits (BytePlus) | Job in the prompt | In the chain | In the bench |
|---|---|---|---|---|
| Picture, first frame | 30 images, up to 4K; 1 to 8 subjects stable | `Image 1 is the first frame ...` | yes, always | yes |
| Picture, face / product / room / look | same pool | one bound line each, "for the face only" and so on | no (the face gate guards the first frame) | yes, to test whether it helps |
| Picture, last frame | with a voice the door refuses it; silent clips only | `Image 2 is the last frame ...` | silent clips, only if different from the first | not on talking cases |
| **Video, motion reference** | up to 10, 30 s together; 5 to 10 s each is best; keep its subtitles and voices out, they override the prompt | `Video N is a motion reference only: copy how the camera moves ... take nothing else` | **sent now** (the Seedance door used to drop the swipe's blurred clips; only the Omni path sent them). The field name `video_urls` is read off the first live call. | yes, upload one |
| Voice read | up to 10, 30 s together; 2 to 15 s | `Audio 1 is X's voice ...` | yes, the locked read | yes |
| Text prompt | shortest that fully says the shot | four blocks below | yes | yes, editable |

A silent clip with a motion reference is made in reference mode (picture + video), not image-to-video, so it gives up a last frame: the two modes cannot mix.

## The four blocks, as built

1. **Assets.** `Image 1 is the first frame and shows <who>: keep this exact person, face, clothing, props, room and light.` A talking clip adds `Audio 1 is <who>'s voice: <who> speaks Audio 1 word for word, lips matching every word.` A silent clip with a different last picture adds `Image 2 is the last frame: the clip settles on it, ...`.
2. **Summary.** The style words, then one sentence: who, what they do, the camera.
3. **Timeline.** `0-3s: ...` windows that tile the clip. The shot's face and gestures ride on the first window. `At the end of the take: <the shot's ends_on>` closes the last.
4. **Constants.** `Constant throughout: one continuous take, <camera>; the same person, clothing, props, room and light as Image 1. No subtitles. No background music.`

Settings: 9:16, 480p and upscaled on this Mac (was 720p until 2026-10-26), duration = the read's length plus 0.6 s, rounded up, 4 to 30; up to three attempts, the best kept and flagged (V34); the face gate first; the face lock after.

## Where the 18 October learnings stand

The 18 October animal-swap test (a 28 s interview clip with every person recast) found six faults. Written here in our words, not copied from his sandbox note. "Done" means a line of code or a rule already does it.

| Learning | In the chain today | Where it lands |
|---|---|---|
| **A recast subject must be built inside the shot's own first picture**, so it takes the room's light, rim colour, contact shadows and grain. A subject made on a studio sheet and laid in reads as pasted on, with a hard edge at the neck. The studio sheet only locks the look. | Partly. A piece with `"frames": "swipe-edit"` already edits the swipe's own frame with the full casting sheet beside it (CLAUDE.md, 2026-10-20). Pieces without it still start from the sheet. No edit prompt names the room's light, rim light and contact shadows. | Picture prompts (the sibling session). V38. Then the clip animates that picture: `Image 1 is the first frame` holds it. |
| **Never recast a whole multi-cut clip in one pass.** One pass missed people, put the wrong animal on the wrong person, and lost track in crowds. Cut at the cuts, recast each shot, and for a shot under the model's four-second minimum play it forward-back-forward and trim. | Mostly. SHOT-ROUTES swaps one shot at a time on the frame map's cut boundaries. Nothing handles a shot under the minimum. | SHOT-ROUTES; V39. |
| **Choose the frame rate; never default to 30.** Every generated clip is 24 fps and the timeline ran at 30, so every fifth frame showed twice. That is the choppy cut. | No. `video-edit/machine/defaults.json` and `render_map.py` hard-code 30. The lip-sync check was fixed for 24; the timeline was not. | video-edit; V40. |
| **Cut the generated pass at its own cuts**, not the source's cut times, then fit each shot to the source shot's length on one grid. The generated cuts drift 0 to 5 frames. | No. Cut detection exists only inside the frame-control tool. | video-edit; V40. |
| **Fill missing frames with real in-between frames** (RIFE), never blends or held frames, and stop one frame before each cut. Blends read fuzzy, holds read choppy. | Tool exists (`components/local-studio` `interp`, RIFE v4.6); the edit does not call it. | video-edit; V40. |
| **Check before anything reaches review:** every cut on the source's cut frame, no jump inside a shot, no held frame, no leftover original person or wardrobe colour (a contact sheet of every shot, partial people included, a minor leftover is a fail). | No. The edit's checks cover lip slip and loudness. | video-edit; V41. |
| Always 9:16; name every accessory to remove (the headwrap tails survived as dark strands); a fast hand smears in the source and the model; motion-control output comes back 3:4 and must be scaled not cropped; cover burned-in captions with a box sized for the worst shot; keep the source sound at -14 LUFS. | 9:16 is cropped to centre at the clip door; the edit finishes at -14 LUFS. The rest is not written anywhere. | picture prompts and video-edit; one line each in V38-V41. |

**On Seedance specifically, wardrobe and face survive because the prompt now says so by number.** The old prompt said "the image is the first frame" but the wrapper called it "the person in image 1", never bound it, and described the face again in a 120-word paragraph that competed with the picture.

## The Video Bench (2026-10-26)

`tools/video-production/bench/` (`serve.py`, `page.html`, `capture.py`), http://localhost:8896. The video twin of the Picture Bench: a frozen case is a start picture, a locked voice read and the line (`capture.py <run> <call ids>`; stored under `runs/video-production/_bench/cases/`, mirrored to Drive). The page shows the inputs numbered by job, the old or new or edited prompt, size and cost, and makes ONE clip through `seedance.talk`, the call every chain uses. The standard board is three short whole-read cases (G03-C1-1, G04-C2, G04-C1-2), each made with the old and the new prompt. Nothing spends until the cost box is ticked; one paid call runs at a time (V37).
A capture check: a clip that says only part of a split line needs `vo/timing.json` to cut its part. A run without it sends the whole scene's read (the Yai paste video's S1 and S2 did: 11 s of voice into a 5 s clip), so those cases were left out of the bench.

## Open items

- 480p, the size every clip is made at, is priced by estimate (about $0.126 a second, by pixel count) until one real call prices it; 720p is the measured figure (6.5 credits a second, $0.283).

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
