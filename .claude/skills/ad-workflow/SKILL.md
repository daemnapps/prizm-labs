---
name: ad-workflow
description: The Winner swipe ad workflow (video). Start or resume an ad workflow from idea sourcing through concept, writing, review, production and editor handoff. Use for requests such as "run the song-ad workflow", "turn these ideas into briefs", or "where is this ad in the workflow". Read-only workflow questions do not authorize generation.
---

# Ad workflow = Winner swipe ad workflow · video

The named workflow is listed in `components/WORKFLOWS.md` → The named workflows: the brand winner + a swipe the owner picked → teardown → writing → production → edit → review → Meta approval page.

This skill orchestrates existing components. `components/video-production/machine/workflow.py run`
resumes a durable workflow, executes its command stations, and resolves every review station through the decision
layer (`components/video-teardown/machine/decide.py`): the exact version is passed, the call is filed for the owner to
agree with or overrule later, and the run continues. THE ONLY STOP THAT REACHES THE OWNER IS THE QUOTE (owner,
2026-11-27, across all briefs: "the only thing i need to see is quotes"): the price of every paid step before any money
moves, and his go on it. Everything else is decided, and anything stuck is diagnosed and fixed in the session.
The assistant completes returned agent tasks, saves their evidence, and resumes the runner.
Read [the execution loop](references/execution.md) before running or resuming work.

External dependencies: `components/swipe-organic`, `components/intake`, `components/research-gatherer`,
`components/marketing-doctrine`, `components/creative-controls`, `components/video-teardown`,
`components/video-writing`, `components/briefs`, `components/image-teardown/tools/briefs.py`,
`components/review`, `components/video-production`, `components/image-edit/handoff.py`, `components/video-edit`.
Commands run from the repo root. Read the owning component's instructions before using it.

## Start by locating the work

Run `python3 components/video-production/machine/workflow.py list`, then `preview <format> --production-route ai|creator|founder`. The preview names actual family provenance and whether coverage ends at a draft reviewed plan.
For an existing idea, inspect its concept brief, registry entry, working run, and prior approvals
before sourcing or writing anything again. Use `components/briefs/briefs_index.py find <brief-key>`
to locate linked runs. Keep existing folder labels; carry `brief_key` separately. Do not rename
legacy runs or mint a second brief ID just to fit the workflow.

Song ads: read [entry routes and commands](references/song-ad-entry.md).
The playbook is `components/video-production/formats/playbooks/song-ad.json`.

Micro dramas (dialogue story ads): the format is `micro-drama`, and its stations and gates are
`components/video-production/formats/playbooks/micro-drama.json` (`workflow.py show micro-drama`). Every micro drama
runs this one path, in order, autonomously, with no step skipped or done by hand: the start (a swipe and its teardown,
whose beats are the swipe's; or with no swipe, `drama_start.py preset` then `scratch.py --preset`, whose beats are a
live-action drama story preset's) → the writing
chain's brief (`run.py <teardown> --autonomous`: every hold is decided by the decision layer and filed for the owner) →
`hf_route.py pack` → the quote, the ONE stop, and the owner's go (`drama_lane.py open`) →
Higgsfield Drama Ads (sheets → script, plan and clip prompts → every setup on the page → clips → each take looked at),
each followed by `drama_lane.py check` → the edit in HyperFrames → the approval page. A series is planned ahead of time, then
each part runs this same workflow; a part that follows a made part is written from what that part shows on screen and
keeps its creative matrix row (`formats/recipes/drama-series-v1.md`). The clip model
is one setting on the lane (`drama_lane.py models`): both Seedance 2.5 and Wan 3.0 (480p) are priced on every quote and the
owner picks at his go (Seedance when he does not say). A stuck step is diagnosed and fixed by the session, never sent to
him; a take finding the run keeps is filed with `drama_lane.py decide`.

```sh
python3 components/video-production/machine/workflow.py run micro-drama --brand <brand> --label <label> --set intake=<intake run> --set teardown=<teardown label> --set writing_run=<writing run folder> --set brief=<brief path> --set pack_label=<film label>
```

## 1. Source the idea — choose the route that fits

- **An existing concept:** search `runs/research/<brand>/**/deliverable/CONCEPT-BRIEF.md`
  and the brief register. Read its sources, selection history and open questions. Reuse it.
- **The owner's own idea:** capture their premise and constraints, then check it against the brand,
  avatar, product, offer and culture context. Research only the missing support.
- **New ideas needed:** activate `.claude/skills/research-round/SKILL.md` for avatar-world
  discovery, a priced research plan, approved pulls, ranking and the concept matrix.
  `research-gatherer` supplies supporting evidence; the agent synthesizes candidate ideas.
  Neither component automatically chooses the winning idea or writes the final production brief.
- **A reference ad/swipe:** activate `.claude/skills/swipe-intake/SKILL.md` to save and index
  the source, then `video-teardown` through stage 2 to recover its structure, audience,
  doctrine and culture read. Do not use the scratch route to pretend a swipe was analyzed.

Keep the source URL/ID or research paths, the actual observation, why it fits the avatar,
and what is invented. Where evidence is missing, investigate it instead of inventing support.
Reuse supported concepts without repeating discovery.

## 2. Create the concept brief — before writing or production

The agent authors or completes `runs/research/<brand>/<concept-label>/deliverable/CONCEPT-BRIEF.md`
using the research and brand inputs. This is the **creative proposal**, not the maker's final brief.
Use an existing concept's location rather than duplicating it under a new label.

It needs:
- Source/provenance, premise, avatar insight, and why this person would watch.
- Product problem, truthful product connection, offer/CTA and destination.
- Awareness level, story arc and beat outline, hook directions, format and visual style.
- For song ads: song premise, lyric/story outline, music direction, singer/story-shot roles.
- Relevant references, claim constraints, unresolved questions and the selected concept/brief ID.

Read `brands/<brand>/` product/offer, avatar profile/language/culture and brand identity;
use `marketing-doctrine` and `creative-controls` to ground awareness, arc and sections.
A playbook default is a proposed choice, not proof that the choices were made.
The concept brief is also where creative choices and the source references are kept together.
Honor prior selections such as "build these". If no concept has been chosen, the chain picks one from the ranked
candidates and files why (the machine picks; pitches are never put to the owner); do not ask again for an existing
selection.

## 3. Prepare the writing inputs

Scratch: use `video-writing/machine/scratch.py` **without `--write`**, once, to lock the story
and selected brand/product/avatar/awareness/arc/format/style into a working run.
Its stages 0–2 are declared scaffolding, not independent research or an observed swipe teardown.
Check the underlying context before treating that scaffold as ready.

Swipe: use the completed `video-teardown` record through stage 2. Preserve its source and structure.
Resume existing runs; never recreate scratch inputs.

## 4. Write and validate the production brief

Activate `.claude/skills/video-writing/SKILL.md`, then run:

```sh
python3 components/video-writing/machine/run.py <label> --autonomous
```

`--autonomous` turns the decision layer on for this run alone: every structure, hook, audit, swipe-match and manifest
hold is decided from the owner's past calls and filed for him to overrule, and the run continues. Writing costs are
never quoted or capped (owner, 2026-11-25). A run that still stops is diagnosed and fixed here, never sent to him.
The component runs injection → reading/hooks → placement/expansion/close → audit → spice → brief,
including its split-output and final gates. Inspect `run.json` and the gate reports.
A `5-brief.md` file alone is not success. A held/error stage or unresolved audit goes back to
writing; do not patch its status to done or start production around the hold.

Working output: `runs/video-teardown/_work/<label>/stages/5-brief.md`.
Filed maker brief: `runs/video-writing/<brand>/<label>/deliverable/5-brief.md`
(or the existing run's actual shelf slug).

## 5. File, link and review the finished brief

Verify the current passed brief is filed; if the shelf is missing or stale, use
`python3 components/video-teardown/machine/file_run.py <label>` after writing passes.
Compare the shelf with the passed working brief. Filing by itself neither registers an ID nor approves it.

Resolve the existing brief identity through `components/image-teardown/tools/briefs.py` and
`components/briefs/briefs_index.py`. Reuse the concept's ID; check that the writing run is linked.
Only a genuinely unregistered finished brief needs `briefs.py open --type video-ai`.
Read that registry's current interface first; do not silently create a new ID when an existing
concept-to-writing association needs repair. `components/briefs` owns brief styles and lookup;
`video-writing` owns creation of these words.

File the finished brief on the board/page for the owner to read, with the concept/source and the script/lyrics,
hooks, CTA, visual plan and the decided calls easy to see. It does not stop the run: the brief review station is
decided by the decision layer and filed for him to overrule. Never write a verdict in his name.

## 6. Enter production and hand off

After the writing checks and the decided brief review comes THE QUOTE, the one stop: the price station prices every
paid step to the cut (count × unit price, the total, the stop point) in `quote.json` and shows it to the owner. Only his
own go in chat opens the spend; record it against that exact quote:

```sh
python3 components/video-production/machine/workflow.py go <format> --brand <brand> --label <label> --approved-by <name> --said "<his words>" --cap <dollars>
```

Then production runs under the go (`run_v2.py ... --go runs/video-production/<brand>/workflow-<label>/go.json`: the
picture and clip-gate sign-offs are the system's for that run alone, flagged pictures held and remade; the house pause
is never changed) → Suno song and song checks → cast/rooms and the cast lock → scene references shown → scene pictures
→ video-editor handoff → clips/edit → upscale → the launch package filed on the Meta approval page. Every review on the
way is decided and filed. Spend past the cap is a new quote. Going live stays his click on the approval page.
Use the format playbook and the owning component's current instructions at each step.
For song ads, the production rules are in [the entry routes](references/song-ad-entry.md), "Production".
Song and picture files existing do not prove their checks passed. A video-editor handoff must contain
the registered, approved maker brief, approved song, approved pictures and the edit instructions.
Generating a handoff package does not authorize sending a message to the video editor or publishing ads.

## Resume and report honestly

```sh
python3 components/video-production/machine/workflow.py run song-ad --label <label> --brand <brand> --brief-key <key> --set story=<concept-file> --set route=scratch
```

The runner saves its values, task and content-bound completion receipts under
`runs/video-production/<brand>/workflow-<label>/`. `--dry-run` prints its next action without writes or
generation. The older `status` command is an artifact inventory, not the resumable executor's verdict.
Never ask for an already-given selection again or manufacture an approval; the only thing put to the owner is a
quote, and the run's other calls are on the decision queue for him to overrule. An unversioned or stale review requires reconciliation,
not automatic acceptance. `pack` is a legacy artifact handoff; for executable resumption share the
runner's `workflow-state.json` and its referenced repo files. Neither command uploads files or creates
phone links. A requested shareable review needs an actual accessible URL, verified separately.

Report the idea and source, concept brief, finished/held writing status, maker brief location,
existing brief key, and the next action. Never call a concept brief production-ready.
