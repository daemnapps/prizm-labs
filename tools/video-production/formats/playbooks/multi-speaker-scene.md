# Playbook · Multi-speaker scene (people talking around a patient or a product) (`multi-speaker-scene`)

**Status:** draft · **state:** seeded from 3 cut runs + 2 matched grandma-format runs, 2026-10-10
**Family:** multi-speaker-scene

Real-looking people in one or a few rooms talking — to the lens and to each other — around one person's problem and the product: the three-doctors consult, the live TV-shopping demo, the grandma test bench. Every speaker in their own cloned voice; on-camera lines spoken inside the clip; the edit cuts between whole takes and never repairs (VIDEO-RULINGS V15).

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

## Structural signature

| | |
|---|---|
| audio | voice |
| speakers | 2 |
| address | mixed |
| settings | 1 |
| product_role | demo |
| pacing | medium |
| capture | studio |
| story | pitch |

## What is specialised, and why

- **voices first, every speaker their own cloned voice, kept once approved** — a run re-recorded approved voices and drifted them (kzn03-face-scrub vo-drifted-2026-10-01); every speaker reads in their own voice (CLAUDE.md 2026-09-23)
- **on-camera lines are said inside the clip: each line's own locked ElevenLabs v3 read goes in as the clip's audio (nothing is fitted afterwards; speech-to-speech retired 2026-10-21, VIDEO-RULINGS V4)** — the owner 2026-10-03: "version a actually sounds like the avatar looks"
- **480p, one take of every clip (another only if it fails, three at most), the pick upscaled locally (VIDEO-RULINGS V5/V6, 2026-10-21; was 1080p for talking faces)** — lip-sync and identity are the whole read of a talking head; 480p is a song-ad saving, not this family's
- **the edit cuts between whole takes; a faulty take is replaced by the best of its other takes, never covered with a punch-in, a zoom-in or b-roll (VIDEO-RULINGS V15, 2026-10-21; replaces 2026-10-09's cover-before-remake)** — the owner 2026-10-20: "I don't want it to look mechanical at all" — the swipe's own shot count, cuts between shots, no unneeded zoom-ins or punch-ins; the edit cuts, it does not repair
- **never cut off a word; a dropped word is patched in the speaker's cloned voice** — the owner 2026-10-04: "We should never be cutting off words"
- **music only when the swipe or the brief calls for it, ducked under the voices (VIDEO-RULINGS V14, 2026-10-21; was a bed for the whole edit by default)** — the owner 2026-10-04: "we need the music for the whole edit"
- **pictures one quality step down (high), made at 9:16 with the subject zone in the first prompt; no zone-fix pass** — a subject-zone fix re-made 32 pictures on kzn03 and ran on every grandma run; cost target

## Stage order

teardown → writing (the hook stays as the format has it) → elements (banked cast first) → voices (every line, every speaker) → storyboard → pictures → clips (Seedance 2.5, 480p, one take, three tries at most; the locked read goes in as the clip's audio) → the locked read goes into the clip as its audio (nothing is fitted afterwards) → words check → edit (cuts between whole takes; no repairs) → hook openings

## Stage settings

**audio**
- first: voice
- voice_model: elevenlabs
- on_camera: said inside the clip: the speaker's own locked v3 read goes in as the clip's audio (nothing is fitted afterwards)
- off_camera: the speaker's cloned voice on its own track
- voices_kept: on
- turns: each speaker waits their turn — no overlapping murmurs

**song**
- flow: the shared chain's own

**pictures**
- door: direct.openai
- model_key: model
- quality: high
- size: 1152x2048
- aspect: 9:16
- fix_calls: off
- subject_zone: 15–85% of the height, said in the first prompt
- style_lock: the swipe's style row (phone-grade realism on every run so far)
- only_these_things: list every prop; nothing from the swipe's own props leaks in

**clips**
- model: seedance_2_5
- endpoint: image-to-video
- resolution: 720p
- seconds: 4, 10
- cut_at: line or sentence boundaries, never padded
- clips_per_picture: 1, 2
- takes: 1
- upscale: local Real-ESRGAN to 1080x1920 — the picked take only (VIDEO-RULINGS V6, 2026-10-21)
- stills_allowed: off
- person_from: the section's approved picture, never a made frame
- restart_on_same_picture: a new shot — the storyboard's next angle or framing — cut at a line boundary; never a punch-in to hide the join (VIDEO-RULINGS V15)
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least

**cast**
- reuse: banked cast first (the same presenter served four formats); new cast only for the roles a format adds (host, artist, doctors)
- recurring: on
- product: real pixels — real archive clip, studio render or the turntable paste (live-action family)

**hooks**
- shape: the hook stays as the format has it; 4–5 alternate openings swap the first scene or line (G01-H2…H6)
- count: 5
- generated: only the opening scene

**captions**
- look: ig-fb-native (Instagram/Facebook) unless the source has none

**gates**
- apply: all 13 (run.py start), line parity on every talking clip, voices kept, never re-recorded, mouths reviewed (a silent person's lips moving), picture QC with a working reviewer
- skip: song gates

**edit**
- method: video-edit machine cut on the voice track
- cover_before_remake: off
- broll: real b-roll about 4 s each
- lip_offset: measure in each clip's own frames; one global picture offset when the whole cut is a frame off
- loudness: -14 LUFS
- music: only when the swipe or the brief calls for it (VIDEO-RULINGS V14); then ducked about -19 dB under voice
- small_print: none (ruled 2026-10-07)

## Known failures → fixes

- **a run re-recorded voices already approved; they drifted** → approved takes restored; voices are kept, never re-recorded by a run  _(from runs/video-production/<brand>/kzn03-face-scrub (vo-drifted-2026-10-01); stage voice)_
- **the picture reviewer crashed (JSONDecodeError); 21 pictures came back unreviewed** → the owner reviewed; a crashed reviewer is a stop, never a pass  _(from runs/video-production/<brand>/kzn03-face-scrub-clean (qc-log/QC-LOG.md round 1); stage pictures)_
- **subjects outside the 15–85% height zone** → subject zone said in the first prompt (the zone-fix re-made 32 pictures)  _(from runs/video-production/<brand>/kzn03-face-scrub-clean (ledger notes); stage pictures)_
- **product drawn at the wrong size** → a product-scale rule in the picture prompt; product pixels from the real kit  _(from runs/video-production/<brand>/kzn03-face-scrub-clean (QC-LOG round 2); stage pictures)_
- **lips moving with no words on a silent person** → the take prompt says "listens in silence, lips closed" (VIDEO-RULINGS V8); a take that still moves them is replaced by another take, never hidden in a close-up (VIDEO-RULINGS V15)  _(from runs/video-edit/<brand>/kzn03-face-scrub-clean (decisions.json closeups); stage edit)_
- **clips ran out mid-word** → trim the line; patch the missing words in the speaker's cloned voice (word_fix.py)  _(from runs/video-edit/<brand>/kzn03-face-scrub-clean (decisions trim_line, add_lines); stage edit)_
- **the clip wrote words on a shirt / a third hand appeared** → caught at the picture and clip checks; the take is replaced by another take, or the shot remade — never a crop punch-in or a b-roll cover (VIDEO-RULINGS V15)  _(from runs/video-edit/<brand>/kzn03-face-scrub-clean (decisions fixes, broll); stage edit)_
- **lip sync about one frame off across the cut** → one global picture_offset (0.042 s)  _(from runs/video-edit/<brand>/01-grandma-house-face-x-dd7gvdvprzl (decisions.json); stage edit)_
- **the clip dropped "look at my"** → a cloned-voice word patch  _(from runs/video-production/<brand>/01-grandma-house-face-x-dd7gvdvprzl (patches/S15-look-at-my-cheek.json); stage edit)_
- **garbled small label text passed by the clip gate** → blur at the edit, never a punch-in past it (VIDEO-RULINGS V15)  _(from runs/video-production/<brand>/01-grandma-house-face-x-dd7gvdvprzl (clips/GATE.md); stage edit)_
- **the swipe's own props leaked into a picture; a person given glasses** → "ONLY these things…" — the prompt lists every prop and look  _(from runs/video-production/<brand>/01-grandma-house-face-x-dd12vx6inuo (picture-fixes.json); stage pictures)_
- **the clip model kept erasing the skin spot** → image-to-image still + push-in as b-roll  _(from runs/video-edit/<brand>/01-grandma-house-face-x-dd12vx6inuo (decisions.json broll); stage edit)_
- **The clip cut to a new framing inside one call** → flagged at QC; one continuous take is in every clip prompt  _(from runs/video-production/<brand>/01-grandma-house-face-x-davxlyhkzsb (qc-log/QC-LOG.md round 3); stage clips)_
- **scrub rendered white / crystalline** → "soft tan, golden-beige cream" — the product's real colour in words, from the kit  _(from runs/video-production/<brand>/01-grandma-house-face-x-dbmik5rnwqv (picture-fixes.json); stage pictures)_
- **the mouth tracker read a background screamer, not the lead** → mouths reviewed by hand  _(from runs/video-edit/<brand>/01-grandma-house-face-x-dbmik5rnwqv (decisions.json mouths_reviewed); stage edit)_
- **two shots planned on a clip door the provider does not offer** → plan only the ruled door (Seedance 2.5 image-to-video / reference-to-video)  _(from runs/video-production/<brand>/01-grandma-house-face-x-dd7gvdvprzl (handoff); stage storyboard)_

## Cost

- target per ad: $20
- measured: kzn03-face-scrub-clean ~$75 (79 i2v clips at 1080p, 108+39 picture calls); TV shopping $57.58; test bench $21.99; body scan $21.47; public reaction $13.90 (ledger.json each)
- how: pictures at high not xhigh, subject zone in the first prompt (no zone-fix pass), one take kept, another only if it fails (no cover-ups at the edit), 1–2 clips per picture where a speaker stays in one set-up, banked cast

## Quality bar — not slop

- every word heard, none cut off (line parity on every talking clip)
- lips on the words within a frame
- a silent person's lips never move on screen
- every speaker sounds like their face — their own cloned voice
- no third hand, no words written on clothes or walls, no garbled labels left readable
- the product is the real thing at its real size and colour
- the room stays the same room across a scene (props, light, wardrobe)
- music only when the swipe or the brief calls for it, never fighting the voice

## Variants (same workflow, refined)

### Expert consultation (the three doctors) (`expert-consult`, draft)
one presenter takes the same problem to several experts in turn; the experts disagree; the last answer is the product
- differs: speakers: 3; settings: 4; pacing: fast
- override `stages.edit.broll` = none before the last expert (the owner 2026-10-03: "put broll on top early … do not do that at all"); real b-roll ~4 s after
- override `stages.edit.cards` = OPTION 1 / 2 / 3 in a native pop (white bold sans, dark rounded box); no receipt or price cutaways (the owner 2026-10-03)
- override `stages.cast.roles` = the presenter + the experts, a wardrobe change marking each consultation; spots shown on bare skin
- override `stages.hooks.count` = 5
- from: runs/video-production/<brand>/kzn03-face-scrub-clean, runs/video-edit/<brand>/kzn03-face-scrub-clean, runs/video-teardown/<brand>/kzn03-face-scrub

### Live TV-shopping demo (`tv-shopping`, draft)
a host to the lens runs a live demo on a model while an artist applies the product — a demonstration, never a price ad
- differs: address: to-camera; capture: broadcast
- override `stages.captions.look` = none (none in the source)
- override `stages.edit.cards` = a live demonstration, not a value (price) ad (the owner 2026-10-09)
- override `stages.cast.roles` = host to the lens + silent artist + the model; host and artist cast new, the model from the bank
- from: runs/video-production/<brand>/01-grandma-house-face-x-dd7gvdvprzl, runs/video-edit/<brand>/01-grandma-house-face-x-dd7gvdvprzl, runs/video-teardown/<brand>/fmt-tv-shop-dd7gvdvprzl

### Grandma's test bench (product explainer) (`grandma-explainer`, draft)
an older woman to the lens tests the product beside a silent younger helper, one kitchen set; the nearest record to the grandma + doctor explainer (no grandma + doctor run is on file)
- differs: speakers: 1; address: to-camera; product_role: held
- override `stages.captions.look` = ig-fb-native
- override `stages.edit.broll` = phone-photo inserts; where the clip erases the skin mark, an image-to-image still + push-in
- override `stages.edit.cards` = offer cards kept (buy 2 get 1)
- from: runs/video-production/<brand>/01-grandma-house-face-x-dd12vx6inuo, runs/video-edit/<brand>/01-grandma-house-face-x-dd12vx6inuo, runs/video-teardown/<brand>/fmt-hua-jin-dd12vx6inuo

### body scan recipe (`body-scan-recipe`, draft)
*
- differs: speakers: 1; address: to-camera; settings: 4; product_role: held
- from: runs/video-teardown/<brand>/fmt-body-scan-davxlyhkzsb
- matched at score 0.94

### public reaction (`public-reaction`, draft)
demonstration · 0:11.6–0:37.5 · the product does the work on the Creator's armpit, hand, stomach and ankle. Each spray-and-wipe is one beat, showing before and after.
- differs: address: to-each-other; pacing: fast
- from: runs/video-teardown/<brand>/fmt-public-reaction-dbmik5rnwqv
- matched at score 0.89

### demonstration (`demonstration`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/fmt-askolivia-dceksuikmvp
- matched at score 0.9

### single presenter (`single-presenter`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/fmt-rooted-health-dbjcmwipmrh
- matched at score 1.0

### expert stitch (`expert-stitch`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/fmt-dannyguo-dscbuh9caej
- matched at score 1.0

### expert reaction (`expert-reaction`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/fmt-dr-romero-dvvtqgcip0
- matched at score 1.0

### split screen comparison (`split-screen-comparison`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/fmt-dr-vanita-du3x2indexf
- matched at score 1.0

### remedy (`remedy`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/v2test-remedy-arden
- matched at score 1.0

### makeover reveal (`makeover-reveal`, draft)
- differs: speakers: 1; address: to-camera; product_role: none
- from: runs/video-teardown/_work/batchtest-barber
- matched at score 1.0


## Built from

- runs/video-production/<brand>/kzn03-face-scrub-clean
- runs/video-production/<brand>/01-grandma-house-face-x-dd7gvdvprzl
- runs/video-production/<brand>/01-grandma-house-face-x-dd12vx6inuo
- runs/video-production/<brand>/01-grandma-house-face-x-davxlyhkzsb
- runs/video-production/<brand>/01-grandma-house-face-x-dbmik5rnwqv
- components/ad-variations/definitions/proven-to-format/<brand>-grandma-2026-10.json

## Rulings behind it

- the owner 2026-10-10: the three-doctors ad, the TV-shopping ad and the grandma explainer are ONE family that shares one workflow, refined per variant
- the owner 2026-10-03: "version a actually sounds like the avatar looks" — on-camera lines in the clip, speech-to-speech (SUPERSEDED 2026-10-20/21, VIDEO-RULINGS V4: the locked read is fitted to the lips, no speech-to-speech)
- the owner 2026-10-04: "We should never be cutting off words"; "we need the music for the whole edit"
- the owner 2026-10-07 (RULINGS.md): the hook stays as the format has it; no small print; a dramatized demo is fine
- the owner 2026-10-09: "only regenerate what's absolutely necessary… cover issues up with zoom ins b-roll" (SUPERSEDED 2026-10-20, VIDEO-RULINGS V15: no unneeded zoom-ins or punch-ins; the edit cuts, it does not repair)
