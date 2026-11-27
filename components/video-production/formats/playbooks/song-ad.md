# Playbook · Song ad (sung story, animated) (`song-ad`)

**Status:** approved · **state:** workflow rebuilt 2026-11-27 on the Higgsfield Singing Ads path of brief 0376
**Family:** sung-story

**Signed:** the owner 2026-10-10 — his rulings of 2026-10-09/10 cover every line (cited per line under rulings): punch first + shorter + flow (SONG-WRITING.md); match the swipe's style; nobody talks, all clips, no stills, Seedance 480p one take + local upscale; product never drawn; cost down "even more".

A dramatic first-person story told as a real song (2:30–3:15). The song is made first and the whole cut follows it: every sung line is a silent clip in the swipe's animated style, nobody talks on screen, the product arrives late, rendered in the film's style from the real product photo, and only the end card is the real packshot.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

> Which model does what: `../../../generative-model-house/MODEL-HOUSE.md` (the only rule, 2026-10-20). The clip model below is today's default; per-format model choices are ruled there.

> How every AI clip moves: `../../../motion/` (the only route, 2026-11-12). Before any paid take, the clip's movement goes through the motion chain: real footage of the same action found, tracked, read as body mechanics, rehearsed in 3D by the real skeletons with the real camera, then passed or held by the chain's own checks (nobody approves it); the finished take is then checked against the reference beat by beat. No format skips it.

## Structural signature

| | |
|---|---|
| audio | song |
| speakers | 0 |
| address | none |
| settings | 6 |
| product_role | insert |
| pacing | fast |
| capture | animated |
| story | narrative |

## What is specialised, and why

- **the song is made and passed before any picture** — the cut is derived from the song's timing; SONG-WRITING.md (the owner 2026-10-10)
- **song flow: gaps up to 3.5 s, dead air up to 10%, 6 beats a rapped line / 8 a ballad line** — the owner 2026-10-10: the first tight pass sounded rushed — "it needs to actually sound like a song, just efficient"
- **the product is rendered in the film's style from the real product photo, held by the cast; only the end card is the real packshot** — the owner 2026-10-10: "you shouldn't be using real b-roll for this" — in an animated ad real footage breaks the film. This OVERRIDES the general 'product is never drawn → real footage' route for stylised formats; that route still holds for real-footage / UGC formats
- **nobody talks; every scene is a silent clip — no stills ever** — attention-first song ads; a held still reads as slop (the owner 2026-10-10)
- **Seedance 2.5 at 480p, one take, then local Real-ESRGAN upscale** — ~$0.13/s at 480p vs about $0.57/s at 1080p; sloppy B-roll is fine under a song (the owner 2026-10-10)
- **pictures at high quality on the house picture model (2026-10-21, VIDEO-RULINGS V17 — was medium on the fast tier), made at 9:16, no framing-fix calls** — pictures were $3.5–7/ad of the spend on xhigh 2:3 + zone-fix remakes; the clips are 480p so xhigh detail is thrown away (cost ruling 2026-10-10)
- **scenes are set-ups, never lyric lines (VIDEO-RULINGS V35): one place and camera set-up per scene, a clear start and stop, the lyric beats played inside it; one start picture per scene, a returning set-up reuses its picture** — one picture per line made 40–57 pictures an ad (and 33 frames on 21 Oct); the owner 2026-10-23: "less frames and more just describing what's in the scene"
- **recurring cast and sets across stories** — the 10-09/10 runs already re-used banked family-3d people; a new cast per story is wasted spend
- **hooks are cut from existing clips, never generated** — h-a..h-d were 3 s scroll stoppers from the story's shocking beats, $0 extra

## Stage order

idea (concept or swipe) → picks (awareness → arc → sections) → writing (video-writing → the brief) → brief review (the owner) → song first (production start → song.py) → cast and 3D rooms → scene pictures (board, the owner OKs each) → hand-off (video editor) → clips and the cut (a creator) → upscale (bulk) → launch (the owner's click)

## Stage settings

**audio**
- first: song
- song_model: suno
- voice_model: the shared chain's own
- nobody_talks: off
- song_how: made by hand in Suno from song.py --suno (model-inputs suno sheet + the style row's suno line); brought back with song.py --from-file through the song gate (the owner, 2026-10-28)
- sung_on_camera: the singer sings his lines on camera like a musical: each sung scene's slice of the song (song.py sung_reads → vo/<scene>.mp3) is that scene's read, and its clip is a lip-synced talking clip; story shots stay silent over the song (the owner, 2026-10-28)

**song**
- length_s: 150, 195
- punch_first: the story's most shocking line sung in the first second — no intro, no humming, no beat-only bar
- sections: fit (lines × beats_per_line + tail beats at the row's tempo) — never a hand-written number
- flow: first_word_s: 1.0; max_gap_s: 3.5; dead_air_ratio: 0.1; ignore_tail_s: 4.0; beats_per_line: 6; tail_beats: 1; shrink: 0.85
- brand_line: said plainly once in the bridge and in the outro tag; a dropped tag is fixed by crossfading an 8 s tag in the same style
- master_true_peak_dbtp: -1.0
- loudness_lufs: -14
- beats_per_line_by_style: story-rap-soul: 6; dramatic-pop-ballad: 8; cinematic-orchestral-ballad: 8
- sound: it needs to actually sound like a song, just efficient: a melody, a sung hook, fewer syllables per line; short musical breaks are fine (under the 3.5 s gap)
- flow_why: the owner 2026-10-10 (second pass): max gap 3.5 s, dead air ≤10%, first word ≤1 s; rap 6 beats a line, ballads 8 — "it needs to actually sound like a song, just efficient"

**pictures**
- door: direct.openai
- model_key: the shared chain's own
- quality: high
- size: 864x1536
- aspect: 9:16
- made_at: 9:16 directly at 864x1536 — exact 9:16, both sides divide by 16 (the API takes any such size: components/image-production/models.json note, 2026-09-22); the clip is 480p so a bigger picture is thrown away
- fix_calls: off
- style_lock: the swipe's style row, formula first (family-3d on every run so far)
- send_size: the shared chain's own
- start_only: on
- max_references: 3
- product: image-to-image from the real product photo, restyled into the swipe's style; shape, colour and label exact

**clips**
- model: seedance-2.0
- endpoint: image-to-video
- resolution: 720p
- seconds: 4, 4
- clips_per_picture: 2, 3
- takes: 1
- audio: silent
- upscale: local Real-ESRGAN realesr-animevideov3 x3 to 1080x1920, crf 15
- stills_allowed: off
- short_clip: slow to no less than 0.75x, then play the rest in reverse (ping-pong) — never hold a frame
- send_size: 432x768
- send_format: jpeg q90, centre-cropped to 9:16
- prompt_order: action line + style lock FIRST, then motion; nothing else
- refused_every_try: the same prompt and references to the backup door (VIDEO-RULINGS V21); never the neighbour clip punched in (VIDEO-RULINGS V15)
- max_tries: 3
- _seedance: 2026-10-26: every clip is Seedance 2.5 at 480p, one take and three tries at most (VIDEO-RULINGS V34, MODEL-HOUSE.md); a clip is 4 s at the least
- _model_why: the owner, 2026-10-29: Seedance 2.0 for song ads (generative-model-house clips.song_ad); every other format stays Seedance 2.5

**cast**
- reuse: banked people and sets in the swipe's style first, across stories
- recurring: on
- product: ANIMATED STYLE RULE: the product is rendered IN THE FILM'S STYLE, image-to-image from the real product photo (shape, colour and label kept exact), held by the banked cast and animated like every other scene; only the end card is the real packshot. Real archive footage and studio renders in the body are refused for an animated style.

**hooks**
- shape: ~3 s scroll stopper cut from the story's most shocking clip, punched in 1.10→1.30x, a lyric line as text + one bank SFX, then into the first sung line
- count: 4
- generated: off

**captions**
- look: lyric lines in the swipe's caption look; the control opens on the first sung line with a headline at 16% from the top

**gates**
- apply: song line gate, song flow gate, style lock, clip words check (no words on the picture), loudness/true peak, product in the film's style from the real photo (no real footage in the body)
- skip: voice per speaker, lip-sync / line parity on clips (nobody talks), talking-scene audio slice

**edit**
- method: video-edit machine cut on the song's clock (renders on python3.14)
- reuse: second chorus and outro reuse earlier clips whole — never punched in (VIDEO-RULINGS V15)
- end_card: camera move on the real packshot / studio render — the ONLY real product pixels in an animated song ad
- garbled_background_text: blur at the edit (gblur sigma 22), never a punch-in past it (VIDEO-RULINGS V15)
- loudness: -14 LUFS, true peak ≤ -1 dBTP (limit the song first)
- versions: control + 4 hook versions

**copy**
- source: AD-SCRIPT.md — the sung lyrics
- why: the copywriter drifts to the story plot from the brand files otherwise

## Known failures → fixes

- **songs 5½–6 min with 35–90 s dead air; first word 12 s in** → punch line first, sections fit from lines × beats_per_line, every take listened to by song.py flow()  _(from runs/video-production/Brand A/resilia-cheating-Brand A (song/LYRICS-owner.md); stage song)_
- **brand line / last line dropped or blurred by the music model** → cut before it and crossfade an 8 s tag in the same style  _(from runs/video-production/Brand A/reddit-wrong-size-Brand A; stage song)_
- **cast made photoreal for an animated swipe** → the teardown names the style row; every element and frame is made in it (family-3d)  _(from runs/video-production/Brand A/resilia-cheating-Brand A; stage elements)_
- **The clip model 'could not generate' on a full-size PNG start picture** → send the start picture centre-cropped to 9:16 as a 432x768 JPEG q90  _(from runs/video-production/Brand B/reddit-the-fan-Brand B; stage clips)_
- **The clip model re-framed a 2:3 picture / refused it** → the picture goes in at 9:16; a 9:16 crop passed where the 2:3 was refused  _(from runs/video-production/Brand B/resilia-cheating-Brand B (ledger probe-G01-crop); stage clips)_
- **clip refusals (prohibited / third-party / safety)** → action line + style lock first; reword the action, never resend the same request; shorten to action + style + motion  _(from runs/video-production/Brand A/resilia-cheating-Brand A (clips/gate-refusals.json); stage clips)_
- **a clip refused on every try** → the same prompt and references to the backup door (VIDEO-RULINGS V21); never the neighbour clip punched in (VIDEO-RULINGS V15)  _(from runs/video-production/Brand A/reddit-wrong-size-Brand A (S28→S25); stage edit)_
- **clip shorter than its lyric window filled with a still push-in** → slow to ≥0.75x then reverse (ping-pong); never a still  _(from runs/video-production/Brand A/reddit-it-was-me-Brand A; stage edit)_
- **garbled background signs and labels** → blur on the start picture, or at the edit (gblur 22) — never a punch-in past it (VIDEO-RULINGS V15)  _(from runs/video-production/Brand A/reddit-it-was-me-Brand A (covered_at_edit); stage edit)_
- **real brands drawn in pictures (snacks, batteries)** → remade unbranded  _(from runs/video-production/Brand A/reddit-it-was-me-Brand A; stage pictures)_
- **shower scenes refused by the picture filter** → reword to the sink  _(from runs/video-production/Brand A/reddit-you-imagined-it-Brand A (S37); stage pictures)_
- **product label misspelt / a stranger drawn into the packshot** → the product is restyled image-to-image from the real product photo with its label kept exact (never drawn from words); end card = camera push on the real packshot  _(from runs/video-production/Brand A/reddit-wrong-size-Brand A; stage edit)_
- **copywriter cards drifted to the story plot** → name AD-SCRIPT.md (the sung lyrics) as the copy source  _(from runs/video-production/Brand A/reddit-you-imagined-it-Brand A (ad_words); stage copy)_
- **control and a hook version held at -0.7/-0.8 dBTP** → limit the song first (alimiter 0.6) and master to ≤ -1 dBTP  _(from runs/video-edit/Brand A/reddit-it-was-me-Brand A (deliverable/checks.json); stage edit)_
- **zone-fix picture remakes unbilled on the ledger and doubling picture calls** → make at 9:16 directly; framing-fix calls off  _(from runs/video-production/Brand A/reddit-it-was-me-Brand A (41 zone-fix rows); stage pictures)_
- **real archive B-roll / studio renders cut into an animated film** → refused for animated styles — the product is rendered in the film's style from the real photo, held by the banked cast  _(from runs/video-production/Brand A/reddit-it-was-me-Brand A (inserts.json product_rule) — ruled out by the owner 2026-10-10; stage edit)_
- **no lane, no quote and no priced go before paid clips (a blanket 'go execute')** → the quote station is the one stop; the lane opens only on the owner's go on that price, and the clip guard passes only an open lane's model  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage clips)_
- **held concept-only sets used as clip references** → the pack is not ready on any held asset, and the lane does not open on it  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage elements)_
- **a delivered clip shows two men hugging, on a lyric that asked for it** → the setups check refuses a hug or kiss in a prompt unless contact_ok names who it is, never two men; the takes look at house rules  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage clips)_
- **captions showed the transcript's mishearing instead of the approved lyric** → the edit's captions are the approved lyric word for word  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage edit)_
- **two brief versions; the pack used one and the production run named the other** → the workflow names one brief, the writing run's accepted stage, and re-files the shelf copy from it  _(from runs/video-teardown/_work/Brand A-this-christmas-photo; stage writing)_
- **the approve action pressed on the owner's behalf** → the run ends at 1-check and never calls approve  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage meta)_
- **a static opening** → the motion law in every prompt: timed 1.5-2 s shots, each an action with a visible result, the camera moving  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage clips)_
- **the product turned the wrong way in progression clips** → the mechanism in one clip; later clips drop the product reference  _(from runs/higgsfield/Brand A/singing-ads-Brand A_flex-face-brush_brief-0376; stage clips)_

## Cost

- target per ad: $10
- cap_usd_per_ad: the shared chain's own
- _cap: 2026-10-21 (P40, VIDEO-RULINGS V17: cost is never a reason): no dollar cap stops an ad; three of every element, the best kept.
- measured: ledger $9.67–16.31 an ad on 8 runs (pictures $3.49–7.02, clips $6.18–10.38) — pictures understated (zone-fix rows unbilled), element sheets ~$2.40–4.70 more, song not on the ledger; ~$18–27 all in
- how: pictures high on the house picture model at 9:16 (V17, 2026-10-21 — was medium on the fast tier), no fix calls, 2–3 clips per picture (~20 pictures not ~50); clips 3–4 s at 480p (~45 × 3.5 s × $0.13 ≈ $20 for a 2:45 song); cast and sets reused (element sheets ≈ $0); hooks cut from clips ($0)

## Quality bar — not slop

- the first sung word lands inside 1 s and it is the story's punch line
- no gap over 2 s between sung words; dead air under 5% (song.py flow)
- every picture in the swipe's style row — no photoreal person in an animated ad
- every shot moves: no still, no frozen frame, no held last frame
- no readable garbage text anywhere on screen (blurred, never punched past)
- no stranger, no merged faces, no real third-party brand in frame
- every clip sits under the lyric it illustrates
- master ≤ -1 dBTP at -14 LUFS
- the brand line is heard plainly once in the bridge and in the outro
- the product matches the real photo exactly (shape, colour, label) AND is in the film's style — no real footage in the body; the end card is the real packshot
- it sounds like a song: a melody and a sung hook, not a rushed list of lines
- the story is real: real cheating, real scandal, real stakes; never a softened version (the owner, 2026-10-28: "I want the cheating to be real")
- innuendo and sus pushed right up to the edge line (Story Playbook): double meanings, 'pause', near-curses; never over it
- every scene has one shocking thing a viewer would screenshot
- it watches like a music video and a movie at once: the singer's performance shots intercut with the story, shot sizes varied (wide, medium, close), every shot staged and lit like film
- depth in every scene: built from its 3D room with a real lens and light, never a flat backdrop
- the clip model is used to its limit: camera moves, physical acting, emotion travelling through the shot; never a held pose
- upscaled to 1080x1920 before launch; nothing ships at the clip model's working resolution

## The workflow — start it by name

The song-ad line, for any song ad, run autonomously: start (a swipe, or our own), writing chain (holds decided by the decision layer), the song, the elements, the Studio pack, the story map, the quote, Higgsfield Singing Ads with a check after every paid step, upscale on this Mac, the edit, the approval page. The only stop is the quote: the owner's go on the price opens the lane.

`python3 machine/workflow.py status song-ad --label <label> --brand <brand>` says where a run is and what runs next.


| # | Station | Component | Does | Signs off |
|---|---|---|---|---|
| 1 | Start: a swipe, or our own | swipe-intake · video-teardown · video-writing scratch.py | Two starts, one workflow. WITH A SWIPE (source=swipe): save and index it (swipe-intake) and tear it down through stage 2 (video-teardown run.py); its structure and beats are the swipe's. source_record = runs/intake/{brand}/<intake>/run.json. WITHOUT A SWIPE (source=own): the concept brief (research-round or the owner's idea), then python3 components/video-writing/machine/scratch.py <label> --brand {brand} --product <p> --avatar <a> --format song-ad --arc <arc> --style <style id> --story <concept.md> (no --write); the arc's beats are the song's sections. source_record = the concept file. Return source, teardown and source_record. | — |
| 2 | Writing chain brief | video-writing | The writing chain writes the song brief with the decision layer on: every hold is decided and filed in runs/decisions/calls.jsonl, and the run continues. Nothing is hand-patched, and no brief is accepted outside the chain. The brief this workflow uses is the writing run's own accepted stage brief ({brief}), one version only. | — |
| 3 | The song | video-production song.py · Suno | Make the song from the brief's lyrics through the song chain (SONG-CHAIN.md): song.py writes the Suno inputs, the takes are made in Suno, and the chosen take goes back through the song gate (song.py --from-file): every line heard, in order, and the last line finished. Keep the song unchanged from here on. The take is chosen by the run (the one whose lines all pass, the cleaner ending on a tie) and filed through the decision layer; the owner hears it on the quote page. | — |
| 4 | Cast, looks, places and product | casting · 3d-print · image production · elements_check | Every person, look, place and the product in the brief's style, each from a filed 3D print through image production (one image process, no side paths; never a session's own image tool). The product is its approved casting sheet in the style (style_chain). A held or concept-only asset is never used as a reference. The elements lock writes itself when every element is banked and checked. | — |
| 5 | Studio pack | video-studio higgsfield/hf_pack.py | Gathers the song, its lines on the song's clock (lines.tsv), the accepted scene plan, the banked cast, places and product into the film folder (pack.json, REQUEST.md). A held asset, a missing line clock or no accepted scenes marks it not ready, and the lane will not open on it. | — |
| 6 | Story map, windows and clip prompts | Higgsfield Singing Ads recipe | Cut the song into windows on its own sung lines (lines.tsv), end to end with no gap, each window inside the clip model's length, one clip a window, following the accepted scene plan in order. Write film/script.json {clips: [{id, make: fresh, images: [refs], videos: [], voices: []}]}, film/plan.json {song_seconds, windows: [{clip, start, end}]} and film/prompts/clip-<id>.txt. Every prompt carries the motion law: a timed shot list of about 1.5-2 s shots, each a physical action with a visible result, the camera moving (drama camera recipe). The product's mechanism is shown in one clip; later clips drop the product reference. A skin or look change keeps the same room, angle and light across its states. No on-screen text. Men never hug or kiss men. | — |
| 7 | Quote, then the owner's go | Higgsfield ads_studio_story_recipe · get_drama_ads_config · video-studio higgsfield/drama_lane.py | THE ONE STOP. Start the ad's record with ads_studio_story_recipe (preset /singing-ads) for its story id, the drama_ads_id. Price every window on both clip models (drama_lane.py models --format song-ad), Seedance 2.5 480p draft and Wan 3.0 480p, with get_drama_ads_config purpose stage under that id, called right before the numbers are shown; never a remembered rate or a hand sum. Show the owner both totals beside the chosen song (to hear) and the story map. His go names the model (Seedance when he does not say). Write quote.json {drama_ads_id, clip_model, resolution, total_credits, quote_refs, other_quote}; only his go opens the lane: drama_lane.py open <film> --format song-ad --quote quote.json --model <his pick> --approved-by <name> --said "<his words>" --cap <credits>. Read the account's credit balance (balance) right before the quote and show it beside both totals, with what is left after the chosen one; a balance below the total is said first. | the owner: the quote (his only stop) |
| 8 | Lane check | video-studio higgsfield/drama_lane.py | Holds every paid step until the lane is open on the owner's go, on one clip model, the quote on that same model, under the cap. | — |
| 9 | Reference sheets | Higgsfield Singing Ads recipe | Upload our banked cast, looks, places and the product's approved casting sheet as the film's references; make a sheet only for a role the pack names as new, once, with the lane's drama_ads_id. Write film/sheets.json {sheets: [{kind, name, job_id | source}]}; the product row's source is the pack's product sheet. | — |
| 10 | Sheets check | video-studio higgsfield/drama_lane.py | Holds the clips until every sheet is made once and the product is the pack's approved sheet, never generated. | — |
| 11 | Every clip's setup on the page | media-production scene input review | Before any clip is sent, publish every clip's exact setup on the film's page: ordered references with role and preview, the full prompt, model, resolution, aspect, duration and its quote. Write film/setups.json {page, setups: [{clip, model (the lane's vendor id), resolution, aspect_ratio, duration, refs: [{role, value, file}], prompt_file, prompt_sha256, camera, quote_credits}]}. Showing the setup adds no stop. | — |
| 12 | Plan and setup check | video-studio higgsfield/drama_lane.py | Holds the clips until the windows run end to end over the song on its sung lines within the model's length, every setup is published on the lane's model and settings within its reference limits, every shot moves, and no prompt has a hug or kiss between men. | — |
| 13 | Clips through the batch tools | Higgsfield Singing Ads recipe | Send each clip exactly as its published setup through generate_video_batch with the lane's drama_ads_id, sound off (the song is laid in the edit), Seedance as a 480p draft so the 1080p finish stays open. Run drama_lane.py request <film> <request.json> before every send. The first clip goes alone and is looked at; the rest follow in batches. Freeze each take in jobs.json {clips: [{clip, take, request: {params}, job_id, result_url}]}. Stop at the lane's cap. | — |
| 14 | Each take looked at | Higgsfield Singing Ads recipe · video-production | Download every take and look at it at 2 frames a second against its window: motion (the timed shots happen, the camera moves), identity, the lyric beat it illustrates, continuity (skin state, wardrobe, room), product use (right way round, in the right clip only), house rules (no men hugging or kissing, no stray text). A wrong take is fixed with clip_tools.py (only the broken seconds) or remade inside the cap, never sent to the owner; a kept finding is filed with drama_lane.py decide. Write film/takes.json {takes: [{clip, job_id, accepted, looked: {motion, identity, lyric_beat, continuity, product, house_rules}}]}. | — |
| 15 | Takes check | video-studio higgsfield/drama_lane.py | Holds the edit until every frozen request matches its published setup and the lane, and every window has an accepted take looked at on all six looks. | — |
| 16 | Upscale on this Mac | local-studio local.py | Upscale every accepted take on this Mac (python3 components/local-studio/local.py upscale, Real-ESRGAN animevideov3, x3); never a Higgsfield upscale. Check each output's frame count, duration and source sha against its take, and write clips/upscale-status.json naming each take and its upscaled file. | — |
| 17 | The edit | video-edit from_higgsfield.py · v2.py · HyperFrames | Build the cut from the accepted, upscaled takes (video-edit from_higgsfield.py; never a hand-written cut), lay the song unchanged, and deliver a captioned and a clean version (run.py deliver). The captions are the approved lyric word for word, kept off faces. Make the opening variations on the first window and splice them with v2.py ad --control --hook, the body proven identical. Covers from the film's frames. Write deliverable/edit.json naming each version, its takes, its checks, and that the song is unchanged. | — |
| 18 | Filed to the approval page | meta-upload | File the control and every opening as one flexible ad into the approval folder (meta-upload, 1-check), with the brand's proven words. Write deliverable/meta-filed.json. The run ends here and nothing is published here. Never call the approval page's approve action: going live is the owner's click on the approval page, outside the run. | — |

## Built from

- runs/video-production/Brand A/resilia-cheating-Brand A
- runs/video-production/Brand A/reddit-wrong-size-Brand A
- runs/video-production/Brand A/reddit-it-was-me-Brand A
- runs/video-production/Brand A/reddit-you-imagined-it-Brand A
- runs/video-production/Brand A/reddit-on-principle-Brand A
- runs/video-production/Brand B/resilia-cheating-Brand B
- runs/video-production/Brand B/reddit-the-fan-Brand B
- runs/video-production/Brand B/reddit-two-more-years-Brand B
- runs/video-edit/Brand A/* and runs/video-edit/Brand B/* (the matching edits + -h-* hook versions)

## Rulings behind it

- the owner 2026-10-10 (SONG-WRITING.md): "the opening line needs to start with the punch … these songs need to be shorter … the songs need to flow"
- the owner 2026-10-09 (THE-CHAIN.md): "the creative format itself is supposed to look like Pixar" — the swipe's style is the lock
- the owner 2026-10-10 (memory: song ads all clips, cheap): no stills ever; Seedance 480p + local upscale; sloppy B-roll is fine
- the owner 2026-10-10 (attention-first song ads): no voiceover, silent scenes follow the sung story
- the owner 2026-10-09/10 (CLAUDE.md, product never drawn): "all this slop stuff is gone … so we can print ads"
- the owner 2026-10-10: "how can we get our cost down even more" — the cost defaults above
- the owner 2026-10-10: "we cannot have AI slop" — the quality bar
- the owner 2026-10-10: "you shouldn't be using real b-roll for this" — animated formats render the product in the film's style from the real photo; only the end card is real
- the owner 2026-10-10: "it needs to actually sound like a song, just efficient" — max gap 3.5 s, dead air ≤10%, rap 6 / ballad 8 beats a line
- {'ruled': '2026-11-27', 'rule': 'song ads run one locked workflow, the path brief 0376 took with its fixes; autonomous, the quote the only stop'}
