# Executing and resuming a workflow

The user says “run the song-ad workflow”; the assistant drives this loop. The user should not need
to run commands, locate stage files or repeatedly ask to continue. This is an active-session workflow,
not a background scheduler. Do not create an automation unless asked.

## Start/resume

```sh
python3 components/video-production/machine/workflow.py run song-ad --brand <brand> --label <writing-label> --brief-key <key> --set route=scratch --set product=<product> --set avatar=<avatar> --set story=<concept-file> --set awareness=<awareness> --set arc=<arc> --set style=<style> --set production_label=<production-id>
```

For an unknown idea, omit unresolved values and let the assistant's source task resolve them; no
paid writing can run until those inputs and the concept review are ready. Set `route=swipe` and
`source_video=<repo-file>` for a swipe. A fresh production label uses the registered ID; an existing
run keeps its actual folder label.

Repeat with just `run song-ad --brand <brand> --label <label>` to resume saved values.
Use `--from-state <repo-relative-workflow-state.json>` to resume a shared checkout's workflow.
A different format cannot reuse another workflow's state folder.

## Service the returned task

The runner returns JSON and writes `NEXT.md` plus `workflow-state.json` under
`runs/video-production/<brand>/workflow-<label>/`.

- **agent:** read the named skill/component instructions; do the work in this session. Reuse verified
  existing work. Save the requested outputs, inspect their meaning (not just file existence), then:

  ```sh
  python3 components/video-production/machine/workflow.py complete song-ad --brand <brand> --label <label> --station <station-id> --evidence <repo-file> --note <what-was-verified>
  ```

  Set newly resolved values with `--set`. Required evidence is specified by the playbook. `complete`
  accepts only the next station and hashes its evidence/inputs; it cannot approve a human review.
  Then run again immediately. This activates research, concept authoring, doctrine/creative choices,
  identity linking, song production and other component tasks instead of merely listing them.
- **command:** the runner executes the component with the current Python interpreter, without a shell.
  It records logs and requires both exit success and completion checks. Known successful commands
  are reused. Existing unrecorded artifacts require inspection, then `complete` to adopt them.
  It does not regenerate an existing brief or production run blindly.
- **decided:** nothing to do by hand. When the run reaches it, the runner hands the exact version (the asset and the
  bytes its manifest binds) to the decision layer (`components/video-teardown/machine/decide.py`), which decides from
  the owner's past calls, files the call in `runs/decisions/calls.jsonl` for him to agree with or overrule later, and
  the run continues; the call id is the station's receipt. `complete` refuses a decided station. If he overrules a
  call, the station reopens on the next run: rework the asset at its authoring station; an overruled version is never
  decided again. Owner, 2026-11-27, across all briefs: "the only thing i need to see is quotes".
- **the quote (quote: true):** the one stop that reaches the owner. Price every paid step to the cut in `quote.json`
  (`total_usd`, the lines, the stop point), show him the total and what it buys, and wait for his own go in chat.
  Record it against that exact quote, then complete the station:

  ```sh
  python3 components/video-production/machine/workflow.py go song-ad --brand <brand> --label <label> --approved-by <name> --said "<his words>" --cap <dollars>
  ```

  A changed quote needs a new go. Never record a go he did not give. Writing is never quoted.
- **review:** kept only for a quote held in `components/review` (a version-bound approval by the named person, its
  `asset.at` commit pinned). No playbook uses it for anything else.

## Paid stations and failures

A paid station runs only after the quote station holds the owner's go on that exact quote (writing is not paid:
its costs are never quoted, owner 2026-11-25). `--allow-paid <station>` is the explicit one-off for a fixture or a
station outside a quoted workflow. Production agent stations run under the go and its cap
(`run_v2.py ... --go runs/video-production/<brand>/workflow-<label>/go.json`); spend past the cap is a new quote.

A failed/interrupted command stops with a log path. Read it, fix the actual problem, then explicitly
resume with `--retry-station <id>` (and the paid permission if applicable). No unbounded retries.
If an interrupted component already finished successfully, inspect and adopt its checked output with
`complete` instead of spending again. A zero exit without the expected outputs is not success.

If evidence or inputs change, the affected station and downstream receipts stop matching. Review and
complete the corrected work; do not edit hashes or statuses to bypass it. Writing errors/held stages
cannot be adopted as complete just because a brief file exists. A stale filed brief must be refiled.

## End condition

Continue through agent, executable and decided work until the quote, the finished workflow, or an
actionable failure; a failure is diagnosed and fixed in the session, never sent to the owner. Creating a handoff package
does not send a creator a message. The launch package filed on the Meta approval page ends this workflow; going live is
the owner's click on that page, outside the run.
No claim of completion should hide an outstanding agent task, review or component error.

## Catalog and current acceptance

Use `workflow.py preview <format> --production-route ai|creator|founder` for a read-only recipe report.
`route=scratch|swipe` names the source; `production_route` names who makes it. Keep these separate.
A stored family/variant match includes its source and is not confirmation of this brief's structure.
`draft-reviewed-intake` completes only a reviewed production plan (or creator/founder maker package),
not generated media. Missing formats stay unresolved; do not infer them from a brief title.

Authoring and review are separate stations. An authoring task that prepares a review manifest writes
`{"files": {"repo-relative-path": "sha256"}}` for exactly the declared outputs, including the actual media.
The review record pins that manifest; the runner verifies both its committed bytes and every current
output hash. Replacing a clip does not inherit approval from an unchanged ledger.

Writing completion calls `video-writing/machine/writing_result.py`'s `inspect_result` and compares the
actual maker-brief hash. A file or a historical done flag cannot satisfy that station. Legacy runs without
current acceptance remain pending revalidation; do not create acceptance receipts from their old flags.
`input_files` and role-prompt bytes are part of station dependencies. Same-path edits reopen affected
stations; the same-input resume reuses their existing receipts. Production and writing labels stay
separate through `production_label`; a new production run uses its canonical brief identity.
