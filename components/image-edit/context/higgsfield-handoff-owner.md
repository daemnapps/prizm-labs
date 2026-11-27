# Designer and Editor Handoffs

Page: https://claude.ai/artifact/X6anK5J2qPT2BSwuPg1GQ7 (updated 23 Nov 2026)

One folder in, Claude makes it with you, one folder out.

## The whole job

1. **Get your brief.** the email lead posts the number, or ask Claude "what's waiting for me?"
2. **Paste one line** into Claude Code, with the brief key.
3. **OK each step.** Claude shows every picture, clip and cut before it spends or moves on.
4. **Pass the checklist.** Work lands in `returned/`, then the owner reviews.

## Paste into Claude Code

Start:
> Open the hand-off KEY. Read BRIEF.md, ELEMENTS.md and RUN.md and follow section B, step by step with make.py plan and make.py save. Put the finished work in its returned/ folder.

Finish:
> Read DELIVERY-CHECKLIST.md and REVISION.md for hand-off KEY. Fill the submission, run the delivery check, and submit when every item passes.

## What's in your folder

`runs/handoffs/<role>/<brand>/<brief key>/` (same path under Shared Assets/ on the Drive)

| File | What it is |
|---|---|
| BRIEF.md | what to make |
| ELEMENTS.md | cast, product, setting |
| RUN.md | how, step by step |
| refs/ | every reference |
| DELIVERY-CHECKLIST.md | what "done" means |
| returned/ | your finished work goes here |

- Video editor: cast → start pictures → clips → cut → cover. Timeline in TIMELINE.html, Premiere in edit/, HyperFrames in hyperframes/.
- Graphic designer: one finished image per checklist slot, in its sizes.

## File names

`<brief key>-v1.png`, `<brief key>-v2.png`, `<brief key>-control.mp4`, `<brief key>-v1.mp4`

## Done means

- Every slot on the checklist filled.
- Every video has its own cover.
- The delivery check passes.
- Changes come back as R01, R02 on the same brief.

## Don't

- Save outside returned/.
- Move or rename anything on the Drive.
- Tell Claude "go ahead with everything".
- Post anything.

## Who to ask

- the owner: the content (scenes, words, look, people, product).
- the email lead: everything else (files, queue, next brief, time, credits, access).

Set up once: Claude Code with the team workspace open, and the team key file on the laptop. Changes to words, hooks and scenes are welcome; log them against the slot they fill.
