# The video-ad line: from a swipe to a named ad in Meta

*How it actually runs on 3 Oct 2026. Checked against the team repo as merged that afternoon (Edit round 5 included), and against the Nova ad: Brand A face scrub, the three-doctors run.*

the owner, 3 Oct 2026: *"Literally just index this entire chain of events all the way from the swipe to now … to the point we can just literally print video ads."* Cost target: **about $__ an ad next**, lower after that.

**The words used here** (one meaning each, THE-CHAIN.md):
- **swipe shot**: the swipe from one cut to the next (K01, K02 …)
- **scene**: one row of our brief (S1, S2 …)
- **section**: scenes filmed as one camera set-up, so one clip to make (Section 1, 2 …)
- **picture**: a still we make to start a section
- **length**: always written m:ss

---

## 1 · One-screen overview

| # | Station | Goes in | Comes out | Lives in | the owner's stop | Cost (Nova) |
|---|---|---|---|---|---|---|
| 1 | **Swipe in** | posts from My Feeds (organic) and competitor teardowns (paid) | one list of swipes, each tagged with its kind and the teardown it goes to | My Feeds page · `components/intake`, `swipe-organic`, `swipe-paid` | he picks the swipe | Apify pulls only when he presses the button. Both Apify accounts were over their monthly cap on 3 Oct |
| 2 | **Teardown** | one swipe video | the record (every line word for word, people, places, sound), the transcript, the **frame map** (every cut, every moment), the spec | `runs/video-teardown/<brand>/<slug>/` | reads the record | not on any ledger (Claude runs) |
| 3 | **Writing → the brief** | record + brand + avatar | **THE BRIEF**: every scene, line, speaker, person, place, prop, on-screen word, plus hooks and close. It then goes through the viewer check (5 viewers) | `runs/video-writing/<brand>/<slug>/` · index `runs/video-writing/INDEX.md` | brief read (and "worth making?") | not logged |
| 4 | **Elements** | the locked brief | cast sheets, places, props, **voices** (cloned from Omni takes), **product truth kit** | `runs/ai-elements/<brand>/` (casting · sets · props · products) | **"elements ok"** (the lock) | Omni voice takes are about $__ each. ElevenLabs is not logged |
| 5 | **Pictures** | brief + elements + blurred swipe shots | one start picture per section (GPT Image 2.5), face-checked, product measured and fixed | `runs/video-production/<brand>/<label>/media/` | approves the pictures on the ad page | **not logged** (108 made ≈ $__). Picture checks $__ |
| 6 | **Clips** | approved pictures + lines | Omni on fal at 1080p animates each picture. On-camera lines are spoken inside the clip and swapped to the cloned voice | `…/clips/` (`omni-ledger.json`, `PROMPTS.md`) | approves the clips (face lineup) | $__ image-to-video + $__ movement clips + $__ old upscale |
| 7 | **Sound** | off-camera lines, sounds ("mm-hmm"), music | off-camera lines in the cloned voice, sounds on their own track, the music bed | `…/clips/offcam/`, sound map `…/clips/SOUND-MAP.md`; music in the edit run | hears the voices | ElevenLabs is not logged |
| 8 | **Edit** | clips + tracks + the owner's calls (`decisions.json`) | **the edit map**: timeline, B-roll, close-ups, captions, option pops, sweep, listen | `runs/video-edit/<brand>/<label>/` | **the timeline** (a player page, not a render) | about $__ (B-roll is free, from Drive, TikTok and Pexels) |
| 9 | **Variations** | the brief's hooks (openings 2–6), plus headlines and scroll stoppers later | one opening clip per hook, and one edit map per hook (`edit-map-<hook>.json`) | `…/clips/G01-H2…H6.mp4` · edit run | picks which go | +$__ (5 hook clips) |
| 10 | **Final render** | edit map(s) | a 9:16 mp4 per version, checked (mouths, every word heard, lips, black/silence) | `video-edit/machine/render_map.py` | — | free (built 3–4 Oct) |
| 11 | **Naming** | the master | named to the short convention | `components/naming` | — | free |
| 12 | **Delivery folder** | the named versions + their words | a card in Drive `Shared Assets/meta/<brand>/1-check/video/<ad>/` | `video-edit/machine/deliver.py` + `meta-upload/to_check.py` (edit-map line); `meta-upload/feed_video.py` (cut-sheet line) | — | free |
| 13 | **Meta upload** | an approved card | a video ad in the account (Prizm Labs app) | `components/meta-upload` approval page | **Approve** on the page | free |

**Where the Nova ad is now:** stations 1–9 are done (the edit is on its 5th round). Stations 10–13 have not run for this ad, because nothing turns the edit map into a finished mp4 yet.
**Nova all-in: about $__ plus the voices.** A clean run of the same ad would be about $__. At the swipe's own length it would be about $__.

---

## 2 · Station by station

### 1 · Swipe in
- **What it does:** `intake` presents paid and organic swipes as one list. It fetches nothing and costs nothing. Organic swipes come from **My Feeds**: the owner types what he wants to see, a dig runs, and it becomes a standing feed. Paid swipes are competitor brands torn down, one folder per brand.
- **Rulings in force:**
  - My Feeds is the front door (19 Sep).
  - No automatic Apify. Nightly jobs were switched off on 23 Sep, and pulls happen only on his button.
  - Meta pulls are narrow only, and stop at 75% usage (2 Oct).
- **Runs as:** the My Feeds page (`swipe-organic/desk.py`) · `intake/tools/run.py`
- **Nova:** an organic swipe (the three-doctors run, a real creator filmed on an iPhone, length 1:21).

### 2 · Teardown
- **Steps:**
  - 1.1 triage
  - 1.2 record, transcript and frame map
  - 1.3 doctrine read
  - 1.4 spec
- **What it makes:** the record of the swipe as it is, with nothing of ours. The frame map (`video-teardown/machine/framemap.py`) is made here, so that motion is settled before anything is generated.
- **Rulings in force:**
  - 1 Oct: *"we should've done this level of frame analysis at the teardown stage"*.
  - 11 Sep: the teardown is shared, then splits into a creator line and an AI line.
  - The route lock: writing starts only with a chosen route.
- **Runs as:** `video-teardown/machine/line.py teardown <video> --brand <brand>`
- **Nova:** `tools/video-teardown/machine/runs/the three-doctors run/`. Done.

### 3 · Writing: the brief
- **Steps:**
  - 2.1 rewrite
  - 2.2 hooks (as format fills)
  - 2.3 expansion
  - 2.4 close
  - 2.5 audit
  - 2.6 spice
  - 2.7 the brief
- **Gates:** structure lock, hooks, audit, spoken words, cast vs swipe, swipe match, manifest. Then the **viewer check**: 5 fresh viewers scroll it in the avatar's feed, and production refuses to spend without a pass (PR 131, 3 Oct).
- **Rulings in force:**
  - The swipe structure is locked: adapt it, never rebuild it.
  - Hooks are hard injections into the swipe's format.
  - Spice should sound spoken.
  - The offer may sell.
  - The latest avatar profile is used.
  - Each brand and product counts brief numbers from 1.
  - Website wording wins.
  - Nothing is invented (Brand B).
- **Runs as:** `video-teardown/machine/line.py ai --label <run> --brand <brand>`
- **Nova:**
  - The brief is `runs/video-production/<brand>/<run>`: 43 scenes and 6 openings (one control plus 5 hooks).
  - It plans **2:42** of video against the swipe's **1:21**.
  - The cut runs **2:25** after the owner took sections out.

### 4 · Elements (production step 1)
- **Steps:**
  - 3.1 check every person, look, voice, place, prop and product in the brief against the bank, both ways (`element_match.py`, `elements_check.py`).
  - 3.2 make whatever is missing from a real reference (`make_character.py`, `make_set.py`, `voice_cast.py`, `product_kit.py build`).
  - 3.3 the owner says **"elements ok"**. That writes `elements-lock.json`, and the lock breaks on its own if anything changes.
- **Voices (3 Oct):**
  - Omni says the person's real lines in 3 takes.
  - The best take is cloned in ElevenLabs.
  - That clone is the person's one voice, on camera and off.
  - the owner: *"use the best voice then clone it for everything so it stays consistent"* · *"version a actually sounds like the avatar looks"*.
- **Product truth kit (2 Oct):**
  - The real shape and size, measured from Drive photos, plus a Blender model.
  - Production refuses a product with no kit.
  - the owner: *"this is how we can actually eliminate all product slop … at scale."*
- **Rulings in force:**
  - AI people are made only from real references (no casting sheet means it isn't current).
  - A recast is a brief change first (1 Oct).
- **Nova:**
  - Nova and Doctors 1–3 are cast and their voices cloned.
  - The Brand A Face Scrub kit is built: the tube is 1.79× as tall as wide. Six of the seven tubes drawn before the kit were wrong.

### 5 · Pictures (4.3 storyboard, 4.4 pictures)
- **Storyboard:** `storyboard_plan.py` groups the brief's scenes into the swipe's own sections and lays out every layer. It writes `BUDGET.md` (low, likely and high cost) before any spend.
- **The recipe (2 Oct, *"this cannot happen again"*):**
  - **GPT Image 2.5 only.** The model is locked by `run.py ruled_model`.
  - The swipe shot goes in first, blurred.
  - Then our people, the room, the real product and the outfits, five references at most.
- **Checks:**
  - The face check (`identity.py`).
  - The 14-line picture inventory.
  - The product measured and fixed (`product_check.py`, `product_fix.py`).
  - Everything is filed in `<run>/qc-log/`.
- **Rulings in force:**
  - 9:16 only, with the content in the middle 4:5 (22 Sep).
  - The swipe shot is always a reference (2 Oct).
- **Runs as:** `video-production/machine/run.py start <brief> … --storyboard`
- **Nova:** 22 sections. 108 pictures were made over the rounds; a clean run needs 22.

### 6 · Clips (4.5)
- **How clips are made:**
  - Omni Flash 1.1 on fal, **1080p**, 9:16. It animates the approved picture and never makes one.
  - A person on screen means image-to-video from the approved picture, with their identity words in the prompt.
  - Movement copied from the swipe (blurred, 3 seconds at most) is used only where nobody of ours is on screen.
  - Each clip is cut at line boundaries into 3–10 second pieces, never padded.
  - On-camera lines are spoken in the clip, then swapped to the cloned voice with the crisp finish.
- **Rulings in force (all 3 Oct, `providers.json ruling_2026_10_03*`):**
  - Omni: *"omni crushed it"*.
  - fal: *"go with fal for sure"*.
  - Voice version A.
  - Face lock at 1080p.
  - **No hand-offs:** 17 of 17 clips made from the approved picture held her face, and 10 of 10 handed-on clips drifted.
  - No invented speech.
  - Sounds are not lip-synced.
  - The speaker comes from the brief.
- **Checks after each clip:**
  - Words check (`lineparity`).
  - Eye check, with one remake.
  - `clip_qc.py`: framing, scene, camera and lips.
  - The **face lineup by eye** is the real check.
- **Runs as:** `run.py start … --clips --dry-run`, then `omni_clips.py run <run> --yes`
- **Nova:**
  - 29 sections are planned at 178 billed seconds ($__ clean).
  - The actual spend was higher because of 360p tests, drift remakes and eye remakes.
  - The words check found 4 clips CUT_OFF and 1 FLAG.

### 7 · Sound
- **Off-camera lines:** read in the cloned voice (`voice.py`) and placed on their own track.
- **"Mm-hmm" and "um":** the person nods with lips closed, and the sound goes on its own track.
- **The sound map:** `sound_map.py` shows each line as voice-in-clip, own track or sound.
- **Music:** ElevenLabs Music v2.5, ruled 23 Sep (*"Eleven Labs won for me for sure"*).
- **Nova:** the music bed is made (`runs/video-edit/<brand>/<run>`) and laid in under the voices with ducking. There are still no sound effects.

### 8 · Edit
- **The clock (the owner, 3 Oct: *"think about the principle"*):** every line sets its own time. On camera, that is the clip's own span. Off camera, it is its own track.
- **The swipe sets** the cuts, angles, push-ins, words on screen and cues.
- **Edit moves before remakes.** The moves are in `EDIT-STANDARD.md` §3.
- **B-roll:**
  - About 4 seconds a piece.
  - Real, phone-grade footage.
  - Each piece used once, and every piece moves.
  - Lead-only until the product comes in.
  - Failed-solution lines cut in the thing that was named.
  - Before/afters go on the results lines.
- **Captions:** in the platform's style (IG/FB native for Nova). Titles keep their capitals.
- **Words on screen:** only what the swipe shows, plus native "Option 1/2/3" pops.
- **Sweep** (`sweep.py`): frame by frame, 4 a second, nothing rendered.
- **Listen** (`listen.py`): the soundtrack mixed and transcribed against the script.
- **The timeline:** a player page, not a render (*"I just need you to build the timeline, don't render"*).
- **Runs as:** one command, `video-edit/machine/line.py <production run>` (plan → mouths → words → render → scan → deliver → file; every check stops it). Looking tools while settling decisions: `sweep.py` · `listen.py` · `mouths.py` · `word_fix.py` · `music_bed.py`. How it runs: `video-edit/EDIT-STANDARD.md` Part A
- **Nova:**
  - Edit round 5 is done.
  - The cut is 2:25 long: 18 sections, 39 lines, 14 B-roll pieces, 24 covers, 1 word patch and 2 added lines.
  - the owner removed the receipt cards (G05, G10, G17), the thumbs-up end card (G19) and the phone shots (G03, G08, G14).
  - Listen findings left: "guaranteed" is clipped (S42). The rest are wording variants (gonna / going to, $__).

### 9 · Variations
- **Hooks:** openings 2–6 are made as clips (G01-H2…H6, $__). `edit_map.py --hooks` writes one edit map per hook (`edit-map-<hook>.json`) on the same body.
- **Headlines and scroll stoppers:** there is no video lane yet.
- **`components/ad-variations`:** plans variations of a proven ad (locks and levers). It plans only and makes nothing.
- **Ruling in force:** double down on winners. Keep the winning message and scale it through formats and slight angle shifts.

### 10–13 · Render → naming → delivery folder → Meta
- **The finished-video path that exists is the older cut-sheet line** (`video-edit/machine/run.py start | render | handoff`, HyperFrames):
  - `render` makes one video per hook, the 15/30/60 cutdowns and the covers, and names each file through `components/naming`.
  - `handoff` puts the master in `returned/` and calls `meta-upload/feed_video.py`. That writes the card to `Shared Assets/meta/<brand>/1-check/video/<ad>/<ad>_asset-01.mp4` plus `card.json`.
- **Meta upload:** handles video (`upload.py` builds `video_data`) through the one Prizm Labs app and key. Brand A and Brand B can both read and write, with no App Review needed (1 Oct).
- **Approval:** nothing goes live except through the owner's **Approve** on the approval page (`approve.py`, 1 Oct). the owner: *"we don't want to just upload ads automatically after making them, we need to do a check."*
- **The words on the card** (primary text, headline) come from the hand-off's `words.json`, or from the brief's copywriter run. With neither, the card fails its check ("no primary text · no headline").
- **Nova:** has not reached any of these, because the edit map has no render.

---

## 3 · Gaps, by station

Status: **built** · **partly** · **not built**.

### Swipe in
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| S1 | Apify capped: both accounts were over their monthly cap on 3 Oct, so B-roll and treatment footage fell back to Pexels and yt-dlp | `runs/video-edit/<brand>/<run> → broll.treatment_source` | a budget or plan decision. yt-dlp needs no Apify for single links | not built |
| S2 | Only organic swipes start a teardown on their own (the **Tear down** button on a My Feeds card, `swipe-organic/desk.py`). Hand-added and paid swipes go by hand, and nothing reads intake's list (`runs/intake/…/swipes.jsonl`) | `intake/README.md` · `desk.py` l.86–106 | the same button on paid and hand-added swipes | partly |
| S4 | The last nightly feed run failed on a wrong file path (22 Sep). The feed docs still describe the switched-off morning run, with a different cap and time than the code | `swipe-organic/records/desk/daily.jsonl` · `README.md` l.45 vs `daily.py` l.30 | fix the path; correct the docs | not built |
| S3 | 60 swipes are torn down with no brief, and the brief index says **0 produced · 0 edited**, so Nova isn't joined back | `runs/video-writing/INDEX.md` header | production and edit write their state back to the index | partly |

### Teardown
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| T1 | The swipe's B-roll moments (failed solutions shown, how-to, results) aren't pulled out as a list for the brief | the edit had to find them (`EDIT-STANDARD.md` §8 "B-roll") | the frame map marks each insert or B-roll moment and what it shows | not built |
| T3 | The Nova teardown record is missing its Sound Sheet and music, though its contract lists both. Three stages were done by hand in a session, and one stage errored | `runs/video-teardown/<brand>/<run>` · `machine/runs/the three-doctors run/run.json` | — | partly |
| T4 | Teardown and writing spend isn't logged in dollars (only seconds per stage) | `run.json`, `stage-times.json` | a cost line per stage | not built |
| T5 | The teardown docs are stale: they still describe pictures on every scene, frame stages 6–9, "nine/thirteen stages" and a removed lane setting. The frame map is missing from the stage list | `video-teardown/README.md` l.61, 165–188 · `machine/README.md` · `.claude/skills/video-teardown/SKILL.md` | rewrite to the 5 stations in THE-CHAIN.md | not built |
| T2 | The teardown's caption read isn't turned into a caption look (`match-swipe`) | `tools/video-edit/CLAUDE.md` "Not built yet" | build `match-swipe` | not built |

### Writing (the brief)
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| W1 | **The brief runs twice the swipe's length** (2:42 planned and 2:25 cut, against 1:21). Every extra second is paid for twice. **Two rulings conflict here:** the writing prompts tell the brief to run past the swipe (AI brief v21 l.1413–1431, *"Finishing at the source's runtime … is the failure"*; expansion v14+, *"a guide, never a ceiling"*, after his 25 Sep *"that's too limiting"*). EDIT-STANDARD §8 (3 Oct) says hold to ±20% | `storyboard.json` (162.06 vs 80.62 s) · `tools/copywriter/prompts/video/` | **his call, then the prompts and a length gate** | not built ("to fix") |
| W2 | **The brief's B-roll has no source.** The brief does write B-roll (19 of Nova's 43 scenes), but as scenes to generate. The real footage (creators' raw clips, TikTok, before/afters) was found, pulled and placed by hand in the edit | `EDIT-STANDARD.md` §8 · `decisions.json → broll` | each B-roll row names its real source (bank, creator raw, TikTok link). Production pulls it, and no AI clip is made for it | not built ("to build") |
| W3 | On-screen text came from the brief, not the swipe (a stack of headlines). The prompt treats the swipe's text as a minimum, not a limit (v21 l.32), and swipe match doesn't check added text | `EDIT-STANDARD.md` §2, §8 · `decisions.json → text_keep` | the brief lists only the swipe's text, and swipe match checks for it | partly (the edit filters it; the brief is still to fix) |
| W10 | **No standard video brief.** Nova's brief is 199 KB, with the reader's part mixed into the build data. The 2 Oct "standardized briefing document" exists for statics only | `tools/image-teardown/templates/brief-standard-static-damon.md` | a video version of the standard brief | not built |
| W11 | The viewer-check stamp on the Nova teardown passed at a length of 85 s, against a 2:42 brief, so it may be stale | `machine/runs/the three-doctors run/viewer-check/STAMP.json` | the stamp is tied to the final brief's hash | partly |
| W4 | Paper-graphic cards (receipts, thumbs-up) felt fake | `decisions.json → drop_sections` | no paper cards. Between-section beats are native text pops | not built ("to fix") |
| W5 | Phone inserts added nothing | `decisions.json → drop_picture` | an insert must show something the line needs | not built ("to fix") |
| W6 | A customer said the brand's promise ("we'll gladly issue"). No writing prompt has a rule about who speaks the offer or guarantee | `decisions.json → audio_patches` · `copywriter/prompts/video/` | brand promises in a customer's mouth are written in the third person | not built ("to fix") |
| W7 | Clips are made for stretches later covered by B-roll | `EDIT-STANDARD.md` §9 | the brief marks B-roll stretches, and no clip is made under them | not built |
| W8 | A video ad's words (primary text, headline) aren't written by the video line | `meta-upload/feed_video.py` (empty lists → the card fails) · memory: *after-the-edit* "video brief-0191 … no ad copy" | the writing station writes `words.json` for every video brief | partly |
| W9 | `ROADMAP.md` is stale: the variation registry is "next" and assembly is "after 6", from 18 Sep | `tools/video-production/ROADMAP.md` | roll it into this index | not built |

### Elements
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| E1 | Voice spend isn't logged: ElevenLabs clone, text-to-speech and speech-to-speech | `the three-doctors run/ledger.json` has no ElevenLabs rows. The budget prints "plus ElevenLabs" | the voice door writes to the ledger | not built |
| E2 | No real before/after of spots fading exists. The one used is the landing-page card, with no permission on file | `EDIT-STANDARD.md` "Open" · `decisions.json → before_after_source` | a product proof bank per product, with usage noted | not built (his call pending) |
| E4 | `voice_cast.py clone` doesn't write the person's `voice.json`; that step was done by hand. It still defaults to 360p | `video-production/machine/voice_cast.py` | write `voice.json` (old voice kept) at 1080p | partly |
| E5 | Step 3.1 doesn't check product kits; the kit gate only bites at production. `element_match` runs only inside QC, not as a gate | `elements_check.py` · `run.py` product gate · `qc.py` l.85 | the kit and match checks in 3.1 | partly |
| E6 | The voice docs are stale (designed voices, old folders) | `PRODUCTION-ELEMENTS.md`, `VOICE-CHAIN.md`, `building-the-cast.md` | point to the 3 Oct cloned-voice route | not built |
| E3 | Usage terms for creators' raw clips and TikTok/web B-roll aren't settled | `EDIT-STANDARD.md` "Open" | — | not built (his call) |

### Pictures
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| P1 | **Picture spend isn't logged.** 108 GPT Image 2.5 rows have `usd: null` (≈ $__) | `ledger.json` · `providers.json → models.gpt-image-2.5-sunburst.rates.usd_per_job: null` (token rates are there but never used) | the picture door works out its cost from tokens and writes it | not built ("to fix") |
| P2 | A talking start picture with **eyes closed** made a clip with brown eyes (Section 18) | `EDIT-STANDARD.md` §8 | refuse to approve a talking start picture with the eyes closed | not built ("to fix") |
| P3 | A **third hand** appeared in the offer clip | `EDIT-STANDARD.md` §8 · `decisions.json` (G22-C1-1) | the prompt names each hand and what it holds | partly (the sweep catches it; the prompt is still to fix) |
| P4 | 108 pictures for 22 sections: rounds of remakes | `ledger.json` | the recipe and checks are now locked (2 Oct). Watch the next run | partly |
| P5 | The reviewer agent failed to run (JSON error) and counted as "did not run" | `the three-doctors run…/qc-log/QC-LOG.md` round 1 | the reviewer must return valid output or block | partly |

### Clips
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| C1 | Omni **made up off-camera lines** (4 clips) | `providers.json ruling_2026_10_03_no_invented_speech` | the prompt says nobody else speaks (done). The words check flags extra speech | partly (prompt fixed in PR 140; check to fix) |
| C2 | **Clips stopped before the line ended** ("Use all three", "Literally", "Guaranteed"). 4 CUT_OFF | `omni-ledger.json` verdicts · `decisions.json → add_lines, trim_line` · listen: "guaranteed" clipped | plan each clip's length from the line's real spoken length plus a margin, and remake if the last word isn't heard | not built ("to fix"). Today the length comes from the storyboard window (`omni_clips.py` ~l.662) and CUT_OFF is only recorded |
| C3 | **Lips moving with no words** (8 stretches) | `edit-map.json → covers` (24 covers) | `clip_qc.py` already measures it, but `omni_clips.make_call` only files the result and never remakes or blocks | not built ("to fix") |
| C4 | **Words burned into a clip** ("So how long?") | `edit_map.py FIXES` (hard-coded G16-C1-2) | read the frames for text after each clip and remake | not built ("to fix") |
| C5 | Hook openings used to be made by hand at the edit | `EDIT-STANDARD.md` §8 | the planner makes one opening clip per hook in the brief | partly (made for Nova, G01-H2…H6. On the merged copy, `storyboard_plan.py` l.901 plans only the hook's text and `omni_clips.py` has no hook planning, so the hook-clip code sits only in the main folder's uncommitted work) |
| C9 | **Much of the clip line is uncommitted:** `omni_clips.py` is untracked in the main folder, and `run.py`, `storyboard_plan.py` and `providers.json` are modified there but not merged | `git status` in `the workspace` | merge it | partly |
| C6 | The automatic face and eye checks are unreliable. The lineup by eye is the real check | THE-CHAIN.md "face lock" pt 4 | — (ruled: no new automated check) | built (as a manual step) |
| C7 | A scene that has to continue can't redraw a last frame from the approved picture | `EDIT-STANDARD.md` "Open" | tested, waiting on his yes | not built |
| C8 | The run record still says `clip_model: seedance_2_5` | `the three-doctors run…/run.json` | write the ruled route into the run record | not built |

### Sound
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| A1 | No sound effects are made. The storyboard's SFX layer is empty for Nova (`sfx: 0`) | `edit-map.json` | an SFX bank, and the edit lays cues | not built |
| A2 | A short gap between "they'll" and "Literally" needed word patches in the cloned voice (by hand) | `decisions.json → audio_patches, add_lines` | fixed upstream by C2 and W6 | partly |

### Edit
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| D1 | **No render from the edit map.** `run.py`, `versions.py`, `compose.py` and `assemble.py` (the HyperFrames line) never read `edit-map.json`. Only `sweep.py` and `listen.py` do | `grep edit-map` → only sweep, listen, tests | an edit-map → mp4 render (one per hook), then `feed_video.py` | **not built (the biggest block)** |
| D2 | **The timeline page is built by a session's scratch script**, not by the repo | `scratchpad/build_editmap.py` reads `edit-map.json` and draws the player, option pops and caption looks | move the timeline page into `video-edit/machine` | not built |
| D3 | Ad-specific fixes are hard-coded in the machine (`FIXES = {"G16-C1-2": …}`) | `video-edit/machine/edit_map.py` l.40 | move them into the run's `decisions.json` | not built |
| D4 | the owner's caption choice (`ig-fb-native`) isn't carried into `edit-map.json`, which still shows the storyboard's lowercase TikTok look | `decisions.json → captions` vs `edit-map.json → captions` | `edit_map.py` reads `decisions.json → captions` | partly (it shows on the page only) |
| D5 | B-roll is still chosen by a person: 2.4 s of S9 and 0.7 s of S36 are left uncovered. Hydroquinone has no clean faceless shot | `edit-map.json → notes` · `decisions.json → failed_solution_source` | a B-roll bank per product and per failed solution | not built |
| D6 | A lip-synced line runs past G22-C1-2's end (133.0 s) and needs a cover | `edit-map.json → notes` | see C2 | to fix |
| D7 | The video-edit `CLAUDE.md` and `README.md` don't mention the edit-map line (edit_map, sweep, listen) at all | `tools/video-edit/CLAUDE.md` | one front door for the edit | not built |
| D8 | The edit's upstream log (§8) isn't joined to the chain's fix log. `CHAIN-FIXES.md` says "Nothing open" while §8 has 12 rows marked to fix | `tools/video-teardown/CHAIN-FIXES.md` l.77 | one log | not built |
| D9 | `learn` doesn't write `learned.json` by itself | `video-edit/CLAUDE.md` "Not built yet" | — | not built |

### Variations
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| V1 | Hook versions exist only as edit maps; there's no finished file per hook | D1 | the render, one per `edit-map-<hook>.json` | not built |
| V2 | Headlines and scroll stoppers have no video lane. `ad-variations` plans and makes nothing ("Production is a later component") | `components/ad-variations/README.md` | the variation plan feeds the brief's hooks and headline layer | not built |
| V3 | Cutdowns (15/30/60) exist only on the old cut-sheet line | `video-edit/machine/versions.py` | carry them over to the edit-map render | not built |

### Naming · delivery folder · Meta
| # | What goes wrong | Evidence | Fix | Status |
|---|---|---|---|---|
| N1 | `feed_video.py` looks for `work/final.mp4` or a hand-off's `returned/`. The edit-map line makes neither, so a video can't reach `1-check/video/` | `meta-upload/feed_video.py` header | the render writes the master where `feed_video.py` looks, named | not built |
| N2 | No delivery folder per variation (one card per hook version) | — | one card per version, or one unit with several videos (`upload.py` allows a unit) | not built |
| N3 | The card's words are empty unless a `words.json` exists (see W8) | `feed_video.py` | — | partly |
| N5 | **Hook versions are stranded even on the old line.** `render` writes them to `deliverable/versions/`, but the hand-off and `feed_video.py` file only the master as asset-01 | `video-edit/machine/run.py` l.505, 538 · `handoff_run.py` l.281 · `feed_video.py` l.60 | one card per version | not built |
| N6 | Two naming forms: version files use the old 13-part name, the master uses the 29 Sep short form | `video-edit/machine/versions.py` l.181–203 vs `handoff_run.py` l.276 | versions use `components/naming` short form | not built |
| N7 | `feed_video.py` needs a hand-off folder in the lab and loads a lab script | `feed_video.py` l.31 · `handoff_run.py` | read straight from the edit run | partly |
| N8 | The ad-handoff gate (copy, links, Drive bytes) runs on image drops only; video skips it | `components/ad-handoff/handoff.py` | the card check covers it, or the gate runs on video too | partly |
| N9 | A video ad has never been validated or gone live through the API, although the code exists (`meta.py` uploads video, `upload.py` builds the video ad) | `meta-upload/GO-LIVE.md` | one dry-run validate of a video card | not built |
| N4 | No first live video go yet for the Prizm Labs app ("Left: … first go") | memory: *role-tools* (1 Oct) | — | not built |

---

## 4 · To print ads end to end: what each build unblocks

Ordered by the money and time it saves per ad.

| # | Build | What it unblocks | Saves (Nova numbers) |
|---|---|---|---|
| 1 | **Edit map → mp4 render**, one per hook, named, into `1-check/video/` (D1, V1, N1, N2) | the first ad that goes all the way to Meta. Every hook becomes a launchable ad | the line itself; nothing reaches Meta without it |
| 2 | **Brief held to the swipe's length ±20%** (W1) | shorter clips, edit and review | clips about $__ → **about $__** |
| 3 | **Brief names B-roll; production pulls it; no clips under B-roll** (W2, W7, T1, D5) | an edit with no hand-finding | clip seconds that get covered anyway; hours of hand-picking |
| 4 | **Clip checks that remake: last word heard, lips without words, burned-in text, invented speech** (C1–C4) | no covers or patches needed in the edit | Nova needed 24 covers, 3 voice patches and 1 punch-in |
| 5 | **Picture and voice spend logged** (P1, E1) | a real per-ad cost on the $__ target | about $__ of pictures plus the voices are invisible today |
| 6 | **Brief writing rules: third person for brand promises, native pops not paper cards, inserts must earn it, swipe-only text** (W3–W6) | fewer of the owner's edit rounds | 4 of his round-5 calls |
| 7 | **Timeline page and per-ad fixes moved into the machine** (D2, D3, D4, D7) | any session or teammate can run the edit; nothing lives only in a scratch folder | time and lost work |
| 8 | **Video words (primary text, headline) written with the brief** (W8, N3) | cards that pass their check | — |
| 9 | **SFX bank** (A1) | a fully dressed cut | — |
| 10 | **One fix log** (D8) and a refreshed `ROADMAP.md` (W9) | the chain improving from every edit | — |

**The $__ math** (`EDIT-STANDARD.md` §9):
- About 22 pictures at roughly $__ = **$__**.
- Clips at the swipe's length, about 100 billed seconds × $__ = **$__**.
- Hooks, 5 × about $__ = **$__**.
- That comes to **about $__**, plus voices (not yet logged).
