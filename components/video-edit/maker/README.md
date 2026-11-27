# video-edit/maker — the hand-off from video-production into video-edit

    python3 components/video-edit/maker/maker_pack.py <production> [--productions <dir>] [--no-drive]

One production in (`<productions>/<production>/`: `brief.json` with the scene order, picks, style and lane, and
`scenes/<scene>/<pick>.json` with each scene's steps and what it made); the video-editor hand-off out, at
`runs/handoffs/video-editor/<brand>/<brief key>/` and the same path under `Shared Assets/`:
`TIMELINE.html`, `BRIEF.md`, `CLIPS.md` + `clips.json`, `ELEMENTS.md`, `made/`, `voice/`, `song/`, `refs/<clip>/`,
the Premiere timeline and HyperFrames project (`maker_editfiles.py`), the standard run sheet (`RUN.md`, `run.json`,
through `components/briefs/runsheet.py`) and `returned/`. Then `components/video-edit/handoff_check.py` runs over it
and its result is in the record. Spends nothing.

Moved here from the Video Studio on 2026-11-17 (owner: the chains run on their own; the Studio only shows them and
calls this). The Studio's `maker_*.py` files now forward to these. Carried with the move: blank scenes left out,
spent `RUN-SHEET-MISSING.txt` / `DRIVE-NOTE.txt` cleared after success, the checklist run at the end.

Where a production lives: `--productions`, else `VIDEO_PRODUCTIONS`, else `VIDEO_STUDIO_DATA/briefs`, else
`runs/video-studio/briefs` here (`maker_settings.py`). Proven 2026-11-17: production `idea-13` (brief 0332) built
from here gives the same BRIEF.md, CLIPS.md, clips.json, ELEMENTS.md and TIMELINE.html as the Studio's copy; checks
25/25.

Open: `machine/editor_handoff.py` (the 2026-10-27 builder from a video-production run) writes another layout into
the same folder. Two builders for one hand-off is a card to merge them.

## The scene packet (2026-11-25, VIDEO-RULINGS V59)

`scene_packet.py` runs inside the build and over any finished folder (`python3 components/video-edit/maker/scene_packet.py
<folder> [--check]`). Every clip of every format gets the same packet: its people's sheets, the product's casting sheet,
its place, props and look as files in `refs/<clip>/`, read from that shot's own `subjects` record in the brief, plus one
start-picture prompt and one clip prompt naming each file by number. The run sheet's steps carry the same files and words.
A clip with a person, product or words missing says NOT READY and `handoff_check.py` holds the pack. Before this only song
ads attached them; every other ad named them (0333: the product's sheet was in the folder and on no clip).
