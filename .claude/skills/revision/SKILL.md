---
name: revision
description: Make only the changes the owner asked for on one piece — his feedback note (typed words, general or exact, or a Tella recording) goes in; a new version of just the stage files it touches comes out, with before and after, the diff and why, tied to his words. The chain is never run again. Use when someone says "revise this", "apply my feedback", "run the revisions", "revise the new notes", "do my notes on this teardown / brief / ad / email", "use the revision", or after notes are saved in the Studio's feedback box.
---

# revision: his feedback, only those shifts

The Studio's feedback box on every piece saves notes to `runs/studio-feedback/<brand>/feedback.jsonl`. This step
reads a note and changes only what it asks for, in the file that owns that thing. Nothing reruns.

## Steps

1. **Which notes.** `python3 components/revision/revise.py list --brand <brand>` lists the notes still new.
2. **Revise.** `python3 components/revision/revise.py run --brand <brand> --note <id>` (or `--all-new`).
   - Two Sonnet passes (the "first drafts" row of `components/job-meter/model-map.json`; never the top tier):
     route (split his feedback into asks, pick the owning file per `components/revision/owners.json`), then edit
     (find-and-replace on only those files). His exact words go in as written; a general note is applied with the
     smallest change in his direction.
   - It writes a proposal: `runs/revision/<brand>/<revision id>/` with `why.md`, `diff.patch`, `before/`, `after/`,
     `record.json` and both prompts and replies. The live files are not touched. The note is marked `revised`.
   - `--dry-run` writes the record only and leaves the note new.
3. **Checks** run on every revision: his exact words are all in; the owner's locked lines are still in the brief
   (video-writing's owner-words check); the free script check, before and after (report only). A held revision shows
   why and gets no "Use this".
4. **Use it** (his click in the Studio, or `revise.py use --brand <brand> --note <id>`): the new files go in place,
   each old one kept as `<name>.before-rev-<id>.md`; then the stage check runs on the piece. It refuses if the live
   file moved on since the revision was made: revise again.
5. **The chain learns from it** (on Use this, never on a proposal): every kept edit and the lesson behind each ask
   go into the chain's own learnings loop (`components/run-kit/run_kit/learnings.py`). A lesson he states as a
   standing rule ("always", "never again", "last time I'm saying this") is in force at once; any other lesson, and
   each kept edit, is a candidate that goes in force when the same change shows in a second run. Lessons are written
   brand-free unless they only hold for one brand. Every later run is handed the rules in force at its station:
   `writing` (video writing), `copy` (copywriter, emails), `video` (production), `image`. His own words stay in his
   own node, never in the shared store. A revision he never uses teaches nothing.
6. **Report** in one line and point to the piece in the Studio, where each note shows its before and after.

## Rules

- Only what he asked. No tidying, no other lines.
- Anything that needs money (new footage, clips, a voice) is listed and stops at the quote, as the chain does.
- The video chain's code (video-teardown, video-writing) is called, never edited.
- The nightly run (`revise.py run --brand <brand> --all-new`) is on the job meter's private list; it only proposes.
