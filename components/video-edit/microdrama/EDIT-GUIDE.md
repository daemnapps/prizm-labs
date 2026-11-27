# Micro-drama edit: the guide (built on the Part 1 edit of "The Forehead", 2026-11-27)

The station after Higgsfield Drama Ads in the micro-drama workflow (`components/WORKFLOWS.md`, "Micro-drama workflow · video").
It takes the accepted scene clips and returns finished, captioned versions ready for `meta-upload`. It never remakes a
clip. A scene that is missing or wrong goes back to the drama lane (a paid remake needs the owner's go on its quote).

Run it end to end:

    python3 components/video-edit/microdrama/microdrama_edit.py build <edit.json> --out runs/video-edit/<brand>/<label>

`edit.json` is the cut list (shape at the bottom). The tool does steps 3 to 8 below. Steps 1, 2 and 9 are a person's or
the line's.

## The rules of the format (direction only)

1. **Start right before the person speaks, end right after the last word.** A scene opens about a third of a second
   before its first spoken word and closes about a third after its last. Long run-in and run-out are the main thing that
   makes a drama feel slow on a feed. Reaction beats that carry the story (a hand taking a note, someone walking out)
   are kept by naming an explicit in or out for that scene.
2. **Open on the conflict.** The first scene opens on the line that starts the trouble, not on the room.
3. **Cut dead space inside a scene too.** A silence longer than about 0.8 s between two spoken words is shortened to a
   short beat (about 0.55 s). The tool cuts in the middle of the silence, so no word is touched.
4. **A scene whose picture is wrong is cut out whole.** If the cast looks different (head size, outfit, face), the scene
   comes out. Do not keep its audio over other footage.
5. **Never leave stray frames at a join.** A join must not land a few frames after a shot change: the viewer sees one
   frame of the next or previous shot. The tool finds shot changes by frame difference and moves the in and out away
   from them. Check every join on screen, frame by frame, before approving.
6. **Open each hook on a clear face.** A hook that starts on the back of someone's head, or a shot that has not
   settled, fails. Start on the first frame where the face is fully in view.
7. **Captions go on in the same pass, never as a later step.** One look for the brand (Brand A: Proxima Nova Semibold,
   white, thin black edge, sentence case, three to four words, one fixed lower-third position for the whole video).
   Timed to the words actually heard in the final cut, with brand words in capitals (FLEX) and names kept as written.
8. **Sound is native.** The scene audio carries the voices. No music or added sounds unless the brief asks. No replacement voices.
9. **The ending.** The last spoken beat is the series line ("Watch Part Two"); the first clip of the next part runs as
   picture under it when it exists (wait for it rather than ship without), then a plain end card. Nothing more is said after it.
10. **Versions.** The regular cut, plus the hooks the owner picks, each a short opening taken from the body (a reaction,
    a key line) laid in front of the regular cut. A hook plays whole, starts on a clear face, and goes straight into the cut.

## The steps

| # | Step | Who | Check |
|---|---|---|---|
| 1 | Confirm each accepted scene file (the final take, not an earlier one) | person | picture and sound present, 9:16 |
| 2 | Write `edit.json` (order, scenes to drop, hook picks, ending) | person or session | none |
| 3 | Hear every scene: word timings from the scene's own audio | tool | every scripted line found |
| 4 | Find shot changes in every scene | tool | list printed |
| 5 | Set in and out from the words (rule 1), move them off shot changes (rule 5) | tool | printed per scene |
| 6 | Shorten silences inside scenes (rule 3) | tool | printed per cut |
| 7 | Build the HyperFrames project: scenes, captions, end card, hooks | tool | `hyperframes check` passes |
| 8 | Render every version and read the sound back (every line present, in order) | tool | line list printed |
| 9 | Look at every join and every caption position; listen end to end | person or session | no stray frame, no caption on a mouth |

Always open the result in HyperFrames in Claude's browser pane for the owner; never the desktop app.

## Lessons from Part 1 (so they are not repeated)

- Captions left off "until later" were missed; they belong in the first full pass.
- Trimming only the ends of scenes is not the edit: the pauses inside scenes are dead space too.
- A render of scene files re-timed from generated video can show one wrong frame at a join; check frames at every join.
- A generated clip's frame rate can differ from the project's (30 against 24); the tool re-times every piece to the project's rate.
- A paid remake needs the owner's go on the quote; the lane record opens only after that.
- A model refusal on a scene is not retried blindly: change what the scene asks for, or try another model, with a new quote.

## `edit.json`

    {"fps": 24, "caption_font": "<path to a woff2, optional>",
     "end_card": {"lines": ["What did he do instead?", "Watch Part 2."], "secs": 2.5},
     "clips": [{"id": "k1", "file": "<path>", "label": "Mom brushes his hair"},
               {"id": "k2", "file": "<path>", "drop": true},
               {"id": "k8", "file": "<path>", "tail_to": 13.0},
               {"id": "k10", "file": "<path>", "lead": 0.68}],
     "hooks": [{"name": "doctor-hook", "clip": "k7", "from": 1.375, "to": 5.208}]}

Per clip: `ranges` (explicit `[[in, out], ...]` when a scene repeats a line or has a bad stretch; the tool then uses exactly those), `lead` and `tail` (seconds, defaults 0.33 and 0.35), `in` / `out` or `tail_to` to force a point, `drop`, `keep_pauses`.
