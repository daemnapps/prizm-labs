# ★ TRIAGE — STATE 2026-10-02 06:47Z (≈ STREAM · atlas [6941d8]) — read this first

History: `HANDOFF-history-2026-10-02.md` (the blocks that lived in the atlas build's handoff until today).

## Direction (the team, 2026-10-02, verbatim where quoted)
- Two themes this round: components / atlas and operations. Red tests are set aside; their lessons are kept (`history/red-tests/`).
- "this will be gernealized for more themes in the future (so just note that but we dont need to design those yet)".
- The approach shows how it generally works, with both themes as real examples.
- "how we actually prioritize is not hard coded in, each theme has its own priotization list". The same holds for grouping: "the group by logic should be custom to each theme as well".
- "Remove weekly digest, lets start with the decision log". The decision log is shown in detail.
- Standing rule: "anything issues that come from this triage process should geneate with the 8 step summary from the start".
- **Option 3 RULED, yes** (the team, received before 07:43Z by date -u: "owner decided yes on option 3"; the first step was to ask the owner). Limits: the summary names the fix and a test proves it; no test check weakened; no live-pipeline change; every change in the decision log with a one-line undo. the team's first change in an owner's component waits for the log's `change`/`undo` acts (#14). The 297 "after a ruling" items are NOT bulk-retagged: each carries its own reason and only 93 have full summaries; re-check per item after ATL-31 (remaining issue briefs). The page shows the owner's flow: what changes for the owner, how the owner reviews, why something changed, and how to undo it.

## Owners
- **Engine:** the team, "for now".
- **Components / atlas:** the team, as theme owner and triage owner.
- **Operations:** the team, as theme owner and triage owner.

Decision log 0d119a6c5. Evaluation tasks: TSK-20261002062419 (the team evaluates components) and TSK-20261002062420 (the team evaluates operations), both due 10-16.

## Pages (custody; all private, the team shares)
- **Meeting page:** (private page) (`approach-two-themes.html`). Part 1 covers the approach; Part 2 is the component drawn to the atlas standard.
- **Component atlas page:** (private page) (`triage-atlas-page.html`, from `flow-triage.json` via `/atlas-view component:triage --flows <folder holding it as triage.json>`).
- **Components queue:** (private page).
- **Operations queue:** (private page).
- **Decision log proposal:** (private page) (`proposals/triage-log.html`).
- **Superseded, in `history/`:** engine view MyiJcUuxeYxQ6BHdtnWibW; owner digest AWGmifrnHKUR1Z8LiRpYMr; red-tests queue PuYUMzVVt5DZoYfM2eQRYa.

## What lives where
- **Here:** the contract, the theme files (`themes/`), the flow, the pages, the proposals, history.
- **Still in `new-workflow-design/builds/atlas/` until ATL-31 (remaining issue briefs) merges and the refactor (#11) lands:**
  - the tools: `triage_page.py` (renderer, must stay Python 3.9-clean), `metrics_insights.py` (operations detectors; reads `themes/operations.json`), `triage_refs.py`, `triage_dryrun.py`;
  - the data workers write: `triage/issue-briefs/`, `triage/briefs/` (ATL-26 (action briefs)), `triage/drafts/` (ATL-29 (drafted changes)), `triage/decisions/` (ATL-30 (decision option cards)), `triage/queue/` (models and pages).

## Filed by the lead (reply after 06:51Z)
- Decision log: the four directions in one entry, verbatim. The eight-parts-at-birth rule is STANDING from 06:43Z.
- Both evaluation tasks repointed to `components/triage/themes/<theme>-FEEDBACK.md`.
- `platform/data/kinds/triage.json` evidence now cites `components/triage/flow-triage.json`. The ATL-28 test and validate_kinds are green.
- `components/CLAUDE.md` gained a Residents row for `triage/`: engine the team for now; definitions the team and the team; PROPOSED; system-review not yet run.
- The record-kind extension (#14) is held by the lead until Option 3 is ruled. The stream recommends carding it now, since only `change` depends on the ruling; the team is weighing it.

## Opening the lists in Claude (the team, 2026-10-02: "for these pages i want them to access directly via claude, not just the shared artifact")
- Team skill `/triage <theme>`. Tested 06:56Z: operations rebuilt live (13 signals, 5 actions); components re-rendered from the newest model (83 actions, no script re-derives it yet). Runs go to `runs/triage/<theme>/<stamp>/` and are never committed unless asked.

## Option 3 filed (lead, a3b9ac629, reply before 07:45Z)
- In the decision log, verbatim, with the four limits. No triage-owner change lands in an owner's component until ATL-32 (triage change trail) merges. Kill: if an owner reverses such a change twice, that owner's components go back to draft-and-owner-lands.
- ATL-32 (triage change trail) is carded and dispatched as specified: five acts, seven fields, "the triage owner", test_atl28 extended, the §5a undo-reopens sentence. Merge is duty 5. It is open issue #14's card.
- ATL-31 (remaining issue briefs): 7 of 8 parts merged at the lead's reply; part H building. Then re-render components, derive the 60 action summaries (#15), and re-check the 297 "after a ruling" items one by one.
- ATL-32 (triage change trail) MERGED (lead, before 07:54Z): the kind has all eight acts with their required-when rules, and SCHEMA §5a says an undo reopens. The writer is built: `tools/file_record.py`, 7 tests green on both Pythons, every passing case a dry run, so no record has been written yet. The `/triage` skill gained Act 4: the Option 3 change steps, the undo steps, and "what has triage changed in my components". The reopen on undo is manual until a reader honours it.

## Option 3 on all three pages, and fix shown as Response (the team via the lead, after 08:04Z)
- The 110 "drafts, owner lands" items were checked too: 0 now (casting#6 overridden to draft, since the owner's CST-1 (casting builds complete) edits the same file), 55 draft, 44 after (mostly the shared records filer), 11 owner. the team's list: 255 now · 218 after · 132 draft · 80 owner. Each item shows its Option 3 line, each action its moved count, each rules panel the ruling plus its effect. Operations: no effect.
- Rename, LABELS ONLY (lead's revised plan): stored keys stay `fix`/`fix_impact`; shown as "Response" and "What the response changes"; `fix` means the response (a fix, a follow-up on a positive signal, or another move). Operations' positive floor signals now read as follow-ups. SCHEMA §5, the system skills and the standing rule are the lead's.
- A regression I caused and fixed: triage_fill had overwritten `has_brief` and `tier` in the components model, so the ATL-31 (remaining issue briefs) tests (which derive their scope from them) lost their scope. The fill now writes `brief_filled` and `tier_from_brief` beside the originals, and all eight ATL-31 suites pass again.

- ATL-29 (drafted changes) round 2 merged (parts A b49d2dfa7, B ac66734dd): all 255 "can do now" items carry a drafted change (132) or a recorded not-drafted reason (123). The components list was re-rendered from a throwaway worktree, because the shared clone held the worker's unresolved index.json conflict.

## GLM rerun of the red-test trial (the team "go", 09:5xZ; asked by ◆ PLAN [6beb2b] on the team's ~02:20Z "trial")
- Package: `history/red-tests/glm-trial/` (60a017393). It has the c0ce1a03f prompts verbatim, the 34 items, the definitions byte for byte, and a worktree at 419334631. Only the model changes, to glm-5.3 via route glm.
- Dispatched by the lead as TI-25 (glm triage rerun), 75ab6f48e. It runs as one job: three `claude -p --model glm-5.3` children, one per part. Run folder: `runs/triage/red-tests-glm-trial/<stamp>/`.
- Asked of the lead: the children get the same tools as the Claude agents (Bash for git and python3, Read, Grep, Glob, one output file). run.json records each child's flags.
- When it lands: score on the trial rubric against e9995982a and the Claude run's 30/34. Publish beside `trial-2026-10-02.html` with ◆ PLAN's line (28 or more → GLM; under 26 → Claude; between → a second trial), and send the team the link.

## GLM: TI-25 parked, the replay is the measure
- TI-25 (glm triage rerun) PARKED on the team's "park" (4cbff88d0). Worker makers may only run python3/node/npm, so tool parity with the Claude red-test trial (git log -S, blame, child sessions) can't be met. It reopens only with a ruled trial lane.
- The GLM replay (`trials/glm-replay/`) is the measure. The briefs job is running (replay/glm/atlas-ATL-31-20261002T101727Z, from 0fabb40eb); the drafts job follows when a slot frees. When both land: copy Opus's tests over, run the blind judge on the 10 pre-registered briefs and the shared diffs, publish, and send the team the page.
- WM-132 (stash pop recovery) merged (6b4590f78): the shared clone should stop jamming on the metrics index.

## Open on the team
1. ~~Option 3~~ ruled yes. The decision-log extension (#14) is now due; relayed to the lead to card and dispatch.
2. The triage owner's four conditions.
3. Each brand's ads owner, and operations targets (#13).
4. A declared `refs:` line on cards and tasks (#12).
5. the team's Slack token scope is too broad.

## Next
1. ~~ATL-31 re-render and the 60 action summaries~~ done: `tools/triage_fill.py` filled 464 issues (19 moved P2 to P3 by their brief) and built 60 action summaries. Coverage is 83 of 83 actions and 656 of 685 issues; the other 29 look fixed. The 297 "after a ruling" items were re-checked at 08:04Z (three readers, then stream overrides on 7: image-edit#11, naming#3, naming#22, 3d#10, atlas#3, quality-checks#13, video-teardown#15, all toward caution). Result: 25 now, 77 draft, 174 after, 21 owner. the team's list is now 255 now · 174 after · 187 draft · 69 owner. Verdicts: `new-workflow-design/builds/atlas/triage/option3-check-2026-10-02.json`.
2. Re-run both lists for 10-09 and 10-16.
3. Refactor: the tools read everything theme-specific from `themes/`, and the tools and queue move here (#11).
4. Collect the 10-16 findings and split them into theme and engine.
