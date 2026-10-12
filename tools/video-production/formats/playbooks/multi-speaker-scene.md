# Playbook · Multi-speaker scene (people talking around a patient or a product) (`multi-speaker-scene`)

**Status:** draft · **state:** seeded from 3 cut runs + 2 matched grandma-format runs, 2026-10-10
**Family:** multi-speaker-scene

Real-looking people in one or a few rooms talking — to the lens and to each other — around one person's problem and the product: the three-doctors consult, the live TV-shopping demo, the grandma test bench. Every speaker in their own cloned voice; on-camera lines spoken inside the clip; faults covered at the edit before anything is remade.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

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

- **voices first, every speaker their own cloned voice, kept once approved** — a run re-recorded approved voices and drifted them (the three-doctors run vo-drifted-2026-10-01); every speaker reads in their own voice (CLAUDE.md 2026-09-23)
- **on-camera lines are said inside the Omni clip, then speech-to-speech into the cast voice + the crisp finish** — the owner 2026-10-03: "version a actually sounds like the avatar looks"
- **clips at 1080p (not 360p) for talking faces** — lip-sync and identity are the whole read of a talking head; 360p is a song-ad saving, not this family's
- **cover a fault at the edit before remaking it — close-ups, 7% punch-ins, b-roll, cloned-voice word patches** — the owner 2026-10-09: "only regenerate what's absolutely necessary… cover issues up with zoom ins b-roll"
- **never cut off a word; a dropped word is patched in the speaker's cloned voice** — the owner 2026-10-04: "We should never be cutting off words"
- **music bed for the whole edit, ducked under the voices** — the owner 2026-10-04: "we need the music for the whole edit"
- **pictures one quality step down (high), made at 9:16 with the subject zone in the first prompt; no zone-fix pass** — a subject-zone fix re-made 32 pictures on the three-doctors run and ran on every grandma run; cost target

## Stage order

teardown → writing (the hook stays as the format has it) → elements (banked cast first) → voices (every line, every speaker) → storyboard → pictures → clips (Omni 1080p, on-camera lines in the clip) → speech-to-speech + crisp finish → words check → edit (cover before remake) → hook openings

## Stage settings

**audio**
- first: voice
- voice_model: elevenlabs
- on_camera: said inside the clip, then speech-to-speech into the speaker's cloned voice + crisp finish
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
- model: gemini_omni_flash_1_1
- endpoint: image-to-video
- resolution: 1080p
- seconds: 3, 10
- cut_at: line or sentence boundaries, never padded
- clips_per_picture: 1, 2
- takes: 1
- upscale: none
- stills_allowed: off
- person_from: the section's approved picture, never a made frame
- restart_on_same_picture: 7% punch-in so the join reads as a jump cut

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
- cover_before_remake: on
- broll: real b-roll about 4 s each
- lip_offset: measure in each clip's own frames; one global picture offset when the whole cut is a frame off
- loudness: -14 LUFS
- music: bed for the whole edit, ducked about -19 dB under voice
- small_print: none (ruled 2026-10-07)

## Known failures → fixes

- **a run re-recorded voices already approved; they drifted** → approved takes restored; voices are kept, never re-recorded by a run  _(from a past run)_; stage voice)_
- **the picture reviewer crashed (JSONDecodeError); 21 pictures came back unreviewed** → the owner reviewed; a crashed reviewer is a stop, never a pass  _(from a past run)_; stage pictures)_
- **subjects outside the 15–85% height zone** → subject zone said in the first prompt (the zone-fix re-made 32 pictures)  _(from a past run)_; stage pictures)_
- **product drawn at the wrong size** → a product-scale rule in the picture prompt; product pixels from the real kit  _(from a past run)_; stage pictures)_
- **lips moving with no words on a silent person** → close-ups with the mouth out of frame  _(from a past run)_; stage edit)_
- **clips ran out mid-word** → trim the line; patch the missing words in the speaker's cloned voice (word_fix.py)  _(from a past run)_; stage edit)_
- **the clip wrote words on a shirt / a third hand appeared** → crop punch-in past it / cover with b-roll  _(from a past run)_; stage edit)_
- **lip sync about one frame off across the cut** → one global picture_offset (0.042 s)  _(from a past run)_; stage edit)_
- **the clip dropped "look at my"** → a cloned-voice word patch  _(from a past run)_; stage edit)_
- **garbled small label text passed by the clip gate** → blur or punch past at the edit  _(from a past run)_; stage edit)_
- **the swipe's own props leaked into a picture; a person given glasses** → "ONLY these things…" — the prompt lists every prop and look  _(from a past run)_; stage pictures)_
- **the clip model kept erasing the skin spot** → image-to-image still + push-in as b-roll  _(from a past run)_; stage edit)_
- **Omni cut to a new framing inside one call** → flagged at QC; one continuous take is in every clip prompt  _(from a past run)_; stage clips)_
- **scrub rendered white / crystalline** → "soft tan, golden-beige cream" — the product's real colour in words, from the kit  _(from a past run)_; stage pictures)_
- **the mouth tracker read a background screamer, not the lead** → mouths reviewed by hand  _(from a past run)_; stage edit)_
- **two shots planned on a clip door the provider does not offer** → plan only the ruled door (Omni image-to-video / reference-to-video)  _(from a past run)_; stage storyboard)_

## Cost

- target per ad: $__
- measured: the three-doctors run ~$__ (79 i2v clips at 1080p, 108+39 picture calls); TV shopping $__; test bench $__; body scan $__; public reaction $__ (ledger.json each)
- how: pictures at high not xhigh, subject zone in the first prompt (no zone-fix pass), cover at the edit before any remake, 1–2 clips per picture where a speaker stays in one set-up, banked cast

## Quality bar — not slop

- every word heard, none cut off (line parity on every talking clip)
- lips on the words within a frame
- a silent person's lips never move on screen
- every speaker sounds like their face — their own cloned voice
- no third hand, no words written on clothes or walls, no garbled labels left readable
- the product is the real thing at its real size and colour
- the room stays the same room across a scene (props, light, wardrobe)
- music bed under the whole edit, never fighting the voice

## Variants (same workflow, refined)

### Expert consultation (the three doctors) (`expert-consult`, draft)
one presenter takes the same problem to several experts in turn; the experts disagree; the last answer is the product
- differs: speakers: 3; settings: 4; pacing: fast
- override `stages.edit.broll` = none before the last expert (the owner 2026-10-03: "put broll on top early … do not do that at all"); real b-roll ~4 s after
- override `stages.edit.cards` = OPTION 1 / 2 / 3 in a native pop (white bold sans, dark rounded box); no receipt or price cutaways (the owner 2026-10-03)
- override `stages.cast.roles` = the presenter + the experts, a wardrobe change marking each consultation; spots shown on bare skin
- override `stages.hooks.count` = 5
- from: runs/video-production/<brand>/<run>, runs/video-edit/<brand>/<run>, runs/video-teardown/<brand>/<run>

### Live TV-shopping demo (`tv-shopping`, draft)
a host to the lens runs a live demo on a model while an artist applies the product — a demonstration, never a price ad
- differs: address: to-camera; capture: broadcast
- override `stages.captions.look` = none (none in the source)
- override `stages.edit.cards` = a live demonstration, not a value (price) ad (the owner 2026-10-09)
- override `stages.cast.roles` = host to the lens + silent artist + the model; host and artist cast new, the model from the bank
- from: runs/video-production/<brand>/<run>, runs/video-edit/<brand>/<run>, runs/video-teardown/<brand>/<run>

### Grandma's test bench (product explainer) (`grandma-explainer`, draft)
an older woman to the lens tests the product beside a silent younger helper, one kitchen set; the nearest record to the grandma + doctor explainer (no grandma + doctor run is on file)
- differs: speakers: 1; address: to-camera; product_role: held
- override `stages.captions.look` = ig-fb-native
- override `stages.edit.broll` = phone-photo inserts; where the clip erases the skin mark, an image-to-image still + push-in
- override `stages.edit.cards` = offer cards kept (buy 2 get 1)
- from: runs/video-production/<brand>/<run>, runs/video-edit/<brand>/<run>, runs/video-teardown/<brand>/<run>

### body scan recipe (`body-scan-recipe`, draft)
*
- differs: speakers: 1; address: to-camera; settings: 4; product_role: held
- from: runs/video-teardown/<brand>/<run>
- matched at score 0.94

### public reaction (`public-reaction`, draft)
demonstration · 0:11.6–0:37.5 · the product does the work on the Creator's armpit, hand, stomach and ankle. Each spray-and-wipe is one beat, showing before and after.
- differs: address: to-each-other; pacing: fast
- from: runs/video-teardown/<brand>/<run>
- matched at score 0.89


## Built from

- runs/video-production/<brand>/<run>
- runs/video-production/<brand>/<run>
- runs/video-production/<brand>/<run>
- runs/video-production/<brand>/<run>
- runs/video-production/<brand>/<run>
- <proven-to-format definition>

## Rulings behind it

- the owner 2026-10-10: the three-doctors ad, the TV-shopping ad and the grandma explainer are ONE family that shares one workflow, refined per variant
- the owner 2026-10-03: "version a actually sounds like the avatar looks" — on-camera lines in the clip, speech-to-speech
- the owner 2026-10-04: "We should never be cutting off words"; "we need the music for the whole edit"
- the owner 2026-10-07 (RULINGS.md): the hook stays as the format has it; no small print; a dramatized demo is fine
- the owner 2026-10-09: "only regenerate what's absolutely necessary… cover issues up with zoom ins b-roll"
