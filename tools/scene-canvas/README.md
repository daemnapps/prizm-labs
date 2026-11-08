# scene-canvas — the Video Studio

One place to make a video ad: the storyboard, the production of each scene, the edit, the versions and the approval card, under one menu that always names the brand, the ad and the stage.

## Run it

```
python3 tools/scene-canvas/scene_canvas.py serve --port 8922      # the Video Studio, http://127.0.0.1:8922
python3 tools/scene-canvas/scene_canvas.py run <brief> <scene>    # remake one scene alone
python3 tools/scene-canvas/scene_canvas.py package <brief>        # the production package for HyperFrames
python3 tools/scene-canvas/seed_from_brief.py <idea>              # a storyboard idea -> a production (never a second one)
```

## Stages

| Tab | What it shows |
|---|---|
| Storyboard | the storyboard board (`SCENE_CANVAS_BOARD`) |
| Production | one node per scene, its steps, every take, and for every AI shot the reference, prompt, model and the takes thrown out |
| Edit | the cut in HyperFrames, run locally, one button per version |
| Versions | every finished version |
| Approve | the ad's approval card (`SCENE_CANVAS_APPROVE`) |

Phones get the same tabs behind a drawer; Edit opens on the computer only.

## Settings, not paths

| Setting | Default |
|---|---|
| `SCENE_CANVAS_DATA` (holds `briefs/` and `sources/`) | `runs/scene-canvas/` |
| `SCENE_CANVAS_DRIVE` (a synced folder of your own library clips) | none; clips come from the brand's own folder |
| `SCENE_CANVAS_BOARD`, `SCENE_CANVAS_APPROVE`, `SCENE_CANVAS_STUDIO` | `127.0.0.1` ports 8914, 8795, 8922 |
| `SCENE_CANVAS_BOARD_DATA` (the storyboard board's `matrix.json`, `owner-edits/`) | `runs/storyboard/` |

Keys come through `components/keys/loader.py`. Brands come from `brands/`: a brand with a `meta/account.json` shows in the menu, under its `label`.

## A brief's own files (data, in `briefs/<brief>/`)

- `brief.json`: scene order, the take each scene uses (`picks`), the storyboard idea, caption spellings (`spell`), the narrator's name (`voice_name`).
- `scenes/<scene>/take-N.json`: one workflow per take; every step's tool, model, prompt, seed, source, in/out, crop, sound and caption.
- `music/suno.json`: the music sheet `suno_bed.py` cuts to the edit (takes, lane, beat grid, cue sheet, EQ).
- A brief's own cut scripts (a shot table, its hook openings) live with the brief, never in this folder.

## AI shots

`gen_ref.py` makes every AI shot one way, from the Generative Model House: a real reference frame → still → clip → phone pass. Every run is recorded on the shot's recipe and shown under "How it was made". Pictures go through `tools/image-production` and its referencing rules.
