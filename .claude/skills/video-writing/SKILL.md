---
name: video-writing
description: Write our version of a swipe video — a finished video teardown goes in; our injection, hooks, script, audit, spice and the shot-ready brief come out (the brief is the one document a maker opens). Use whenever someone says "write the brief for this teardown", "write this up for a brand", "run the writing on a teardown label", "turn this teardown into our script", "write the hooks and script for this one", "start a new piece from this teardown", "lock my script into the writing", "where is the brief for a teardown label", or names a finished teardown and wants the brief.
---

# Video writing

> **Activates component:** `components/video-writing` — `machine/run.py`, the writing stages (injection, hooks, script, audit, spice, brief) on a finished video teardown.


External dependencies: `components/video-writing/` (`prompts/` and `prompts/v2/` hold every writing prompt, highest `-vN-` is live), `components/video-teardown/machine/` (the chain engine the writing runs on, and the station that must have finished first), `runs/video-teardown/_work/<label>/` (the finished teardown it reads and writes into), `runs/video-writing/<brand>/` (the shelf the written words are filed to).

**Station 2 of four** (teardown · writing · production · edit). It does not read the swipe (video-teardown does) and does not make the video (video-production and video-edit do). The teardown must already be finished through stage 2 on a route, or the command stops and says so.

**One command. One finished teardown.**

```
python3 components/video-writing/machine/run.py <teardown label | teardown run folder>
python3 components/video-writing/machine/run.py <label> --piece <new label>
python3 components/video-writing/machine/run.py <label> --owner-script <locked script.md>
python3 components/video-writing/machine/run.py <label> --revalidate
python3 components/video-writing/machine/run.py --help
```

- `<label>` is the teardown's folder name under `runs/video-teardown/_work/`, or the full path to that folder.
- `--piece <new label>` starts a NEW piece from a finished teardown: the teardown's record is copied into a new folder, its frames and video are linked, never torn down again, and the writing runs there.
- `--owner-script <file>` locks the owner's own script into the writing: every pass carries its lines verbatim and the brief is HELD if one is missing.
- `--allow-new-format` writes on a format that has not been ruled on yet — test runs only; do not use it for real work.
- `--revalidate` checks the existing brief once without writing passes or repairs. It preserves source bytes and the audit retry budget, records every final gate in `revalidation/`, and issues acceptance only when all required checks complete. Review model calls may cost money. A skipped/unavailable reviewer, proposed content change or open finding keeps it held; fix the named issue before another explicit check. Do not combine with input-changing flags. Exact already-accepted inputs reuse their receipt without model calls.
- `--sandbox` is for a test copy of a run (the swipe-library shelf goes inside the copy). Not for real work.
- **There is no `--dry-run` on this command.** It makes paid model calls from the first writing pass. Do not run it to "see what happens". The free check is the test suite: `/usr/bin/python3 -m unittest discover -s components/video-writing/tests` (spends nothing; proves every pass's prompt exists and every `{slot}` has a source).
- The shared mini has its own door, `machine/mini_step.py --brand <brand> --label <label> --out <dir> [--route ai|creator|founder] [--dry-run]`; its `--dry-run` makes zero model calls and says whether every writing pass resolves. That door fetches the teardown from the shared drive and is meant for a run filed to the mini, not for a person's quick run here.
- Alternatively the teardown hands off by itself: `python3 components/video-teardown/machine/run.py <video> --brand <brand> --route ai --v2 --writing v2`.

Before running it for a person: confirm the teardown exists and say which brand and route it is on, and tell them it spends money on model calls. Run it only when they have said to.

## What it reads

The finished teardown's stage files in `runs/video-teardown/_work/<label>/stages/` (0 through 2), the run record `run.json`, the brand's own context from `brands/<brand>/` (read, never written), and the prompts in `components/video-writing/prompts/v2/`.

## Verbatim evidence before creation

For source-based writing, assemble the evidence before starting the injection: exact winner words (including on-screen text for a wordless winner), the swipe transcript and on-screen text, and full selected customer records with their IDs, attribution, source and surrounding context. Keep those originals in the run; a description of what they mean does not replace them. Cite source paths and ranges or record hashes so the extraction can be checked.

Put the verbatim inputs and this run’s combination requirements in its `RULINGS.md` so every writing pass receives them. Verify the saved `prompts/` actually contain the evidence. `machine/writing_v2.py` also carries earlier literal language rows into subsequent calls; a fresh retrieval does not erase earlier evidence.

In the injection’s `SOURCE COMBINATIONS`, map each new line to the exact source words and IDs. Distinguish unchanged quotes, combinations and authored joins. Preserve assumed attribution and conflicting source facts; a comment is not verified-buyer proof, and a draft score is not measured performance. Keep original drafts when revising. Review the final spoken and on-screen words against these sources before calling the revision complete.

## The rules the command enforces — do not work around any of them

1. **Only a finished teardown goes in.** No teardown at that label or path: it stops with "run the teardown first".
2. **The AI lane writes on v2; creator and founder runs write on v1** (the teardown keeps v1 writing for any other route, and v2 refuses one before any call). All routes write on the same lane, spice and realism rules — paid and organic are the same video.
3. **The writing has seven ordered passes:** injection, controlling idea, reading plus hooks, placement plus expansion plus close, audit, spice, brief. The audit can repair the named pass at most twice per run; that budget persists across resumes.
4. **The highest `-vN-` in a prompt folder is the live one**; older ones sit in that folder's `archive/`. The prompts are versioned files, never edited in place.
5. **The owner's locked script is carried verbatim.** With `--owner-script`, a brief that is missing any of its lines is HELD, named in the run record.
6. **A held or unverified run exits non-zero.** Read `writing-result.json` or the provider-free `machine/writing_result.py.inspect_result(run_dir)`: `artifact_written` is separate from `accepted`. An inherited passed flag or a changed brief never proves acceptance. AI filing keeps text archives but does not promote or number unaccepted output.
7. **The stage-5 gates run here:** the swipe match (5m), the manifest check (5n) and the cast match. A brief that fails them is held with its reason, not passed.
8. **Cost is never a reason to give a pass less to read.** Each call logs its real cost and seconds on the run record.

## What comes back, and where it lands

- The written stage files go into the teardown run it was handed: `runs/video-teardown/_work/<label>/stages/` (`3-injection.md`, `4a-reading.md`, `4b-hooks.md`, `4c-placement.md`, `4d-expansion.md`, `4e-close.md`, `4f-audit`, `4g-spice`, `5-brief.md`).
- The teardown's filing copies the written words to the shelf: `runs/video-writing/<brand>/<id>/` with
  - `deliverable/5-brief.md` — the brief; this is the one a maker opens
  - `stages/` and `prompts/` — each stage's output and the exact prompt it ran on
  - `run.json`, `manifest.json`, `swipe-match.json`
- `runs/video-writing/INDEX.md` is the index of every brief (route, product, avatar, awareness, format, source).

Report: written or held (and why, one clause), the cost the run record shows, and the brief itself — show its opening so the person sees it without opening anything.

Walls: this component sends nothing outside and writes nothing into `brands/`. It writes only into the teardown's run folder and the `runs/video-writing/` shelf. Creator and founder runs write on v1; there is no `--dry-run` on the main command.

Reply with the result and the folder it landed in (repo path or Drive folder name).
