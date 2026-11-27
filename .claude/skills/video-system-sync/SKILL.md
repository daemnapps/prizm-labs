---
name: video-system-sync
description: Coordinate every update to the video system (teardown, writing, production, edit) so it lands everywhere at once. Use whenever the owner gives a new rule about how videos are made, after any change to a video chain, or when someone says "sync the video system", "audit the chains", "run the video system sync", "where does this update go", "go deep into the chains", "what needs to change in the chains", "/video-system-sync".
---

# video-system-sync: one ruling in, every chain updated, checked

> **Standalone skill:** activates no component — coordinates a rule change across video-teardown, video-writing, video-production and video-edit; runs none of them.


External dependencies (read, never copied):
- `components/video-production/VIDEO-RULINGS.md`: the register every audit checks against
- `components/video-production/VIDEO-SPICE.md`, `components/video-production/spice/realism-index.json`
- `components/generative-model-house/` (which model does what)
- The four stations: `components/video-teardown`, `components/video-writing`, `components/video-production`, `components/video-edit`, and the runners `lab/the owner/suite/batch_run.py`, `components/video-production/machine/mini_v2.py`, `components/video-edit/machine/mini_v2.py`
- The pages the owner reads: The Final Video System (https://claude.ai/artifact/DV8pSQCq1k6AJYZab5gfxP, source `lab/the owner/final-video-system.html`, mirror `.md`) and The Video Machine (https://claude.ai/artifact/WwiDdz6db27ZfyDH5PeTeF, source `lab/the owner/video-machine.html`, mirror `.md`)

Why it exists (the owner, 2026-10-21): "every time we make updates establish this as a skill to run on the system so
it's all coordinated." Rules about video were scattered across six docs and three sessions, and a page once called
work "not built" without reading the code. This skill makes the order fixed: rule first, audit with evidence,
one change list, one worker per station, verify.

## The steps, in order

1. **Record the ruling.** If the update is a new rule, add it to `VIDEO-RULINGS.md` (next V#, date, the owner's words
   verbatim, one plain line). If it replaces an older one, mark that row superseded; never delete.

2. **Audit, in parallel, with evidence.** Launch three read-only agents at once (Explore), each given the full
   register:
   - teardown + writing (incl. the live prompt versions the code really loads),
   - production v2 (incl. the Model House, playbooks, prompts/v2),
   - edit v2 + the runners.
   Each returns a table: ID · file:line · ACTION (UPDATE / REMOVE / CONNECT / RESOLVE-CONFLICT / BUILD) · what
   exactly (quote the current text) · ruling V#. Nothing is called missing without the place it was looked for
   (V18).

3. **One change list.** Merge the three tables, rank by impact on video quality, and write it to
   `runs/video-system/sync/<YYYY-MM-DD>/CHANGES.md` with the register's version (git short sha) at the top.
   Conflicts between rulings (or between a ruling and a standing rule in a CLAUDE.md) go in their own section
   as questions for the owner; never resolve a conflict by picking one silently.

4. **Show it.** Update The Final Video System page (the fine-tunes bubbles and the change list) and its mirror;
   update The Video Machine only if the stations themselves changed. Republish both to their same links. Lines
   and bubbles, not walls of text (the owner reads visually).

5. **One worker per station.** Propose one session per station that has changes (writing, production, edit,
   runners), each with only its own rows, file paths and the rulings behind them. Two workers never touch the same
   files. Each works on its own branch, keeps tests green, commits with exact file lists.

6. **Verify.** When the workers are done, run step 2 again on what changed. Rows that pass turn green on the
   page; anything still open stays on the list with the reason.

## Rules
- the owner never runs a command; the session runs everything and reports in one line per station.
- Organic and paid are the same video (V1): never propose a separate track for one lane.
- Cost is never a reason to drop a step (V17).
- Prompts change by new `-vN-` files only (V19).
- Never claim what a chain does or lacks without file:line (V18).

## Tested
2026-10-21: the first run of steps 2–4 (three parallel audits of the v2 line against the register, merged into one
change list on The Final Video System).
