# components/creative-controls — the dials, and the names behind them

**creative-controls** — answers **how far a piece goes, and what that is called**: one set of dials
(intensity, valence, absurdity, humor, specificity, dramatisation, swap depth, edge, realism,
ad-likeness, stopping power, relevance, rhyme, anchorage, borrowedness, plus the film and picture
dials), a named emotion bank, the techniques that turn a dial up, five guards, presets, and the
glossary of what practitioners and researchers actually call each move. It does not **write** an ad:
chains bind its slice; its reader measures an ad that already exists.

the owner, 2026-10-23: *"standardize this for copy, video, and images in terms of the different types of
controls we have creatively on them ... a real-time matrix of creativity, and we can turn things up and
down ... similar to how we have model house ... the nomenclature, the literature, the language that is
used at a fundamental level to describe what we are actually doing."* Default stance: absurd, maxed out,
hyper-specific.

## The rule for every chain

- A chain binds `slices/controls.md` as `{creative_controls}` and never restates a dial, a level or
  a technique in its own prompt. The dials change in `controls.json`, then `creative_controls.py render`.
- The delivery dials in `components/marketing-doctrine/delivery.json` (humor kind, delivery style,
  register, pacing) say how a piece **sounds**; these say how **far** it goes. The humor dial here
  points at the delivery dial's humor values and never copies them.
- A level the chain aims for comes from `target(preset, brand, medium)`: every dial's default, the
  preset on top, then any level the owner saved on the Creative Controls page.

## The four new-resident questions

- **Engine + owner:** `creative_controls.py` (library + renderer; stdlib, no credential) and `read.py`
  (the reader; Gemini through `GEMINI_API_KEY` by name). Owner the owner.
- **Definitions + curator:** `controls.json` (dials, emotions, techniques, guards, interactions,
  presets), `glossary.json` (the literature), `prompts/read-controls-v1-owner.md`. Curator the owner.
  The research behind them is in `research/`, every claim tagged checked or not.
- **Plane:** `read.py` writes `runs/creative-controls/<brand>/<label>/scores.json` (every asset: its
  level and reason per dial, emotion, techniques, standout). Saved page levels are synced to
  `runs/creative-controls/<brand>/levels.json`. Runs filer: none yet; the Creative Controls page reads
  the scores.
- **Manifest per entry:** every dial, emotion, technique, preset and glossary term carries `status`
  (draft / approved / deprecated); every dial names its `media` (copy · video · image).
- **Runs by:** both.

## Who uses it

- `components/image-teardown` stage 3 v4 (reads the swipe's levels with `read.py one`, sets ours) and
  stage 6 v9 (carries them into the picture). `run.py --controls <preset>` picks the preset.
- `components/copywriter`: stage 1 read v4 (measures the source on every copy dial), stage 5 hooks v7 (never sterile, reads cold, one idea with the picture), the ad-words set copy-set v3 (`machine/copy_set.py`); `machine/copy.py` `controls()` binds the slice.
- The video chain: ruling V33 in `components/video-production/VIDEO-RULINGS.md`; the station changes are listed by the video-system sync.

## The story layer (2026-10-28)

the owner, 2026-10-28: *"amplify creative storytelling abilities, conversion, amplification, dramatization ... take this
all the way to the edge"* — ethically. `controls.json` carries `arcs` (18 story shapes, each with beats, why it works,
how it runs in a short ad and in a song ad, and the awareness it fits), `story_devices` (27 tension, character, emotion
and payoff switches), `persuasion_triggers` (13, each with how far to push and the line), `edge_line` (push / never)
and `story_interactions`. All `draft`. They render into `slices/controls.md` (copy, pictures) and into the video
writing's own block (`video-writing/machine/writing_v2.py` `story_lines`). Page: Story Playbook,
https://claude.ai/artifact/EXBgTv6LTtE2LsmD1HCixF, built by `page/build_story_page.py` (mirror
`context/STORY-PLAYBOOK-owner.md`). Sources are named per row from the literature, not yet opened and checked.
`research/arc-evidence.json` (2026-11-26, `draft`) holds outside evidence on which arcs sell and which are consumed most, keyed to
these arc ids, brand-free (films, books, ad studies, vendor format reports; each row names its source and strength). Read by
`components/winners/shapes.py`, which ranks every brand's own winners by arc.

## Story presets (2026-11-21)

Owner direction 2026-11-21: formats, then presets of those formats; a preset picked and filled by our chain with our
research and dials is how any creative is written at volume. `story_presets.json` (a manifest, every entry `draft`,
brand-free) is the preset layer between a format and the writing; `story_presets.py` builds and reads it.

- **Five shelves**, each row saying what OURS is for it or that we have none (a gap, never a coined name):
  `presets` — the 47 Higgsfield Drama Ads cards as our structured version (beats at % marks, product entry and how it
  shows, cast roles, tone and sound, captions, length, the arc and devices from the story layer, the format links to
  `video-production/formats/names.json` and the element bank's look); `shots` — the 80 slash recipes (still,
  product motion, person effect; model and settings); `formats` — every format their workflows make (34) with our
  production/script format or tool; `looks` — 110 named looks (drama, short drama, music cards, what-if, faceless);
  `galleries` — the live galleries counted but not yet captured (Marketing Studio 649, Viral 87, Soul 33, Genjutsu
  styles 20, Genjutsu motion, Katana, Shorts Studio).
- **Captured text stays data** (workspace rule 8): the capture is `components/workflow-teardown/sources/higgsfield/`;
  `build` re-reads it and keeps the curated fields (`status`, `state`, `arc`, `arc_why`, `notes`). Arcs were picked by
  the session (`state: arc-picked-by-session`) for the curator to correct.
- **Our nine checks** (`CHECKS`, our wording of the drama script review: hook in 3 s, obvious in 5, on screen,
  exposition, agency, mute test, ending, physics, clean) ride in every preset block; `check_brief` runs the mechanical
  half on a written brief as notes, never a hold.
- **Public surface:** `load`, `get`, `ids`, `pick`, `block`, `check_lines`, `check_brief`. Read by
  `video-writing/machine/writing_v2.py` (`--preset`) and `scratch.py` (`--preset`).

      python3 components/creative-controls/story_presets.py list | show <id> | pick --format <f> | build [--check]
      /usr/bin/python3 components/creative-controls/test_story_presets.py

## Page

Creative Controls — https://claude.ai/artifact/XRDxT6HRWkPi6HbQTzYcHi (the gap by source, every dial
shown low against high with real pictures, the sliders, how it runs, the glossary). Recorded in
`components/image-teardown/context/artifacts.md`; mirror `components/image-teardown/context/CREATIVE-CONTROLS-owner.md`.

## Commands

    python3 components/creative-controls/creative_controls.py render [--check]
    python3 components/creative-controls/read.py <brand> <label> <manifest.json>
    python3 components/creative-controls/read.py one <picture> <out.json>
    python3 components/creative-controls/page/build_page.py <brand> <label> <thumb-dir> [example asset id]
    python3 components/creative-controls/test_creative_controls.py
