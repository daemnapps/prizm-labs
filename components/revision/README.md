# revision

The owner's feedback on one piece in; only the shifts he asked for out. The chain is not run again.

You say "revise my notes" or press **Revise now** under a note in the Studio. Claude runs it. You never type a command.

## What it does

| | |
|---|---|
| **Reads** | The note from the Studio's feedback box: typed words (general or exact) and/or a Tella recording (every word, the stills) |
| **Finds** | The piece's run: teardown and writing runs, a production's writing run, an email run |
| **Decides** | Which file owns each ask (`owners.json`): hook, script, spice, brief, cast, look, subject, copy… the cheapest one that holds it |
| **Writes** | A new version of only those files, as a proposal. Before, after, diff, and why, tied to his words |
| **Checks** | His exact words are in; the owner's locked lines are still in the brief; the free script check, before and after |
| **Use this** | His click puts the new files in place, keeps each old one beside it (`<name>.before-rev-<id>.md`), runs the stage check |
| **Learns** | On Use this, the kept edits and the lesson behind each ask go into the chain's learnings (`run-kit/run_kit/learnings.py`). His stated rules are in force at once; the rest once seen in a second run. Every later writing, copy, video and image run is handed them |

## Where things land

`runs/revision/<brand>/<revision id>/`: `why.md`, `diff.patch`, `before/`, `after/`, `record.json`, and the prompt and
reply of both passes. The note in `runs/studio-feedback/<brand>/feedback.jsonl` is marked `revised` and points there.

## Model

Two short passes on the "first drafts" row of `components/job-meter/model-map.json` (Sonnet). Never the owner's top
tier. About $0.25–0.35 a note on a full video brief.

## Commands (Claude runs these)

| | |
|---|---|
| `revise.py list --brand B` | notes still new |
| `revise.py run --brand B --note ID [--dry-run]` | one note |
| `revise.py run --brand B --all-new` | every new note (the nightly run; exit 3 when none) |
| `revise.py use --brand B --note ID` | put a revision in place |
| `revise.py ask --brand B --input "ID" \| "use ID"` | what the Studio's `revise` job runs |

## Rules

- Only what he asked. Anything that needs money stops at the quote, as the chain does.
- The video chain's own code is called (script check, owner-words check, stage check), never edited.

## Keys this tool needs

None of its own. The model passes run on the signed-in Claude.
