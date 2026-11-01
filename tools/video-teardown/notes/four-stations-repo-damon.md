# The Four Stations — in the repo (2026-09-30)

Mirror of **The Four Stations** artifact ((team page)), tab *repo · In the repo*.
One command runs it all: `tools/video-teardown/machine/run.py`.

| Station | Step | Folder | Running now |
|---|---|---|---|
| 1 Teardown | T0 | `tools/video-teardown/prompts/stage-0-triage/` | triage v2 |
| | T1 | `components/audio-teardown/` (called by `machine/transcript.py`) | words · voice cards · music, effects, mix |
| | T2 | `prompts/stage-1-teardown/` + `machine/deepen.py` | teardown v14 |
| | T3 | `prompts/stage-1c-doctrine/` | doctrine v4 (changed 30 Sep) |
| | T4 | `prompts/stage-2-replication/` | replication v4 |
| 2 Writing (still in `tools/video-teardown/`; moves to `tools/copywriter/`) | W1 | `prompts/stage-1b-audience/` | audience v10 |
| | W2 | `prompts/stage-3-injection/` | injection v18 |
| | W3–W9 | `prompts/stage-4-loop/4a…4g/` | read v4 · hooks v18 · placement v13 · expansion v17 · close v11 · audit v7 · spice v5 |
| | W10 | `prompts/stage-5-brief/` · `stage-5m-swipe-match/` · `stage-5n-manifest/` | creator v27 · AI v19 (changed 30 Sep) |
| | W11 | `prompts/stage-7b-page/` | her page v7 (changed 30 Sep) |
| | W12 | `prompts/stage-8-profile/` | profile v2 |
| | Social | `tools/copywriter/prompts/` | its own stages 0–9 |
| 3 Production | | `tools/video-production/machine/run.py start` | gates, voice, stills, clips, editor pack |
| | | `prompts/stage-6-frames/` | retired 30 Sep — never runs |
| 4 Editing | | `the team notes/video-edit/machine/run.py from-run` | cut, the owner's two stops, render |

## Changed 30 Sep
- Route lock — `machine/run.py`, `machine/test_route_lock.py`
- Teardown brand-free — `machine/run.py` (`brand_free_list`), doctrine v4, `machine/test_brand_free_teardown.py`
- Reading reads the run's own brand — `machine/extra-stages.json`
- No more frames; swipe file link in every brief — `machine/run.py`, creator brief v27, AI brief v19, her page v7
- Spice reaches her as HOW TO SAY IT — creator brief v27, her page v7
- My Feeds' Tear down asks the route — `components/swipe-organic/desk.html`, `desk.py`, `briefs.py`

## Next steps — state
1. Frames out, swipe link in — done 30 Sep
2. Spice as her notes — done 30 Sep
3. Copywriter side by side — waiting; goes with the move
4. My Feeds asks the route — done 30 Sep
5. File moves — waiting; two other sessions changed the machine within 20 minutes on 30 Sep, so not a quiet window

The creator brief still prints the AI notice word for word ("The AI images in this brief show framing and mood…"), though no images are made now; left as a promise about her likeness.
