# moves: the creative machine

**moves** takes a scene and the music under it and pitches **three ways to
move it**: one safe, one bold, one wild. Transitions, cuts, objects flying
between shots, things popping in, the camera, time, breaking the frame, type,
and syncing to the sound. Built 2026-09-26 for Lost & Found, on the owner's word:
*"I want some type of Creative machine running in here… the whole point I
want to establish in the system is the ability to create and do anything."*
The first example he gave: after the bandeja, a 3D padel ball rockets at the
lens so viewers flinch (`ball-at-the-lens`).

## The steps

index → shortlist → prompt → options → the owner picks → the build

| Step | Who | What |
|---|---|---|
| index | Claude keeps it | `library/moves-v1-damon.json`: 89 moves in 9 families, same versioned-library pattern as image-edit's fixes/variations. Each has what you see, a real reference (or "house move"), the music event that fires it, how our machine builds it, the cost, a wow score (1–3), and what makes it look cheap. A changed row is a new file (`-v2-damon.json`); new moves get added to the current one. |
| shortlist | the machine | `machine/suggest.py` reads the project's loop, the kick and bass files and the 3D catalogue, and writes the 8 best candidate moves per scene, scored by plain rules (the music in that bar, the scene's kind, the objects in it). No API, no cost. |
| prompt | Claude | `prompts/creative-director-v1-damon.md`, word for word, once per scene, on the shortlist. |
| options | Claude | `out/<project>-options-vN-damon.md`: 3 options per scene, each with the move ids, the exact second and beat it fires, what you see and feel, how it's built, the cost, what to watch for. |
| pick | **the owner** | He chooses. Nothing is built or generated before he does. |
| build | the machine | The picked moves go to the edit (ffmpeg), Blender (objects, see `components/objects/`), or Higgsfield (paid, only with his OK). |

## One command

    python3 machine/suggest.py [<project>]     # default productions/music-video

Writes `out/<project>-moves.json` and `.md`. Then Claude runs the prompt on
it and writes the options file.

## Rules

- **Report options; the owner decides.** No ranking, no "go with this".
- **No clip used twice.** Face first, then experience. Him in motion at the
  centre. Real and AI side by side so you can't tell the difference.
- **Left-handed:** racket and the one pink wristband on his **left**, which
  is the right of the frame when he faces camera.
- **Cheapest generation that does the job, then finish on the Mac.** Paid
  steps are proposals until he says yes.
- **No slop tells:** melting or swapped hands, floating feet, objects
  changing between cuts.
- **Real references only.** If we aren't sure where a move is known from,
  it says "house move".
- **Times come from the song files** (`song/crsl/kicks.json`, `bass.json`).
  Snares aren't measured yet, so nothing is timed to one.
- **The prompt is kept verbatim.** A change to it is a new version (`-v2-damon`).
