---
name: video-edit
description: Hand any finished production to Video Edit and get the delivery back — every version (control and hooks), levelled, covered, on one card on the approval page. Format does not matter. Use whenever someone says "edit this video", "edit <production or brief>", "deliver <brief>", "send it to video edit", "finish the edit", "cut this kit", "cut the video machine run", "where is the edit at", "status on the cut", or names a Studio production, a production run, a hand-off folder or a kit.
---

# Video edit

> **Activates component:** `components/video-edit` — `machine/run.py deliver <what>` (the one door, 2026-11-21).

## The one door: hand it over, get the delivery

```
python3 components/video-edit/machine/run.py deliver <what> --dry-run     # which road, what is due; runs nothing
python3 components/video-edit/machine/run.py deliver <what>               # straight through to the card
python3 components/video-edit/machine/run.py deliver <what> --no-file     # everything but the approval card
```

`<what>` is a Video Studio production (as the Studio lists it: `idea-36`, `0332`, or its brief number), a
video-production run folder, a video-editor hand-off folder, or a kit folder. The door picks the road
(`machine/deliver_any.py`), runs it with no stops, and writes `DELIVERY.md` + `delivery.json` beside the work.

- The edit only assembles what production made. When production is not finished (shots, voice, AI shots, a song),
  the delivery is HELD and names what production owes; never make a picture, clip, voice or line from here.
- A held delivery: fix what it names at its source (the production step, the brief), then run `deliver` again.
- Nothing goes to Meta. The card waits in `meta/<brand>/1-check/video/` for the owner's Approve.
- Report to the owner in one line: delivered (the card) or held (the one reason). The Studio screen shows each
  stage as it runs, so he can watch it there.

The older doors below still work and are what `deliver` runs inside.


External dependencies: `components/video-edit/` (the machine; `looks/bank.json` the caption looks, `looks/transitions.json` the transitions, `learned.json` what the owner has taught the cut), `components/video-production/` (a production run is the usual source of a kit), HyperFrames (the render engine, installed on this Mac).

Read `components/video-edit/CLAUDE.md` and `EDIT-STANDARD.md` for the active doors and rules before editing.
A finished AI production run enters `python3 components/video-edit/machine/line.py <run>`;
a named beat-cut decision uses `machine/beat_cut.py` (or `line.py` with `decisions.json.beat_cut`).
A creator/founder return enters `delivery.py --ingest-filming <handoff-folder>` first, then the kit door below.
These doors share the existing renderer; do not convert a human filming assignment into AI generation.

**Kit door: `from-run · start · approve · change · status`.**

```
python3 components/video-edit/machine/run.py from-run <video-production-run-folder>                      # the join: writes the kit from a production run
python3 components/video-edit/machine/run.py start <kit-folder> --brand <brand> --label <label> --dry-run
python3 components/video-edit/machine/run.py start <kit-folder> --brand <brand> --label <label>
python3 components/video-edit/machine/run.py approve <run-folder> timeline [--note "…"]
python3 components/video-edit/machine/run.py approve <run-folder> captions [--note "…"]
python3 components/video-edit/machine/run.py status <run-folder>
```

- `--brand` and `--label` are required. There is no default brand.
- **`--dry-run` checks everything and renders nothing.** Do it first.
- The run stops twice: **STOP 1 — the timeline** (dead space out), then
  **STOP 2 — the captions**. `approve` moves it on. A change at either stop
  is the `recut` skill (timeline) or the `caption-look` skill (captions):
  `change` records the ask and reopens the stop; the cut sheet gets a NEW
  version, never a regeneration.
- `--cut auto` uses the mechanical cut instead of the model's; the model is
  on by default (it decides only where B-roll and on-screen text go).

## The Brief Editing Board — a brief's cut, scene by scene, for the video editor

When the video editor (or the owner) says "open the board for <brief>", "edit <brief>", "swap scene 3", "show me the
cut for <brief>", or a brief's footage ledger points here: start the `brief-board` launch entry (port 8916; never
publish it) and open `http://localhost:8916/<brand>/<brief folder>/`. The person works on the page; Claude runs it.

- Each swap or trim on the page is already a new cut-sheet version with its reason (`components/video-edit/CLAUDE.md`,
  "The Brief Editing Board"). Never edit a board-written sheet by hand; make the change on the page or through
  its `swap` / `trim` actions, so the change log stays whole.
- A regen request on the page (`runs/video-edit/<brand>/<brief>/regen-requests.jsonl`, status "waiting for the owner's
  yes") is paid. Bring the owner the scene and its price in one line and wait. Only on his yes for that run: a production
  run's scene goes through the `remake-clip` skill; a scene with no production run goes through `video-production`.
  Mark the row's status with what was done.
- The board's preview is a draft; the master comes from the edit line.

## The rules the command enforces — do not work around any of them

1. **The model decides, the sheet records, the machine executes, the owner
   approves.** The cut sheet is the one file that IS the edit.
2. **A talking clip keeps its own sound.** A separate voice file over a
   talking clip is refused as two voices. More than one frame of lip slip is
   HELD.
3. **Dead air is cut ON the clip** — picture and sound together, a breath
   each side. Punch-ins follow the swipe or an explicit edit decision; automatic alternate-cut punch-ins are retired. B-roll hides the rest.
4. **B-roll is placed by the WORDS it covers**, never by seconds. B-roll with
   nothing under it is refused.
5. **A headline that opens the video is there on frame one** and lives
   exactly as long as the clip under it.
6. **Nothing unapproved reaches the edit.** A clip without `approved: true`,
   or with no roll label, is refused at `gather`.
7. **Nothing renders red.** The gate names the field: a hole in the picture,
   a trim past the source, a caption inside the safe zone, a look or
   transition not on its list, a cut with no `why`.
8. **Text is a layer, never a generation.** A caption look is a setting;
   switching it never re-edits the footage.
9. **The editing rules are checks, not taste:** nothing moves in a straight
   line; never a lone fade; exits twice as fast as entrances; one loud colour
   per frame; no frozen stills; captions 2–4 words, one highlight, inside the
   safe zone; a sound effect lands two frames early; music 18 dB under the voice.
10. **The approved read is never touched** — levelling is done on a copy.

## Not built yet — say so plainly if asked

`match-swipe` caption looks · 4:5 and 1:1 outputs · the contrast check ·
the Drive copy and the naming gate at `file` · the learn step writing
`learned.json` by itself · music and sound-effect stations upstream.

## What comes back

`runs/video-edit/<brand>/<label>/` — `kit/`, `run.json`, every
`cutsheet-vN.json`, `changes.jsonl`, `timeline.html` (the page he sees at
each stop, with the rough cut or the captioned cut in it), `deliverable/`;
the video to the same path on Drive. The shared page is "The Format
Frontier → The edit" (`components/video-edit/context/artifacts.md`).

Report: which stop it is waiting at, the clip count and running time, and
the timeline page link.

Reply with the result and the folder it landed in (repo path or Drive folder name).
