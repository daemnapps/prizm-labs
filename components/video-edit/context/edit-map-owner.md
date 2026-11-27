# Video Edit Map (2026-11-21)

Page: https://claude.ai/artifact/NTigDR6WoxWC3d3r6rXHcY · source `edit-map-owner.html` beside this file.

Direction: Video Studio becomes a front end only (a HyperFrames view plus buttons); every edit job runs in
`components/video-edit`. This map is the state before that change. Paths are repo-relative; `VS` =
`components/video-studio/video_studio.py`. Line numbers are from the repo copy on 2026-11-21.

## Headline findings

- Eight edit jobs are implemented in both components (table below).
- The Studio on :8922 runs from an installed copy (`~/Library/Application Support/daemn/video-studio/`), not the
  repo; it differs in covers_stage, swipe_cut, to_studio, video_studio and voice_continuous, and lacks
  song_captions.py. A repo copy also runs on :8932.
- The ad-workflow song-ad playbook edit stations (`handoff`, `clips-edit`, `upscale`,
  `video-production/formats/playbooks/song-ad.json:725-798`) have `"run": ""` — no code runs the edit there.
- Studio output lands under `~/devel/daemn/board/scene-canvas/briefs/<n>/`, outside `runs/` (builder card rule 1).
- Circular reach: `video-edit/moves/machine/director.py:189,:637` puts video-studio on sys.path.
- video-studio has no CLAUDE.md and no Residents row in `components/CLAUDE.md`.

## How an edit starts (six doors)

| Door | Trigger | Path |
|---|---|---|
| A (main) | "Next step" in Studio | `canvas.html:304` → `studio.html:418` POST `/api/next/<n>` → VS:3013 `next_start` VS:1309 → detached `video_studio.py next` → `_run_next` VS:1038; stage picked by `next_due` VS:777-840 (shots, aishots, voice, cut, maker, check, render, edit, covers). cut VS:1170 (`swipe_cut.py --run`, `run_scene` VS:1723, ffmpeg); render VS:1192 (`to_studio.py` → video-edit `compose`, `hyperframes render` VS:1202, loudnorm VS:1209-1214, hooks VS:1228-1242); edit VS:1255 → `edit_stage.run` (`edit_stage.py:518`), changed `bed.json` re-queues render VS:829-831; covers VS:1286 |
| B | "Produce" / "Prepare hand-off" | POST `/api/produce` VS:3114 or `/api/handoff` VS:3009 → `seed_from_brief.py`; then door A |
| C | Studio "maker" stage | VS:1095-1141 → `video-studio/maker_pack.py` shim → `video-edit/maker/maker_pack.py`; editor opens via `video-edit/open_brief.py` (HyperFrames :200, Premiere :216); delivery back through brief-handoff → door E |
| D | Session runs `video-edit/machine/line.py` | edit_map → music_bed → sfx_make → mouths → render_map (compose, `hyperframes render` :650) → audit → watch (Gemini) → covers → deliver → `meta-upload/to_check.py` |
| E | Session runs `video-edit/machine/run.py start|handoff` | gather → cut (Opus, `prompts/stage-2-cut`) → gate → timeline → captions → export (`run.py:514-530`) → audit → checks → file → learn |
| F | Launch agent `com.daemn.studio-watchdog` (300 s) | `watchdog.py:99-102,201-203` re-posts `/api/next/<n>` → door A |

## Done twice

| Job | video-studio | video-edit |
|---|---|---|
| Cut to the swipe | `swipe_cut.py`, `run_scene` VS:1723 | `beat_cut.py`, `edit_map.py`, `run.py auto_cut` :270 (CLAUDE.md retired `swipe_cut.py` 2026-10-21) |
| Captions | `_caption_chunks` VS:1573, VS:1811-1822, `song_captions.py`, `to_studio.py:128-168` | `run.py:191-197` transcribe, `model_cut` :411 |
| Music bed | `music_bed.py` (own ElevenLabs, unused), `edit_stage.make_music` :298-337 | `machine/music_bed.py` |
| SFX | `edit_stage.py:165-180` | `sfx_make.py` |
| Render + loudness | VS:1202-1215 | `run.py:514-562`, `render_map.py:650` |
| Hook versions | VS:1228-1249 | `run.py:616` `render_versions`, `line.py --hooks` |
| Covers | `covers_stage.py` (still points at retired `thumbs.py`, :150) | `line.py` `make_covers` :468 |
| Edit screen | Edit tab (:8922, `hyperframes preview` VS:1949-1972) | Brief Editing Board (:8916) |

Already shared (Studio calls video-edit): `compose.py`, `brief_layout`, `looks`, `cut_check`, `shot_timing`,
`cover_rules`, `edit_notes`, moves director, `maker/*` (via four shims).

## Video Studio pieces

- Front end: `studio.html` (6 tabs), `canvas.html` (scene canvas), routes in `video_studio.py`, `chain_view.py`, `checks_board.py`, `settings.py`, `watchdog.py`.
- Edit logic living in Studio (to move to video-edit): next-step engine, `run_scene`, render stage, `swipe_cut.py`, `swipe_check.py`, `edit_stage.py`, `edit_moves.py` apply, `music_bed.py`, `song_captions.py`, `to_studio.py`, `layers.py`, `reply_card.py`, `covers_stage.py`.
- Production (not edit): `seed_from_brief.py`, shot lists/fill/copy/spec, `gen_ref.py`, `take*.py`, `lips.py`, `ai_shots.py`, `doors/`, voices, `sound_board.py`, `suno_bed.py`, `mic_place.py`, `product_layer.py`, `quick_variation.py`, `creator_lane.py`, `production_inject.py`.
- Pass-throughs: `maker_*.py` ×4 and `edit_notes.py` → video-edit; `motion*.py`, `blocking_blender.py` → motion.

## Video Edit pieces

- Engine (`machine/`): run.py (kit road), line.py (edit-map road), v2.py, compose.py (only HyperFrames writer), edit_map, render_map, map_sheet, assemble, audit, watch, retention, music_bed, sfx_make, learn, to_drive, brief_board (:8916), mini doors.
- Prompts: stage-1 read-pack (parked), stage-2 cut (Opus), stage-4 watch v3 (Gemini, untracked), stage-9 learn, moves creative director.
- Libraries: looks/, moves/ (89 moves), learned.json, frame-control/ (dormant), skills/ (Higgsfield notes).
- Hand-off: maker/, open_brief.py, handoff/ (stage hand-off), premiere/ bridge.
- Experiments (draw-in-code): lowpoly, cartoon, anime, stick, thread.

## After the move (same day)

All of the Studio's edit stages now run Video Edit's code (`components/video-edit/machine/studio/`); one door,
`machine/run.py deliver <what>`, runs any finished production to the approval card. Detail and proofs:
`components/video-edit/DELIVER.md`. First full delivery on a private copy of idea-36 held, correctly, at the edit
stage's own hard check: S1.2 shows the scrub on an arm where the line says legs.
