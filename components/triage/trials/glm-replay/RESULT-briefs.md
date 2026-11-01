# GLM replay: briefs result (ATL-31 (remaining issue briefs) part F)

**Verdict: FAIL on the decision line.** Briefs stay on Opus.

| Measure | Opus (original) | GLM (glm-5.3 replay) |
|---|---|---|
| Opus's own gate `test_atl31f` | 274 / 274 | 274 / 274 normalized (273 raw: the replay repo names the base bf2a10ffc; same tree ffd685a89 as 0fabb40eb, verified) |
| New evidence cites | 252 | 164 |
| Blind judge, picks on the 10 pre-registered briefs | **10 of 10** | 0 of 10 |
| Factual errors across the 10 (each cited path:line@0fabb40eb) | **1** | 7 |
| Wall time · spend | — · Claude plan | 1,715 s · glm-5.3 only, "plan window" |

**Errors that would mislead the triage owner:**
1. meta-upload#11: GLM says <brand> has no funnels registry. `brands/<brand>/web/funnels/funnels.json` exists at the base with 5 funnels, and the gap was <brand>'s, already fixed by aed8f7989. Its response asks for work that is done.
2. atlas#6: GLM says the id-tag lint flags the component's CLAUDE.md. The lint scans only the decision log, PLATFORM-CONTEXT and `team/plans/` (`.githooks/id-tag-lint.py:35-38`).

The stream re-checked both against the base; the judge's other five GLM errors are cited in `judge/verdicts-briefs.json`.

**Read:** GLM matches Opus on shape. It passes every structural check of the original test, and fast. It does not match Opus on truth: 7 to 1 factual errors over 10 briefs, the same pattern as TI-24 (red-test summaries GLM), which had 8 to 2. A judge leaning toward Opus's style can't explain this, because the deciding measure is cited, checkable errors. The stream verified two of them itself.

**Method:**
- Pairs randomised A/B (seed 4242); the key was kept apart from the judge (`judge/key-briefs.json`).
- GLM's citations were normalized to @0fabb40eb in the pairs, so the commit id could not reveal the writer.
- One Opus judge checked claims only at 0fabb40eb.

The drafts replay (ATL-29 (drafted changes) round 2 part A) is still running; its result is scored separately.
