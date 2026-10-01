# video-edit

Turns an approved kit — voice, A-roll, B-roll, music, sound effects — into the
finished captioned video, with two stops for review: the timeline, then the
captions. No timeline software, no editor.

    python3 machine/run.py start <kit-folder> --brand <brand> --label <label> --dry-run   # check, spend nothing
    python3 machine/run.py start <kit-folder> --brand <brand> --label <label>             # runs to the next stop
    python3 machine/run.py change  <run> timeline "bring the cutaway in later" --why "it covered her face"
    python3 machine/run.py approve <run> timeline
    python3 machine/run.py status  <run>

Rules, files and what is not built yet: CLAUDE.md. The page: context/artifacts.md.

## Frame control

`frame-control/` — the editor's kit: `framectl.py` (clean, lastframe, seams, bridge, retime and the music-video moves), `FRAME-CONTROL.md` (what each move fixes, the knobs, local vs Higgsfield), `MOTION-VOCABULARY.md`, and `breakdowns/` (three AI reels reverse-engineered frame by frame).
