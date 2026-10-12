# Playbook · General chain (no playbook) (`default`)

**Status:** approved · **state:** the shared chain as it runs today
**Family:** default

**Signed:** the owner 2026-10-10 — the general chain stays the fallback for any format without its own playbook: "as opposed to just having a general workflow for all ads"

Every setting here is the shared chain's own (THE-CHAIN.md, providers.json, RUN-PROTOCOL.md). null = the shared chain decides; a family playbook overrides only what it names.

*Rendered from the .json beside this page by `machine/playbook.py` — edit the .json.*

## Structural signature

| | |
|---|---|
| audio | the shared chain's own |
| speakers | the shared chain's own |
| address | the shared chain's own |
| settings | the shared chain's own |
| product_role | the shared chain's own |
| pacing | the shared chain's own |
| capture | the shared chain's own |
| story | the shared chain's own |

## Stage order

teardown → writing → elements → gates → voice → storyboard → pictures → clips → edit

## Stage settings

**audio**
- first: voice
- song_model: the shared chain's own
- voice_model: the shared chain's own

**song**
- flow: the shared chain's own
- length_s: the shared chain's own

**pictures**
- door: direct.openai
- model_key: the shared chain's own
- quality: the shared chain's own
- size: the shared chain's own
- aspect: 9:16
- fix_calls: on
- style_lock: the swipe's style row
- send_size: the shared chain's own

**clips**
- model: gemini_omni_flash_1_1
- resolution: 1080p
- seconds: 3, 10
- clips_per_picture: 1
- takes: 1
- upscale: none
- stills_allowed: off
- short_clip: the shared chain's own

**cast**
- reuse: per-brand cast bank first
- recurring: off

**hooks**
- shape: hooks as format fills (writing station 2.2)

**captions**
- look: the swipe's own caption look (style.caption)

**gates**
- apply: all 13 (run.py start)
- skip: 

**edit**
- method: video-edit machine cut, or the editor hand-off
- loudness: -14 LUFS

## Known failures → fixes

- none recorded yet — the first run's learn step fills this

## Cost

- target per ad: $None

## Quality bar — not slop

- the shared QC gate: inspector + director verdicts on every clip
