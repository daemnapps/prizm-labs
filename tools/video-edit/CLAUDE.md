# video-edit

**video-edit** — takes **an approved kit: one voice track, A-roll and B-roll
clips, music and sound effects**, makes **the finished, captioned video**. Does
not **make, regenerate or restyle a clip, and never rewrites a line**.
Triggered by `python3 machine/run.py start <kit-folder> --brand <brand> --label <label>`
(`--dry-run` checks everything and renders nothing).
From a video-editor hand-off folder: `python3 machine/run.py handoff <folder>` — the
whole line, stopping only at the timeline and the captions (`--approve timeline|captions`
carries on), the master into the hand-off's `returned/` and take-back at the end.

**Owner:** the owner (engine and definitions both). **Definitions + curator:**
the owner — `looks/*.json` (fonts, zones, transitions, grades, platform UI,
icons) are his settings, changed by him or on his word.

**Runs by:** person — the edit-map line needs macOS Vision; not the mini for
now (2026-10-07 triage, video-edit#11 (machine installs), the owner's call taken
by the team, he is told).

**The plane it emits:** `runs/video-edit/<brand>/<label>/` — `run.json`, every
`cutsheet-vN.json`, `changes.jsonl`, `timeline.html`, `deliverable/` — and the
video to the same path on the Drive; the hand-off road also returns its master
into the hand-off folder's `returned/` and files an approval card under
`Shared Assets/meta/<brand>/1-check/video/`. **Manifest per entry:** the
settings rows in `looks/` (`bank`, `fonts`, `grades`, `icons`, `placement`,
`platform_ui`, `transitions`) each carry an `id` and a `status` from rule 6's
set — all `draft` today; the 13 registry transitions not yet installed also
carry `state: "not installed"` (with `drawn: false`, which the gate reads);
`looks/registry.json` and
`looks/retention.json` rows carry no status.

Built 2026-09-20 on the owner's word: *"I basically need to get rid of video
editors… We're going to use hyperframes… build a foundationally sound video
editing system."* It replaces the ffmpeg assembly tool in his private repo,
which is not carried over. The video machine (`tools/video-production`)
says the edit is "a separate process, deliberately out of scope here" — this is
that process.

## ONE EDIT PATH (video system sync, 2026-10-21 — C13, R5)

Two roads in, one renderer out. **`compose.py` (HyperFrames) is the only thing that draws a word, a transition or
the finish**; the cut sheet is the one shape it renders; `audit.py` checks every version of either road.

| Road in | When | The cut | Then |
|---|---|---|---|
| `machine/line.py <video-production-run>` | a finished AI production run — what the runners, the batch approval and the mini's doors use (row 16) | `edit_map.py` — the clock (every line its real sound, a take laid whole, a breath between takes), the mouths, the swipe's cuts moved into a silence, no repairs, the bank's music and SFX | `render_map.py` assembles picture + sound with ffmpeg (no words), lips held → `map_sheet.py` makes it a cut sheet → `compose.py` draws every word → `audit.py` → scan → card |
| `machine/run.py start <kit>` / `handoff` / `v2.py ad` | a kit with no production run (a hand-off, a creator's clips); the mini's v1 door passes `--cut auto` | `run.py auto_cut` on the same clock rule: a take laid whole, the cut between takes (the 2026-09-20 pause cutter only when a run names `max_pause`) | assemble → placement → `compose.py` → `audit.py` → checks |

Retired the same day: `swipe_cut.py` (a third path with no caller, last at e3054a695c), `render_map`'s PIL words
(`render_map.font`/`draw_block` now draw only a thumbnail's type), the automatic punch-in on alternate cuts, the
6% push on still-looking shots, the 60–72% mid-frame text band, the two caption registries (now `looks/bank.json`,
picked by format through `machine/looks.py`) and the two loudness tables (now `defaults.json` `sound`).
Rules every change is checked against: `../video-production/VIDEO-RULINGS.md` (V1–V20).

## The edit-map line: AI-made ads (built 3–4 Oct 2026)

    python3 machine/line.py <video-production-run> [--brief brief-NNNN] [--batch …] [--links …]

One command from a finished `tools/video-production` run to a card in Drive `meta/<brand>/1-check/video/`,
waiting for Approve: plan (`edit_map.py`) → mouths (`mouths.py`) → words heard (`listen.py`) → render with lips held
(`render_map.py`, then `compose.py` for the words) → audit (`audit.py`, every version) → scan → names + card
(`deliver.py`) → file (`meta-upload/to_check.py`). Every check stops it; the step list is `machine/steps.json` `line`.
How it runs, what each step checks, and every rule in the owner's words: **`EDIT-STANDARD.md`** (Part A runs it, Part B
is the rules). An ad's own choices live only in its `decisions.json`; text looks in `looks/edit-looks.json`, caption
looks in `looks/bank.json`, levels in `defaults.json`; nothing of one ad is in the code
(tests/test_edit_map.py `NothingOfOneAdInTheCode`).

## The principle

**The model decides, the sheet records, the machine executes, the owner approves.**
The cut sheet (`machine/cutsheet.py`) is the one file that IS the edit. Nothing
else knows what is in the video. A change is a new version of the sheet —
never a regeneration — and every change is kept with its reason.

The engine is HyperFrames (HeyGen, Apache-2.0, installed on this Mac
2026-09-20): a video is a web page with timing marks, rendered frame by frame,
so the same sheet always gives the same video. `machine/compose.py` is the only
file that knows HyperFrames exists; swap the engine and only that file changes.

## v2 — built 2026-10-18; the runners use it (batch_run.py, both mini_v2.py)

    python3 machine/v2.py ad --control <kit> --hook <kit> [--hook <kit> ...] --brand <b> --label <l>   # cut + rough preview, stops
    python3 machine/v2.py ad ... --yes          # after the yes: control once in full, each hook = its new opening joined on
    python3 machine/v2.py share <v2-run> <version>   # one share copy, picked version only, never bigger than its master
    python3 machine/v2.py clean <v2-run>             # once shipped: this run's own work/ only

Same cut, assembly, gate, compose and master as v1 (it imports run.py). What it changes: a hook renders only the
seconds where its sheet differs from the control (plus up to the next keyframe), joined onto the control's own
frames and checked frame by frame — a mismatch falls back to a full render; faces, scene reads, levelling and
transcription cached on disk in `.cache/v2`; every clip given a keyframe a second once; one render at a time;
`--crf 18` pinned; renders keyed by content (a song swap redoes only what changed); the reviewer gets the brief,
a slim sheet, frames at caption times with the words expected, and a BLOCKER/FIX holds the version; prompt
caching off. Proof run 2026-10-18 on the it-was-me control + 4 hooks: the shared notes folder's
`video-edit-v2-proof.md`.

## The steps — `machine/steps.json` is the list; the page, the runner and line.py read it

gather → cut → gate → **STOP 1 timeline** → **STOP 2 captions** → export → **audit** →
checks → file → learn. (The edit-map line's own list is `steps.json` `line`.)

the owner's order, 2026-09-20: see the timeline with the dead space out; then the
captions on; then the final export. Every change runs back through learning.

## Hard rules

- **A talking clip keeps its own sound.** That is the only thing that keeps the
  lips right (the owner, 2026-09-20, on the first proof: "the lip sync is off… the
  A-roll was already good"). A separate voice file laid over a talking clip is
  refused as two voices. The finished file is measured against the source clip
  (`machine/syncheck.py`); more than one frame of slip is HELD.
- **The cut falls between shots, never mid-breath** (V15, 2026-10-20: *"I don't want it to look mechanical
  at all"*; replaces "dead air is cut ON the clip", 2026-10-21). A talking take is laid whole, from a hair
  before its first word to a breath after its last; the pace is the format's (`defaults.json` `pace`). A
  punch-in happens only where the swipe itself pushes in — never on alternate cuts by itself.
- **B-roll over the voice read has no lips**, so its voice slice is cut freely
  and the picture runs on (`voice_cuts`). A piece with no talking clip at all
  may use one whole voice track instead.
- **B-roll is placed by the WORDS it covers**, never by seconds, so it survives
  re-timing (`covers: {"from": "is why", "to": "worked"}`).
- **A headline that opens the video is there on frame one** — no fade, no slide —
  and lives exactly as long as the clip under it (`with: <clip id>`).
- **Nothing unapproved reaches the edit.** `gather` refuses a clip without
  `approved: true`, and a clip with no roll label.
- **A-roll carries the line, B-roll covers it.** B-roll with nothing under it —
  no A-roll and no voice cut — is refused. The roll labels come from the teardown and the brief, not from here.
- **Nothing renders red.** The gate names the field: a hole in the picture, a
  trim past the source, a caption or overlay inside the safe zone, a look or
  transition that is not on its list, a cut with no `why`.
- **Text is a layer, never a generation.** Captions, hooks and the end card are
  composed on top. A caption look is a SETTING (`looks/bank.json`); switching it
  never re-edits the footage. `match-swipe` builds a one-off look from the
  teardown's caption read.
- **The editing rules are checks, not taste:** nothing moves in a straight
  line; never a lone fade; exits twice as fast as entrances; one loud colour per
  frame; no frozen stills; captions 2–4 words, one highlight, inside the safe
  zone; a sound effect lands two frames early; music 18 dB under the voice.
- **The edit only assembles** (the owner, 2026-09-23: the teardown names every element,
  the brief carries it, production makes it, the edit assembles it — "all these
  elements need to be green"). Every element in `tools/video-production/ELEMENTS.md`
  is laid by `machine/assemble.py` and drawn by `compose.py`: card · screen (per surface)
  · split · greenscreen · endcard · lower thirds · annotations · platform UI ·
  disclaimers · transitions · one grade · music · SFX · room tone. A card's, screen's
  or endcard's words must match the plan word for word; a plate, bank file or
  disclaimer that is not there is RED by name (`unmade`), never skipped.
- **Words sit in zones, in named fonts, one space apart** (the owner, 2026-09-23: safe zones,
  fonts, bubble styles, "a lot of space between words", transitions, icons — "everything in
  my repo synced with the same language and components"). Every text layer names a ZONE in
  `looks/placement.json` (never a raw height): each zone is inside the 4:5 content band and
  clear of every feed's buttons (`defaults.json → safe_zones.surfaces`, the strictest of
  `platform_surfaces`). `machine/placement.py` moves a layer off the face when production
  marks one (`subject_box` per scene) and off words already on screen, and the sheet
  records why; no box = a WARN "face-blind". Fonts are ids in `looks/fonts.json`, LOCAL
  files for a same-every-time render — `machine/fonts.py` lists and (only when run with
  `install`) fetches them; until then the fallback draws and the gate WARNS. Platform UI
  is a style row (`looks/platform_ui.json`); icons, emoji, stickers and drawn elements are
  rows in `looks/icons.json` (`machine/icons.py`, same rule); transitions are a catalogue
  with what triggers each (`looks/transitions.json`). An unknown id is RED.
- **Words never on a face or a mouth; the caption look by format** (V13, 2026-10-20; C1 settled 2026-10-21 — the
  2026-10-12 "captions stack up from the bottom" line still holds as the DEFAULT and is superseded only for a format
  with a look of its own). The look is picked by format, else by the app the piece pretends to be made in
  (`looks/bank.json` `pick`): bottom (`caption-band`) by default; edits-glow aims at the neck (38%, never lower than
  56%). Headlines and callouts sit above the subject (`top-headline`); nothing else sits mid-frame. Placement holds
  the look's height and moves a line only off a face or a mouth it reads in the picture; `audit.py` reads the
  finished frames and stops the line on a caption over a face or mouth (WORDS ON FACE / WORDS ON MOUTH).
- **Sound only when called for, laid by one table** (V14, 2026-10-20: *"Music and sound effects are only relevant
  if that's what's being called for … don't just assume"*; C10, 2026-10-21). Music, sound effects and room tone
  are laid only when the swipe or the brief calls for them (room tone: the piece's `room_tone` cue or production's
  room-tone file); a swipe that has music or SFX and a cut that has none fails the audit. When laid: music ducked
  18 dB under the voice and cut so the last frame lands on a bar; a sound effect two frames early; room tone under
  the trimmed joins and silent spans; mastered to −14 LUFS integrated, −1 dBTP — every level in `defaults.json`
  `sound`, read by both roads. Every piece of sound fades in and out over 15 ms at its edges so no join clicks, and
  the voice is never encoded below 192k AAC / 48 kHz (copies between encodes 320k, the master 256k); the audit
  holds a JOIN CLICK or a voice MUFFLED against its own source clip (E33, 2026-10-21). Production owns the voice
  itself — the edit only proves it did not dull it.
- **Disclaimers come from `brands/<brand>/brand-identity/compliance.json`, read-only**, by claim
  type and platform. A piece that makes a claim and has no file is red; the edit
  never writes one.
- **9:16 only** (the owner, 2026-09-23: "I do not want 4:5 or 1:1 videos at all"). The
  frame is 9:16 with its content in the 4:5 zone (22 Sep rule). `render` makes one
  video per hook on the same body, the 15/30/60 cutdowns (lowest priority whole
  scenes out first — a line is never cut mid-scene; priority 1 and the opener stay),
  a cover per hook (its first frame, hook text on) and names every file through
  `components/naming`. Each scene's `section` rides on the sheet as the doctrine's
  own id (`components/marketing-doctrine/frameworks.json`, read, never restated;
  the old `module` tag is only a deprecated alias — mechanism → unique-mechanism,
  cta → call-to-action — and never required). Swapping sections is a separate build.
- **The approved read is never touched** — levelling to −16 LUFS is done on a copy.
- **Tests never touch live runs** — they pass their own `--runs-root`.
- Brand-agnostic: no brand name in any code, prompt or look.

## Files

| | |
|---|---|
| `machine/run.py` | the one command: `from-run · start · approve · change · status · render` (`start --versions` renders them straight after the final) |
| `machine/line.py` · `machine/edit_map.py` · `machine/mouths.py` · `machine/listen.py` | the edit-map line: the run, the cut as a map (the clock, the swipe's cuts), the lead's mouth only moving when heard, every scripted word heard (a check; it times only an own-track line's captions) |
| `machine/render_map.py` · `machine/map_sheet.py` | the map's picture and sound assembled with ffmpeg, lips measured on it; the map turned into a cut sheet so `compose.py` draws every word |
| `machine/audit.py` | every version of either road: words cut, lips still, wrong shot, sync, words on a face or mouth on the finished frames, the swipe's music and SFX |
| `machine/looks.py` · `machine/realism.py` | the one look registry and loudness table, the pace and moves per format; the realism index's editing rows picked for a piece |
| `machine/handoff_run.py` | THE VIDEO EDITOR AS A TOOL — `run.py handoff <video-editor hand-off folder>`: finds the kit and its media (the folder, else its copy on the Drive mount), copies the kit into the run, calls `start`; at each stop writes `STATUS.md` + `status.json` (what is waiting, the preview and its Drive link, what the kit is missing, the open decisions) and mirrors the previews to `Shared Assets/runs/video-edit/…`; `--approve <stop>` carries on; at the end names the master by the short form, puts it in `returned/` (here and on the Drive) and runs take-back, and files the same master as a card in `Shared Assets/meta/<brand>/1-check/video/` for the owner's approval (components/meta-upload/feed_video.py). `--dry-run` spends nothing |
| `machine/kit_from_run.py` | THE JOIN — reads a video machine run record (every scene kind, layer, bank row, hook, naming field) and writes the edit kit; reads only, approves nothing |
| `machine/assemble.py` | lays every element the kit carries onto the cut: kind data, layers timed on the final clock, SFX, music duck + bar, room tone, disclaimers, hooks, versions |
| `machine/versions.py` | every version from one sheet: hooks, cutdowns, the file names — 9:16 only |
| `machine/syncheck.py` | are the lips in time — the finished sound measured against the talking clip it came from |
| `learned.json` | what the owner has taught the cut; the cut prompt reads it and it outranks the prompt's own rules |
| `machine/steps.json` | the declared steps |
| `machine/defaults.json` | the dials; a run's `controls.json` overrides any of them |
| `machine/cutsheet.py` | the cut sheet's shape and the gate |
| `machine/compose.py` | cut sheet → HyperFrames page (the only engine-aware file) |
| `machine/timeline_page.py` | the page the owner sees at each stop |
| `looks/bank.json` · `looks/transitions.json` · `looks/grades.json` · `looks/layers.json` | caption looks (font id, zone, word/letter spacing), the transitions catalogue (drawn: cut · whip · match · zoom · flash; punch-in is a move; 13 registry rows listed, not installed), grades, and how every layer looks — SETTINGS, brand-agnostic |
| `looks/fonts.json` · `looks/placement.json` · `looks/platform_ui.json` · `looks/icons.json` | the font library (15, open licence) · the text zones (9) · the platform-UI styles (16 over 13 kinds) · icons, emoji, stickers and drawn elements (52) — SETTINGS |
| `machine/follow.py` · `machine/spelling.py` · `machine/cutout.py` | annotations that follow the face · captions in the script's spelling · the presenter cut-out (cached) |
| `machine/placement.py` · `machine/fonts.py` · `machine/icons.py` | zones + face/crowd moves · the font fetch list and installer · the icon fetch list and installer (dry run by default; nothing downloads without `install`) |
| `prompts/stage-2-cut/` · `prompts/stage-9-learn/` | one folder per model step, `-vN-`, the highest wins; never edit in place |
| `context/artifacts.md` | its pages |
| `tests/` | the gate (every element field), caption and plate line grouping, cutdowns, hook versions, the join, the sound, the naming — `python3 -m unittest discover -s tests` |

Output: `runs/video-edit/<brand>/<label>/` — `run.json`, every `cutsheet-vN.json`,
`changes.jsonl`, `timeline.html`, `deliverable/` — and the video to the same
path on the Drive (`runs/README.md`).

## The video editor's handoff — a person or an agent makes the ad from one folder (built 2026-10-27)

    python3 handoff.py <video-production run folder> [--out DIR] [--no-drive]

the owner, Tella 2026-10-27: *"final handoff capabilities for both the team and the team"*; then *"make this name agnostic. and
the name of the folders need to be the same for both repo and drive ... briefs should come from final stages of the
chains, not some random set up"* and *"standardization is the default"*. `machine/editor_handoff.py` takes only a
production run made from the writing chain's final stage (`stages/5-brief.md`, filed at
`runs/video-writing/<brand>/<slug>/deliverable/`) whose brief number the register gives to this run; a test run
(`v2test`, `batchtest`, `dryrun`, `fw-v…`, `scratch` …) is refused by name. It reads the kit through
`kit_from_run.build` (never re-derived) and writes the Hand-off Standard's folder at
`runs/handoffs/video-editor/<brand>/<brief key>/` — `handoff.md` (the eight sections, for the role, never a person),
`manifest.json`, `briefs/<brief>/` (brief, script, edit notes), `assets/` (clips, stills, voice, music and sound),
`references/` (the swipe), `returned/` — every file named with the brief key, then copies it through gdrive-creator to
the same path below `Shared Assets/`. A folder the handoff skill staged there is never written over. The finished
videos come back into `returned/`, named `<brief key>-control.mp4`, `<brief key>-v1.mp4` …, where the delivery check
reads them. Every made clip also gets `higgsfield/<scene>/` (the owner, 2026-10-27: the video editor works in Higgsfield
Supercomputer too): `prompt.md` with the prompt word for word as sent (the clip's `clips/omni/<call>/mcp-request.json`,
else `clips/plan.json`), the model and settings, and its `IMAGE-n` / `AUDIO-1` inputs, so any scene or missing opening
can be remade there. The one front door for both lanes is `tools/image-edit/handoff.py <brief ID>`, which calls this CLI
and reads its last `link:` line. The role's job sheet: `team/handoffs/2026-10-27-video-editor-job.md`. Tests:
`tests/test_editor_handoff.py`.

## The handoff — joined 2026-09-20

`python3 machine/run.py from-run <video-production-run>` reads the production
run's own record (`plan.json` scenes, `media/<id>.mp4`, `vo/<id>.mp3`,
`verdicts.json`, `media/<id>.parity.json`) and writes the kit to
`runs/video-edit/<brand>/<label>/kit/`. A type-A to-camera scene becomes talking
A-roll; a type-B scene becomes B-roll over its voice slice. A clip is approved
only when the record says so — motion and director verdicts on file, the words
check PASS — and everything else is listed by name. The production run is never
written to. Since 2026-10-21 it also carries production's own word times (the take's
`clips/calls/<call>/transcript-words.json`, a voice slice's `vo/timing.json` words — never
transcribed again), each scene's `emphasis` (the captions' accent face), its `hands_off`
(whip/match drawn), the piece's `room_tone` cue and app. The kit route does not read the
plan's cutaways (`kit_from_run.py` notes them); the edit-map line does (`edit_map.py`,
second angles).

## The cut — the model is ON

`start` cuts with the model by default (`--cut auto` for the mechanical one).
The machine first makes the lip-safe draft — each talking take laid whole, every
word timed on the final clock — and the model (Opus, through
`components/run-kit`) only decides where B-roll and on-screen text go, reading
the brief, the roll map and `learned.json`. The prompt as sent and the reply
are saved in the run. A red sheet gets one retry with the gate's reasons; a
second red, or no model, falls back to the auto cut and the sheet says so.

## Retention, the helpers and the asset packs — built 2026-09-23

the owner, 2026-09-23: *"we're going to get this machine ultra dialed in for attention
retention and customer acquisition … we are literally programming ads for social media."*

- **Retention checks** (`machine/retention.py`, rules and every threshold in
  `looks/retention.json`): hook in 3 s · length band for the placement · static hold ·
  visual change cadence · dead air · caption-pop ↔ SFX pairing · zoom on emphasis words ·
  B-roll cadence in talking runs · words on screen within 1 s · loop-friendly ending (SSIM,
  first frame vs last). **Nothing here blocks an export** (the owner, 2026-09-23: "don't worry
  about the feed ads run 6–15 seconds or hooks lands in the first 3 seconds") — the two
  evidence-backed rules are INFO lines, the rest are WARNs with a score. Printed at the gate
  and after the final; `deliverable/retention.json` per run; the live timeline draws a
  Retention lane (flags at their seconds) and the score panel. Dials: edit the JSON, or a
  run's `controls.json → retention: {placement, dials: {<rule>: {...}}}`.
- **The helpers venv** (`.venv`, Python 3.12, gitignored; pins in `requirements-helpers.txt`;
  `machine/helpers.py setup` rebuilds it). The machine calls them as subprocesses; it is
  otherwise standard-library EXCEPT the edit-map line, which needs Pillow (render_map.py,
  sweep.py, thumbs.py import it), swiftc with the Xcode command-line tools and macOS Vision
  (thumbs.py:53-58, edit_map.py:136-137), and ElevenLabs — its two Pillow-bound test files
  skip, named, without Pillow (SI-90 (Pillow test guard)): `faces.py` (MediaPipe) tracks faces per frame → `face_track` on each clip →
  placement keeps each timed layer off the boxes seen WHILE it is up (tracking beats
  `subject_box`; a clip where the tracker sees no face falls back to `subject_box`, then
  face-blind). `beats.py` (librosa) puts the music's beats on the sheet and snaps B-roll
  covers over talking A-roll and graphic starts to the nearest beat within
  `looks/retention.json → beats.snap_tolerance_s` (talking cuts never move; a graphic never
  leaves its scene). `cutout.py` (BiRefNet) cuts the presenter out of every greenscreen `cutout`
  scene — the whole clip once, a VP9-alpha WebM cached by the PICTURE's hash in `.cache/cutout/`
  (gitignored), ≈16 s per second of video the first time on this Mac's GPU (0.17 s a frame +
  load + encode), instant after — and compose stands it on the plate while her own (unseen)
  clip carries the sound. No venv or a dry run: she shows whole and the gate WARNS. `pip` is unchanged.
- **Asset packs:** 8 GL transitions (`looks/gl-transitions/`, gl-transitions MIT; rows
  `engine: "gl"` in `looks/transitions.json`, drawn by `machine/gl_transitions.py`) ·
  44 Fluent emoji (MIT), 30 animated as seek-safe sprite strips (`icons.py install` rebuilds
  them; the PNGs are gitignored) · `confetti-burst` (canvas-confetti's physics, ISC, ported
  seek-safe in compose.py).
- **The HyperFrames registry as a bank:** `looks/registry.json` indexes all 382 blocks and
  components by id with our family (`fits`). A sheet names one in `layers.registry`; the gate
  refuses an unknown id and one not installed (`python3 machine/registry.py install <id>`).
  Installed blocks pass the gate; drawing them inside the edit is not wired yet.

## Finished 2026-09-23 ("fill in any of the partly")

- **Annotations that follow** (`machine/follow.py`): an arrow/circle/underline/highlight whose
  `target` is `"face"`/`"subject"`/`"person"` (or `{"follow": "face"}`) rides the face track
  (faces.py; a greenscreen's boxes are mapped through its layout onto the frame), else production's
  `subject_box`, as smoothed keyframes; a fixed target stays fixed. Nothing to follow → a WARN and
  a fixed anchor (`fallback`, else `center`), never red.
- **Captions in the script's spelling** (`machine/spelling.py`): the transcriber's words are
  aligned to the scene's `line` (and production's `vo/timing.json` swaps — `said_as`, `numbers`,
  carried by the join as `said`) and the SCRIPT's words are shown on the heard timings: a brand name
  heard a letter off → the brand's spelling, "twenty-nine dollars" → $29, "twenty-eight to forty" → 28 to 40. A word that will
  not align is shown as heard and WARNED (`captions.spelling`).
- **Pause review, T-3 default:** every mid-clip pause the trim cut or kept (≥ `defaults.json →
  pauses.mark_from_s`, or cut by the pace dial) is on the sheet (`pauses`) and on the live
  timeline's **Pauses** lane — length, cut or kept, click to jump and hear it. No separate stop.

## The video editor as a tool — built 2026-10-01

the owner: the human editor's job moves to visual concepts and briefing; the edit is
automated. `run.py handoff <folder>` is that: one command from a video-editor hand-off
(`lab/owner/handoff-standard`) to one 9:16 master in its `returned/`, stopping only at
the two review points in `steps.json`. It is a front door on `start`, not a second
line — every rule above applies unchanged. A master a final check HELDs never goes to
`returned/`. The talking-clip cut now stops at the clip's last frame when the word
tool times words past it (CUT-1, "cut from the sound": the clip has no sound past its
end), and says so on the sheet as a note for the owner (T-7: listen for a line cut short).

## Not built yet

`match-swipe` caption looks · registry blocks drawn inside the edit (they pass the gate once
installed) · annotations that follow a thing on screen other than the person · the contrast
check over one-second windows · the Drive copy and the naming gate at `file` · the learn step
for the cut-sheet `change` command (the timeline page's 🎬 now runs it on every render — below)
· the fonts and icons fetched (lists ready, nothing downloaded) · the registry transitions
installed · real bank files (production's music and SFX banks are indexed but few are made) ·
the slow-downs, nudges and calm inserts still in `edit_map.py` (cut_out, add_lines, close-ups, crops and
clean_baked are off the runner path since 2026-10-21 row 6 — only `edit_map.py --repairs` lays them) · the kit route
reading the plan's cutaways.

(Done since the last list: captions placed per line against the faces read on the picture,
2026-10-20/21; face boxes from production are read when there — `subject_box`, else the scene
read.)

## Added 2026-09-29 (the owner: "pull that out … sync this to the real repo now with the video edit")

- `skills/` — the video editing skills people pull into Higgsfield
  (`reframe-9x16`, `logo-swap`, `avatar-swap`, `element-swap`), indexed in
  `skills/README.md`. Image versions: `tools/image-edit/skills/`.
- `objects/`, `moves/`, `local-studio/`, `3d/` — brought over from the owner's
  private repo on his say-so, code and prompts only (clips, pictures and model
  weights stayed behind; media never goes in git). Siblings brought over the
  same day: `lab/owner/higgsfield-catalogue/` and `lab/owner/model-map/` (the
  model list the skills' model check leans on).

## Sorted 2026-09-30 (the owner: "index both image edit and video edit, and see
what actually makes sense")

Of the four folders above, only two are actually editing tools — `moves/` (89
named creative moves, now `moves/library/moves-v1-owner.json`, the same
versioned-file pattern image-edit's fixes/variations use) and the frame
kit below (now `frame-control/library/moves-v1-owner.json` too, 11 named
technical moves). `objects/`, `3d/` and `local-studio/` were production
tools with no editing logic in them — moved out to their own components,
`components/objects/`, `components/3d/`, `components/local-studio/`.
Paths inside `local-studio/` still point at where it came from in the owner's
sandbox and are fixed as it's first run here; `objects/`'s reach into `3d/`
was fixed on the move (`components/3d/make3d`, a real sibling path now).

## The timeline page closes the loop — built 2026-10-16

the owner: "with any changes we make, they need to be banked and leveraged as knowledge for chain updates and
optimizations in real time as soon as we hit render ... a fully closed loop." The Ad Editor
(`lab/owner/suite/timeline.html`, http://127.0.0.1:8880/timeline) edits any run here on one standard set of tracks.
Every save writes a new version with a line in `changes.jsonl` that names each bar, what it was and what it is now.
Every 🎬 Make the video runs `prompts/stage-9-learn/stage9-learn-v2-owner.md` over the changes since the last lesson:
every row is banked in `runs/video-edit/_lessons/lessons.jsonl` with the STAGE it teaches (edit, captions,
production-picture, production-clip, voice, brief, teardown), and edit/caption rules he stated or that are now seen
twice are promoted into `learned.json`, which the cut prompt obeys over its own rules. Lessons for upstream stages
wait in the bank; no upstream prompt reads it yet.

## Approved opening replacements (2026-10-28)

`machine/hook_edit.py` exposes `prepare(opening, root)` and `render(opening, root)`. It requires the opening workflow approval, validates control/edit/decision fingerprints, replaces only the first spoken scene, shifts later cues together and invokes the existing render_map → map_sheet → compose renderer. Outputs remain under the matching video-edit run path; `hook-edit.json` in the opening records the full cut and source fingerprints. The board edit action delegates here.
