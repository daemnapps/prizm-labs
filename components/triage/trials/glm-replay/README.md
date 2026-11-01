# GLM replay of recent atlas triage runs, blind against the Opus originals

the team, 2026-10-02 at 10:05Z, "replay", answering ◆ PLAN [6beb2b]: "Say "replay" and I'll ask the atlas stream for the sample and the lead for the dispatch." The ask was "test if glm can be tested against some of recent runs". Why it matters: ATL jobs were the largest worker spend today (~204M input tokens, mostly ATL-31 (remaining issue briefs), ATL-29 (drafted changes), ATL-26 (action briefs) and ATL-30 (decision option cards)).

**Only the model changes.** Each replay reruns one original worker job exactly: the same request instruction, at the same base commit, on route glm with glm-5.3. Its output lands on a replay branch that is NEVER merged. Nothing gets carded or merged from it.

## The two jobs (picked so that Opus's own output already passed a test GLM's output can be run against)

| | Briefs | Drafts |
|---|---|---|
| Original | ATL-31 (remaining issue briefs) part F | ATL-29 (drafted changes) round 2 part A |
| Request (instruction verbatim) | `platform/data/records/workflow-requests/20261002T061737Z--dayu--impl-atl31f-issue-briefs.json` | `platform/data/records/workflow-requests/20261002T091838Z--dayu--impl-atl29-r2a-remaining-now.json` |
| Base | 0fabb40eb | e6d8103826 |
| Opus output | branch tip b1be1d4d4 (merged 2c8de3b27) | merged b49d2dfa7 |
| Scope | 58 issue briefs, 6 components (copywriter, image-teardown, intake, meta-upload, media-render, atlas), 50 P2 and 8 P3 | 10 new rows: 6 diffs (apify#11, elements#1, image-production#22, image-teardown#2, marketing-doctrine#6, run-kit#15) and 4 not-drafted reasons |
| Opus's own gate | `test_atl31f_issue_briefs.py`: 274 of 274 | `test_atl29r2a_drafts.py`: all green, 6 of 6 diffs apply at BASE |

## Measures

1. **Same gate as Opus (objective).** Copy Opus's declared test from main into the replay branch unchanged and run it on GLM's output: `test_atl31f` (checks pass out of 274) and `test_atl29r2a` (all green or not). The original instructions tell the maker to write the test, so the replay maker writes one too: the instruction stays verbatim, so only the model changes. That test is recorded but is not the gate. The gate is Opus's test, copied from main over it in the lead's verification worktree (lead, 10:1xZ: worker `base_ref` replay at the base, branches under `replay/glm/`, items replay-glm-atl31f-briefs and replay-glm-atl29r2a-drafts).
2. **Briefs, blind judge on 10.** The sample is pre-registered in `sample-briefs.json` (seed 20261002, one per component, at least one P3, picked before any GLM output exists): atlas#6, copywriter#6, copywriter#10, image-teardown#14, image-teardown#15, intake#4, media-render#3, media-render#4, media-render#6, meta-upload#11.
   - An independent Opus reviewer sees the Opus and GLM brief for each issue as A and B, randomised per item. The key goes in a separate file the reviewer never reads.
   - It scores factual accuracy: every claim is checked against the code at 0fabb40eb, and each wrong claim is counted. It also scores completeness of the eight parts and usefulness to the triage owner, then picks equal, A or B.
   - Counter-weight to judge style bias: the factual-error count is the deciding measure, and each error is cited as path:line@0fabb40eb so a person can check it.
3. **Drafts.**
   - Each GLM diff: `git apply --check` at e6d8103826, and its file stays inside its component (the r2a test checks both).
   - Diff-or-not agreement with Opus on the 10 rows.
   - For the diffs both models made, the same blind judge asks whether the diff carries out the issue's stated response with no unrelated change.

## Decision line (◆ PLAN's, sharpened with the objective gate; the team applies it)

- **PASS:** GLM passes both of Opus's tests, its briefs are judged equal or better on 8 or more of 10, it makes no more factual errors than Opus across the 10, and every GLM diff applies. Then the triage write-ups (briefs, drafts, and by extension action briefs and option cards) move to route glm.
- **FAIL:** more factual errors than Opus, a failed test, or a diff that does not apply. They stay on Opus.

## Not available, said plainly

There are no triage-owner acts to score against. `platform/data/records/triage/` holds no records yet: the team has not acted on any brief through the decision log. So the "score against the team's own acts" leg of the proposal can't run today. It can be added after the first real records.

## Prior evidence

TI-24 (red-test summaries GLM) compared summaries blind: GLM 235 against Claude 259 out of 272, with 8 factual errors against 2, so summaries stayed on Claude. This replay asks the same question on component issue briefs, plus drafts, which TI-24 did not cover. TI-23 (red-test fixes on GLM) merged 9 of 10 test-only fixes.

## The run records

`runs/triage/glm-replay/<stamp>/{briefs,drafts}/`, holding the replay branch name, the gate test output, and `run.json` (CLI modelUsage per job, wall time, the tool flags each CLI ran with, and cost as "plan window", never the dollar figure, per the 09-17 ruling). The judge's pairs, key and verdicts go in `judge/`. The comparison page is the atlas stream's, and it goes to the team.
