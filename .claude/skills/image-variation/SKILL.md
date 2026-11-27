---
name: image-variation
description: Make clean variations off one baseline draft — the baseline plus one or more named variations from the library (headline · angle · person · product · colour · background · reframe) go in; N pictures come out, each ONE delta off the baseline, each judged against it. Use whenever someone says "give me the headline and angle variations of p152", "variations of this draft", "run the brief's variations", "same ad, different person", "swap the headline on this", "this one in the gold accent", "reframe this for 4:5", "image variation", "what variations are there", or names a baseline and a variation.
---

# Image variation

> **Activates component:** `components/image-edit and components/image-teardown` — `vary.py` for one baseline; `chain.py variations` for a brand's batch.


External dependencies: `components/image-edit/` (the engine; `library/variations-vN-owner.json` the library, `splits.json`, `prompts/compare-judge-vN-owner.md`), `components/image-production/` (the image engine), `brands/<brand>/` (the product photo that rides along on a product swap — read, never written), `components/image-teardown/` (stage 4e of a brief writes its variation list against these ids; the baseline is that brief's draft).

## The batch off a brand's briefs — the usual job

the owner, 2026-09-23: *"we need to just focus on this image editing so we can
get our batch of variations from the briefs, that's the whole point of this
stage specifically."* For a whole brand rather than one baseline, the chain
owns it — generate, judge, stage, **name to the convention**, one list,
mirrored to Drive:

```
python3 components/image-teardown/chain.py variations --brand <brand> --product <slug>
python3 components/image-teardown/chain.py variations --brand <brand> --product … --briefs p158
python3 components/image-teardown/chain.py variations --brand <brand> --product … --dry-run
```

It ends at named pictures and `drop.csv` — **not** at ad copy or a Meta
import sheet, taken out of this stage on his word the same day. The ruling
and its five rules: `components/image-teardown/VARIATION-STANDARD.md`. A brief
with no written variations is skipped, never invented for.

Report back: how many ads, how many assets, what was held and why, and a
contact sheet — baseline left, its variations beside it.

## One baseline, one delta — the underlying command

```
python3 components/image-edit/vary.py <baseline.png> --brand <brand> --v headline:headline="Stop the itch tonight"
python3 components/image-edit/vary.py <baseline.png> --brand <brand> --v angle:headline="…",proof="…" --v person:who="a woman in her fifties"
python3 components/image-edit/vary.py <baseline.png> --brand <brand> --v colour:from_colour=teal,to_colour=gold
python3 components/image-edit/vary.py <baseline.png> --brand <brand> --v product:product_name="…" --product <slug>
python3 components/image-edit/vary.py <baseline.png> --brand <brand> --v reframe:aspect=4:5
python3 components/image-edit/vary.py <baseline.png> --brand <brand> --v … --dry-run
python3 components/image-edit/vary.py --library                   # the rows, verbatim
```

- `--brand` is required. Each `--v id:key=value,…` is one row from the
  library with its slots filled; a missing slot is refused BY NAME.
- `--keep "…"` adds one more thing that must not move; `--ref <png>` attaches
  another reference; `--product <slug>` attaches the brand's product photo;
  `--count N` rolls per variation.
- **`--dry-run` spends nothing.**
- The baseline is a draft the draft standard already made (the `image-draft`
  skill); its brief's variation list names the rows to run.

## The rules the command enforces — do not work around any of them

1. **The instruction carries the delta and nothing else.** The baseline
   carries the composition. Past 400 characters it is refused, unspent.
2. **One change per variation.** Two variations are two edits, each off the
   baseline — never one edit off another.
3. **The baseline is never written to.** Every result is a new version.
4. **Every result is judged against the baseline** by the two-picture judge:
   CHANGE PRESENT · NOTHING ELSE MOVED · the row's own test — after the image
   engine's own judge. Anything that moved more is held under `rejected/`
   with its reason. The judge not running is a HOLD.
5. **Refused, never guessed.** An unknown row or slot names the real ones.
6. **9:16 only, content in the 4:5 zone** — edited at 4:5, finished.
7. **Every library row is `draft` until the owner marks it approved.** A changed
   row is a NEW file `-v<N+1>-owner.json`.

## What comes back

`runs/image-edit/<brand>/<label>/<id>/` — one folder per variation with
its `edit.json`, its result and any `rejected/`; the set's record in
`variations.json`; pictures mirrored to
`Shared Assets/runs/image-edit/<brand>/<label>/`.

Report: per variation, pass or held (one clause), and a contact sheet —
baseline left, each variation right — sent as an image.

Reply with the result and the folder it landed in (repo path or Drive folder name).
