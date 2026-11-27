# components/world-skit

**world-skit** takes **a mission file**: a world, a mission, the problem, the turn, the product moment and the close. It makes **a finished comedy skit video in that world, plus a brief for the video editor**. It does not write the swipe's teardown or run Meta uploads. Triggered by `python3 machine/variation.py plan|make|handoff <mission.json>`.

- **Engine + owner:** `machine/variation.py`, `machine/script_check.py`, `machine/check.py`, drawing through `components/video-edit/lowpoly/`. Owner the owner.
- **Definitions + curator:** `plot.json` (the slots), `worlds/*.json` (saved worlds), `context/script-lessons.md`. Curator the owner. Every entry is `status: draft`.
- **Plane:** `runs/video-edit/<brand>/<label>/` with the video mirrored to the same Drive path; hand-offs at `runs/handoffs/video-editor/<brand>/<key>/`. Filer: none yet.
- **Manifest per entry:** a world file declares its locations, look, cast, game moves, sound, voices and caps.
- **Runs by:** person.

Mission files live under `runs/world-skit/<brand>/<label>/mission.json`, since they hold brand words. `plan` spends nothing and states the cost; `make` refuses over the file's `cap_usd`. A line whose words didn't change reuses its voice.

The standing check: `check.py listen` after every render, `check.py compare` against the swipe, then a person listens. `script_check.py` runs before any render. Rules: `context/script-lessons.md`.

Tests: `python3 -m unittest discover -s tests`.
