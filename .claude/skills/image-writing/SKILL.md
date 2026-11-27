---
name: image-writing
description: Write our version of a torn-down static ad — a finished image teardown goes in; our injection (with its swaps record), the headlines, the brief's five variations as data and the brief come out. Use whenever someone says "write the brief for this static", "run the writing on <run>", "re-write the brief for <run>", "write the variations for <run>", "give me the five variations as data", "re-run stage 5 on <run>", "re-run the brief on <run>", or names a torn-down static and wants its brief or variations.
---

# Image writing

> **Activates component:** `components/image-writing` — `run.py`, the writing steps 3 to 6 (injection, headlines, variations, the brief) on a torn-down static.


External dependencies: `components/image-writing/` (`prompts/` holds every writing prompt, highest `-vN-` is live; `templates/` the standard brief; `tools/` the steps, the swaps record and the variations record), `components/image-teardown/` (the chain engine the writing runs on, and the station that must have finished steps 1, 2 and 2b first), `brands/<brand>/` (products, avatars, offer bank — read, never written).

**Station 2 of the picture line** (teardown · writing · production · edit · Model House). It does not read the swipe (image-teardown does) and does not make the pictures (image-production makes the first one, image-edit the five variations).

**One command. One torn-down run.**

```
python3 components/image-writing/run.py <run> all --brand <brand> --product <product> --avatar <avatar> --dry-run
python3 components/image-writing/run.py <run> all --brand <brand> --product <product> --avatar <avatar>
python3 components/image-writing/run.py <run> 5,6 --brand <brand> --product <product> --avatar <avatar>
python3 components/image-writing/run.py --help
```

- `<run>` is the run's folder name under `components/image-teardown/runs/` (several, comma separated, run in parallel).
- The steps are `3`, `4`, `5`, `6` or `all` (3 to 6). Steps 1, 2 and 2b are refused here: they are the image teardown's.
- `--sub`, `--ask`, `--controls <preset>` and `--gates hold|warn` work as they do on the teardown.
- **`--dry-run` spends nothing**: every prompt, file and variable resolved, OK or MISSING per step, no model called. Run it first.
- The teardown hands off by itself: `chain.py start ...` and `components/image-teardown/tools/run.py <run> all` run 3 to 6 through this station. This command is for the writing alone (a new prompt, a re-write).

Before running it for real: say which run, brand and product, and that it spends money on model calls. Run it only when they have said to.

## The rules the command enforces — do not work around any of them

1. **Only a torn-down run goes in.** No run at that name: it stops. A run held at the elements gate does not reach step 3.
2. **The batch is six pictures: the approved one plus exactly five variations** (the owner, 2026-10-27). Step 5 writes the five as data, each ONE change off the approved picture, and code reads them into `out/variations.json`. A record with any other count, or a row that changes nothing or carries a key image-edit does not read, is sent back once with the reason, then left unwritten and said so.
3. **Step 3 writes the swaps record** (`out/swaps.json`); a broken one is sent back once.
4. **The copy gate after step 6:** no UNFILLED note, every price one the offer bank sells today, the standard brief's sections in order. A held run says why in `check.json`.
5. **A changed prompt is a new version file** (`-vN-owner.md`, highest number wins), never an edit in place, and only on the owner's word.

## What comes back, and where it lands

Into the run it was handed, `components/image-teardown/runs/<run>/out/`: `03-injection.md` + `swaps.json`, `04-headlines.md`, `05-image-variations.md` + `variations.json` (the five rows), `06-brief.md` (section 6 lists the same five). The teardown files the words to `runs/image-teardown/<brand>/<run>/`.

The five variations are made by image-edit from the approved picture: `python3 components/image-edit/vary.py <approved.png> --brand <brand> --from-brief components/image-teardown/runs/<run>/out/variations.json --dry-run`.

Report: written or held (and why, one clause), and the five variation lines from `05-image-variations.md` so the person sees them without opening anything.

Walls: sends nothing outside, writes nothing into `brands/`.

Reply with the result and the folder it landed in (repo path or Drive folder name).
