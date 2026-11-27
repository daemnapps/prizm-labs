# Micro Drama Line

Page: https://claude.ai/artifact/9zn9JxsC67KrzXKKAgqPwa (source `micro-drama-line-owner.html` beside this file).

Any micro drama (a dialogue, live-action story ad) runs one named workflow: format `micro-drama`,
stations in `playbooks/micro-drama.json`, shown by `python3 machine/workflow.py show micro-drama`. It is the path the
first clean part 1 took, with a mechanical check after each paid step. Built 2026-11-27.

## Autonomous: the quote is the only stop (2026-11-27)

The run makes every call itself. Writing runs with `run.py <teardown> --autonomous`: every structure, hook, audit,
swipe-match and manifest hold is decided by the decision layer (`components/video-teardown/machine/decide.py`) from the
owner's past calls, filed in `runs/decisions/calls.jsonl` for him to agree with or overrule, and the run continues. A take
that fails is fixed or remade inside the lane's cap; a finding the run keeps is filed with `drama_lane.py decide`. A stuck
step is diagnosed and fixed by the session. The one stop is the quote before paid generation: both models priced, his
go names the model and opens the lane. Going live is his click on the approval page, outside the run.

Why the writing stopped before: `decide.on()` needs `VT_CHAIN=v2`, which only the mini's door set (the writing command
never did), and the house Outlier settings have had `automation.paused: true` since 2026-10-19, which turns every stage
to manual. `--autonomous` sets both for that run alone; the house settings file is not changed. The writing-v2 hook
matrix check also stopped after its one remake without ever asking the layer; it now goes to the layer like the others.

## The seven steps (15 stations)

| Step | Stations | In | Out | Check / owner stop |
|---|---|---|---|---|
| 1 Start | `swipe` | a swipe, or none | with a swipe: intake record and teardown through stage 2, the beats are the swipe's; with none: `drama_start.py preset` picks a live-action drama story preset (rotating per person) and `scratch.py --preset` makes the run, the beats are the preset's | run_check on stages 0-2 (both paths) |
| 2 Brief | `brief` | the teardown | the writing chain's accepted brief (`--autonomous`) | brief_check; holds decided by the decision layer |
| 3 Studio pack | `pack` | the brief | `runs/higgsfield/<brand>/drama-ads-<label>/pack.json`, `REQUEST.md` | NOT READY stops |
| 4 Quote and go | `price`, `go-check` | the request | both models priced, `quote.json` for his pick, `lane.json` (open) | THE ONE STOP: owner's go; `drama_lane.py check <film> go` |
| 5 Drama Ads | `sheets`, `sheets-check`, `script-plan`, `setups`, `setups-check`, `clips`, `takes`, `takes-check` | the request, the approved product casting sheet | `film/sheets.json`, `script.json`, `plan.json`, `checks.json`, `setups.json` + page, `jobs.json`, `takes.json` | `drama_lane.py check` sheets / setups / takes; `drama_lane.py request` before every send |
| 6 Edit | `edit` | accepted takes and their sound | `deliverable/` versions, `edit.json` | HyperFrames in Claude's browser pane, Gemini pacing, openings, full teaser kept |
| 7 Approval page | `meta` | finished versions | one flexible ad in 1-check, `meta-filed.json` | the run ends; going live is his click there |

## Series: planned ahead, not a step

A series is planned before part 1 is written (the parts, each part's job, one creative matrix row for all of them),
then each part runs this same workflow. A part that follows a made part is written from what that part shows on screen
and keeps its row: `recipes/drama-series-v1.md`, checked by `machine/drama_series.py check|written`.

## The clip model is one setting

`lane.json` carries `clip_model` and its Higgsfield `clip_vendor_id`, set when the lane opens
(`drama_lane.py open ... --model`). The quote, every setup, every request and every frozen job must name it, and the
clip guard (`~/.claude/hooks/clip-chain-guard.py`) lets a lane's requests through only on that model. Lanes opened
before this field keep working as before.

| | Seedance 2.5 (default) | Wan 3.0 (option, far cheaper) |
|---|---|---|
| Resolution | 480p, 9:16 | 480p, 9:16 |
| Length | 4-30 s | 2-30 s |
| References a clip | 30 images, 10 videos, 10 audio | 10 images, 5 videos, 5 audio |
| Extension | yes | none: plan every clip fresh |
| Request | `generate_audio: true` | `generate_audio: true`; no `mode` or `extension_mode` |
| Price | `get_drama_ads_config` film quote | `get_drama_ads_config` purpose stage on `wan3_0`, same drama_ads_id; both shown on every quote |

Read live from Higgsfield `models_explore` 2026-11-27. Drama Ads' own skill names Seedance only; the Wan lane runs
the same skill steps, sandbox checks and our lane checks, with the limits above.

## Dry run on the Forehead swipe (2026-11-27)

`workflow.py status micro-drama --brand Brand A --label forehead-dryrun` with the swipe's intake and teardown, part 1's
writing run, brief and film label: 15 stations listed; swipe and pack read as done from files on disk; the brief reads
not done (part 1's writing run is currently held); `run --dry-run` stops at the first station needing its receipt.
Nothing was written and nothing spent.

## Files

- `playbooks/micro-drama.json` (+ `.md`): the family, its stations, `clip_models`, failures with their runs
- `recipes/drama-series-v1.md`, `recipes/drama-camera-v1.md`: the series layer and the camera rule (the scene packet guidance stays in `micro-drama.md`)
- `machine/drama_series.py` + `machine/test_micro_drama_workflow.py`
- `components/video-studio/higgsfield/drama_lane.py` + `test_drama_lane.py`
- `components/video-writing/machine/run.py --fork-only` + `tests/test_fork_only.py`

Open: the `short-movie` playbook still lists a `micro-drama` variant; the family file now wins, so it is shadowed and
can be dropped by whoever next edits that playbook.

## Song Ad Line (2026-11-27)

`playbooks/song-ad.json`, 18 stations, rebuilt on the Higgsfield Singing Ads path brief 0376 took, with its fixes and
without its mistakes. Same rules as micro drama: autonomous, the quote the only stop, a check after every paid step.
Start (swipe or own) → writing chain `--autonomous` (one brief: the chain's accepted stage) → the song (song.py → Suno →
song gate) → cast, places, product from filed 3D prints → `hf_pack.py pack singing-ads` (now `ready`/`not_ready`;
held assets stop it) → story map (windows on the sung lines, end to end; timed 1.5-2 s shots; product mechanism in one
clip; no hug or kiss between men) → quote (story id from `ads_studio_story_recipe /singing-ads`, both models priced,
song to hear) → `drama_lane.py open --format song-ad` → sheets, setups page, clips (sound off, Seedance 480p draft),
takes (motion, identity, lyric beat, continuity, product, house rules) each checked → local Real-ESRGAN upscale → edit
(from_higgsfield cut, captioned + clean, captions = the approved lyric, openings via v2.py) → 1-check; never approve.

Found in 0376 (delivered, in 1-check): clip 7 shows two men hugging (a run override with no owner ruling); captions say
"stink" where the approved lyric says "sting"; it ran with no lane, no quote and no priced go (Codex sent the clips, and
Codex runs no Claude hooks); two brief versions. A lane left open since 2026-11-21 (brief 0339 hooks) with no model
named was closed.

