# Spec: summaries for the 34 red tests, written on the GLM route and evaluated against Claude

2026-10-02, ≈ STREAM · atlas [6941d8]. the team, typed to this stream: "Add red test summaries" and then "But red test summaries try glm route and evaluate".

## What to write

The 34 red-test items in `new-workflow-design/builds/atlas/triage/queue/model-red-tests-2026-10-02.json` already carry the triage engine's verdict: cause class, cause, causing commit, the fix, lane and decider. Under the issue-summary standard (SCHEMA §5) they lack three parts:

- `why`: why it matters, in one sentence a non-engineer understands. Say what a person or the mini cannot do, or gets wrong, while this suite is red, and not only "the test fails".
- `impacts`: `{people: [...], components: [...], machines: [...]}`, by name. People come from the code owner (components/CLAUDE.md Residents row, or the build folder's owner) and from whoever uses what the suite guards. Use no pronouns; use names.
- `if_ignored`: what goes wrong, for whom and when, if the suite stays red. A red gate suite blocks merges; a red suite on a live path hides real breaks.

Also add, for checking:

- `evidence`: 1–3 cites as `path:line@<sha>` that back the `why` and `impacts` (for example the code the suite tests, or a reader of it). Every cite must resolve at the sha you name.
- `confidence`: high | medium | low.

## Output

One file: `components/triage/history/red-tests/summaries-2026-10-02.json`, holding `{"route": "<glm|claude>", "base_sha": "...", "items": [{"id": "R1", "suite": "...", "why": "...", "impacts": {...}, "if_ignored": "...", "evidence": [...], "confidence": "..."}, ... 34 items]}`.

Read anything in the repo. Write only that file. Change no code or test. Run no suite.

## Route and the class it sits in

This is a single-file documentation card, which fits the glm class ruled 2026-09-17 ("tests-only and single-file, fixture-tested cards: config, doc, README drift"). Its output feeds decisions on the red-tests page, so it is evaluated before the route is used for summaries at scale.

## The evaluation

A Claude baseline of the same 34 is written separately, by the atlas stream, out of the GLM maker's sight (in the stream's scratch space; it is not committed before the GLM part lands). Then:

1. Mechanical checks on both: the file parses; all 34 items are present; every `evidence` cite resolves (`git show <sha>:<path>` has that line); no pronouns.
2. A blind judge (a Claude session given both versions per item as A and B, routes hidden) scores each item 0–2 on four counts: **accurate** (claims check out against the code), **specific** (real names, components and effects, not generic), **plain** (a non-engineer understands it), **useful** (would change what the triage owner does).
3. The stream spot-checks 10 items by hand against the code, 5 drawn from each version.

Decision rule:
- **GLM is good enough for issue summaries at scale** (the 302 atlas P2/P3 items that need one) if its total is at least 90% of Claude's, it has no cite that fails to resolve, and the spot check finds no factual error.
- **Use GLM for drafts only, with Claude finishing them,** if it scores 75–90%.
- **Keep summaries on Claude** if it scores under 75%, or has any factual error in a P0/P1 item.

Results are written to `components/triage/history/red-tests/eval-summaries-2026-10-02.md`. The better version is merged into the red-tests page.
