# The video chain — one order, start to finish

the owner, 2026-10-01: *"we need to establish the logical chain … the whole point
of doing all that work at the very start is to get everything down before we
even go into production, which would then mean we generate our casting … all
the elements … based off the brief."*

One ad goes through five stations, in this order, and each one stops for
the owner before the next. A station never does the next one's job, and nothing
for the ad itself is generated before the brief and its elements are locked.

| # | Station | Takes | Makes | Stops for the owner | Home |
|---|---|---|---|---|---|
| 1 | **Teardown** | a swipe | the record of the swipe as it is — every line verbatim, every person, place, shot, sound — **the frame map** (every cut found in the pixels, every shot watched moment by moment: who moves, how, which edge each arm enters from, every word on screen, the sound, the edit, and how the swipe was captured — `video-teardown/machine/framemap.py`) — and the spec (its reusable structure). Nothing of ours. | reads the record | `tools/video-teardown/` → `runs/video-teardown/<brand>/<slug>/` |
| 2 | **Writing** | the record + the brand | **THE BRIEF** — our version, and the blueprint for everything after it: every scene, every line, every person (look, voice), every place, prop, frame and on-screen word. Gates: structure lock, hooks as format fills, audit, spoken words, cast vs swipe, swipe match, manifest. | reads the brief (`brief-read`) | the writing prompts → `runs/video-writing/<brand>/<slug>/` |
| 3 | **Elements** — production step 1, three steps in order | the brief | **3.1 check** — the brief informs it: every person, look, voice, place, prop the brief names is listed, and each banked one is compared both ways — the bank against the brief (`element_match.py`), and every word of the brief about that person against the bank (same gender as the swipe person, their own hands, clothes and look). **3.2 make** — everything the check marks TO MAKE or MISMATCH is generated from a real reference to match the brief (casting sheets and looks, each person's voice, places with no people in them, props, packshot). **Products:** every product the brief shows must have its **product truth kit** (real shape, real size, labels, 3D model — built from its own Drive photos; see "Products have a truth kit" below and `PRODUCT-KITS.md`): no kit → 3.1 marks it TO MAKE and 3.2 builds it (`product_kit.py build <brand> <slug>`, then `publish` to the product's Drive `product-kit/` folder for editors and designers); a product with no real photos stays "no real photos" — nothing invented. Production refuses a product with no kit. **3.3 approve** — the owner looks at every element and says **"elements ok"**; that is the lock. | 3.3 — **"elements ok"** | `machine/element_match.py`, `elements_check.py`, `make_character.py`, `make_voice.py`, `make_set.py` → `runs/ai-elements/<brand>/` |
| 4 | **Production** — steps 2–4 | the locked brief + locked elements | **gates** (all 13, `run.py start`), then **the read** (every line in the person's cloned voice, checked: words, pitch, accent — the storyboard's timing ruler and the off-camera lines; on-camera lines are said inside the clip at 4.5), then **the storyboard** (`storyboard_plan.py`: the brief's scenes grouped into the swipe's own sections, every layer laid out — voice, picture, text, room sound, music, sound effects, frame control, capture look, outfits — and only the frames each section needs: a start + end frame for a section we lip-sync or add, one reference still per kind of shot for a section the swipe's own clips drive by motion transfer, one plate per card), then **pictures** (`run.py start --storyboard`: only the storyboard's pictures, GPT Image 2.5, no clips; a clip the swipe uses twice is made once), then **clips** (Omni on fal at 1080p animates each approved picture; a person's clip always starts from the approved picture) | the voices · the storyboard · the pictures · the clips | `machine/run.py` → `runs/video-production/<brand>/<label>/` |
| 5 | **Edit** — by the machine, or by the editor | the clips + voice + banks | **5.0 editor hand-off** (when a person edits — the owner, 9 Oct: "I will just assign briefs to my editor to execute directly from the google drive"): the ad's brief number in the register, its edit kit (`video-edit run.py from-run`: clips in scene order, voice, music, sound, timing) and an editor brief (`handoff.md`), in ONE folder named by the brief's short form `brand_product_brief` under the shared drive's `handoffs/video-editor/<brand>/` — the editor's queue; the batch joins at delivery. Or the machine cut: the swipe's rhythm, cards, music, captions | the timeline · the captions (machine cut) | `tools/video-edit/` → `runs/video-edit/<brand>/<label>/` · the hand-off: the editor hand-off tool |

Then the hand-off: named to the convention, filed, one link.

## Every ad gets one page, laid out the same way

the owner, 2026-10-01: *"show each step as it's completed then the next steps
that need to be filled … this is going to be a template / process for all
future generations."* One artifact per ad, updated in place, never a new one:

1. **The process** — every step below in a table: `done` (linked to its
   section), `now` (what the owner does next), `to fill`.
2. **One section per finished step**, in chain order, each headed
   `Station N · <station>: <step>`.
3. **One dashed card per step still to fill**, at the bottom — what it will
   make and the owner's part — replaced by the real section when it is done.
4. **the owner's next step on top, finished steps folded to one line each**
   (the owner, 2026-10-02: "page looks really chunky") — only the step he is on
   and the one after it are open; nothing is deleted, it is folded.
5. **One set of words, one meaning each, the same in chat and on the page**
   (the owner, 2026-10-02: "my brain rounds up and combines things randomly, so
   please use consistent definitions and metrics"). A key near the top:

   | Word | Means |
   |---|---|
   | **swipe shot** | the swipe from one cut to the next (K01, K02 …) |
   | **scene** | one row of our brief: one spoken line, or one card (S1, S2 …) |
   | **section** | scenes filmed as one continuous camera set-up — one clip to make (Section 1, 2 …) |
   | **picture** | a still we generate to start a section |
   | **length** | always minutes:seconds, never a bare number beside counts |

   A kind of scene (an insert) is counted inside the scenes, never as extra.
   A reader never sees a machine id like G03 — it is "Section 3".

| Station | Steps |
|---|---|
| 1 Teardown | 1.1 triage · 1.2 record + transcript + frame map · 1.3 doctrine read · 1.4 spec |
| 2 Writing | 2.1 rewrite · 2.2 hooks · 2.3 expansion · 2.4 close · 2.5 audit · 2.6 spice · 2.7 the brief |
| 3 Elements | 3.1 element check (from the brief, incl. a product truth kit for every product shown) · 3.2 make the elements (and any missing product kit) · 3.3 approve — "elements ok" |
| 4 Production | 4.1 gates · 4.2 off-camera lines (the cloned voice) · 4.3 storyboard (layered timeline) · 4.4 frames (GPT Image 2.5) · 4.5 clips (Omni at 1080p, from the approved picture; on-camera lines are spoken inside the clip) — no upscale step since 3 Oct |
| 5 Edit | 5.0 editor hand-off (a person edits: one folder per brief, `brand_product_brief`, in the editor's queue) — or the machine cut: 5.1 timeline · 5.2 captions · 5.3 hand-off |

**4.3 storyboard** — the storyboard now comes with a budget: a low / likely / high dollar range for the pictures, voices and clips (with the clips priced on each clip model side by side), written to `<run>/BUDGET.md` before anything is spent (`machine/budget.py`; works on any existing run too).

**4.5 clips** (the Omni route, 3 Oct; **720p from 9 Oct**, the owner: "they're social media ads so they usually get compressed anyways" — no upscale, and a clip with nobody speaking on camera is made at 75% of its slot and slowed at the edit, `providers.json` `resolution` / `upscale_below_1080p` / `silent_share`) — `run.py start … --clips` (`--dry-run` first; `--only G05,G12` for some sections) plans, and `machine/omni_clips.py run <run> --yes` makes. Omni (Google Gemini Omni Flash 1.1, `image-to-video` on fal, **1080p**, 9:16 — the ruled clip model, locked) never makes a picture: it ANIMATES the picture approved at 4.4 (GPT Image 2.5) — the movement, the mouths, the speech. A person on screen = image-to-video with the approved picture as the first frame, their identity words in the prompt and the swipe's movement said in words; only a shot with nobody of ours in it gets up to three heavily blurred 3-second pieces of the swipe's own footage (`reference-to-video`), for movement only. A line is on camera only when its speaker's face is in the picture (`<run>/clips/on-camera.json` corrects the brief where the picture says otherwise); who says it is the brief's `speaker` — a line without one is refused, never guessed from whose hands are in the shot. Off-camera lines stay out of the clip and are read by that person's cloned voice. Each storyboard clip is cut at line (or sentence) boundaries into pieces of 3–10 seconds, never padded, one continuous take each, no words on the picture, no music; **every piece with a person on screen starts from the section's approved picture — never from the last frame of the piece before** (only a shot with nobody in it may chain; the planner, the live runner and preflight all refuse a person's clip from a made frame); cards and the endcard get no clip, a reused section is made once. **Before any clip spends — the clip gate** (the owner, 9 Oct: "a clean and clear gate that things need to go through"; `machine/clip_gate.py`): `clip_gate.py check <run>` holds every clip whose picture is not approved as it is now, whose person's **face lineup** (their cast master beside every picture they are in, `clips/gate-lineups/`) is not approved, whose picture carries **the swipe's words** in none of our files (MASCARA, LASHES), whose after-the-routine scene's prompt still **describes the spots**, whose prompt shown is not the prompt **sent**, whose **reference path** is gone, or whose exact request the model **refused** before, or whose picture carries **text a viewer would notice as slop** — a misspelt brand or product name, or big text that is not words (small print is noted, not held); `clip_gate.py approve <run> --by <who>` approves the pictures and lineups as they are now; `omni_clips.py run` refuses to spend on a red or stale gate. **After:** every planned clip made or the run is **INCOMPLETE**, each missing clip named (`clips/coverage.json`), and frames of every new clip read for the same slop (`clips/frame-check.json`, `clip_gate.py frames`) — a clip that drew a bad label is named, NOT CLEAN; a clip already made is kept and said so — `clip_gate.py remake <run> <ids>` moves it aside so it is really made again. Then, per clip: each on-camera line turned into its person's cloned voice + crisp finish, words checked, `clip_qc.py` — no upscale step at 1080p. Every prompt, the per-section table and the budget are in `<run>/clips/PROMPTS.md`; every spend goes in the ledger. (`--legacy-clips` keeps the old Seedance/MiniMax door's planner as a record — not the ruled model, and it too never hands a made frame to a person.)


## Where the playbooks sit (10 Oct)

the owner, 2026-10-10: *"I need a system that can build out the specific workflows based
off of the videos that come into the system."* The five stations stay the same for
every ad; a **format playbook** (`formats/playbooks/`) says how each station runs
for this kind of ad.

- **Station 1, right after triage names the format:** the playbook builder matches
  the swipe's structural signature to the families we have — close → a variant of
  that family; nothing close → a new draft family (`machine/playbook_builder.py`,
  started by the teardown in the background; decision in `runs/playbook-learn/`).
- **Stations 2–5 read it:** audio first (song / voice / none), picture quality,
  size and fix calls, clip model / resolution / seconds / clips per picture, cast
  reuse, hooks, captions, which gates apply, the edit method, the cost target and
  the format's "not slop" checks (`machine/playbook.py setting(<format>, ...)`).
- **After the run:** `machine/playbook_learn.py <run>` adds what broke and its fix
  to the playbook and proposes (or, where the rules allow, applies) setting changes.

## The swipe's style is read at 1 and locked before anything is made (9 Oct)

the owner, 2026-10-09, on the Brand C song ads: *"the creative format itself is
supposed to look like Pixar … these characters look like real people … you
need to actually analyze the format and the style, like this should be in the
process."* The swipe was a 3D-animated film; the elements were made photoreal
because nothing told step 3.2 what the swipe looked like, and the maker
"translated to a real photographed person" by default.

- **Station 1 names the style.** Looking at real frames of the swipe, the
  teardown names its style as ONE row of `styles/bank.json` (the test: swap it
  and the script, cast and beats stay the same), plus what the swipe shows of
  it (eyes, proportions, skin, light, caption look). No row fits → a new
  `draft` row, written from the frames, never a free-text look.
- **That style is the lock for every picture after it.** 3.2 makes every
  person, look and place IN that style — the style row's formula goes at the
  top of every element prompt, with a real swipe frame as the style guide.
  Never translate an animated swipe to photoreal, or a phone-shot swipe to
  animation, unless the brief says so (a restyle is a brief change).
- **Already made in the wrong style?** Restyle image-to-image from the made
  picture (identity, wardrobe, skin marks and age kept; only the rendering
  changes) — never re-cast from scratch.
- **4.4 and 4.5 inherit it** — the first frames and the clips carry the same
  style lock and motion line (`restyle.py` for an approved scene set).

## The real frames of the swipe — made at 1, used at 3.2 and 4.4 (8 Oct)

the owner, 2026-10-08: *"It needs to be frame by frame, by frame … when we get to
the frame generation … we can actually work with the real frames … use those
as the references."*

- **Station 1 (1.2, the frame map) saves every frame.** `framemap.py` keeps
  every frame the judge watched — 8 a second, original resolution — in
  `framemap/frames/<K##>/<K##>-<index>-<t>.jpg` with `frames/index.json`, then
  `frame_elements.py` cuts every person, place and prop the frame map names out
  of them: `framemap/elements/<kind>-<slug>/` — a crop per frame at the
  recorded position (padded 8%; no position = the full frame; a place = one
  full frame per shot, people noted), `element.json` and `best.jpg`. Frames,
  shots and elements are copied to the Drive beside the teardown stages,
  the shared drive, under the run's `teardown/framemap/` (copy only, never
  a delete). Media never goes in git; the repo gets `elements/index.json` only.
  An old run: `framemap.py <run> --frames-only` (no model, no re-map).
- **3.2 starts from them.** `elements_check.py sheet` attaches `swipe_frames`
  to every element still TO MAKE — the swipe person / place / prop the brief's
  real reference names (else the same name, else the times it names): best
  frame, the frame at each time named, one crop per shot. `make_character.py`
  and `make_set.py` take them as **"real video frame"** references when a spec
  names none (`--sheet <run>/elements.json`).
- **4.4 copies from them.** Every first frame carries the swipe shot it
  recreates as a **COMPOSITION reference** (`element_refs.py`), labelled in the
  prompt: match framing, camera, positions; replace the people, product and
  brand with ours. Every swipe frame goes in **SHARP**, people included
  (the owner, 2026-10-08: "we're always using our swipes in their entirety … I
  don't know why you would blur a frame"); our people come from the cast
  masters ahead of it, and `with_swipe_camera` moves it first, never in twice. Order inside the five: person masters → product packshot → swipe
  composition frame → set plate → look sheets → props.

## The rule that keeps it in order

**A change upstream re-runs everything downstream of it.** A brief that
changes after its elements were made sends the elements back through step 3;
an element that changes after the lock re-opens the lock (`elements-lock.json`
breaks on its own); a line that changes after the voices re-records that line.
Nothing downstream is patched in place to cover an upstream change. And the
other way: **an element is never changed without the brief changing first** —
a recast is a brief change (the owner, 2026-10-01: "step by step, the brief informs
the element check, then you need to generate the elements, then the elements
need to be approved"). The brief's own words about a person are checked against
their element at stage 5 (`cast_match.py`) and again at 3.1, so a brief that
still says "her hand" for a man never reaches the voices or frames.

## Why this page exists

One face-scrub run (2026-09-23 → 10-01) reused people and places made
for an earlier version of its brief. Nothing checked them against the new
brief, so the mismatches surfaced one at a time inside production — Doctor 3
the wrong gender, the sidewalk a skin clinic instead of the swipe's hair
clinic, a stray person in a sidewalk plate, Doctor 2's voice built from the
wrong surgeon. Step 3 now checks every banked element against the brief
before it is reused (`machine/element_match.py`).

## Motion is settled before anything is generated

the owner, 2026-10-01: *"we should've done this level of frame analysis at the
teardown stage … so by the time we get to the storyboard it's 10x faster /
easier and our brief … significantly more detailed in the correct way for us to
produce video at scale."* The frame map is made at the teardown, the brief
writes from it (AI brief v21: every swipe shot carried, each scene names the
K-shots it copies, body geometry and movement are the shot's, every word on
screen is carried), the brief is held on anything it drops
(`storyboard_plan.swipe_carry`, stage 5), and the storyboard lays the timeline
out from all of it. The pictures are finished to the swipe's own capture —
"nova literally shot this video on iphone and the quality isn't good, that's
perfect for what we want."

## The pictures — the recipe, the checks, the lock (the truth, 2 Oct)

the owner, 2026-10-02, after a session switched the picture model mid-run and the
pictures went wide, posed and pasted-in: *"literally everything looks perfect
now. Even the dark spots are on the right side of her face … this cannot happen
again."* Then: *"These checks need to be put in place in our chain every single
time. This is literally the process."*

**The recipe — every picture, every run.**
1. **The ruled still model: GPT Image 2.5** (`providers.json` doors.still, ruled
   18 Sep: "gpt for all image work"). No other model makes a picture.
2. **The swipe shot it copies goes in FIRST, sharp** (`framemap/shots/<K>-camera.jpg`,
   unblurred since 2026-10-08 — the swipe is used whole; a transition frame is
   skipped for the shot's first usable frame), followed by our people's references, the room, the real
   product and the outfit sheets — five at most.
3. **The written framing comes out**; the rule `frame_rules.swipe_camera` says
   what to copy from the swipe shot. The outfit, the label and the product's real
   size are said in words (`wardrobe_in_words`, `product_label`, `product_scale`); `first_instant`, `endcard` and the card
   plate's clean line apply as written in `machine/MODEL-INPUTS.md`.

**The checks — every picture, every run, automatically.**
- **The face check** (`machine/identity.py`): each person against their own
  reference, three asks; a check only, it changes nothing.
- **The picture inventory** (`marketing-chain-checks` review, stages.json
  `video-production.pictures.checklist`): every picture answers the same
  fourteen lines, ✓ / ~ / ✗ with a note — **framing** like the swipe · the
  **moment** (first instant: who touches what, gaze, expression) · **people** are
  ours · **skin marks** there, right side, not blotchy · **hands and bodies** ·
  **light and shadow** as the swipe (direction, hardness, colour, shading on
  faces, necks, hands, clothes) · **fits the look** of the swipe and its format
  (real footage reads real; an animated format fits its style — never judged on
  its own) · **outfit** · **place** · **product and props** exact · **continuity**
  with this person's other pictures (nails, jewellery, hair) · **nothing added** ·
  **frame and safe zone** (9:16, people and product in the middle 4:5) · **cards**
  framed like the swipe's. Any ✗ sends it back. Each line is a problem seen on
  2 Oct (the owner: "we need to account for all these little things").
- Both are filed in the run's QC log (`<run>/qc-log/`) and shown beside the
  picture on the page, where the owner approves or writes his note.

**The lock.** `run.py` `ruled_model`: a picture, edit or clip made on any model
but the one ruled for its station in `providers.json` STOPS the run, named. A
model changes only by the owner's ruling, written there first. A test proves it.

Withdrawn the same day (made without his ruling): Nano Banana Pro for pictures,
the sharp face-covered guide, the face pass. The research on trained identities
and real-footage swaps is filed (`providers/research/identity-*-2026-10-02.md`)
as candidates only — none enters the chain without a test against the ruled
model and his ruling.


## Products have a truth kit — built once, measured in every picture (2 Oct)

**Where in the chain:** station 3, Elements (3.1 checks every product the brief shows has a kit; 3.2 builds a missing one). Then station 4, Production, measures and fixes the product in every picture. The same kit serves image ads and emails.

the owner, 2026-10-02: *"similar to how we have casting sheets for our avatars, you
basically have to build real models of products as well"* — *"this is how we can
actually eliminate all product slop … at scale."* No spec sheets exist; each
product is built from its own real photos (the shared drive: `brands/<brand>/
products/<slug>/` — packshots, and shoots where a hand or face holds it).

**The kit** (`runs/ai-elements/<brand>/products/<slug>/`, `machine/product_kit.py`):
`kit.json` — the outline measured from the packshot, the **shape** as length
over width along the product's own axis (from its exact cut-out, SAM 2.1,
cross-checked on real in-hand photos), the **real size** estimated from hands and
faces (± noted), the true colours, the label words; `model/` — a Blender model of
the exact shape with the real front and back labels (`machine/blender/<kind>.py`)
and its reference renders. Media stays on disk, never in git.

**In every picture with the product** (`run.py product_of`): the product is
**measured** (`product_check.py`: its exact cut-out's shape against the kit,
±12%, and the label words read off the picture). Off, the picture is **kept and
only the product replaced** (`product_fix.py`: image-edit's "Wrong product" fix —
the whole object at its real size — on the ruled edit door, with the kit's render
and the real packshot), measured again, twice at most, the closest kept. The
verdict is filed on the picture's record.

First kit: Brand A's product (real tube 1.79× as tall as wide, ≈10.5 ×
6.3 cm). Measured on the Nova ad: six of seven drawn tubes were 2.15–2.41×.

**The standard for every product is `PRODUCT-KITS.md`** (2 Oct): one command
builds a kit from the product's real photos (`product_kit.py build <brand>
<slug>`), `publish` puts the team copy in the product's Drive folder
(`product-kit/`), and `list` is the gate — a still made from a photo of a
product with no kit stops the run, naming the product.


## Voices — where they are made now (3 Oct)

the owner, 2026-10-03, after hearing the clip model's own voices against the cast voices:
*"even the doctor's voice sounded better with omni"* · *"use the best voice then clone it for
everything so it stays consistent"* · *"version a actually sounds like the avatar looks"*.
This replaces "a designed ElevenLabs voice reads every line before the clips".

| Where | What happens | Tool |
|---|---|---|
| **3.2 Elements — make** | A person's VOICE is cast from the clip model: Omni says their real lines from their casting master, three takes; the take that says every word and fits the character is cloned (ElevenLabs instant voice clone). That clone is the person's one voice, saved in their casting `voice.json` (old voice kept under `previous_voices`). | `machine/voice_cast.py takes` → pick → `voice_cast.py clone` |
| **3.3 Elements — approve** | the owner hears one check line per new voice; "elements ok" locks it. | — |
| **4.2 Production — off-camera lines** | Lines whose speaker is not in the picture (a doctor seen only by the hands, voice-over) are read by the cloned voice (ElevenLabs text-to-speech), crisp finish, placed on the off-camera track. | `machine/voice.py` with the casting `voice.json` |
| **4.5 Production — on-camera lines** | The clip is Omni ANIMATING the approved picture (the picture itself is made earlier, at 4.4, by GPT Image 2.5 — Omni never makes pictures). Lines whose speaker's mouth is in the picture are SPOKEN INSIDE THE CLIP: Omni says them (lip sync built in); the transcript's word timings split who says what; each stretch is turned into that person's cloned voice (ElevenLabs speech-to-speech); crisp finish; laid back on the untouched picture; words checked; cut after the last word. | `machine/omni.py` (talk / `revoice_lines`) |
| ~~4.6 upscale~~ | Retired 3 Oct: clips are made at 1080p (the face lock), so nothing is upscaled. | — |
| **5 Edit** | On-camera voices stay inside their clips (never drift); off-camera voices, room sound, effects and music on their own tracks. | `tools/video-edit/` |

**Why the voices used to come first, and why they don't now** (the owner, 2026-10-03): *"the only
reason we had the audio split out differently was because sometimes there would be awkward space in
the video clips … generate the audio, then cut out the dead air when you get to editing, then generate
the scenes on top of that … it's actually just easier to generate the voices directly from the model
itself, and then we can adjust the voice later. Also, the lip sync's already done … it's just literally
just changing the voice."* Dead air is now handled by the clip's own word timings: every clip is made
to its storyboard length (never padded), and the edit trims each clip's head and tail to its first and
last spoken word (the same transcript that splits the speakers), so no awkward space reaches the cut.

**The face lock — every clip keeps the person on their casting sheet** (the owner, 2026-10-03: *"you're
literally changing this woman's eye color and face … troubleshoot the problem at a fundamental level so
that we can not have this happen again"*). Measured on the Nova run (machine/face_lock.py): at 360p with
only the picture, eye colour drifted from the approved picture in 24 of 27 clips (blue-grey → brown),
spots moved, and "movement" clips (reference mode) started on a different woman; chained clips drifted
most; the upscaler was not the cause. Tested fix: identity words + 1080p → drift 0.023, a 1080p chain
0.013 (from 0.10–0.26) — the chain figure is from before the hand-off root cause was found; chaining
people is now ruled out (point 3). So, for every clip, any character, any brand:
1. **Made at 1080p** (no upscale step).
2. **Each visible person's identity is written into the prompt** — eye colour, marks, spots, hair —
   read from their casting `spec.json` (`omni_clips.identity_words`), never typed per ad.
3. **A person on screen locks the approved picture as the first frame** (image-to-video); the swipe's
   movement is said in words. Reference mode (blurred swipe footage) only for shots with no face.
   **Every clip of that section starts from the approved picture — never from the clip before's last
   frame.** Root cause found 3 Oct on the Nova run: the 17 clips that started from the approved picture
   all held her; the 10 that started from a handed-on last frame all drifted, worse each hand-off (paler
   and fading spots → older, harder face → brown eyes). A handed-on frame is a copy of a copy. Between
   clips the edit cuts back to the same starting pose, like a creator's jump cuts.
4. **The face lineup by eye is the real check** — every clip's face beside the approved picture,
   looked at before anything is shown. The automated eye check that runs after each clip
   (`face_lock.eyes_held`: eye colour off a close crop, against the approved picture, remade once, then
   flagged) is only a first filter: it missed faces that aged or hardened while the eyes stayed light and
   read some brown eyes as light, and whole-frame and pixel eye checks proved useless (sunglasses, blinks,
   second faces). No new automated face check is added; the lineup decides.

**Sounds that are not words** (the owner, 2026-10-03: *"we should just keep that as a separate sound, not
worry about lip sync there. Obviously, keep her head nod, but we don't need to put in the vocals with
it"*). "Mm-hmm", "uh-huh", "hmm", "um" are never said inside a clip: the person on screen nods, lips
closed (`words.nod`), and the sound is made in their cloned voice as its own track (`clips/offcam/`,
marked `sound`) and laid in at the edit. A sound at the start or end of a spoken line is cut from what
Omni says and made the same way (`omni_clips.split_sound`).

**Who says each line = the brief's `speaker`**, which matches the swipe's transcript — never whose
hands or face are in the shot. (3 Oct: going by the shot put the doctor's "A little glycolic peel."
over the phone insert into Nova's mouth; it is the doctor talking over the cut, as in the swipe.)

**How the sound attaches** — three kinds, shown per section on the ad's page: *voice in the clip*
(lip-synced, swapped to the cloned voice, travels with the clip) · *own track* (off-camera voice,
cloned voice, laid in at the edit) · *sounds* (nod in the clip, sound laid in at the edit).

**The crisp finish** (`omni.CRISP`): the cast voices measured dull next to the clip model's sound
(4–10 kHz −19 dB vs −12; above 10 kHz −26 vs −17); every voice line is lifted to match.

## When the brief changes after the voices

The words decide, never the scene number: `voice_remap.py <run> --brief <brief>`
reuses every recording whose words are unchanged and cuts a split line out of its
own recording at the word, then checks each cut back by speech-to-text. Nothing
the owner already listened to is re-recorded (2026-10-02).

## QC runs beside every step — the owner sees output, not problems

the owner, 2026-10-02: *"You're the best checker of your own work … have something
in parallel that is always checking and updating your own work, QCing it … if
it's catching any issues, then it can trigger something else to go ahead and
dynamically update that chain or whatever the upstream issue is … so I can just
focus on output."*

After every step, before anything reaches the owner or spends money:

1. **`machine/qc.py <run> --teardown <teardown run>`** — every machine check the
   chain has, in one pass (brief contract, people vs elements, swipe shot by
   shot, spoken words, stamps; elements banked; every voice is its line;
   storyboard current and complete). Each finding names the **station that made
   it**. `--look` adds the picture judges, `--listen` the speech-to-text.
2. **A reviewer** (a separate agent, read-only) goes over the same run as a
   careful producer would — what no machine check covers — and returns
   BLOCKER / FIX / NOTE findings, each with the station to fix it at.
3. **Every finding is fixed at its station, not patched downstream**, the
   station's check is tightened so it cannot recur, and the steps after it are
   re-run (the rule above). Then QC runs again.
4. **Every QC round is filed in the repo, by the machine** (the owner, 2026-10-02:
   "each qc log needs to be filed in the repo … so improvements to the chain can
   be made"). `machine/qc_log.py` keeps `<run>/qc-log/QC-LOG.md` — one row per
   round: step, checked by, method, passed, sent back, causes, the CHAIN-FIXES
   row that fixed it — with the raw findings beside it
   (`<step>-r<N>-<by>.json`). `qc.py` files its own round every time it runs;
   the reviewer's findings and the owner's own reads are filed with
   `qc_log.py add <run> --step <step> --by <who> --findings <file>`; the chain
   fix is written back with `qc_log.py fix <run> --round N --fix "CHAIN-FIXES …"`.
5. **the owner gets one thing: checked output and a yes/no.** Never a list of
   problems to judge, never a question QC can answer.
