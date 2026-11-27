# video-studio

**video-studio** — the owner's view of a video ad being made: the storyboard, each scene's production, the edit, the
versions, the covers and the approval card under one menu (http://127.0.0.1:8922). It makes production's pieces
(shots, AI clips, voices, the product layer) and shows the edit; **it does no editing of its own** (owner,
2026-11-21: Video Edit does the work, the Studio is the view). Every edit stage runs
`components/video-edit/machine/studio/`; the same-name files here forward there.

**Owner:** the owner (engine and definitions both).
**Definitions + curator:** the owner — the stage switches now live with Video Edit (`edit-stage.json`, `cover-stage.json`).
**Runs by:** person.
**The plane it emits:** each production's folder under `VIDEO_STUDIO_DATA/briefs/<production>/` (brief, scenes,
takes, voice, music, the renders and covers made through Video Edit); a delivery writes `DELIVERY.md` +
`delivery.json` there. **Manifest per entry:** none.

Deliver a production end to end: `python3 components/video-edit/machine/run.py deliver <production>`
(`components/video-edit/DELIVER.md`). How the Studio works: `README.md`, `PRODUCT-LAYER.md`.

## Clip tools: one door (2026-11-25)

`higgsfield/clip_tools.py list|plan|make` with `higgsfield/tools.json`: fix part of a clip, carry it on, change the light, a new
camera on the same moment, another language. `plan` is free and says the words, seconds and credits; `make` asks
for the live quote first (a `--cap` is optional), goes through the spend guard, buys only the broken seconds and sets them back on their exact frames with
the clip's own sound. Rows with engine "ours" (colour, sharpen, sound effects, cut-out, versions, swipe edit, reframe) are refused
by name: our own tool does them free. A wrong clip is fixed here before it is made again. Tests: `higgsfield/test_clip_tools.py`.

## The Drama Ads lane (2026-11-27)

`higgsfield/drama_lane.py models|open|check|request`: the micro-drama workflow's lane. `open` writes `lane.json` only on
the owner's go on a quote, with ONE clip model (Seedance 2.5 480p by default, Wan 3.0 priced beside it and picked at the owner's go, from the
`micro-drama` playbook's `clip_models`); `check <film> go|sheets|setups|takes` holds each paid stage; `request` checks
one outgoing clip against the lane; `decide` files a kept take finding through the decision layer (the quote is the only stop). Stations: `components/video-production/formats/playbooks/micro-drama.json`.
Tests: `higgsfield/test_drama_lane.py`.

Order input and production-context contract: `../video-writing/CREATIVE-INPUTS.md`.
