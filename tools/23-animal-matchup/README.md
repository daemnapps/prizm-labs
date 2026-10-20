# animal-matchup — a proven clip in, a hit-then-music-video post out

**animal-matchup** — takes **a viral human-vs-animal clip** (one take, already proven), makes **a 9:16 post**: the
real clip plays to the hit, then the animal becomes a music video wearing the brand's clothing, with the lead
swapped into every human role. Does not **pick the clip or the outfit** — those are the owner's calls.

Built from two posts made by hand (a goat that launches a knight, a grizzly that charges a car at a gas station),
with every fix the owner called out written into the stage where it happened. Organic first: a format that wins
organically is the one that gets repurposed into ads.

## The shape of every post

| Part | What happens |
|---|---|
| Before the hit | The real clip, its own sound, the lead swapped in for the person, the animal already dressed |
| The hit | Silence breaks: the song's piano intro starts on the impact |
| The build | A multi-angle camera-move shot around the centred animal, cut on the beat |
| The drop | A DJ scratch into the track lands exactly on the hero shot's first frame (measured, never planned) |
| The end | Whole-beat hero shots, hard cut, no fade. 1080x1920, 24 fps, ~19 s |

## The cast comes first — always

Every character is cast once and every post consumes it. This tool does not describe characters in words and hope:
it attaches their pictures. It runs on `../video-production`:

- `building-the-cast.md` — "The identity carries the FACE. The text carries the CLOTHES. They never mix."
- `prompts/stage-0f-cast/` — the cast-sheet prompts: master, turnaround (front, three-quarter, profile, back),
  angles. An animal gets the same sheets; every core element (horns, ears, markings, size) must show in every view.
- `prompts/stage-5-qc/` — every take checked against the PICTURE first, never the description.
- `PLATE-CHECK.md` — nine checks on every still.
- `machine/face_lock.py` — the lead's face and eyes, frame by frame, against the master.

Why: a goat's prompts never said "horns" and never attached a sheet, and two posted shots came out hornless; a swap
copied the original person's bun onto the lead. Both are now impossible to miss: the sheet rides with every render
and every take is checked element by element.

`CAST.md` says how a cast folder looks and how a render uses it.

## Run it

1. Make the piece folder; copy `piece.template.json` to `piece.json`.
2. Walk `chain.json` stage by stage. Each stage says what to do, the tool, the prompt (in `prompts/`, verbatim
   templates) and **the check that must pass before the next stage**. Nothing is called final until every check in
   the last stage passes.
3. The machinery in `machine/`:

| Tool | Does |
|---|---|
| `person_comp.py` | pastes the swapped lead onto the dressed clip without touching the animal; anything held (hose, leash) pasted whole; clean hand-back |
| `seam.py` | splices real frames into a generated shot where the model invented something |
| `garment_grade.py` | pulls a drifted garment colour back to the master's |
| `match_grade.py` | matches a whole shot's colour to the hero shot |
| `cut.py` | cuts from piece.json, measures the hero cut, lays the song so the drop lands on it |
| `qc.py` | the checks: core elements, hair, suit side by side, scrub, zoom, pops, held frames |
| `deliver.py` | the full-size phone copy (never a preview) and a page copy |

Needs ffmpeg and Python with opencv-python and numpy.
