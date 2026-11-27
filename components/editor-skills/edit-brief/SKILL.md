---
name: edit-brief
description: Edit a pulled brief inside Higgsfield with our edit kit — writes the cut sheet, listens to every clip, cuts to the sound, burns captions and cards, punch-ins and frame fixes, checks the 4:5 safe zone and loudness, makes the one 9:16 master, then hands to delivery with the editor's "why it works" note. Trigger when the editor says "edit this brief", "edit it", "cut it", "make the master", or "edit brief <id>".
---

# Edit a brief

*Made 2 Oct 2026. The edit runs on our own tools, pulled from the public Prizm Labs repo into Higgsfield's sandbox: the editor decides, the tools do the cutting. It picks up where pull-briefs stops (review and asks done, the `<brief>--edit` folder made) and ends where deliver-brief starts.*

## The two brand folders (Google Drive, shared drive "Shared Assets")

| Brand | Briefs folder (the queue, the packages, `claims/`) | Deliver into |
|---|---|---|
| Brand A | https://drive.google.com/drive/folders/1-WlAVOrbhwCdroRk02LrWWxToHQyCuY9 | https://drive.google.com/drive/folders/142iy3AZe0AedKHbq55Mr0biJ9GFplzbR |
| Brand B | https://drive.google.com/drive/folders/1LEXFnXIL3Z2cXW7YSZzEZojhIJky4y0M | https://drive.google.com/drive/folders/1bLLYR3OMbXP6zo3U-9IiWlprqe3tCnAj |

## Video briefs: the hand-off folders (from 17 Nov 2026; this overrides the queue and the zips for video)

| Brand | Video hand-offs (one folder per numbered brief) |
|---|---|
| Brand A | https://drive.google.com/drive/folders/1nkOhgco7bSBb86MMz175FnoPnl1sPDTf |
| Brand B | https://drive.google.com/drive/folders/1JIkj3RRHBoFMVAsdPXIv0Pb9FaV_zltL |

- Every video brief is a folder `Shared Assets/runs/handoffs/video-editor/<brand>/<brief key>/`, e.g. `Brand A_flex-face-brush_brief-0333`. Only folders named `…_brief-NNNN` are briefs; a folder starting with `_` is set aside.
- A brief is **open** while its `returned/` folder is empty, **back** once it holds a file.
- In the folder: `BRIEF.md` (the ad), `RUN.md` (how to make each piece, step by step), `CLIPS.md` (every clip to make, its recipe and the exact file name to return), `ELEMENTS.md` (cast, sets and props to build first), `TIMELINE.html` (the ad on its clock), `edit/<key>.premiere.xml` (the Premiere timeline), `hyperframes/` (the same timeline in HyperFrames), `voice/` or `song/`, `refs/<clip>/`, `made/`.
- **Deliver into that folder's `returned/`**: each clip as named in `CLIPS.md`, then the cut as `<brief key>-control.mp4` (hooks `<brief key>-v1.mp4` …). Nothing goes to `briefs/delivered/` for video.
- On a machine with this repo, `python components/video-edit/open_brief.py list <brand>` lists them and `open <number> premiere|hyperframes` opens one.

Deliveries go to `briefs/delivered/<brief>/` — one folder per brief.

Editing session on {BRAND}, brief {BRIEF}. Do these in order; stop and show me at every ⏸.

## How the tools run (read once)
- The tools are `tools/video-edit-kit/edit.py` in https://github.com/the owner/prizm-labs. Run them with `sandbox_exec`. The sandbox already has ffmpeg, Python, Pillow, faster-whisper and the caption fonts.
- The sandbox is wiped seconds after each call. So every call does the whole job in one command: fetch the kit, fetch the clips, run, upload what it made. Start every command with:
  `git clone -q --depth 1 --filter=blob:none --sparse https://github.com/the owner/prizm-labs kit && git -C kit sparse-checkout set tools/video-edit-kit tools/video-edit/frame-control && K=kit/tools/video-edit-kit/edit.py`
- Clips come in by link: a Higgsfield generation's URL, or a Drive file as `https://drive.google.com/uc?export=download&id=<file id>`. If a link will not download, bring it into Higgsfield with `media_import_url` and use that URL.
- Anything I need to see (the master, the contact sheet) goes out the same way every time: call `media_upload` first, add `curl -f -X PUT --upload-file <file> '<upload url>'` to the end of the same command, then `media_confirm` after it returns 200. Show me the confirmed link.
- A run longer than a minute goes with `background: true`; read its log with a second call.
- Show me what the tools print — the tables, as they are. Do not summarise them away.

## 1. SYNC — always first
- If pull-briefs ran on this brief in this session, carry on from its `<brief>--edit` folder and say so in one line.
- If it did not, ask which brand and which brief, then do pull-briefs steps 3 GET THE PACKAGE, 4 REVIEW and 5 THE ASKS first, with their stops. Never edit a brief nobody reviewed.
- Run `python3 $K doctor` and show me the table in one block.

## 2. THE CUT SHEET
Write `cut.json` from the brief's `CUT-SHEET.md` (or THE INTENDED SHAPE in the handoff):
- `scenes` — every clip in the handoff's scene order, the approved rerolls in place of what they replaced. A clip with nobody talking gets `"talks": false` and the seconds to use. A plate (card, receipt, end card) is a `still` with its `hold`.
- `line` — each talking scene's words exactly as the script writes them, so the captions use the script's spelling.
- `overlays` — the hook and every card in the handoff's exact words and line breaks. The hook goes `"with"` the first scene so it is on screen from frame one.
- `captions` — `bold-highlight` unless the handoff names another look.
Anything the handoff lists as not made yet (a plate, a sound, a figure waiting on a ruling) is left out and named.
⏸ Show me the cut sheet as a table: scene · clip · words · overlay. I approve it or change it.

## 3. LISTEN
Run `python3 $K listen` on every talking clip.
- A clip marked **CUT OFF** stops the edit for that clip. Its line runs into the last frame, so it goes back to production to be made again — never edited around. Name it, and what it should say to the end.
- Every pause of 0.35 s or more is numbered (P1, P2 …) with its length and where it sits. Breaths are shorter and always stay.
⏸ Stop. Play me each numbered pause in context and I say which ones stay because they land a beat. Those go into that scene's `"keep"`.

## 4. CUT AND DRESS
Run `python3 $K run cut.json --out-dir out --name <brief>` (add `--anyway` only if I asked for a review cut with a cut-off clip in it). It does, in order: cut to the sound (start and end silence out, breaths kept, the pauses I did not keep cut, a 7% punch-in after each cut pause, every clip levelled to match) → words → captions and cards → master → safe-zone check → final checks.
Upload the master and the safe-zone contact sheet. Show me both and the check table.
Then the fixes, each one a rerun of the same command with one change:
- Punch-ins on a moment that needs weight: add its seconds on the rough cut's clock to `"punches"` in the cut sheet (for example `[[12.4, 13.6]]`) — they go in before the captions, so the words never zoom.
- A clip that stutters (AI clips are often 24 fps padded to 30): `python3 $K frame clean <in> <out>`. A join that jumps: `python3 $K frame seams <a> <b>`. These two need `pip install -q numpy 'opencv-python-headless<5'` in the same command.
- A pause to put back or take out: change the scene's `"keep"` and run again.
⏸ Stop. I watch it and say what changes.

## 5. THE FINAL GATE
Every row of the check table passes, or I have said why it does not:
- 9:16, 1080×1920. Never black. −14 LUFS with peaks at or under −1 dBTP.
- Every word on screen inside the centred 4:5 band. Faces and the product inside it too — read the contact sheet: anything that matters above or below the red lines fails. A scene that fails gets rerolled with the subject pulled in, not cropped later.
- Dead air: a row here is a pause someone chose to keep. Say which one it is.
⏸ Show me the final table and the master link.

## 6. WHY IT WORKS — then deliver
Ask me, one at a time, and write down my answers in my words:
1. What stops the scroll in the first three seconds?
2. What keeps people watching through the middle?
3. Where does the offer land, and why does it land there?
4. What would you change if you made it again?
Then say "deliver" and the deliver-brief skill takes over. The master goes up as `<brief>--master--v1.mp4`. In `briefs/delivered/<brief>/DELIVERED.md`, after what deliver-brief writes, add a section `## Why it works` with my four answers as they were said.

Rules, always:
- Nothing invented. If the brief does not say it, say "not in the brief" and ask.
- Every identity visible in a frame carries its reference. A person or product generated without their reference is a reroll, not a delivery.
- Hard cuts only. 9:16 only. Type is always a layer on top, never generated into a clip.
- A tool that fails: show me its last lines and stop. Never patch around it by hand.
- When Drive or GitHub cannot be reached, say which door failed, in one line, and wait.
