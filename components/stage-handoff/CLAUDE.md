# stage-handoff — data only

**stage-handoff** is a data folder since 2026-11-19 (owner: "Fold it in"). It holds the definitions the video
process reads; it runs nothing.

- `chains/<chain>.json`: the stages of a chain, the role that holds each, how each is switched on and what each
  hand-off carries; `chains/<chain>-map.json`, `-stops.json`, `-formats.json`, `-format-map.json`,
  `-decision-logic.json`, `-format-style-calls.json`: the chain map, stops, format trace, format map, decision logic
  and the formats page data.
- `roles.json`: who holds each role. A role is a job, never a person.

Every entry `status: draft`; the owner curates both.

**The tools that read this live in the video process:**
- hand-offs (library, checker, pack, pull, SPEC, tests): `components/video-edit/handoff/`;
  the editor stage's own checker stays `components/video-edit/handoff_check.py`.
- the chain canvas, map page, format map, decision-logic board and the formats page:
  `components/video-production/chain-map/`.
- the locked video names: `components/video-production/formats/names.json`.

**Runs by:** person (through the tools above).
