# Evaluation: red-test summaries, GLM vs Claude (TI-24 (red-test summaries GLM))

2026-10-02, ≈ STREAM · atlas [6941d8]. Spec and decision rule: `SPEC-red-test-summaries.md` (cbb170260), set before either version existed.

## Result: keep issue summaries on Claude. The GLM file is not merged.

| | GLM (glm-5.3) | Claude (baseline) |
|---|---|---|
| Mechanical checks (34 items, cites resolve, no pronouns, no empty fields) | pass, 90 cites | pass, 88 cites |
| Blind judge total, out of 272 | **235** | **259** |
| accurate / specific / plain / useful | 59 / 65 / 52 / 59 | 66 / 64 / 68 / 61 |
| Items won (of 34) | 4 | 16 (14 tied) |
| Factual errors | **8**, in 6 items, including R1 (P0) and R20 (P1) | **2**, in R10 (P3) and R18 (P3) |
| Time | 941 s on the GLM plan window | about 470 s on Claude |

GLM scored 90.7% of Claude, just over the 90% line. But the rule set beforehand says any factual error in a P0 or P1 item keeps summaries on Claude, and GLM has one in each:

- **R1 (P0):** GLM says one worker card is "read twice". In fact two cards share the id WM-120 (system second slot), so one card is hidden.
- **R20 (P1):** GLM says inbox views show nine items as unfiled. Nothing reads that index today.

GLM's other errors are in the same direction:

- **R6, R7:** cs-loop called "chief-of-staff". It is customer service.
- **R14:** says the cockpit shows old models. `seat_kinds.sh` already says claude-opus-5-5.
- **R26:** says the guard names the wrong folder. It names the right one; only the test is wrong.

The judge opened about 80 cites, and every cited line exists. All ten errors are prose that claims more than its cites show. GLM writes plausibly and cites correctly, but over-reaches in the prose. That is the failure that misleads a person deciding.

The stream checked two of the judge's error calls by hand, and both hold: R14 (`seat_kinds.sh` lines 142–143 already read claude-opus-5-5) and R6/R7 (workflows.json: cs-loop is "the CS process").

## What was used instead

Claude's version, with its two errors corrected from the judge's notes:

- R10: only the manifest check is red; the pricing tests pass.
- R18: a second cause, the team's pm.html copy behind after PM-60 to PM-64. GLM found this one and Claude missed it.

It is written to `summaries-2026-10-02.json` and shown on the red-tests page.

## What this means for the 302 atlas summaries

If the team approves them, they go on the Claude route. GLM stays right for what it has proven: TI-23 (red-test fixes on GLM), test-only re-pins, 9 of 10 merged, with every changed assertion reviewed by the lead.

**Reverse if** a re-run on a fresh sample after a GLM model update scores ≥ 90% with no factual error in a P0/P1 item.

Also from the judge: the team has asked not to be reminded about cs-loop (`workflows.json:379`), so R6 and R7 should not be raised with her.
