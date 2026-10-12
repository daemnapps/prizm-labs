# local-studio

**local-studio** — takes **one local-compute editing job** (interpolate,
upscale, matte, segment, caption, stem-separate, voice, image edit/generate,
image-to-3D), makes **the job's output file on this Mac**, timed and logged.
Does not **decide which job to run, or call a paid API** — every job here runs
a local model, free, on this Mac's own hardware. Triggered by `python3
local.py <job> <input> -o <output> [options]` (`local.py runs` lists every
run so far: time + peak memory).

Runs by: person — a Mac with its local models; not the mini (2026-10-08, B4a (decide-now cards) card 3, R-person-or-mini: the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:49:43Z: "3 yes, 4 yes,5 yes, 6 yes"; the owner told after). Install: README.md "Where things are" (a setup script is carded); `.venv-mlx/`, `models/` and `src/` are git-ignored here, so an install never stages weights.

**Owner:** the owner — ruled 2026-10-07 (triage A-repoint-old-and-moved-paths), recorded 2026-10-08 (the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:32:36Z: "go on B1, 2, 3"; decision log 2026-10-08 B1 (owner names); the owner may object). Built 2026-09-27 for Lost & Found (the music video),
brought into the workspace 2026-09-29 nested inside `video-edit/`, moved out
2026-09-30 to its own component. "the owner never runs this" by its own README —
Claude sessions and the pipeline call it; changes to the launcher and the
per-model jobs are the owner's.

**Definitions + curator:** none — no curated list; `jobs/` is one script per
model, added as `## Add a model` in the README describes.

**The plane it emits:** `runs/local-studio/_system/runs.jsonl` at the repo root — one line per run (wall seconds,
peak memory, input, model). No records adapter; the Control Room/atlas cannot
see these runs today (O12).

**What the manifest declares:** not applicable — no manifest; the run log
is a log, not a definitions list. Internal paths still point at where this
lived in the owner's own sandbox (`tools/local`, `tools/av`, `~/.cache/…`) — not
yet fixed; first real run here updates them.

**Public entry (local-studio#15):** `jobs/segment_image.py` is called directly
by video-production (`machine/product_check.py`, `product_mask()`) through
`components/local-studio/.venv/bin/python`; it needs that `.venv` with SAM 2
installed, and nothing in the repo installs it yet — the install recipe and a
`segment-image` job in `local.py` come later.
