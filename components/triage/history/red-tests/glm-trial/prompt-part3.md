You are the triage engine running BLIND on red test suites. Read-only. Do NOT edit or commit anything in ~/Projects/workspace, and never run git reset, rebase, stash or checkout there.

Work in the read-only worktree <WORKTREE>, which is at commit 419334631. Run git commands and suites there.

BLIND RULE: do NOT open, grep or read `team/handoffs/2026-10-02-red-tests-triage.md` or commit e9995982a, in any checkout. That file is the ground truth your output will be scored against. Also avoid any other file that lists triage verdicts for these suites.

Read the definitions first: components/triage/history/red-tests/glm-trial/DEFINITIONS-red-tests.md (read it from the main checkout, not the worktree).

Items: components/triage/history/red-tests/glm-trial/items3.json (read it from the main checkout). Each item gives the suite path (relative to the repo root) and its first failing line from the reporter. One item is a timeout, not a failure.

For each item:
1. Read the suite around the failing assertion.
2. Find the cause. Use `git log -S`, `git log -p -- <file>` and blame on the code or text the assertion pins, and look at the commits since the test last passed.
3. If you need to, run it once in the worktree: `cd <worktree> && python3 <suite>`, with a 300 s cap. Use plain `python3`.
4. Classify it per the definitions.

Output a JSON list to <RUN>/out3.json, one object per item, with these keys:
- id, suite
- class (REAL | STALE | ENV | RULING)
- cause: one sentence naming the commit sha that caused it, if found
- causing_commit (sha or null)
- fix: one concrete sentence
- fix_group (the kebab slug of the one action)
- severity (P0–P3)
- lane (maker | owner | decision)
- decider: who
- confidence (high | medium | low)
- secondary_class: optional, if it truly fails for two reasons

Final report: a count per class, and the fix_groups you used with their counts.