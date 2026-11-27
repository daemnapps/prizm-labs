# Stage hand-offs: each component of the video chain hands its output to the role that runs the next one

The video chain is four components, in order: **video-teardown → video-writing → video-production → video-edit**.
A hand-off is one component's finished output, filed as a folder in the shape the next component's own door takes,
so whoever holds the next role pulls it in and switches the chain on from there with that component's command.

## The rule

1. **A stage is a component. A stage is held by a role, never a person.** Who holds a role is data: `roles.json`
   (a person from `team/people/<name>`, later `agent:<name>`). Change a holder there and every door follows.
2. **A hand-off is one folder**: `runs/handoffs/<role>/<brand>/<brief key or run label>/`, the same path under
   `Shared Assets/` on the Drive. The Drive is its home (the folders travel by Drive, not git:
   `runs/handoffs/.gitignore`). Before writing there is no brief number, so the teardown's hand-off is named by its
   run label; from production on it is named by the brief number in the brief register.
3. **Each stage declares, in `chains/video.json`:** its component, its role, its door (the component's own command,
   from its CLAUDE.md), what it makes, and what a hand-off INTO it must carry. The checker reads that list.
4. **Every hand-off carries** `HANDOFF.json` (chain, stage, role, brand, key, where it came from, the door, what comes
   next), `START.md` (the line to say to your Claude and the door) and `returned/`. Sources are named by repo path or
   Drive label, never a machine path.
5. **A stage hands on by filing the next stage's hand-off.** The pull door shows a hand-off as `open`, `back` (work in
   `returned/`) or `moved on` (the next stage's hand-off is filed).
6. **After the hand-off the holder runs everything.** No owner approvals inside a stage, except spend past a cap,
   going live, sending and signing.

## The four stages

| Stage = component | Role (holds it today) | Its door | It makes | The hand-off INTO it carries | Built by |
|---|---|---|---|---|---|
| video-teardown | creative-strategist (the owner) | `video-teardown/machine/run.py <swipe> --brand <b> --route ai` | `runs/video-teardown/_work/<label>/`: stages 0, 1, 1k, 1c, 1b, 2, frames, sound sheet | `SWIPE.md`, `refs/swipe.mp4` | the swipe intake (declared, not built here) |
| video-writing | creative-strategist (the owner) | `video-writing/machine/run.py <label>` | stages 3 to 5; the accepted brief at `runs/video-writing/<brand>/<label>/deliverable/5-brief.md` | `teardown-run/`: the teardown's working run whole (run.json, stages 1 and 2 done, frames, video); the door puts it back at `runs/video-teardown/_work/<label>/` | `pack.py video-writing <label>` |
| video-production | video-producer (a creator, the owner) | `video-production/machine/run.py start BRIEF.md --brand <b> --format <format>` (the Video Studio) | voice, stills, clips; the edit kit = the video-editor hand-off | `BRIEF.md` (accepted), `teardown/` (1-teardown, 2-spec, FRAME-MAP), `SWIPE.md`, `refs/`; record: writing accepted, route ai, format | `pack.py video-production <brief>` |
| video-edit | video-editor (a creator) | `video-edit/machine/run.py handoff <folder>`, or `video-briefs` (Premiere, HyperFrames) | the finished cut in `returned/`, the approval card in `meta/<brand>/1-check/video/` | its own checks: `video-edit/handoff_check.py` | the Studio's Send to maker (the edit kit) |

## Proven, 2026-11-17

- **teardown → writing:** `Brand B-sale-ends-dark-spots` (torn down, not written) packed for the creative strategist;
  the writing's door reads `teardown-run/` by its label.
- **writing → production:** brief 0355 packed for the video producer; production's own door
  (`run.py start --dry-run`) reads its BRIEF.md: 16 scenes. One real finding: the Studio's copy (E06) carries brief
  number 0366, the register 0355.
- **production → edit:** the editor's checks run unchanged through the shared checker (0332: 23/23).

## The doors

| Who | Says | Runs |
|---|---|---|
| Whoever finishes a stage | "hand 0355 to video production" | `pack.py video-production 0355` (or `pack.py video-writing <label>`) |
| Anyone | "is the 0355 hand-off ready" | `check.py 0355 --role video-producer` |
| The role holder | "what's waiting for me" | `pull.py waiting --person <name>` |
| The role holder | "open 0355 as video producer" | `pull.py open 0355 --role video-producer`, then the door it prints |

## Continuing unfinished writing

An explicitly delegated writing continuation may enter the producer inbox at its actual **video-writing** stage. It retains the source stage records and acceptance hold; it does not become an accepted production brief. The selected recipient role is separate from `work_role`, the work being continued. See `pack.py --help`, `resume_writing.py` and its tests for the packet and resume behavior.

The existing pull door restores the working run and bundled media only where absent, preserves newer local work, and supplies the selected winner's source text. The recipient resumes through video-writing's public runner. Production's acceptance checks are unchanged.

## The map: every piece, every handshake

`chains/video-map.json` holds every piece of the four components as the code runs them (119 on 2026-11-17, each
with file:line, prompt, model, what it reads and writes, what holds it, the skill and the sub-processes it calls),
and each seam: what one component hands over, what the next one's door reads, and the gaps where they do not meet.
`map_page.py` draws it to `runs/stage-handoff/video/map.html` (the owner's page). Refine the workflows in the map
file, then re-draw.

The same map as a whiteboard you can zoom into and rearrange: `canvas.py` writes it as whiteboard elements under
`runs/stage-handoff/video/canvas/` (one file per element plus `board-meta.json`), loaded into the Video Chain Canvas
(https://claude.ai/artifact/H1WiuMEqNKAE7n8ZNYeb1h). Each component is a section, its pieces in run order six to a
row with arrows, each hand-off between components a block listing what passes and every gap.

**Every stop.** `chains/video-stops.json` lists every place each component can stop, hold, wait or quietly pass a bad
result on (403 on 2026-11-17, swept from the code, each with file:line), keyed to the map's pieces: what trips it,
what it says, whether the person holding the role can clear it (or it needs the owner, a build, or nobody can), and
whether it breaks the hand-off. The canvas hangs each stop under its block: yellow the holder clears, pink they can't.

**The path and the causes.** The same file groups every stop under one of 13 root causes (`_causes`, each with its
one fix; every stop carries `cause`) and lays out the path from an idea to a live ad (`_path`: the four components,
their duplicate roads, and the stages not mapped yet). The canvas draws both above the components. The proposals on
the path (one production engine, one edit builder) are proposals until the owner rules.

**Format by format.** `chains/video-formats.json` traces each ad format through the stages (runs alone, needs a
person, not built), with the proof it has run, what the trace found, and what a format would have to declare for the
chain to run it alone. The canvas draws it as a grid to the right of the path.

**The format map.** `chains/video-format-map.json` sorts every format-like name the chain holds (the format bank, the
element lists, the production recipes and their variants, the owner's format calls, the organic structures, styles,
delivery, caption looks, hook types) into the layer it belongs to: script format, production format, hook type, hook
format, structure, style, delivery, caption look, maker. It groups the names that are one thing and lists the calls
that are the owner's. It is a PROPOSAL (`status: draft`): no bank, list or recipe has been changed. `format_map.py`
draws it to `runs/stage-handoff/video/format-map/`, loaded into the Format Map board
(https://claude.ai/artifact/GNn1yBAtYuiwKJ4Hf5bc3h); the canvas links to it.

**Decision logic along the chain.** `chains/video-decision-logic.json` walks the real chain in nine stages (pick the
post, decide what to make, read it apart, write, produce, cut, launch, read the results, decide what is next) and,
for each decision a stage makes, records what decides it today and the reasoning the chain gives it. The chain is the
authority: where it states its logic (`state: stands`) nothing is added. Where it is silent, thin or left to a person
with no criteria, the reasoning is filled from the owner's older procedures and recorded walkthroughs and marked with
its source (lesson ids in the owner's own knowledge store; the texts stay there). `carry` marks a reason that is
written and read by no later stage. It is a reading aid for adding logic between stages: no check, no gate, and it
changes nothing by itself. `creative_system.py` draws it to `runs/stage-handoff/creative-system/`, loaded into the
Decision Logic board (https://claude.ai/artifact/2TgVZ54rsm2EQtnfEGt7w4), linked from the Format Map and the canvas.
`chains/creative-system.json` (an earlier framing that treated the older material as the standard) is deprecated.

## One brief with three selected variations

`group.py build SPEC.json --key <registered video-ai key>` packages three separately accepted AI writing runs as one producer job. The spec names the existing source runs, unique variation IDs, audience and title. It refuses current unaccepted writing, a different brand/product/audience, and an unbanked production format. Each variation keeps its full brief, exact accepted-byte hash, writing receipt, teardown and original swipe. `RUN.md` and `group.py plan <folder>` expose one production preview command per variation, with distinct labels. No generation occurs.

The combined `BRIEF.md` is for review; production reads each `variants/<id>/BRIEF.md` separately. The stage checker applies the ordinary production input-file checks to every variation and verifies each accepted brief hash. Optional openings inside those source briefs are retained reference material, not extra assignments.

An older source packet may record `state: superseded` and `superseded_by: {key, drive_url}`. It remains readable and opens as a pointer; it is omitted from waiting assignments. Native pull refreshes handoff and delivery/revision metadata from Drive, never overwriting local working files. Existing in-progress and back-for-revision jobs remain visible with their revision IDs.
