# Playbook · Fake billboard stunt ad (street video, no speaker) (`fooh-stunt`)

**Status:** draft · **state:** drafted-by-builder
**Family:** fooh-stunt · nearest when drafted: `short-movie`

A ~9 s wordless phone-shot vertical clip of a real city street where a giant billboard appears to come alive and hand the product out of the screen, resolving on a real hand holding the actual product, carried by a music bed with no voice and no captions.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

## Structural signature

| | |
|---|---|
| audio | none |
| speakers | 0 |
| address | none |
| settings | 1 |
| product_role | none |
| pacing | medium |
| capture | studio |
| story | pitch |

## What is specialised, and why

- **the ad is built in TWO LAYERS, not one picture-to-clip chain: a PLATE layer (handheld street footage, real or made to look phone-shot) and a SCREEN layer (the billboard content), composited — the plate is generated/sourced once and the whole ad is assembled on top of it** — the triage AI read says exactly this: the billboard content 'is then composited into real phone footage of a street using traditional VFX techniques'. The nearest playbook has one picture per set-up going straight to a clip; here one plate carries the entire piece and the work is in what sits inside the billboard rectangle
- **ONE setting only — a single street corner, single camera walk — so the element sheet is a street, a billboard geometry, the screen content and one hand** — the structural signature reads settings: 1 against the nearest playbook's 4, and the triage one-line describes a single continuous street-to-hand move; there is no second location to bank
- **the BILLBOARD RECTANGLE is a tracked surface, not a drawn one: the plate is made with a flat, clearly-bounded blank billboard (or a real one blanked), the screen content is generated separately at the billboard's own aspect, then corner-pinned into the plate at the edit** — the only reason a FOOH stunt reads as real is perspective-correct screen content with matching edge occlusion; generating a 'billboard with a woman on it' inside one picture is the single most reliable way to get a melted, perspective-wrong sign — and the nearest playbook already records 'garbled background signs' and words generated into pictures as real failures
- **the SCREEN layer is allowed to be openly synthetic and is generated at a higher quality tier than the plate — it is the one element the viewer stares at** — the triage AI assessment names the tells it saw (morphing, texture shimmer, unnatural physics in the woman's movement, hair and face as she leans forward) and still calls the piece an effective ad; the format's conceit is that the screen is a screen, so the usual anti-slop spend goes here and nowhere else
- **the PLATE is deliberately cheap and imperfect — handheld wobble, natural daylight, no grade, no retouch, phone-lens look; it is the one place where low quality is correct** — the style read is phone-ugc: 'handheld vertical video of a city street, natural lighting, unretouched hand holding the product, serving as the base plate'. A clean cinematic street would kill the illusion, so the cheapest setting is also the right one
- **the HAND-OFF is the single hardest moment and gets its own station: the match cut from the screen's hand releasing the product to the real hand holding it, planned as two clips designed to meet (same frame position, same light direction, same hand size in frame)** — the triage one-line makes this the whole ad: a woman on the billboard 'grabs a digital candle, which seamlessly transitions to a real hand holding the physical product on the street below'. Everything else in 9 s is set-up for that one join
- **the real product in the real hand is REAL footage or a pasted real packshot — never a generated or restyled product** — the format's payoff is the jump from digital to physical; a generated product at the reveal removes the only thing the stunt is proving. The nearest playbook's animated-style rule (product rendered in the film's style) is inverted here — the plate is live-action, so the product must be the actual object
- **the product does not appear for the first ~6 s and has no demo, no use, no label close-up — product_role is 'none' until the final beat** — the structural signature reads product_role: none against the nearest playbook's 'demo'; the triage category is 'scented candle, no speaker' and the runtime is 00:09. There is no room for a routine, so the nearest playbook's four product moments and its vanity block have nothing to do here
- **runtime 8–12 s with 3–5 cuts: approach/reveal of the billboard, the screen coming alive, the reach, the hand-off, the hold on the real product** — measured runtime is 00:09 and the pacing reads medium, against the nearest playbook's 26 s and 17 cuts; its fast-middle/slow-ends rule does not apply to a piece this short — this one is one continuous gesture
- **camera MOVES, which is the opposite of the nearest playbook: a handheld walk-up and a tilt from billboard down to hand, generated into the clips rather than added at the edit** — the style read says 'handheld vertical video' and the one-line describes the billboard being above and the hand below, i.e. a vertical traverse. The nearest playbook locks every camera off to hide 480p softness; here the shake IS the style, so the move must be in the clip
- **clips at 480p, one take of every clip (another only if it fails, three at most), the pick upscaled locally (2026-10-21, VIDEO-RULINGS V5/V6 — was 720p for the billboard and the hand-off beats)** — the nearest playbook's 480p-plus-upscale works because its camera is static and its look is animated; a moving handheld street plate with a corner-pinned screen inside it shows upscale mush on the billboard edges, which is where the illusion lives
- **NO captions, NO headline, NO on-screen type, and no brand word except whatever is legibly on the product or on the billboard itself — and any billboard copy is composed as a type layer over a blank screen plate** — the sound form is MUSIC ONLY with 0 on-screen text and 0 speakers in the signature, and no caption band is recorded anywhere in the swipe; the nearest playbook's four type layers (phone bubbles, clock face, on-pack name, brand) all come from content this swipe does not have. Type-as-layer still holds for the one place words can appear
- **music is a single short bed chosen for the gag's timing — one hit on the screen coming alive, one on the hand-off — no loop sections, no lyric, no foley pass as its own station (SFX is 3–4 cues, placed at the edit)** — SOUND FORM is MUSIC ONLY at 9 s; the nearest playbook's foley station exists because it measured 13 cues across 26 s with effects doing the work of dialogue. At 9 s with no physical routine there are only the two beats worth hitting, so a whole station is overhead
- **cast is a SCREEN PERSON only — one banked face that lives inside billboards across ads, plus a hand double for the reveal; no full-body character, no wardrobe states, no continuity checklist** — speakers: 0, on_screen: 0 in the signature and the only person described is 'a woman on a massive CGI billboard'; there is no character moving through rooms, so the nearest playbook's three declared hair/makeup/wardrobe states have nothing to track
- **the hooks are re-times and re-frames of the SAME walk-up, plus one alternate that opens mid-reach; no alternate opener is generated** — at 9 s the reveal is at roughly the halfway mark, so a hook lifted from the middle spoils the gag — the same logic the nearest playbook applies at 26 s, tighter
- **the street plate and the billboard geometry BANK as reusable assets: one corner, one tracked rectangle, reused for every product and every brand, with only the screen content and the hand re-generated per ad** — the format's entire cost is in the plate; once one street plate with a clean tracked billboard exists, each further ad in this family is a screen clip plus a hand clip. This is the cheapest repeatable shape in the whole library and the reason to make it its own family

## Stage order

teardown (style read + structural signature + where the billboard sits in frame) → beat sheet (5 beats in ~9 s: walk-up · screen alive · reach · hand-off · hold) → elements (street plate, billboard rectangle + geometry, the screen person, the real product, the hand) → plate (the handheld street clip with a blank billboard — generated or banked) → screen content (the billboard clip, made at the billboard's own aspect, higher tier) → hand-off pair (the screen hand releasing + the real hand receiving, designed to meet) → composite (corner-pin the screen into the plate, edge occlusion, screen glow spill) → upscale → music bed + 3-4 SFX cues → type layer (only if the billboard carries words) → edit (control + hook re-times) → copywriter (from the beat sheet)

## Stage settings

**audio**
- first: none
- song_model: the shared chain's own
- voice_model: the shared chain's own
- nobody_talks: on
- note: audio does NOT drive the cut — the gag's timing does. One short music bed and 3-4 SFX cues are laid under a cut that already exists. No voice at any point.

**song**
- length_s: 12
- punch_first: the shared chain's own
- sections: the shared chain's own
- flow: the shared chain's own
- brand_line: never sung and never spoken — the brand arrives only on the real product in the hand
- master_true_peak_dbtp: -1.0
- loudness_lufs: -14
- beats_per_line_by_style: the shared chain's own
- sound: no song. One short bed from the music bank with a clear accent available at ~0:03-0:04 (the screen coming alive) and ~0:07 (the hand-off); made once if no bank row fits. City ambience under it at a low level.
- music_level: laid over the whole piece at a steady level; the two accents sit above the bed, the SFX cues above that

**pictures**
- door: direct.openai
- model_key: the shared chain's own
- quality: high
- size: 864x1536
- aspect: 9:16
- made_at: 9:16 at 864x1536 for the plate and the hand; the SCREEN content is made at the billboard's own aspect (landscape or portrait as the plate's rectangle demands), not 9:16
- fix_calls: off
- style_lock: phone-ugc — handheld vertical, natural daylight, no grade, no retouch, slight phone-lens distortion and soft highlights; the screen layer is the exception and is lit as an emissive LED panel
- send_size: the shared chain's own
- start_only: on
- max_references: 3
- product: the REAL product — a real packshot or real archive clip pasted/held in the hand; never generated, never restyled. Only the billboard's digital version of the product may be synthetic, and it is made image-to-image from the same real photo so the two match
- plates: the street plate is made with the billboard BLANK (flat mid-grey or black panel, clean corners, no content, no words) so the screen can be pinned in
- count_target: 4-6 pictures for the whole ad: 1-2 street plate frames (walk-up, billboard framed), 1 screen-content start frame at billboard aspect, 1 hand-receiving frame, 1 real-product hold; plus the banked plate reused on every later ad in this family
- blocks: picture per LAYER, not per shot — the plate is one picture carrying the walk-up and the tilt, the screen is one picture, the hand is one picture

**clips**
- model: seedance_2_5
- endpoint: image-to-video
- resolution: 720p
- seconds: 4, 4
- clips_per_picture: 2, 3
- takes: 1
- audio: silent
- upscale: local Real-ESRGAN x2 to 1080x1920, crf 15 — plate only; the composited screen is not upscaled after the pin
- stills_allowed: off
- short_clip: generate at 2-4 s and trim at the edit; the hand-off pair is generated at the model's floor so the join frame is exact
- send_size: 720x1280 for the plate and hand; the screen clip is sent at its own billboard aspect
- send_format: jpeg q90
- prompt_order: camera move + style lock FIRST (handheld, phone, natural light), then the action; the screen clip prompts the opposite — locked frame, LED panel, the person's move only
- refused_every_try: use the banked street plate and re-pin a new screen clip; the plate is never the blocker twice
- camera: the PLATE moves — handheld walk-up with real wobble, then a tilt down from billboard to hand, generated into the clip. The SCREEN clip is locked off with motion only inside the panel. Three takes of the plate, as of every clip, because handheld plus a flat tracked surface is where the model drifts
- long_tail: one clip at ~3 s for the final hold on the real product in the hand
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least

**cast**
- reuse: one banked SCREEN PERSON (a face that lives inside billboards) reused across every ad in this family, and one banked street plate with its tracked billboard reused across every brand; the hand is a banked hand reference
- recurring: on
- second_person: none — the passer-by holding the product is a hand only, never a face, never a body
- continuity: no wardrobe states to track. Two things must hold instead: the screen person's look is identical across every ad using the banked plate, and the hand at the reveal matches the hand that appeared on screen (same skin tone, same size in frame, same light direction)
- voice: none — nobody speaks and nobody makes a sound
- product: LIVE-ACTION RULE, the inverse of the animated families: the product in the real hand is the actual object from a real photo or real clip. The billboard's version is generated image-to-image from that same photo so shape, colour and label match exactly across the hand-off

**hooks**
- shape: the walk-up IS the hook (0:00-0:03, the billboard arriving in frame). Alternates are re-times and re-frames of that same move — faster approach, tighter crop on the panel, opening already mid-reach — never a clip lifted from after the hand-off
- count: 3
- generated: off

**captions**
- look: none. No captions, no headline, no lower-third, nothing in the caption band — the swipe carries zero on-screen text and there is nothing spoken to caption. The only words allowed are on the real product's own label and, optionally, on the billboard — and billboard copy is composed as a type layer over the blank screen plate, corner-pinned with it, never generated.

**gates**
- apply: style lock (plate reads phone-ugc; screen reads as an emissive panel), clip words check (no words generated into any picture, including on the billboard), type-as-layer check (any billboard copy is a composed layer), billboard geometry check (perspective, corners and edge occlusion hold through the camera move), hand-off match check (frame position, hand size, light direction and product match across the join), product true to the real photo (shape, colour, label) and REAL at the reveal, loudness / true peak
- skip: song line gate, song flow gate, voice per speaker, lip-sync / line parity on clips (nobody talks), talking-scene audio slice, protected words / spoken numbers (nothing is spoken), caption band placement (no captions), foley coverage (3-4 cues, not a planned track), wardrobe / hair continuity states (no full-body character)

**edit**
- method: composite first, cut second: corner-pin the screen clip into the plate's billboard rectangle, add edge occlusion and a little screen-glow spill onto the street, then cut the 5 beats on the gag's own timing (~9 s, 3-5 cuts)
- reuse: the banked street plate is the reuse — every further ad in this family re-pins a new screen clip and a new hand into the same plate rather than generating a street
- camera_moves: generated into the plate, not added here; the only move added at the edit is a small push on the final product hold
- end_card: the real product held still in the hand for the last ~2 s; a real packshot push is allowed as an alternate ending
- garbled_background_text: blur at the edit (gblur sigma 22), never a punch past it (VIDEO-RULINGS V15) — a real street plate will carry third-party signage and it must not be readable
- loudness: -14 LUFS, true peak <= -1 dBTP; bed steady, two accents and the SFX cues above it
- versions: control + 3 walk-up re-times
- trim: clips are generated at 2-4 s and trimmed to their beat length here; the hand-off is trimmed to the exact join frame

**copy**
- source: the beat sheet (5 beats, wordless) — there are no lyrics, no script and no captions
- why: with nothing spoken and nothing on screen, the copywriter has only the gag to work from and will drift to the brand files unless the beats are named as the source

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $3
- why: 9 s, one street, one layer pair: 4-6 pictures at high on the house model, three versions each, 6-9 clips at 480p mostly 2-4 s, one take each, the pick upscaled locally (2026-10-21; was medium/fast and 720p), music one bank row, 3-4 SFX from the bank, hooks re-timed at $0 — and from the second ad on, the street plate and billboard geometry are banked, so only the screen clip and the hand are new

## Quality bar — not slop

- the billboard reads as a real structure on a real street: the panel's corners stay pinned to it through the whole camera move, with no sliding, swimming or floating
- the screen content is perspective-correct in every frame and occluded correctly by the billboard's frame, poles, wires or passing objects
- light from the screen spills onto the street in the frames where the screen is bright — the composite sits in the scene, not on top of it
- the plate reads as phone footage: handheld wobble, natural daylight, no grade, no retouch, phone-lens softness
- the hand-off is seamless — same hand, same skin tone, same position in frame, same light direction, same product, with no visible cut-point mismatch
- the product at the reveal is unmistakably the real object, matching the real photo exactly in shape, colour and label
- the billboard's digital product and the real product are the same object, same size, same label
- no readable third-party brand or signage anywhere in frame
- no generated words anywhere — any billboard copy is clean, correctly spelt composed type
- every shot moves, including the final product hold
- no voice, no caption, no headline, no lip movement implying speech anywhere in the piece
- the whole piece lands in 8-12 s with the reveal legible without a single word
- the two music accents land on the screen coming alive and on the hand-off
- master <= -1 dBTP at -14 LUFS

## Variants (same workflow, refined)

### bts reveal (`bts-reveal`, draft)
- from: runs/video-teardown/_work/04-dd19bxxyjln-<brand>
- matched at score 1.0

### pause challenge (`pause-challenge`, draft)
- from: runs/video-teardown/_work/dd6u-pause-dunk
- matched at score 1.0


## Built from

- runs/video-teardown/_work/07-dcq9klkk7ml
