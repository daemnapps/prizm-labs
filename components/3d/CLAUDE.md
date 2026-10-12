# 3d — make3d

**make3d** takes **one picture**, makes **one textured `.glb` 3D model**, free
and local on this Mac. Does not **texture from a paid model, need a credential,
or upload anything**. Triggered by `components/3d/make3d <image.png> <out.glb>`
(`--seed`, `--faces`, `--texture-size`, `--pipeline-type`, `--keep-raw`).

**Owner:** the owner — named 2026-10-08 (the developer, relayed verbatim by ◆ PLAN [1cc25f] before 04:32:36Z: "go on B1, 2, 3"; decision log 2026-10-08 B1 (owner names); the owner may object). Built 2026-09-26 for Lost & Found (the music video),
brought into the workspace 2026-09-29 nested inside `video-edit/`, moved out
2026-09-30 to its own component. Changes to the wrapper and the finish pass
are the owner's. Its callers today: `components/objects/`
(`machine/run.py`) and `components/local-studio/`'s `3d` job (`local.py`,
which still names the old `tools/3d/make3d` path, absent in this repo).

Runs by: person — the owner's Apple-Silicon Mac, where its ~16 GB of weights and Blender live; not the mini (2026-10-08, B4a (decide-now cards) card 2: it declares how it runs today).

**Definitions + curator:** none — this is pure engine, no curated list.
TRELLIS.2-4B (Microsoft, MIT) via the `trellis-mac` Apple-Silicon port does
the generation; `finish.py` + `bake_blender.py` do the local finish pass
(decimate, orient, UV-unwrap, bake). See README.md for what changed from the
stock port and why.

**The plane it emits:** none of its own — it writes the `.glb` its caller
names on the command line. `components/objects/` calls it and records the
result on its own plane (`<project>/3d/catalogue.json`); `components/local-studio/`'s
`3d` job names it too and keeps the `.glb` where its caller asked.
**Records (O12 (records adapter)):** none: the caller files — objects records the result on its own plane (the developer, 2026-10-07, triage page 7).

**What the manifest declares:** not applicable — no manifest, no contract
beyond "one picture in, one `.glb` out."
