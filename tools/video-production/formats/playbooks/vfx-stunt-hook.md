# Playbook · Fake stunt opener, then unboxing (`vfx-stunt-hook`)

**Status:** draft · **state:** drafted-by-builder
**Family:** vfx-stunt-hook · nearest when drafted: `song-ad`

A short phone-shot ad that opens on one impossible, obviously-faked moment composited into real handheld footage to stop the scroll, then cuts straight to a real person unboxing and wearing the product under a song, with nobody talking.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

## Structural signature

| | |
|---|---|
| audio | song |
| speakers | 0 |
| address | none |
| settings | 1 |
| product_role | none |
| pacing | medium |
| capture | studio |
| story | narrative |

## What is specialised, and why

- **the ad is two blocks, not a story arc: a 3–5 s impossible stunt, then a ~12 s real unboxing-and-wear block; the cut between them is the whole idea** — the triage reads the swipe as "opens with a fake, impossible CGI moment … then cuts to a standard product unboxing and try-on" — the nearest playbook's single narrative sung story has no such hard break
- **the song is picked, not written — an existing bank track trimmed to 17 s; no lyric writing, no section fit, no flow gate** — the swipe is 00:17 with SOUND FORM: SUNG and 0 speakers, and the frame map records no sung story beats; the nearest playbook's 150–195 s lyric-driven cut cannot drive a 17 s ad, so the song stops being the script
- **the cut is NOT derived from the song's timing; it is derived from the stunt beat — the reveal lands on the first downbeat after the stunt** — with no lyrics there is nothing for a clip to "sit under"; the only timing contract left is stunt → cut → product
- **the body is real-looking handheld live action, not an animated film: product, hands and garment are real pixels wherever they are in frame** — STYLE phone-ugc — "unretouched real-world environment, meant to look like a casual phone recording"; the nearest playbook's animated-style product render is an animated-format rule and does not apply here, so the general product-never-drawn route (real archive/packshot footage) governs instead
- **the stunt shot is built as a composite: one plate clip of the real location plus the impossible object placed into it — never one generated shot of the whole impossible event** — the AI assessment reads the swipe as "traditional 3D VFX compositing … not generative AI. LIKELY HUMAN" — a wholly generated impossible shot is exactly the AI tell this format must avoid
- **the impossible object is allowed to look impossible, but the physics around it must be sober: real camera shake, real shadow direction, real ground contact** — the swipe's stunt reads as a fake someone filmed, which is why it stops the scroll; a floating, shadowless object reads as slop instead of a prank
- **one setting only, reused across every ad in this family — the same plate location and the same unboxing surface** — signature settings: 1; the nearest playbook budgets 6 settings and banks sets across stories, so here the saving is larger: one plate clip serves the whole family
- **the product is never held up to camera, named on screen or priced; it arrives as the thing being opened and worn** — signature product_role: none and address: none — nobody speaks to camera and there is no pitch in the 17 s
- **pacing medium: 5–8 shots total, 2–4 s each, no fast montage** — frame map cuts read 0 and the triage calls the second half "standard"; a rapid-fire cut would read as a different format and break the casual-phone look
- **hooks are not cut from the body — the stunt IS the hook, so hook versions are alternative stunts over the same unboxing block** — the nearest playbook cuts 3 s hooks out of existing story clips; here the opening is the only scroll-stopping footage, so varying the ad means varying the stunt
- **clips at 480p, 4 s, one take of every clip (another only if it fails, three at most), the pick upscaled locally (2026-10-21, VIDEO-RULINGS V5/V6 — was 720p, 2 takes on the stunt shot only)** — a 17 s ad is ~6 clips, so even at a higher resolution the clip spend is a fraction of a 2:45 song ad; the stunt is the one shot where a bad take kills the ad, and real-looking footage at 480p reads as a compression artefact rather than a phone video
- **pictures at high quality on the house picture model (2026-10-21, V17 — was medium), 9:16, 864x1536, no framing-fix calls — and only ~4 start pictures for the whole ad** — same cost ruling as the nearest playbook, but with one setting and 5–8 shots the picture count drops from ~20 to ~4

## Stage order

teardown (style + stunt read) → audio (pick and trim a bank track) → ad-script (stunt beat + unboxing beats, no dialogue) → elements (plate location, one person, the real product photos) → storyboard (stunt → cut → unbox → wear → end card) → pictures → clips → composite (place the impossible object into the plate) → edit (control + stunt-swap versions) → copywriter (from AD-SCRIPT.md)

## Stage settings

**audio**
- first: song
- song_model: the shared chain's own
- voice_model: the shared chain's own
- nobody_talks: on
- source: an existing bank track trimmed to the runtime — no song is written for a 17 s ad
- note: no voiceover, no on-screen speaker; natural handheld sound may sit under the song at low level to keep the phone-recording read

**song**
- length_s: 15, 20
- punch_first: the track enters on the stunt, loud, from its own hook — never from an intro bar
- sections: the shared chain's own
- flow: the shared chain's own
- brand_line: the shared chain's own
- master_true_peak_dbtp: -1.0
- loudness_lufs: -14
- beats_per_line_by_style: the shared chain's own
- sound: one continuous bank track across both blocks — the song is the only thing that holds the stunt and the unboxing together
- written: off

**pictures**
- door: direct.openai
- model_key: the shared chain's own
- quality: high
- size: 864x1536
- aspect: 9:16
- made_at: 9:16 directly at 864x1536
- fix_calls: off
- style_lock: the swipe's style row (phone-ugc): handheld framing, overcast natural light, unretouched, no studio polish, no colour grade
- send_size: the shared chain's own
- start_only: on
- max_references: 3
- count: ~4 start pictures: the plate location, the unboxing surface, the person wearing it, the end card
- product: from the real product photos — never drawn from words, never restyled; this is a real-footage format

**clips**
- model: seedance_2_5
- endpoint: image-to-video
- resolution: 720p
- seconds: 4, 4
- clips_per_picture: 2, 3
- takes: 1
- audio: silent
- upscale: local Real-ESRGAN to 1080x1920, crf 15 — the photoreal model, not the anime one
- stills_allowed: off
- short_clip: slow to no less than 0.75x, then ping-pong — never hold a frame
- send_size: 432x768
- send_format: jpeg q90, centre-cropped to 9:16
- prompt_order: action line + phone-ugc style lock FIRST, then motion; handheld drift named explicitly
- refused_every_try: the same prompt and references to the backup door (VIDEO-RULINGS V21); never the neighbour clip punched in (VIDEO-RULINGS V15)
- plate_rule: the stunt's background plate is generated or shot as an ordinary location clip; the impossible object is added after, at composite
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least

**cast**
- reuse: one banked person and one banked location across the whole family — same hands, same street, same table
- recurring: on
- product: REAL-FOOTAGE RULE: the product in the box, in the hands and on the body comes from real archive clips and the real packshot; nothing about the product is drawn or restyled. The only invented object in the ad is the impossible stunt prop, which is never the product.

**hooks**
- shape: ~4 s impossible stunt in the plate location, cutting on a downbeat into the unboxing block
- count: 4
- generated: on
- why_generated: the stunt is the hook and each version needs a different impossible moment; there is no story footage to cut one out of

**captions**
- look: almost none — this format reads as a real phone clip, so at most one short line in the swipe's caption look over the stunt, plus the restock/offer line on the end card; captions in the bottom band, headlines in the top band, never mid-frame, never on a face

**gates**
- apply: style lock (phone-ugc on every picture and clip), clip words check (no words on the picture), product from real photos, label and shape exact, composite sanity (shadow, ground contact, camera shake match), stunt-to-reveal cut lands on a downbeat, runtime gate (16–20 s), loudness/true peak
- skip: song line gate, song flow gate, voice per speaker, lip-sync / line parity on clips (nobody talks), talking-scene audio slice, animated-style product render check

**edit**
- method: video-edit machine cut on the stunt beat, not on a lyric clock
- reuse: the unboxing block is identical across versions; only the opening stunt changes
- end_card: camera move on the real packshot / the garment worn, with the offer line
- garbled_background_text: blur at the edit (gblur sigma 22), never a punch-in past it (VIDEO-RULINGS V15)
- loudness: -14 LUFS, true peak ≤ -1 dBTP
- versions: control + 4 stunt-swap versions
- composite_note: the impossible object is comped onto the plate at the edit so the plate clip can be reused for every stunt version

**copy**
- source: AD-SCRIPT.md
- why: the copywriter drifts to the brand files otherwise; here the script is the stunt beat and the restock claim, nothing more

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $5
- why: ~4 pictures at high 9:16 (three versions each) and ~6 clips of 3–4 s at 480p (one take each, another only if it fails; 2026-10-26) against a 17 s runtime, with the plate, the person and the unboxing surface reused across the family — a fraction of a 2:45 song ad; stunt-swap versions re-comp the same plate, so each extra version is near free

## Quality bar — not slop

- the first second shows the impossible thing — no establishing shot, no logo, no build-up
- the impossible object sits in the world: shadow on the right side, contact with the ground, moving with the camera
- the whole ad looks like one person's phone: handheld drift in every shot, natural light, no grade, no studio polish
- the cut from stunt to unboxing lands on a beat and reads as deliberate
- the product in frame matches the real product exactly — shape, colour, label, and the same object every time it appears
- nobody speaks and nobody addresses camera
- every shot moves: no still, no frozen frame, no held last frame
- no readable garbage text, no real third-party brand or logo anywhere in frame
- no merged faces, no extra limbs, no warped hands on the unboxing shots
- under 20 seconds
- master ≤ -1 dBTP at -14 LUFS, the track entering on the stunt
- a viewer who watched it twice would say "someone filmed that and faked the box", not "that was made by AI"

## Variants (same workflow, refined)

### problem solution dance (`problem-solution-dance`, draft)
- from: runs/video-teardown/_work/fmt-kbeauty-code-da5j02xmfhn
- matched at score 1.0

### symptom checker (`symptom-checker`, draft)
- from: runs/video-teardown/_work/fmt-tcmtea-ddq66wcqygs
- matched at score 1.0


## Built from

- runs/video-teardown/_work/05-ddubgr0kev7
