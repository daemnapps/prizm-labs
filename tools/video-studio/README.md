# Video Studio

One place to make a video ad: the storyboard, the production of each scene, the edit, the versions and the approval card, under one menu that always names the brand, the ad and the stage.

## Run it

```
python3 tools/video-studio/video_studio.py serve --port 8922      # the Video Studio, http://127.0.0.1:8922
python3 tools/video-studio/video_studio.py run <brief> <scene>    # remake one scene alone
python3 tools/video-studio/video_studio.py package <brief>        # the production package for HyperFrames
python3 tools/video-studio/seed_from_brief.py <idea>              # a storyboard idea -> a production (never a second one)
```

## One address

The Studio is the only address: it serves the storyboard board under `/board/` and the approval page under `/approve/`, and sends their own requests back to them, so a computer and a phone open one link. The apps keep running where they are (`VIDEO_STUDIO_BOARD`, `VIDEO_STUDIO_APPROVE`); nothing in them changes. The HyperFrames editor in the Edit tab still opens on its own local port.

## One ledger

Where every ad stands comes from the ledger, the Queue (`VIDEO_STUDIO_LEDGER`), in its own stage names (`components/naming/stages.json`): the Studio never keeps a stage of its own. The Studio answers `/api/productions` for the ledger to read, so an ad being built shows there at Making (Editing once it has versions), and its approval card carries it on to Approve ad, Sending to Meta and On Meta. A production made from a storyboard idea's writing run is linked to that idea by the run's name, so the board, the Studio and the ledger show one piece once.

## Stages

| Tab | What it shows |
|---|---|
| Storyboard | the storyboard board (`VIDEO_STUDIO_BOARD`) |
| Production | one node per scene, its steps, every take, and for every AI shot the reference, prompt, model and the takes thrown out |
| Edit | the cut in HyperFrames, run locally, one button per version |
| Versions | every finished version |
| Approve | the ad's approval card (`VIDEO_STUDIO_APPROVE`) |

Phones get the same tabs behind a drawer; Edit opens on the computer only.

## Settings, not paths

| Setting | Default |
|---|---|
| `VIDEO_STUDIO_DATA` (holds `briefs/` and `sources/`) | `runs/video-studio/` |
| `VIDEO_STUDIO_DRIVE` (a synced folder of your own library clips) | none; clips come from the brand's own folder |
| `VIDEO_STUDIO_BOARD`, `VIDEO_STUDIO_APPROVE`, `VIDEO_STUDIO_STUDIO` | `127.0.0.1` ports 8914, 8795, 8922 |
| `VIDEO_STUDIO_BOARD_DATA` (the storyboard board's `matrix.json`, `owner-edits/`) | `runs/storyboard/` |

Keys come through `components/keys/loader.py`. Brands come from `brands/`: a brand with a `meta/account.json` shows in the menu, under its `label`.

## A brief's own files (data, in `briefs/<brief>/`)

- `brief.json`: scene order, the take each scene uses (`picks`), the storyboard idea, caption spellings (`spell`), the narrator's name (`voice_name`).
- `scenes/<scene>/take-N.json`: one workflow per take; every step's tool, model, prompt, seed, source, in/out, crop, sound and caption.
- `music/suno.json`: the music sheet `suno_bed.py` cuts to the edit (takes, lane, beat grid, cue sheet, EQ).
- A brief's own cut scripts (a shot table, its hook openings) live with the brief, never in this folder.

## AI shots

`gen_ref.py` makes every AI shot one way, from the Generative Model House: a real reference frame → still → clip → phone pass. Every run is recorded on the shot's recipe and shown under "How it was made". Pictures go through `tools/image-production` and its referencing rules.
