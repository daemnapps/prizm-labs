# The video brief — one shape, every brand, every ad

> **2026-09-18:** the brief shape below stands. `machine/run.py start` also reads it (`plan_from_brief.py`), for both spines, alongside the board tools named below.

**Ruled 2026-09-14, the owner:** *"I want to standardize this brief template for all
video production. This is going to be a brand-agnostic process and interface
that is built for every single brief that we get out, and that needs to be
established in the chain."*

Brand-agnostic by construction: nothing in this spec names a brand, a person or
a product. Those are arguments.

---

## Why this exists — what it cost not to have it

One brief went through the chain on 14 September. Three machines read it and
**all three disagreed about what a brief is**:

| machine | what it expects |
|---|---|
| teardown stage 5 (writes it) | `### Scene 1 · 0:00 – 0:01.8 · 1.8 s` · `**On screen.**` · `**You say.**` · `**How.**` · a `> **Prompt**` block |
| `scenes.py` (storyboard reads it) | `**Scene 1 · … · TYPE B**` · `**Happens:**` · `> **Say:**` · `**Delivery:**` |
| `board.py` (cinema board reads it) | `out/plan.json` — `cast.elements[]` with `slot·name·id·role·desc·thumb`, `cutaways[]` with `id·over·at·seconds·why·place·subject·action·look·generate` |

None of it was written down. Fitting the brief to the cinema board meant
discovering one required field at a time from a stack trace — `over`, then
`desc`, then `role`, then `generate` is a dict not a bool, then `overrides` is a
map not a list. That is not a schema, that is an excavation.

## The two ad shapes, and which board each gets

There are **two**, and conflating them is what broke the day.

| shape | what it is | the board |
|---|---|---|
| **TALKING SPINE** | someone speaks on camera; inserts cover the take | `board.py` — the cinema board, `BOARD_PORT`, default 8456 |
| **VOICE-OVER** | nobody speaks on camera; every scene is an insert under one continuous VO | `storyboard.py` — port 8455 |

The cinema board is built around A-roll: a cutaway declares the beat it sits
`over`. An ad with **zero** A-roll has nothing to sit over, and the board cannot
render it — correctly, because its whole model is "inserts cover a take."

**So: a brief declares its shape, and the shape picks the board.** Do not force
a voice-over ad onto the cinema board. The source a VO ad is torn from never
shows the speaker; that is the format, not a gap.

## The scene header — one line, both shapes

```
**Scene <n> · <start> – <end> · <seconds>s · TYPE <A|B|C>**
```

| type | means | needs |
|---|---|---|
| **A** | someone speaks on camera | a still of the speaker, then the voice |
| **B** | a generated clip, or footage we already own | a clip |
| **C** | a product packshot, moved | the real packshot |

An ad with no TYPE A rows is a voice-over ad and says so in `overrides.aroll`.

## The scene body

```
**Happens:**  what is in frame and what moves. One action with a beginning and an end.
> **Say:**    the words, verbatim. Omitted entirely when nobody speaks.
**Delivery:** how it is said, or how the beat plays.
**Refs:**     every element id whose subject is VISIBLE in this frame.
**Still:**    the generation prompt, verbatim, minus the refs.
```

## Scenes and shots — a scene is a sequence (ruled 2026-11-08)

A **scene** is one continuous moment: one place, one time, the same people, one sound bed. It holds the moment's whole script in order, every line with its `speaker`. A **shot** is one cut inside a scene: an angle or framing, the action it shows, and the lines it covers (`lines`, each with its `speaker`).

1. **One moment is one scene, however many people speak in it.** A back-and-forth between a host and a guest is one scene whose shots cover the turns, never one scene per turn.
   - **One generation carries as many shots as fit (ruled 2026-11-12).** Consecutive scenes that share a section, or carry on in the same place (rooms of one hotel or one home count as one place), are one scene while the whole stays within 30 s, the length most video models take per generation. The hook is one scene. A run of solution beats is one scene.
   - Each such scene is one continuous take, with its motion, characters and development programmed across the whole scene.
   - A new scene starts when the section changes in a new place, at 30 s, for a 3D cut-away (a skin cross-section), and for a card, insert or screen. The hook is always its own scene, because hook versions swap the opening.
   - **Hook versions swap only the opening (ruled 2026-11-16).** A hook version is the made hook scene with its opening element changed and nothing else: `take.py variant <hook scene> <name> <opening.json | words>` reuses the scene's start picture, motion, camera, cast and line-up as made and replaces only the beats before the second person in the line-up (5 s by default, `--whole` for the full scene). No new staging or motion run for a version. When the new element is already in the first frame (a prop in a hand, wet skin), the start picture gets that one element changed through image production first and goes in as `--picture`; when the opening is all action, the main start picture is used as made. A changed prop or detail is changed in that person's written look too (`--look`), or the old words win over the picture. The main scene's motion is not sent with a new opening (its body moves are the main opening's), and an opening-only version stays with the first person in the line. The edit cuts from the version's opening into the main take.
2. **Speakers live on lines, not on scenes.** A scene may carry several speakers. The voice step reads each line in its speaker's voice and lays the reads down in order, so a scene is never split to give a speaker a voice.
3. **A shot is at least 1.5 s** and names the source shot it copies (`copies`).
4. **AI shots in one scene are made as a sequence, not one at a time.**
   - Shot 1's still is the scene master: made from the real reference, it sets the place, the people, their clothes and the light.
   - Every later shot's still is made with the scene master as a reference (`scene_master`), so the same people stand in the same place.
   - A shot that continues without a cut (`hands_off: continuous`) starts from the last frame of the shot before it (`continue_from`).
5. **The check.** `components/video-writing/machine/scene_shots.py check <brief>` refuses consecutive scenes that fit one generation but are split apart: one moment (the same parent scene, or the same section, setting, people and source shot), or the same section or place within 30 s. `fold` joins them into one scene with their shots in order, and the Video Studio sets a brief up folded.

The example to copy is a street-interview hook: one scene of four shots of the same two-shot (the question, the card rising, the answer, the glance), cut on the words, with one continuous read.

### Continuous takes and motion (ruled 2026-11-09)

6. **Shots follow the swipe's own cuts, never the lines.** Where the swipe holds one continuous take, the scene is `take: "continuous"` and is made as **one clip** that carries every line in order. It is never split into a clip per line. A scene is cut into shots only where the swipe itself cuts.
7. **Motion is the most important element of a swiped scene.** Every swiped scene carries `motion`: the swipe file and the seconds it copies (`{"source": "<file>", "from": s, "to": s}`), what the camera does (a phone held by a person, following the action: drift, bob, re-frame; never a tripod or a smooth glide), the staging (who moves where, in order) and the body language on each beat (lean in, recoil, laugh, react). The clip is made from that motion: the swipe's seconds go in as the motion reference, and the prompt names the camera, the staging and the body language. A clip that animates people in place under a still camera is a miss.
   **Every AI clip goes through the motion chain (ruled 2026-11-12).** The one route for an AI clip's movement is `components/motion/` (`motion_chain.py`); `take.py` and `gen_ref.py` both call it and nothing else makes motion. Before any paid take, in order: (1) **real footage of the same action** is found: footage we own first, then the swipe's own seconds, then a TikTok/YouTube search list that waits for the owner's yes before anything is downloaded (`finder.py`); (2) it is **tracked** (`motion.py`: every body, hand and face, each body's own 3D pose, and the camera's own path); (3) the **motion read** (`read.py`, `prompts/motion-read.md`) turns the clip and its track into body mechanics per beat: who starts, who answers and how late, weight, torso, head, hands, eyes, contact, distance, timing in seconds, what the operator does, and the one measure that proves each beat; (4) the **3D rehearsal** (`retarget.py`) moves the stand-ins by the real skeletons and films them with the real camera's path; (5) the **preview** (reference, skeleton and rehearsal side by side) is measured against the reference (`match.py`) and looked at (`watch.py`), and the chain **decides by itself**: the motion passes on its own checks or is held with the reason (`motion_chain.py decide`; ruled 2026-11-12: nobody approves motion, the tool is agnostic). Held motion gets one more read and rehearsal on its own; still held, it stays held and no take is made from it. The start picture is made from the rehearsal's first frame and laid over it (`start-check`): `video-studio/take.py scene <scene dir>` makes it, remakes it when it does not match, makes the take and checks the take against the reference in one go; a take made from a take.json whose picture does not match is refused with the reason. `approve --by` exists only as an override the chain records. **When the motion carries a tracked camera, the take sends no written shot sizes, moves or operator style**: the camera is said only as the track measured it (written sizes made models invent push-ins), and a punch-in added in the swipe's edit is left to our edit. After the take, (6) the **motion-match check** (`match.py`, `motion_chain.py check`) sets the take against the reference beat by beat as pass or fail rows on the production's Checks panel. The verbs below (`motion_program.py`) are the fallback only when no real footage of the action exists yet.
   - **Our own action, per person per beat.** Where the action is ours (not the swipe's), each script line carries `moves` (what each person's body does on that beat) and `faces` (each person's face, one of: neutral, smile, grin, laugh, disgust, unsure, surprise, bite-lip, flirty, deadpan). Every route takes them as words. To copy a body 1:1 instead, the scene is acted out on a phone by people standing where the characters stand, tracked (`components/motion/motion.py`) and given as `motion` to the pose route.
   - **The take is read back.** `take_layers.py` reads every person's face (smile, jaw open, brows, frown, lip bite, eyes), body (hands up, moving, where they stand) and the camera (pan, tilt, push) off the finished take; `take.py check` marks each beat's asked-for face pass or miss. A person is known by face: their character sheet, or one place they were `seen` in the take.
   **Programmed motion, the fallback (ruled 2026-11-09; second to real footage since 2026-11-12).** With no real footage of the action, a scene's motion is our own: programmed from its take (the staging, every line's `do` and `moves`, its camera words) by `components/motion/motion_program.py`. Claude, on the plan of whoever runs it, writes the blocking (`prompts/motion-program.md`): where every person stands, who walks to whom, whose hands go to whose cheeks, the mic to the mouth, and where the phone camera goes. Stand-in figures act it out in 3D, locally in Blender or hosted in Higgsfield 3D Jutsu, and their exact skeletons drive the take. Programmed motion is ready as made, with nothing to approve; it is all worked out before a video model is paid for. Tracking a clip is the exception, used to learn how a format moves.
   **Motion sources (ruled 2026-11-09).** A scene's motion can also come from one of three clips, read by `components/motion/motion.py` into a pose track (every person's body, hands and face points, kept as the same person frame to frame), a skeleton preview and the camera's own path (pan, tilt, push, roll and shake, solved from the background with the people masked out): (a) **the swipe's seconds**; (b) **a phone act-out**: someone films the beat on a phone and drops the video on the scene in the Video Studio; this is how a scene gets an action the swipe does not hold; film it with space between the people, since two bodies pressed together read as one; (c) **a 3D blocking**: stand-in people, an optional `.glb` set, beats (walk to, reach both hands to someone's cheeks, turn) and a moving camera, rendered headless (`motion.py blocking <spec.json>`; the worked example is `components/motion/blocking/reach-to-cheeks.json`). The motion is shown as moving skeletons beside the scene's lines. `take.json` `motion: {"scene": "<scene folder>"}` uses the scene's motion once it has passed the motion chain's own checks; a take never sends motion those checks held, and nobody is waited on.
8. **A continuous take is one call.** Its inputs: the scene's start picture (made by image production from the swipe's frame), every person's character sheet (so each person stays ours and the same from the first frame; without them the model drifts toward the swipe's people), one short voice sample per speaker (the model speaks every line itself in that voice), the swipe's seconds as the motion reference, and the whole script in order in the prompt, each line with its speaker. The maker is `components/video-studio/take.py`.
   - **Voices by name.** Each speaker's `voice` in `cast` names a voice we own (made from a real speaker by `components/video-production/machine/make_voice.py`); every line of theirs is read again in it, so changing the name changes the voice. `take.py voices` lists them and `take.py hear "<name>" "<line>"` plays one before a take is paid for.
   - **The camera, inside one scene.** `camera` names the move (handheld-follow, push-in, pull-out, pan-left, pan-right, orbit, static, whip-pan), the angle (eye, low, high, over-shoulder, pov) and the framing (wide, medium, close, two-shot); a line's own `camera` changes it on that beat. `shots` cuts inside one take from a shot list (several angles of the same moment in one call). `views` makes the same moment once per view and cuts them together line by line on the take's own speech (multi-cam), so the words run on across every cut. Camera control runs on Wan 3.0 and Seedance 2.5 only (ruled 2026-11-09).
   - **A take with no voices of its own is lip-synced.** The pose route prints silent; our reads are laid on and each line's speaker is made to speak it (`take.py lipsync`, LatentSync by default) on a window where that face is the largest in frame.

9. **What the picture does with the voice is measured on every swipe shot, and each take is made that way (ruled 2026-11-12).** `components/video-studio/lips.py` reads every face on screen against the word timings and gives each frame-map shot one picture type. A written Roll label is never trusted for this: on 12 Nov the teardown called 80 shots of a narrated drama lips-on where 3 were.
   - `talking`: the voice's owner is on screen speaking it, lips opening and closing with the words. The take carries that speaker's voice and is lip-synced. This is A-roll.
   - `mime`: someone else on screen mouths a line the voice says (a retold line acted out). Their mouth moves, and no voice goes into the take.
   - `reaction`: one opening of the mouth under the voice (a gasp, a laugh). It is not speech.
   - `present`: the voice's owner is on screen with a still mouth, and the voice runs over them.
   - `away`: the picture has left the speaker (hands, the product, another place) while the voice runs on.
   - `silent`: no voice under the shot.
   - Who owns the voice comes from the teardown's cast list (who speaks), and the owner's face is learned from the shots where they are alone. A moving mouth is theirs only if the face matches.
   - **The voice is one continuous read, laid under the whole ad, and never restarts at a cut.** A scene is A-roll only where someone speaks on screen. Every voice-over, present, away and reaction line is made as a silent take with mouths closed, and the read is laid over it. A mimed line is made silent with the mouthing written as action.
   - **It runs in every teardown, before any writing**, for every brand. It runs where the frame map is handed to the writing: the measured table is added to the frame map every writing stage reads, `lips.json` is kept in the run and linked into every piece written from it, and `lips.py setup` makes the reader ready on any machine the first time (its models and a Python with mediapipe under `~/.cache/take-layers`). Each speaker's face is learned on its own. When a speaker's face cannot be learned, an unmatched moving mouth counts as talking, never as a mime.
   - The shot list (`swipe_shots.py`) shows each shot's picture type, and the Video Studio sets each scene's roll, each line's `lips` (on, mime or off) and each shot's `picture` from it. `take.py` sends a voice sample only for lips-on lines.

The example to copy is the beach Smash or Pass hook: one 20 s take, a blindfolded woman walking down a line of men feeling each face, the host following with the mic, a handheld phone following both, every verdict in order. It went from ten one-line scenes, to one scene of ten shots, to one continuous take, to one continuous take carrying the swipe's motion.

## The anchor rule — the one that is not optional

**Every identity visible in a frame carries its element on that frame — not only
the identity the scene is about.**

Measured, not argued. On the Braille set the brief attached her face element to
**1 scene of 19** because only one scene was *about* her face. She was visible in
most of them. Nineteen frames came back with several different women, several
different brushes and several different bottles.

> An identity that is not attached is an identity the model invents, every time.

`frames.py` enforces it: it scans each scene's prose for each identity's own
words and attaches the element whether the brief listed it or not, **printing
every addition** — a silent fix is a fix nobody can check. `--no-anchor`
reproduces the old behaviour, so the drift stays demonstrable.

## The tail

One block, appended to **every** generation prompt without exception: wardrobe
stated completely for every person in the ad, the light, the skin rule, and the
do-not-include list. Never left to inference — a setting that invites undress
with clothing unstated produces an undressed subject, which has reached a
published brief.

## The chain

```
brief.md
   │
   ├─ plan_from_brief.py --brand <b>   → out/plan.json   (the boards' input)
   ├─ adapt_brief.py                   → stages/5-brief.md (scenes.py's dialect)
   │
   ├─ TALKING SPINE → board.py       BOARD_PORT=<p>  → cinema board
   └─ VOICE-OVER    → storyboard.py                  → storyboard
```

`plan_from_brief.py` reads either header dialect and both field dialects, pulls
the cast from `brands/<brand>/elements/index.json`, and emits the plan in the
shape the boards actually read. It is the only file that knows all three
dialects, so a fourth machine never has to.

## Still open

- **The cinema board cannot render a zero-A-roll ad.** Today that is correct
  behaviour and the VO ad goes to the storyboard. If one surface should serve
  both, the cinema board needs a spine that is the voice-over rather than a
  talking beat — a real change, not a field.
- **`board.py` has no schema of its own.** The table above was reverse-
  engineered from its source and from the one run that works. It should validate
  its input and say what is missing, instead of raising `KeyError` inside a
  request thread and returning an empty reply.
