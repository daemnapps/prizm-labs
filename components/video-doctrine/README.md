# components/video-doctrine — the craft doctrine every video tool cites


**video-doctrine** — how any video is read, written, shot and cut. It takes
`frameworks.json` and renders the slices in `slices/` that a prompt binds by
path. It writes nothing but `slices/*.md`. Triggered by
`python3 components/video-doctrine/render.py`.

It is brand-agnostic and format-agnostic: no brand, product, avatar, model or
platform name appears here. Model-specific wording stays in `model-inputs/`.

## The one rule

**A machine reads its craft words from here and never restates them in a
prompt.** A change goes in `frameworks.json`, then `render.py` runs. The swipe's
own read wins over a default; `VIDEO-RULINGS.md` wins over this doctrine.

| Variable | Slice | Teardown | Writing | Production | Edit |
|---|---|---|---|---|---|
| `{shot_language}` | `slices/shot-language.md` | yes | | yes | |
| `{look}` | `slices/look.md` | yes | | yes | |
| `{staging}` | `slices/staging.md` | yes | | yes | yes |
| `{cutting}` | `slices/cutting.md` | yes | | | yes |
| `{consistency}` | `slices/consistency.md` | | | yes | |
| `{video_shapes}` | `slices/video-shapes.md` | | yes | | |
| `{shot_brief}` | `slices/shot-brief.md` | | yes | | |

## New-resident answers

Runs by: person

| question | answer |
|---|---|
| **engine + owner** | `render.py`, stdlib, no credential. Owner the owner |
| **definitions + curator** | `frameworks.json`, curated by the owner. Every row is draft until signed |
| **the plane it emits** | none: `slices/` is a rendered projection, not a run record |
| **what the manifest declares per entry** | a name, a job and a `status`; every group carries a source key |

**Read surface:** `slices/<name>.md` by path, and the variable map above.

## Kill-condition

If prompts start restating these terms inline, the slices are too coarse and the
split gets fixed here.
