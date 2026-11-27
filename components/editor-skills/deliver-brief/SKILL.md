---
name: deliver-brief
description: Deliver a finished brief — uploads the finished videos or pictures to the brand's delivered folder on Google Drive under the brief's own folder, writes DELIVERED.md, and confirms the path. Trigger when the editor says "deliver", "deliver this", "deliver brief <id>", "I'm done", or "upload the finals".
---

# Deliver a brief

*Made 1 Oct 2026 from step 7 of the Pull-briefs prompt v2. After delivery nothing else is the editor's job: every hour the delivery is renamed to the naming standard and put on the owner's approval page; nothing reaches Meta until the owner approves it.*

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

`briefs/QUEUE.md` in the brand's briefs folder is the work queue — every brief, who it is for (the `For` column) and its state; the brief packages sit beside it (`ai-video-production/<brief>.zip` for video, `image/<brief>.zip` for pictures, `carousel/<brief>.zip` for carousels). Deliveries go to `briefs/delivered/<brief>/` — one folder per brief.

## 7. DELIVER
- Upload the finished files to `briefs/delivered/<brief>/` in the {BRAND} folder on Google Drive, named `<brief>--<what>--v1.<ext>`. Never into the source package. `<brief>` is the brief exactly as the queue's Brief column shows it (for example `crush brief-0003`); if that says "no number yet", use the old code beside it.
- Write `briefs/delivered/<brief>/DELIVERED.md`: what was delivered, what was rerolled and why, what is still open for the owner to rule on, in that order, plain lines.
- Confirm to me with the Drive path. The queue picks it up from the folder — you do not edit QUEUE.md.
- If the brief came from a session that never ran pull-briefs, ask which brand and which brief before uploading anything.
- Deliver only finished files: the final 9:16 masters (video) or the final pictures (static) — not working clips, not the source package.

Rules, always:
- Nothing invented. If the brief does not say it, say "not in the brief" and ask.
- Every identity visible in a frame carries its reference. A person or product generated without their reference is a reroll, not a delivery.
- When Drive or GitHub cannot be reached, say which door failed, in one line, and wait.
