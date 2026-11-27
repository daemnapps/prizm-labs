# Song-ad entry routes

Read this when starting or resuming a song ad. These are component entry points, not a batch
script to execute from top to bottom. Resolve parameters from existing records and quote actual
shell arguments. Read the activated component/skill for its detailed behavior.

## New ideas

Read `.claude/skills/research-round/SKILL.md` first. Start free discovery with:

```sh
python3 components/swipe-organic/round.py worlds --brand <brand> --avatar <avatar> --label <research-label>
```

The agent builds the worlds record from avatar research, then uses `plan` to declare the research
question, searches and keep/drop rules. Show that plan's cost before an authorized `pull`; `rank`
and the component's matrix workflow organize the evidence. The agent writes concept proposals,
the owner selects, and the chosen proposal becomes the research deliverable `CONCEPT-BRIEF.md`.
Do not invent a `research-gatherer create-concept` command; there is no such automatic entry point.

For already banked concepts, read their source material and the selection instead of pulling again.
For a supplied idea, use the same concept deliverable after filling only the missing evidence/context.

## A saved swipe

Read `.claude/skills/swipe-intake/SKILL.md` to ingest/index the source if necessary.
Then analyze the source through the existing stage-2 boundary (paid calls):

```sh
python3 components/video-teardown/machine/run.py <source-video> --label <label> --brand <brand> --product <product> --route ai --v2 --writing v2 --to 2
```

Read the actual teardown/audience/doctrine/culture/spec outputs. Create the concept brief for OUR
adaptation, retaining the swipe ID and what is being reused. Review the creative direction before writing.

## A chosen scratch concept

After the context, concept and picks are ready, prepare the run once, without generating writing:

```sh
python3 components/video-writing/machine/scratch.py <label> --brand <brand> --product <product> --avatar <avatar> --awareness <awareness> --arc <arc> --format song-ad --style <style> --story <concept-file>
```

Resume both routes with `python3 components/video-writing/machine/run.py <label>`.
Do not combine setup and paid writing with `--write` when the intermediate inputs still need review.

## File and identify

After all writing checks pass:

```sh
python3 components/video-teardown/machine/file_run.py <label>
python3 components/briefs/briefs_index.py find <existing-brief-key>
```

Inspect the existing registry entry and joined run paths. A concept may already have a numbered
brief before its production brief is written. Do not use `open` to repair a missing join; it can
allocate another ID. If there is genuinely no registered entry, the finished-brief entry point is:

```sh
python3 components/image-teardown/tools/briefs.py open <label> --brand <brand> --product <product> --avatar <avatar> --type video-ai
```

After the completed maker brief passes its decided review (the decision layer, filed for the owner to overrule) and
the owner's go on the quote is recorded (`workflow.py go`, his one stop), follow production's start command in the playbook.
Use the registered brief ID for a new production run's label; keep an existing production folder's
label when resuming. The working writing label and production label can legitimately differ.

## Production

Every song ad runs this order, swipe or scratch. The settings are `stages` in the playbook; this is the
order to drive them in, on the board, never by direct model calls.

1. **Style.** Set in the picks and carried as `piece.style_id` in the plan. Every scene, set and cast sheet
   is in it. An animated style redraws its rooms.
2. **Song.** A real story in new lines, long lines split (`SONG-WRITING.md`), through the song gate.
3. **Cast lock.** Full cast and product casting sheets, locked in the run's `cast-lock.json` before any scene picture.
4. **References.** Every scene's IMAGE 1 is shown on the page first: the swipe's frame, or on a scratch ad the
   scene's `reference` frame in the plan. An animated style uses soft grey pose guides. Bars come off wide frames.
5. **Pictures.** Full 9:16, no bars, no overlays, safe zone measured on every one. The system's reviewer passes each
   (a flagged picture is remade, never shipped); the scene-pictures station is decided and filed for the owner to overrule.
6. **Clips.** Inside the owner's go on the quote and its cap; spend past the cap is a new quote. Directions run beat by beat by the second from frame one at maximum
   absurdity and movement (`stages.clips.direction`). Romance stays dressed and non-explicit; no real person's
   name or lookalike. The clip model is `stages.clips.model` (MiniMax H3 at 2K, no upscale); what it takes is its model-inputs sheet.

## Current Brand A example

- Concept: `runs/research/Brand A/celeb-i-hit-it-first/deliverable/CONCEPT-BRIEF.md`.
- Existing concept identity: `Brand A_flex-face-brush_brief-0280` (verify the live registry on resume).
- Working writing run: `runs/video-teardown/_work/Brand A-scratch-i-hit-it-first/`.

Read the current run record, not this example, for completion. The concept and a working run
are not evidence that hooks, audits or a production brief passed.
