# Edit kit

The edit, as small commands. An editor's agent runs them inside **Higgsfield
Supercomputer** (its sandbox already has ffmpeg, Python, Pillow,
faster-whisper and the caption fonts), or on any laptop with Python and
ffmpeg. The editor never types a command: they say "edit this brief" and the
`edit-brief` skill runs these.

One file does the work (`edit.py`), one file holds every number
(`settings.json`), and one file lines captions up with the script's spelling
(`spelling.py`). No brand lives here: a brand arrives only through the brief.

## What it takes

A folder with the brief's clips and a **cut sheet** (`cut.json`), written
from the brief's CUT-SHEET.md. See `example-cut.json`:

```json
{
 "fps": 24,
 "scenes": [
  {"id": "s01", "clip": "scenes/01.mp4", "line": "what she says, as the script spells it"},
  {"id": "s02", "clip": "scenes/02.mp4", "keep": ["P1"]},
  {"id": "s03", "clip": "scenes/03-broll.mp4", "talks": false, "from": 0, "to": 2.5},
  {"id": "s04", "still": "cards/plate.png", "hold": 1.2}
 ],
 "overlays": [
  {"text": "LINE ONE\nLINE TWO", "with": "s01"},
  {"text": "A LABEL", "start": 8.0, "end": 10.5, "zone": "upper-third"}
 ],
 "punches": [[12.4, 13.6]],
 "captions": {"look": "bold-highlight"}
}
```

- **scenes** play in this order, hard cuts only. A talking clip is cut to its
  sound; `keep` names pauses (from `listen`) that stay because they land a beat.
  `talks: false` plays a picture as asked. `still` holds a plate.
- **overlays** are the hook and cards: the exact words and line breaks. `with`
  ties one to a scene (the hook sits on frame one for its whole first scene).
- **line** (optional) gives the script's words, so captions use its spelling.
- **punches** (optional) are extra 7% push-ins, in seconds on the rough cut's
  clock, put in before any type goes on.

## The commands

| Step | Command | What it does |
|---|---|---|
| Check the machine | `edit.py doctor` | What's installed, which steps can run |
| Listen | `edit.py listen scenes/*.mp4` | Per clip: start/end silence, breaths, pauses numbered P1, P2…, a line that runs into the clip's last frame, loudness |
| Cut to the sound | `edit.py cut cut.json --out rough.mp4` | Start/end silence out, breaths kept, pauses cut unless kept, 7% punch-in after each cut pause, every clip levelled to −16 LUFS, scenes in order |
| Words | `edit.py words rough.mp4 --out words.json --sheet cut.json` | Word timings off the sound, in the script's spelling when lines are given |
| Captions + cards | `edit.py captions rough.mp4 words.json --out captioned.mp4 --report rough.report.json` | 2–4 words at a time, the spoken word lit; the hook and cards from the sheet. Type is always a layer on top |
| Punch-ins | `edit.py punch in.mp4 --at 3.2-4.1 --out out.mp4` (or `punches` in the sheet) | Extra 7% push-ins on chosen moments, sound untouched |
| Frame fixes | `edit.py frame clean in.mp4 out.mp4` (also `seams`, `bridge`, `loopclose`, …) | Runs `../video-edit/frame-control/framectl.py`; needs `pip install numpy 'opencv-python-headless<5'` |
| Safe zone | `edit.py safezone master.mp4 --boxes captioned.boxes.json --sheet-out sheet.png` | 9:16; every word on screen and (with opencv) every face inside the centred 4:5 band; a contact sheet with the band drawn in red |
| Loudness | `edit.py loudness master.mp4` | Integrated LUFS and true peak |
| Master | `edit.py master captioned.mp4 --out master.mp4` | −14 LUFS, −1 dBTP; picture copied untouched |
| Final gate | `edit.py check master.mp4 --report rough.report.json` | 9:16 1080×1920, length, never black, mastered, no dead air (0.7 s or more) |
| All of it | `edit.py run cut.json --out-dir out` | cut → words → captions → master → safe zone → checks, one 9:16 master |

## The rules it carries (the settled edit line)

- Silence is heard in the sound (quieter than −35 dB for 0.15 s), never read off the words.
- Start and end silence: always cut. Breaths (under 0.35 s): always kept.
- Mid-clip pauses (0.35 s or more): the kit proposes cutting them and lists
  them; the editor keeps any that land a beat. A kept pause of 0.7 s or more
  shows in the final gate as dead air, so it is a choice someone made.
- After a cut pause the next piece is 7% closer — it reads like a second camera.
- A clip whose line runs into its last frame is **cut off**: the cut stops and
  the clip goes back to production. `--anyway` makes a review cut only.
- 9:16 only. Faces, product and every word sit inside the centred 4:5 band
  (the middle 1080×1350 of 1080×1920) and clear of the app's buttons.
- The master is −14 LUFS with peaks at or under −1 dBTP.

## Inside Higgsfield

The sandbox is wiped seconds after each call, so one call does everything:
fetch the kit, fetch the clips, run, upload the master.

```bash
git clone -q --depth 1 --filter=blob:none --sparse https://github.com/daemnapps/prizm-labs kit \
 && git -C kit sparse-checkout set tools/video-edit-kit tools/video-edit/frame-control \
 && mkdir -p job/scenes && cd job \
 && curl -sfL -o scenes/01.mp4 '<clip url>' && ... \
 && python3 ../kit/tools/video-edit-kit/edit.py run cut.json --out-dir out \
 && curl -f -X PUT --upload-file out/<name>--master-9x16.mp4 '<upload url>'
```

Run it with `background: true` (a 60-second piece takes well under the
15-minute lease) and read the log with a second call.
