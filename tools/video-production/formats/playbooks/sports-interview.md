# Playbook · Sports interview (press-conference answer) (`sports-interview`)

**Status:** draft · **state:** drafted-by-builder
**Family:** sports-interview · nearest when drafted: `multi-speaker-scene`

A single seated person at a branded press-conference table answering questions from off-camera reporters, filmed from the press seats — one unbroken set-up, the whole read carried by the words and the subject's face.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | 4 |
| address | to-each-other |
| settings | 1 |
| product_role | none |
| pacing | slow |
| capture | broadcast |
| story | interview |

## What is specialised, and why

- **ONE set-up, one room, two framings only — a wide walk-in with reporters' heads in the foreground and a static medium on the subject held for the rest of the piece** — the frame map reads 90.007 s with 0 cuts and a single shot K01 (eye level, medium, set down still, no move); the shot table changes framing once, at 0:04.2, and never again. Every clip comes off one or two pictures of the same table
- **only the subject is ever generated — three of the five cast members are voices with no face** — the cast sheet marks Moderator, the two reporters 'Not seen' on face, hair, body, wardrobe; the Staff Member appears as a torso and arms for one second (0:10–0:11). No person pictures are owed for them, which is the cheapest cast list of any family we have
- **the off-camera questions and announcements are voice-only tracks over the subject's listening clip — no reverse shots, no reporter pictures** — the shot table never cuts to a questioner: 0:20.9–0:46.7 is 25.8 s of a reporter talking over a static medium of the subject listening. Phase 2's own note is 'a long, unbroken 25-second hold'
- **listening is a scene, not dead air — the longest single stretch (25.8 s) is the subject reacting while someone else speaks** — `B-vo` carries 46.9 s of 90 against `A`'s 42.1 s. More than half the runtime is the subject silent on camera, so the clip plan has to hold identity and micro-expression with the mouth closed
- **nothing to camera — the subject looks at whoever asked, then scans the room; never into the lens** — signature address is to-each-other, and the cast note reads 'Maintains steady eye contact with the person asking the question, then scans the room while answering'. A to-lens look reads as an ad and kills the broadcast premise
- **no product anywhere in the piece — product_role is none; the offer lands in the caption, the comments or the endcard the lane adds, never in the room** — props are a microphone, a water bottle and a name card; nothing in the teardown touches a product. This is the first family where the picture prompts owe no product-scale or product-colour rule at all
- **the branded backdrop and table skirt are the whole production value — an original institutional backdrop (repeating logo pattern, matching table cloth, bright flat front light, no shadow on the wall), built once as a set element and reused for every piece in this family** — the places read says the backdrop and skirt 'provide immediate institutional authority… forcing the viewer to accept the premise as reality'. The swipe's real team and sponsor marks are the swipe's, not ours (holds follow the swipe — flaggable things become original stand-ins), so one banked original backdrop replaces them and amortises across every press-conference ad
- **broadcast capture look is explicit in every picture prompt: tripod eye level from the press seats, reporters' heads soft in the foreground of the wide, hard even frontal studio light, no grade, no bokeh, no phone-grade realism** — capture is 'broadcast', not 'studio' or 'phone'. The aesthetic archetype is 'authentic sports journalism… harsh lighting, step-and-repeat banners'. The nearest playbook's phone-grade style lock would read as the wrong genre here
- **room sound is the signature: continuous camera shutters under the whole piece, with faint shuffle and a laugh beat where the room reacts** — every row of the shot table carries 'room: heavy camera shutters', and 0:15.4–0:20.9 adds 'faint laughter from reporters'. Nine added effects were measured. Shutters are the cheapest and strongest realism cue in this format and are a bed, not a cue
- **music is a low ambient drone under the voices for the full runtime, not the nearest playbook's ducked bed — measured 92.3 bpm, F minor, textural rather than beat-driven, one subtle build around 22 s, ending quietly** — the music read: 'dark, atmospheric ambient drone… low, ominous synthesizer pads and sub-bass rumbles… the rhythm is very loose and textural rather than beat-driven'. A rhythmic bed would fight the press-room realism and expose the piece as an ad
- **lower thirds are the only on-screen text, white, on the cut at 0:04.2 for about four seconds — place card, then name and role; no captions at all** — the layer sheet lists exactly two lower thirds and 'Hook text: none / Captions: none'. Captions on a press conference look like a repost, not a broadcast, so the ig-fb-native caption look is off for this family
- **the hook is the premise, not a line — the opener is the wide walk-in and the impossible pairing of person and uniform; alternate openings swap the premise (who, in what, where) rather than rewriting the first spoken line** — psychological play 1 is 'The Pattern Interrupt (Visual)'. Phase 1's purpose is to 'arrest attention through a highly unexpected visual'. The nearest playbook's hook alternates swap a scene or a line; here the swappable unit is the premise itself
- **the subject's spoken delivery keeps the hesitation — 'um', 'uh', 'you know', a thought narrated while it forms, softeners before absolutes — and the voice is cast for a mid-low, calm, resonant, measured read** — the voice fingerprint: 'Frequent use of "Um", "Uh", and "you know" as connective tissue'; 'Narrates the way in, buying time to formulate the answer'. A clean, fluent read is the single fastest way this family reads as AI
- **480p, one take of each (another only if it fails, three at most), the pick upscaled locally (2026-10-21, was 1080p) for the subject; clip length pushed to the 10 s ceiling and several clips off ONE picture — the static medium is the same picture all the way through, restarted with a small punch-in at each join** — zero cuts across 90 s means every join is ours, not the swipe's. One approved medium picture can carry 6–8 clips at 1–2 clips per picture elsewhere; this family supports 4+ off a single frame, which is where its cost advantage comes from
- **two pictures total as the floor: the wide walk-in and the static medium. No per-scene pictures** — one setting, one shot, one subject. The nearest playbook budgets 108+39 picture calls on a multi-room family; the shot table here supports two framings and nothing else
- **a hands-and-props pass on the medium picture — gooseneck mic, water bottle, folded tent name card — because the subject's business in the scene is handling them** — the props list times each one (water handed in at 0:10, the card picked up at 0:15.4 and set down at 0:19.0) and the manner note is 'adjusts his seating and microphone with familiarity'. These small handled objects are where extra fingers and warped text show up
- **the name card, the backdrop logos and any sponsor patch are the only readable text in frame and must be our own words, spelled right, checked at full resolution before any clip** — the clip gate already refuses a misspelt name or big text that is not words. Here legible text is in three places at once (card, backdrop pattern, jersey patch) and it is the first thing a viewer reads
- **a real-person likeness gate before anything spends: the subject is a banked original character, never a recognisable public figure in a situation they were not in** — the triage read on this swipe is 'Impossible scenario… indicates a deepfake… LIKELY AI'. The structure — press conference, unexpected announcement, slow reveal — is what carries over; the swipe's actual person does not

## Stage order

teardown → writing (the premise is the hook; the answer carries the message) → elements (one subject, one backdrop set, three props — three voices with no face) → voices (every speaker, including the three never seen) → storyboard (two framings, one room) → pictures (the wide, the medium) → clips (Seedance 2.5, 480p, one take, many off one picture; the locked read goes in as the clip's audio) → the locked read goes into the clip as its audio (nothing is fitted afterwards) → words check → edit (shutter bed, drone under, lower thirds; cuts between whole takes, no repairs) → hook openings (premise swaps)

## Stage settings

**audio**
- first: voice
- voice_model: elevenlabs
- on_camera: said inside the clip: the approved read goes in as the clip's audio (nothing is fitted afterwards)
- off_camera: the moderator's and each reporter's cloned voice on its own track — no picture is ever owed for them
- voices_kept: on
- turns: strict turn-taking with a beat of room tone between — a reporter finishes completely before the answer starts (the swipe withholds the answer until the question ends)
- delivery: keep the fillers and the self-interruptions; mid-low, calm, measured, resonant for the subject; mid-pitch professional for the moderator and reporters
- room_tone: continuous camera shutters under the entire piece, laid as a bed before the music

**song**
- flow: the shared chain's own

**pictures**
- door: direct.openai
- model_key: model
- quality: high
- size: 1152x2048
- aspect: 9:16
- fix_calls: off
- count_floor: 2
- framings: wide walk-in: subject entering from frame left, reporters' heads and shoulders soft in the foreground, backdrop visible behind, static medium: subject seated centre, mic in front, backdrop filling the frame behind
- subject_zone: 15–85% of the height, said in the first prompt
- style_lock: broadcast press capture — tripod eye level from the press seats, hard even frontal studio light, no shadow on the backdrop, no grade, no shallow depth, no phone-grade look
- set_reuse: one banked original backdrop + table skirt element, reused across every piece in this family
- only_these_things: list every prop — gooseneck mic on a desktop stand, water bottle, folded tent name card, table cloth; nothing from the swipe's own marks, team or sponsor leaks in
- text_in_frame: only our own words on the name card and backdrop pattern — spelled, checked at full resolution
- product: none — this format has no product in the room

**clips**
- model: seedance_2_5
- endpoint: image-to-video
- resolution: 720p
- seconds: 4, 10
- cut_at: line or sentence boundaries, never padded
- clips_per_picture: 4, 8
- takes: 1
- upscale: local Real-ESRGAN to 1080x1920 — the picked take only (VIDEO-RULINGS V6, 2026-10-21)
- stills_allowed: off
- person_from: the approved medium picture for every seated beat; the approved wide for the walk-in only
- restart_on_same_picture: the swipe has zero cuts, so the fewest joins the clip length allows, each at a line boundary, a straight cut or a continuous hand-off — never a punch-in to hide it (VIDEO-RULINGS V15)
- listening_clips: the longest clips in the piece carry no speech — the subject listens, chin on hand, eyes on the questioner; no mouth movement at all
- camera: static in every clip, one continuous take, no reframe inside a call
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least

**cast**
- reuse: banked cast first — one subject carries every piece in this family; the moderator and the reporters are banked VOICES only, no faces owed
- recurring: on
- faces_owed: 1
- likeness: banked original character — never a recognisable public figure placed in a situation they were not in
- product: when our version hands the subject the product: real size from the turntable, pasted from real photos

**hooks**
- shape: the premise IS the hook — alternates swap who walks in, what they are wearing and whose backdrop it is, not the first line
- count: 5
- generated: only the wide walk-in picture and its clip

**captions**
- look: none — a press conference with burned-in captions reads as a repost, not a broadcast
- lower_thirds: two, white, in on the cut at ~4 s for ~4 s: place line top left, name and role bottom left

**gates**
- apply: all 13 (run.py start), line parity on every talking clip, voices kept, never re-recorded, mouths reviewed — the subject's lips must be still through every listening clip, picture QC with a working reviewer, readable-text check on the name card, backdrop and any patch at full resolution, likeness check — no recognisable public figure
- skip: song gates, product-scale and product-colour checks (no product in frame), caption gates

**edit**
- method: video-edit machine cut on the voice track
- cover_before_remake: off
- broll: real footage only, ~2.5 s each — customer before/afters and the product in use; no AI clips, no burned-in text (the owner 2026-10-09)
- lip_offset: measure in each clip's own frames; one global picture offset when the whole cut is a frame off
- loudness: -14 LUFS
- music: low ambient drone under the whole piece, F-minor-dark and textural, one subtle build around 22 s, ending quietly — about -22 dB under voice, quieter than a rhythmic bed
- room_bed: camera shutters continuous under everything; a faint laugh beat where the room reacts
- joins: every join is ours (the swipe has zero cuts) — the fewest the takes allow, each between lines as a straight cut, never a punch-in (VIDEO-RULINGS V15)
- small_print: none
- end_card: none (the owner 2026-10-09: "forget the end card, it's weird")

## Known failures → fixes

- **the picture door refused a public figure's likeness** → re-sent once with the swipe frame's faces covered; the subject is an original banked character  _(from runs/video-production/<brand>/lebron-to-philadelphia-2026 (commit d4bcf065c9); stage pictures)_
- **The clip model refused the same 3 clips on every try** → those clips went to the alternate door (Seedance) with the subject's real cloned voice  _(from runs/video-production/<brand>/lebron-to-philadelphia-2026; stage clips)_
- **an invented name card in a picture** → fixed at the picture — name card text is ours, checked at full resolution  _(from runs/video-production/<brand>/lebron-to-philadelphia-2026; stage pictures)_
- **the frame map found only 12 moments with 40 s gaps on the single-camera swipe; production improvised** → frame map in 8-second windows on a single locked shot (67 moments)  _(from runs/video-production/<brand>/lebron-to-philadelphia-2026-r2 (commit b139b04e83); stage teardown)_
- **the cut went away to the press pack** → one fixed wide camera, one take — no cutaways; chained start and end frames  _(from runs/video-edit/<brand>/lebron-to-philadelphia-2026 (decisions.json _swipe) → r3; stage edit)_
- **overlapping 'uh/um' murmurs cut off a name** → no overlap — each speaker waits their turn  _(from runs/video-edit/<brand>/lebron-to-philadelphia-2026-r3 (decisions sounds); stage audio)_
- **a false 2-frame lip slip — the checker counted 30 fps on 24 fps clips** → lip offset measured in each clip's own frames  _(from runs/video-production/<brand>/lebron-to-philadelphia-2026-r3 (HANDOFF.md); stage edit)_
- **a clip dropped one word ('so')** → that one clip re-made ($1.50)  _(from runs/video-production/<brand>/lebron-to-philadelphia-2026-r3 (HANDOFF.md); stage clips)_

## Cost

- target per ad: $8
- why: one room, one subject, two pictures and no product — the whole piece runs off 4–8 clips per picture on a locked-off static frame, with three of five speakers costing voice only and the backdrop banked once and reused
- measured: r1 $17.77, r2 $37.56, r3 ~$20.35 (old Omni route 1080p + pictures, ledger.json each)

## Quality bar — not slop

- one room all the way through — same backdrop pattern, same light, same table dressing, same wardrobe
- the camera never moves and never reframes inside a shot; only two framings exist in the finished ad
- the subject's lips are completely still whenever someone else is speaking
- every word is heard, none cut off, and the hesitations are still there
- the subject sounds like their face — mid-low, calm, measured, in their own cloned voice
- the moderator and the reporters are never seen, only heard
- the name card, the backdrop text and any patch are our own words, spelled right and readable at full size
- the subject looks at whoever asked, then scans the room — never into the lens
- no third hand, nothing warped on the mic, the bottle or the card
- camera shutters run unbroken under the entire piece, including across every join
- the music is a low drone under the voices and never turns into a beat
- the lower thirds appear once, on the early cut, and never return
- no burned-in captions anywhere
- no product is visible in the room at any point
- the person in the last clip is the same person as in the first

## Variants (same workflow, refined)

### meme (`meme`, draft)
- differs: speakers: 1; pacing: medium; capture: studio
- from: runs/video-teardown/_work/v2test-meme-dalk
- matched at score 0.785


## Built from

- runs/video-production/<brand>/lebron-to-philadelphia-2026
- runs/video-production/<brand>/lebron-to-philadelphia-2026-r2
- runs/video-production/<brand>/lebron-to-philadelphia-2026-r3
- runs/video-edit/<brand>/lebron-to-philadelphia-2026-r3
- runs/video-teardown/<brand>/lebron-to-philadelphia-2026

## Rulings behind it

- the owner 2026-10-09 (r3 decisions.json): "start the ad from 'You guys know who I am, right?'" — the opener is the subject's first line
- the owner 2026-10-09: "forget the end card, it's weird"
- the owner 2026-10-09: "Real footage and real customer photos only: no AI clips, no burned-in text."
- the owner 2026-10-10: the matcher puts this swipe at 0.50 against multi-speaker-scene — its own family (one locked take, off-camera questions, interview shape)
