# motion — how every AI clip gets its movement

The motion chain. Every AI clip's movement goes through here, every time, before any paid take (ruled 2026-11-12):
real footage of the same action is found, tracked, read as body mechanics, rehearsed in 3D by the real skeletons with
the real camera, then measured and looked at; the chain **decides by itself** whether the motion passes or is held,
and the finished take is checked against the reference beat by beat. **Nobody approves anything** (ruled 2026-11-12:
"the tool needs to be completely agnostic"): a person's override exists and is recorded, and nothing waits for it.

Runs by: both

## The four new-resident questions

- **Engine + owner.** `motion_chain.py` (the one door) over `finder.py`, `motion.py` + `people.py` (the tracker),
  `read.py`, `measure.py`, `retarget.py`, `blocking_blender.py`, `match.py`, `board.py`, and the fallback
  `motion_program.py`. Owner: the owner.
- **Definitions + curator.** `prompts/motion-who.md` (who is who), `prompts/motion-read.md` (the motion read) and
  `prompts/motion-program.md` (the fallback's blocking writer); the measures and their floors in `measure.py`; the pass
  marks in `match.py`. Curator: the owner. `status: draft`.
- **The plane it emits.** None of its own. Everything is written into the caller's scene folder, `<scene>/motion/`
  (a production's `scenes/<scene>/<take>/motion/`), and shown through the caller's board (`motion_chain.py rows`).
- **What the manifest declares.** `<scene>/motion/chain.json`: per stage `name`, `ok` (true / false / null = waiting),
  `short`, `detail`, `file`, `at`.

## The one door

Other components reach motion only through `motion_chain.py`:

| Call | What it does |
|---|---|
| `prepare(scene_dir, take, brand, framemap, source, spans, clip, only)` / `motion_chain.py run <scene dir> ...` | runs the stages for a scene |
| `who(scene_dir, {"A1": "NAME", "B1": "extra"})` / `motion_chain.py who <scene dir> A1=NAME B1=extra` | a person's correction of who is who (`who.json`, wins over the model's read); rehearses, previews and decides again (an earlier pass or override does not carry over) |
| `decide(scene_dir)` / `motion_chain.py decide` | the chain's own decision: passed, or held with the reasons, from the rehearsal's rows, the watcher and the start picture's rows. `prepare` ends with it; nobody is asked |
| `ready(scene_dir)` | for the moment a take is made: the motion decided, the start picture made from the rehearsal's first frame and checked against it (made again when it does not match). `video-studio/take.py scene <scene dir>` runs it, the take and the take's check in one go |
| `approve(scene_dir, by)` / `motion_chain.py approve` | an override, recorded (who, when, what it overrode); it does not carry over when the motion changes |
| `for_take(take, dry_run)` | the take as it may be made: motion that passed its checks (or a recorded override) in, held or never-checked motion refused with the reason, the take's own start picture checked against the first frame, the motion read's beats in as `mechanics`, written shot sizes out when the camera was tracked |
| `photoreal_refs(take, frame0)` | a photoreal start picture's references: the scene's filed 3D set print (take.json `set_print`, printed from the rehearsal's camera with the cast's face board) leads, the stand-in frame only places people; without one the picture door (GATE-4) refuses it |
| `frame_words(scene_dir)` / `motion_chain.py frame-words` | the rehearsal's first frame in words (per person: where the head sits, how much of the body the frame shows, which way they face, where each hand is), for the start picture's prompt: an image model reads words, not a grey stand-in's camera |
| `start_check(scene_dir, picture)` / `motion_chain.py start-check` | the start picture against the rehearsal's first frame: everyone there, in place, the same size in the frame (`match-start-picture.json`; exit 1 on a fail). A picture framed wider or from another side than the motion it must start is caught before a take is paid for |
| `picture_held(scene_dir, picture)` | wired into `for_take` and `motion_program.first_frame`: the start picture's prompt opens with `frame_words`, the made picture runs `start_check`, and a picture that fails holds the picture step and any take from it (part 0 of a long scene) before a paid call |
| `check(scene_dir, clip, name)` / `motion_chain.py check` | a finished take against the reference |
| `rows(production)` / `motion_chain.py rows` / `board.py` | every scene's stages and match rows, in the Checks panel's shape (`board.py` loads on its own, by path) |

`components/video-studio/take.py` (`motion_in`) and `gen_ref.py` (`motion_clip`) call this door and nothing else makes
motion. `components/video-studio/motion.py`, `motion_program.py` and `blocking_blender.py` are forwards to the files here.

## Stages and files (all under `<scene>/motion/`)

| Stage | Tool | Writes |
|---|---|---|
| find | `finder.py` | `candidates.json`: own footage (asset-index `search`), the swipe's shots (frame map), a web search list. A web candidate is downloaded only by `finder.py yes <scene> <n> --by <name>` |
| track | `motion.py` + `people.py` | `ref.mp4`, `ref.json`, `read.mp4`, `pose.json` (with each body's 3D `world` points), `camera.json`, `skeleton.mp4`, `overlay.mp4`, `sheet.jpg`, `motion.json` |
| read | `read.py` | two looks at the tagged clip: who is who (`motion-who.sent.json` / `.answer.json`), then the mechanics with the track under our names (`motion-read.sent.json` / `.answer.json`); `motion-read.json`, `labelled.mp4`. A person's `who.json` wins over the first look |
| build | `build.py` | `build.json`: each cast member's chest, waist and hips (shares of torso length) measured off the front view of their cast sheet, else read from their look; `match-build.json` (rows `build · NAME`), `build-lineup.png` |
| rehearse | `retarget.py` → `blocking_blender.py` | `rehearsal/spec.json`, `rehearsal/blocking.mp4`, `rehearsal/skeleton.mp4`, `rehearsal/pose.json` |
| preview | `motion_chain.py` + `match.py` + `watch.py` | `preview.mp4`, `preview.jpg`, `match-rehearsal.json` (rows, with `held_by`), `verdict.json` (the watcher: `motion-watch.sent.json` / `.answer.json` kept) |
| decide | `motion_chain.py` | `motion.json` `status` (`approved` = passed, or `held`), `decided` (`ok` = the checks alone, `passed` = the checks or a standing override, `held`, `checked`, `picture`), `take_motion.approved` / `.held`; `chain.json` rows "Motion checks" ("passed", "held: <reason>", or "held, overridden by <name>") and "Start picture" |
| check | `match.py` | `match-<name>.json`, the take's own track in `match-<name>/` |

## Rules

- **What each kind of motion is held to.** A rehearsal from real footage (`real-skeleton`) is held to the checks below,
  made against this reference and this rehearsal (each check is stamped; a stale one does not count). A shot with
  nobody in it (`camera_only`), programmed motion and a hand-built 3D blocking pass as made. A clip read but never
  rehearsed (a phone act-out or the swipe dropped on a scene) is held until the chain runs on it; the Video Studio's
  own motion buttons run the chain. The start picture is judged apart from the motion (`decided.picture`, the "Start
  picture" row): a take is checked against its own picture when it is made.
- **It decides by itself.** A fail holds the motion only where it means the take would be wrong: the beat's own move
  missing, a stand-in off its real person or the wrong size, a person who acts in a shot never followed, a shot the
  watcher says does not do its move, a start picture that does not match the first frame. Other fails are noted
  (timing read off another body, a bystander who stands still, the camera's small print). Held motion gets one more
  read and rehearsal on its own; still held, `for_take` refuses it with the reasons. A preview the watcher could not
  look at (no account answered) is decided on the measured rows alone, and `decided.checked` says so.
- **What is paid for here:** the reads (who is who, the mechanics, the watcher: three calls to the house's video
  judge, generative-model-house `behind.judge`; three more on the one retry) and, only through `ready`, the start
  picture. Tracking, the rehearsal, the preview and the match run on the machine. No take is made here.
- **Two readers find the people.** `people.py`: a crowd-trained 2D whole-body reader (RTMPose through rtmlib) finds
  everyone and keeps two bodies apart when they touch (a kiss, a hug, a lean in); MediaPipe gives each body's depth,
  read with everyone else blurred out and trusted only where it lands on that person. `motion.py setup` builds the
  reader's own Python once per machine (`MOTION_READER_HOME`, default `~/.upright/venvs/motion-pose`). Without it the
  tracker falls back to MediaPipe alone, which merges people who touch: `motion.json` `reader` says which read it.
- **Stand-ins have the cast's bodies.** Every stand-in in the rehearsal is shaped to its cast member's build
  (`build.py`): the cast sheet's front view is outlined, the arms are kept out of it, and the torso's width is read at
  the chest, waist and hips; hips a sheet gives a man past 1.12 of his chest (1.55 for a woman) are a jacket's hem or a
  skirt and are held to that. No sheet: the look's words (slim, broad, heavy...). The stand-ins are then rendered in a
  line-up and measured the same way; a body more than 15% off its sheet at any level holds the motion (`build · NAME`).
- **Measured rows are not proof by themselves.** The rehearsal is measured against the reference's own track, so
  three more checks stand beside the rows: someone the footage shows who was never followed fails the preview
  (`reference · NAME in shot N`), the rehearsal is laid over its footage joint by joint (`on the footage`, `framing`),
  and the watcher looks at the preview shot by shot (`watch.py`: is the move there, are the people placed and sized).
  Who is who is the model's word; a person may correct it (`who`), and the chain re-decides.
- **Edits are not camera moves.** A cut named from outside is moved onto the frame where the picture changes; a
  span's last frame and a half is trimmed; a sudden punch-in and a slow centred zoom with no drift or shake are marked
  as edits, left out of the rehearsal's camera and never asked of a take.
- **A download needs a name.** The finder lists; it downloads a web candidate only on `yes ... --by <name>`.
- **A take waits for nobody.** `for_take` hands over motion that passed its checks, and refuses, with the reason,
  motion they held or that never went through them.
- **Camera from the track only.** A motion with a tracked camera carries `take_motion.camera = {"from_track": true,
  "words": ...}`; `for_take` then drops the take's `shots`, `framing`, `move`, `style`, `angle`, `focus` and per-line
  `camera`. A punch-in added in the reference's edit is marked as an edit and never asked of a take.
- **A long scene is made in parts.** A reference longer than one generation (15 s of motion) is split at its own cuts,
  then at the ends of the read's beats (`segments.json`, never over the limit, never mid-move). A take names its part
  with `motion: {"scene": "<dir>", "segment": k}`; `for_take` gives it that part's seconds of the rehearsal, its beats
  and its camera, on the part's own clock. Each later part's take starts from the last frame of the take before it.
- **A model that refuses real footage still gets the motion.** The take is never sent the reference itself: it is sent
  the 3D rehearsal (grey stand-ins, nobody's face or likeness) as the motion video, its exact skeleton video as `pose`
  for a pose route, and the read's beats as words (`mechanics`).
- **The verbs are the fallback.** `motion_program.py` (walk, reach, lean...) is for a scene with no real footage of
  its action yet, and for a person the reference does not show.
- **Agnostic.** No brand, product, person or machine path in code or prompts. The brand, the frame map and the source
  come from the caller. Keys by name (`GEMINI_API_KEY`, then `GEMINI_API_KEY_PERSONAL`) through `components/keys`.
- **Needs.** ffmpeg; the reader's Python (`MOTION_PYTHON`, else the one `motion.py setup` builds, else a Python with
  MediaPipe and OpenCV); Blender for the rehearsal (`MOTION_BLENDER`, else `blender` on the path); yt-dlp for the web list.
  `MOTION_WORKSPACE` names another copy of the workspace to read neighbours' data from (the asset index; for a start
  picture it also defaults `AI_WORKSPACE` and `VIDEO_STUDIO_WRITING` to that copy). A start picture made from a
  code-only copy also needs `VIDEO_STUDIO_DATA` (where the Studio's productions are), which only the caller knows.

## Tests

`python3 -m unittest test_motion test_motion_chain` (no MediaPipe, Blender or network needed).
