# Playbook · Doll short movie (wordless animated story) (`short-movie`)

**Status:** draft · **state:** drafted-by-builder
**Family:** short-movie · nearest when drafted: `song-ad`

A 26–35 s wordless 3D-animated story about one character moving through a few rooms of one home, driven by sound effects and a lo-fi music bed, where the other person exists only as phone text on screen and the product is used in close-up as part of the routine.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

## Structural signature

| | |
|---|---|
| audio | none |
| speakers | 1 |
| address | none |
| settings | 4 |
| product_role | demo |
| pacing | fast |
| capture | animated |
| story | narrative |

## What is specialised, and why

- **no song and no voice — the audio is a flat music loop plus a foley track of sharp one-hit effects, and the cut is built from the STORY's beats, not from an audio clock** — the records measure music under 83% of the runtime as a flat loop (117.5 bpm, C major, laid-over, loud, 'none — steady' builds and drops) and only 5 non-verbal utterances in the transcript; there is no sung or spoken line for a clip to sit under, so the sung-story playbook's 'song first, cut follows the song' station has nothing to drive it
- **the music is picked from the bank (or made once) as a 115–120 bpm lo-fi loop at a fixed level, no sections, no bridge, no outro tag — the brand line is never heard, only shown** — measured 'flat-loop · laid-over · loud', voice-over-music 0.3 dB, 'ends quietly'; the swipe has no sung brand line at all — the brand arrives as on-screen text (the brand name at 0:22 and 0:25), so the song playbook's bridge/outro-tag rule has no place to land
- **a FOLEY PASS is its own station after the clips: one bank hit per physical action, placed on the frame it happens (notification chime, popcorn scatter, fast ticking, pop, rubbing, brushing, fabric rustle, zip, fabric thud, wiping, wet slap, low rumble)** — the sound sheet lists 13 cues across 26 s — roughly one every 2 s — and the mechanics say 'fast cuts and ASMR sounds keep pace high'; the effects ARE the dialogue in this shape, so they are planned like lines rather than sweetened at the end
- **non-verbal character vocals (laugh, hmm, gasp, oof) are made as 4 one-shot takes on the voice door, not a read — no script, no line parity** — transcript T2–T5 are isolated reactions at 0:03.1, 0:11.0, 0:19.0, 0:20.0 and the voice card measures ~62 words/min 'consisting entirely of isolated reactions'; a stitched read would invent speech the swipe does not have
- **the second person is a TEXT MESSAGE on a phone screen — never cast, never rendered, never voiced; two screen scenes only** — the roll sheet has exactly two S rows ('BOYFRIEND / I'll arrive in 1 hour.' at 0:02 and 'Sorry, I won't be able to come.' at 0:18) and the doctrine read says the other person is 'seen only as text messages'; this saves a whole second character's element sheet
- **a VANITY MIRROR set is the workhorse: one plain grey mirror-reflection background carries the whole product sequence (0:05–0:14), 6+ clips off 1–2 pictures** — the frame map shows K04–K11 as eight consecutive eye-level close-ups, static camera, same bright even neutral light, same grey background; one set-up re-shot eight times is the cheapest possible block and it is what the swipe actually does
- **the clock is a repeating MOTIF insert, generated ONCE and reused with a different speed/push-in each time it returns** — the same prop returns at 0:04, 0:14 and 0:16 with the same on-screen text ('12 / QUARTZ') and the same 'fast ticking' cue; two B-silent rows plus one in-shot appearance is one picture, not three
- **clips run 0.7–2.4 s (median ~1.0 s), so the clip floor is the model's minimum and the edit trims in — not 3–4 s clips** — 18 shots in 26.98 s with 17 cuts; the frame map's own durations are 0.333–2.4 s except the 5.75 s final hold; a 3 s clip would be longer than almost every shot in the piece
- **the last shot is the one long one — ~5.7 s on the mask, resolving, then the brand text** — frame map K18 is 5.747 s against a 1.0 s median, and the mechanics call the end 'slower at the start and end to emphasize relaxation'; the pacing rule is fast-middle, slow-ends, not uniformly fast
- **every camera is locked off — 'set down still' — with motion only inside the frame; the only camera moves in the whole piece are two fast push-ins and one fast pan** — the frame map records 'held: set down still' on all 18 shots and 'move: none' on 14 of them; this both matches the swipe and makes the clips cheap, because a static camera on an animated set hides 360p softness
- **the product is rendered in the film's 3D style from the real product photo and HELD in close-up as the demo — label legible, used on skin, four separate product moments (dropper, jar, tube, mask)** — the prop list names four distinct product items with on-pack text, and product_role is demo, not insert; the sung-story playbook's 'product arrives late as an insert' does not hold here — the product IS the middle of the film
- **on-pack and on-screen type is composed as a LAYER over a clean plate, never generated into the picture** — the swipe carries readable text in six shots (the product names at 0:05 and 0:08, '12 / QUARTZ' twice, the two text messages, the brand name twice); generated label text is the single most reliable source of slop and the nearest playbook already records 'product label misspelt' and 'garbled background signs' as real failures
- **pictures at medium quality, fast tier, 9:16 at 864x1536 — same as the nearest playbook — but ~10–14 pictures for the whole ad because of set reuse** — four settings, one character, one costume change, a static camera, and an eight-shot block on one mirror set-up; the sung-story playbook's ~20 pictures assumes six settings and a 2:45 runtime against this 26 s
- **no hook versions cut from the body — the opener IS the hook and the alternates are 2 s re-times of the same popcorn-drop beat** — the roll sheet marks 0:00 A as 'opener: true' and the mechanics name the text arriving as 'the inciting incident' that 'breaks if cut'; the whole piece is 26 s, so a 3 s hook lifted from the middle would spoil its own ending
- **wardrobe and hair are a continuity CHECKLIST, not a free choice per shot — three states, and every clip declares which it is in** — the cast card times the changes precisely: messy high bun 0:00–0:13 then long straight hair 0:14–0:26; bare face, then berry lip + heavy blush 0:12–0:20, then bare again 0:21–0:26; the t-shirt look, the dressed look, then the t-shirt look again — a wrong state is the obvious tell in a getting-ready story

## Stage order

teardown (style read + structural signature) → story beats (the wordless story, shot by shot — no lyrics, no script) → elements (one character in three states, four sets, the product in style, the clock motif) → storyboard (from the beat sheet's own clock, 17 cuts) → pictures (set-blocks, not one per shot) → clips → upscale → foley pass (one bank hit per action) + non-verbal takes + music loop → type layer (product labels, text messages, clock face, brand) → edit (control + opener re-times) → copywriter (from the beat sheet)

## Stage settings

**audio**
- first: none
- song_model: the shared chain's own
- voice_model: the voice door, one-shot non-verbals only (4 takes: laugh, hmm, gasp, oof)
- nobody_talks: on
- note: audio does NOT drive the cut in this format — the story's beats do. The music loop, the foley hits and the non-verbal takes are all laid under a cut that already exists.

**song**
- length_s: the shared chain's own
- punch_first: the shared chain's own
- sections: the shared chain's own
- flow: the shared chain's own
- brand_line: never sung — the brand is shown as type on the last two shots
- master_true_peak_dbtp: -1.0
- loudness_lufs: -14
- beats_per_line_by_style: the shared chain's own
- sound: no song. One flat lo-fi loop, 115–120 bpm, warm synth + bass + drum machine, medium energy, no builds, no drops, ending quietly — from the music bank where a row fits; made once if none does.
- music_level: laid over the whole piece, loud (the swipe's measured mix: music does not duck, voice-over-music 0.3 dB)

**pictures**
- door: direct.openai
- model_key: model_fast
- quality: medium
- size: 864x1536
- aspect: 9:16
- made_at: 9:16 directly at 864x1536; the clip is 360p so a bigger picture is thrown away
- fix_calls: off
- style_lock: 3D stylised realism — rounded forms, soft matte skin, exaggerated expression, visible pores and freckles, warm interior light; locked from the swipe's style read, formula first
- send_size: the shared chain's own
- start_only: on
- max_references: 3
- product: image-to-image from the real product photo, restyled into the film's 3D look; shape, colour and label exact, then the label composed as type at the edit
- plates: every shot carrying words (product in hand, phone screen, clock face, brand end) is made as a TEXT-FREE plate
- count_target: 10–14 pictures for the whole ad: 2 living room (sofa wide, sofa close), 1–2 vanity mirror (carries 6+ clips), 1 bedroom/closet, 1 entryway, 1 clock, 1 phone plate, 2–3 product closes, 1 end
- blocks: picture per SET-UP, not per shot — the eight consecutive vanity close-ups come off one or two pictures

**clips**
- model: gemini_omni_flash_1_1
- endpoint: image-to-video
- resolution: 360p
- seconds: 1, 2
- clips_per_picture: 3, 6
- takes: 1
- audio: silent
- upscale: local Real-ESRGAN realesr-animevideov3 x3 to 1080x1920, crf 15
- stills_allowed: off
- short_clip: the model's floor is longer than most shots here — generate at the floor and TRIM IN at the edit; never hold a frame
- send_size: 432x768
- send_format: jpeg q90, centre-cropped to 9:16
- prompt_order: action line + style lock FIRST, then motion; nothing else
- refused_every_try: use the neighbour clip with a 7% punch-in
- camera: locked off on every clip ('set down still') — motion inside the frame only; the two fast push-ins (clock zoom, 0:04) and one fast pan (0:03) are the only camera moves and are done at the edit, not generated
- long_tail: one clip at ~5–6 s for the final mask beat

**cast**
- reuse: one banked 3D character in this style carries the whole ad and every ad after it; the sets (living room, vanity, closet, entryway) bank as one apartment reused across stories
- recurring: on
- second_person: NEVER cast — the other person is text on a phone screen only
- continuity: three declared states, every clip tagged with one: (A) messy high bun · bare face · oversized grey tee + black shorts + white socks; (B) hair down straight · berry lip + heavy blush · adds olive trench, black boots, crossbody bag; (C) hair down · bare face · back to the tee and shorts
- voice: no speaking voice — one non-verbal set (laugh, hmm, gasp, oof) banked with the character and reused
- product: ANIMATED STYLE RULE: the product is rendered IN THE FILM'S STYLE, image-to-image from the real product photo (shape, colour and label kept exact), held and used by the banked character; only the end card may be the real packshot. Real archive footage and studio renders in the body are refused for an animated style.

**hooks**
- shape: the opener IS the hook — the relaxed beat, the phone lighting up, the popcorn flying (0:00–0:03). Alternates are re-times of that same beat (speed, hold on the shock frame, which frame the chime lands on), not clips lifted from the middle
- count: 3
- generated: off

**captions**
- look: no captions and no spoken lines to caption. Four type layers instead, each composed over a clean plate: the phone text bubbles in the platform's own message look (sender name above), the product name on-pack, the clock face, and the brand word on the last two shots. Optional silent-viewer headline at 16% from the top on the control.

**gates**
- apply: style lock (every element and frame in the 3D style row), clip words check (no words generated into any picture), type-as-layer check (every readable word on screen is a composed layer), continuity check (hair / makeup / wardrobe state declared and correct per clip), product true to the real photo (shape, colour, label) and in the film's style, foley coverage (every physical action in the beat sheet has a cue placed on its frame), loudness / true peak
- skip: song line gate, song flow gate, voice per speaker, lip-sync / line parity on clips (nobody talks), talking-scene audio slice, protected words / spoken numbers (nothing is spoken)

**edit**
- method: video-edit machine cut on the beat sheet's own clock — 17 cuts in ~27 s, fast through the middle, slow at both ends
- reuse: the clock motif and the sofa set-up return with a different speed or a 7% punch-in rather than a new generation
- camera_moves: the two fast push-ins and the one fast pan are done here from a static clip
- end_card: the brand word over the final mask beat; a real packshot push is allowed as an alternate ending
- garbled_background_text: blur at the edit (gblur sigma 22) or punch in past it
- loudness: -14 LUFS, true peak ≤ -1 dBTP; music laid over at the swipe's measured balance, foley hits above the bed
- versions: control + 3 opener re-times
- trim: clips are generated at the model's floor and trimmed to their 0.7–2.4 s shot length here

**copy**
- source: the beat sheet (the wordless story, shot by shot) — there are no lyrics and no script
- why: with nothing spoken, the copywriter has no lines to work from and will drift to the brand files unless the story beats are named as the source

## Known failures → fixes

- **a clip blocked: no approved start picture** → every clip's start picture approved before the clip run  _(from a past run)_; stage clips)_
- **2 clips carried words that are not words** → type is a layer over a clean plate, never generated; the clip words check holds them  _(from a past run)_; stage clips)_
- **the packshot stayed outside the frame zone after one fix** → packshot framed at 9:16 in the first prompt  _(from a past run)_; stage pictures)_
- **mouths moved with no voice — the 'talking, no voice' check held a wordless render** → eye review of mouths (mouths_reviewed); in this family that check is a review, not a stop  _(from a past run)_; stage edit)_
- **the edit tool crashed: amix with 0 inputs; KeyError 'clip' in thumbs** → no-voice edits pass an empty voice list explicitly; thumbnails from the cut, not clip ids  _(from a past run)_; stage edit)_

## Cost

- target per ad: $__
- why: 26 s, one character, one apartment: ~10–14 pictures at medium/fast 9:16 (~$__), ~20 clips at 360p mostly 1–2 s (~$__), music one bank row or one make, foley from the bank, 4 non-verbal takes, hooks re-timed from the opener at $0 — a fifth of a 2:45 song ad's runtime at the same per-second settings, with the vanity block collapsing eight shots onto one picture
- measured: $__ (34 pictures $__ at xhigh, 12 Omni 720p 3 s clips $__; ledger.json) against a $__ budget

## Quality bar — not slop

- it is the same person in all 18 shots — face, proportions and skin read identically across the eight-shot vanity block
- hair, makeup and wardrobe are in the right state for every shot (bun/bare → down/made-up/dressed → down/bare/tee)
- every readable word on screen is clean and correctly spelt: both phone messages, both product names, the clock face, the brand
- the product matches the real photo exactly in shape, colour and label, and is in the film's 3D style — no real footage in the body
- hands hold and use the product plausibly in every close-up — no extra fingers, no product melting into the palm
- the four rooms read as one apartment: consistent wall colour, floor, blinds and light temperature
- every shot moves — no still, no frozen frame, no held last frame, including the long final beat
- no camera drift on a shot the format locks off; the only moves are the two push-ins and the one pan
- the cut is fast in the middle (shots around a second) and settles at both ends — the panic is legible without a word
- a sound lands on every physical action, on its frame: the chime, the popcorn, the ticking, the pops, the rustle, the thud, the wipe, the slap
- no voice, no spoken line, no lip movement that implies speech anywhere in the piece
- the music is one flat warm loop at a steady level across the whole ad — no build, no drop, no duck
- no second person is ever seen or heard; the other party exists only as text
- no readable garbage text and no real third-party brand anywhere in frame
- master ≤ -1 dBTP at -14 LUFS

## Variants (same workflow, refined)

### micro drama (`micro-drama`, draft)
micro-drama · 0:00.0–0:24.5 · Two characters in one continuous set (the Airport Customs Desk) run a confrontation (passport scrutiny, 0:00.0–0:05.5) and a turn (peel and gasp, 0:17.0–0:20.5). The offer beat is absent; the asset closes on a 
- differs: speakers: 0; settings: 1
- from: runs/video-teardown/<brand>/<run>
- matched at score 0.897


## Built from

- runs/video-teardown/<brand>/<run>
- runs/video-production/<brand>/<run>
- runs/video-edit/<brand>/<run>
- runs/video-production/<brand>/<run>

## Rulings behind it

- the owner (autopilot rulings, 2026-10-07/10): "The variations are the look, not the hook." — one locked brief, made in korean-doll / thai-puppet / plush-mascot
- the owner: "A wordless opening is fine."
- the owner 2026-10-09: the reveal is instant
- the owner 2026-10-10: "you shouldn't be using real b-roll for this" — animated formats render the product in the film's style from the real photo; only the end card is real
- the owner 2026-10-10: the doll short movie is its own family
