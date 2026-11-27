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
| index | Claude keeps it | `library/moves-v1-owner.json`: 89 moves in 9 families, same versioned-library pattern as image-edit's fixes/variations. Each has what you see, a real reference (or "house move"), the music event that fires it, how our machine builds it, the cost, a wow score (1–3), and what makes it look cheap. A changed row is a new file (`-v2-owner.json`); new moves get added to the current one. |
| shortlist | the machine | `machine/suggest.py` reads the project's loop, the kick and bass files and the 3D catalogue, and writes the 8 best candidate moves per scene, scored by plain rules (the music in that bar, the scene's kind, the objects in it). No API, no cost. |
| prompt | Claude | `prompts/creative-director-v1-owner.md`, word for word, once per scene, on the shortlist. |
| options | Claude | `out/<project>-options-vN-owner.md`: 3 options per scene, each with the move ids, the exact second and beat it fires, what you see and feel, how it's built, the cost, what to watch for. |
| pick | **the owner** | He chooses. Nothing is built or generated before he does. |
| build | the machine | The picked moves go to the edit (ffmpeg), Blender (objects, see `components/objects/`), or Higgsfield (paid, only with his OK). |

## On the chain (2026-11-17)

Owner, 17 Nov: "we just need 1 for now then we can add more if needed with
machine decision making". Every Video Studio production now runs this at its
edit stage, with no hand pick:

    python3 machine/director.py <production folder> [--pitch rules|claude]

`machine/director.py` reads the production (scenes, shots, voice, its music
bed's beats and sections, the brief's creative-controls target), shortlists
with `suggest.py`'s scoring, has the director pitch Safe / Bold / Wild
(`prompts/creative-director-v2-owner.md`, through the chain's Claude door;
the shortlist stands in when no door answers), and keeps ONE per scene by the
pick rule written at the top of `director.py`. It writes
`<production>/edit/moves-picks.json` (+ `.md`): every pitch, the pick, its
reason, the second and music event it fires on, and every gap. The Studio lays
the pick on the next render (`components/video-studio/edit_moves.py`,
`to_studio.py`): a match or whip on a scene hand-off, a punch-in split on a
beat. What the edit lays today is `LAY` in `director.py`; a move that needs
paid generation, a drawer the edit lacks, or a shot framed in production is a
gap row on the Checks panel, never made. Owner rulings filter every pick:
clean cuts, no flash frames, no repeated clip, no dead air, every cut placed on
purpose; a card or end card is never punched in (its picture carries its
words); a move must score the rule's floor or the clean cut stays. Switch:
`components/video-studio/edit-stage.json` `director`.

The by-hand flow below (the owner picks from three) stays for the music video.
v1 of the prompt is untouched; v2 is the same director generalised for ads.

## One command

    python3 machine/suggest.py [<project>]     # default productions/music-video

Writes `out/<project>-moves.json` and `.md`. Then Claude runs the prompt on
it and writes the options file.

## Rules

- **Report options; the owner decides** on the music video. On the chain the
  director still pitches without ranking, and the pick rule decides.
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
- **The prompt is kept verbatim.** A change to it is a new version (`-v2-the owner`).
