# Red-test triage trial on GLM: the exact rerun of c0ce1a03f

the team, 2026-10-02 at ~02:20Z, "trial", answering ◆ PLAN [6beb2b]: "Say "trial 1" and I'll ask the atlas stream to rerun the red-test trial on GLM." the team confirmed "go" in the atlas stream after red tests had been set aside for this round. The question is whether the engine's bulk passes can move off Claude limits onto the GLM plan.

## What is the same as the Claude run (c0ce1a03f)

- **Inputs:** `items1.json`, `items2.json` and `items3.json`, 34 suites in total (12, 11 and 11). Each gives the suite path and the reporter's first failing line, exactly as the Claude run had them.
- **Definitions:** `DEFINITIONS-red-tests.md`, byte for byte the c0ce1a03f version, before the cause/blocked_by split.
- **Prompts:** `prompt-part1.md`, `prompt-part2.md` and `prompt-part3.md`, the three Claude agents' prompts verbatim. Only the machine paths are replaced by `<WORKTREE>` and `<RUN>`.
- **Code under test:** a read-only worktree at commit **419334631**, which is `<WORKTREE>`.
- **Blind rule:** unchanged. The agents never read `team/handoffs/2026-10-02-red-tests-triage.md` or commit e9995982a.
- **Shape:** three agents in parallel, one per part. The Claude run used the session's main model, so no part used a small model.

## What changes

- **Model:** glm-5.3 for all three parts, reached through the worker's route `glm` (claude_env layering). Nobody reads the key file by path; that is a wall.

## What the run must record

- `<RUN>/out1.json`, `out2.json`, `out3.json`, in the shape the prompts specify.
- `<RUN>/run.json`:
  - the CLI's `modelUsage` per part: which model actually answered, not the alias;
  - wall time per part;
  - cost as "plan window", never the CLI's dollar figure (09-17 ruling).

## Scoring (the atlas stream, after the run)

The rubric is the same as `../trial-2026-10-02.html`: agree · same fix, different label · partial · differ. The run is scored against ◆ PLAN's 34 hand rows (e9995982a) and against the Claude run's verdicts (`../engine-verdicts-2026-10-02.json`, 30 of 34 leading to the same action).

Decision line (◆ PLAN's, the team's to apply):
- 28 or more of 34 → the engine's bulk passes move to GLM;
- under 26 → they stay on Claude;
- 26 or 27 → a second trial on another list.

Nothing gets carded or fixed from this trial.
