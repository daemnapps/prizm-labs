---
name: image-teardown
description: Run the image teardown — a competitor's static ad or carousel goes in, its element labels and a brief come out (the designer's work order, or a creator brief with --route creator; slide by slide with --form sequence), and an AI run ends with judged drafts in the draft folder. Use whenever someone says "tear down this static for <brand>", "tear down this carousel", "tear down this slideshow for a creator", "tear down this static for a creator to shoot", "run the image chain on <competitor>", "static teardown", "run the statics for <brand>", or names a swipe library and a brand and wants briefs from it.
---

# Image teardown

> **Activates component:** `components/image-teardown` — `chain.py start`: the records (steps 1, 2, 2b), then hands off to `components/image-writing` for steps 3 to 6, then the drafts.


External dependencies: `components/image-teardown/` (the machine: the records, the engine, the gates, the filing), `components/image-writing/` (steps 3 to 6, their prompts, the swaps record and the variations record — handed off to automatically), `brands/<brand>/` (products, avatars, offer bank), `components/swipe-paid/` and `components/swipe-organic/` (where the swipes live).

**One command. It runs the tool's own chain; nothing here adds logic.**

```
python3 components/image-teardown/chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe-library> --count 3
python3 components/image-teardown/chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe-library> --dry-run

# one picture handed over (an Instagram post, a screenshot), not a library: open its run, then run the records
python3 components/image-teardown/chain.py open --brand <brand> --file <picture> --source organic
python3 components/image-teardown/tools/run.py <the run it printed> all
```

- `--swipe` is the name of a swipe library (a competitor's folder under
  swipe-paid or swipe-organic). `--count N` runs the N hottest blocks;
  `--picks 1,2,5` runs those ranks instead.
- `--brand`, `--product`, `--avatar` are all required and are looked up in
  `brands/<brand>/`. There is no default brand.
- **Who makes it, and what it is** (the branch, 2026-09-22): `--route creator`
  writes a brief addressed to a person with a phone instead of the designer's
  work order (default `--route ai`). `--form sequence` tears a carousel or
  slideshow down slide by slide and writes a sequence brief; `--form auto`
  (default) reads it off the swipe — several stills means a sequence. So the
  four sentences are: "tear down this static" · "tear down this static for a
  creator to shoot" · "tear down this carousel" · "tear down this slideshow for
  a creator". A creator still gets a reference picture drafted, not a work
  order; an AI sequence drafts slide one and hands slides two onward to the
  `image-sequence` skill; a creator sequence drafts nothing — a person makes it.
- **`--dry-run` spends nothing** — it resolves every stage's prompt, files
  and variables, prints OK or MISSING per stage, opens no run, calls no model.
  Run it first when anything about the inputs is new.

## The matrix first

Every batch, whatever its format, is a grid before it is made: `creative_matrix.py make → check → lock → cell` in
`components/creative-diversity/`. It is not optional: step 3 does not start without the run's row. A run with none gets one
made for its person, fitted to its swipe's own format; a row the swipe breaks is held. `creative_matrix.py swipes` lists the
swipes whose format is a row's. What is written is checked against the row, and the finished picture is read back at filing.

## What it does

Every block, in parallel. **The records** (this component): teardown → the
format with the brand stripped → element labels, plus the swipe's dial read.
**The writing** (`components/image-writing`, handed off at step 3, written
into the same run): injection of our brand with its swaps record →
headlines → the brief's five variations as data (`out/variations.json`: the
approved picture plus exactly five, each one change off it, the owner
2026-10-27) → the brief. The `image-writing` skill runs the writing alone. Each finished brief gets an id (`p152`-style) and the
run ends with the draft standard — judged drafts in `components/image-teardown/drafts/<brand>/` — without
anyone asking (see the `image-draft` skill for that half).

## The rules the command enforces — do not work around any of them

1. **No brand in code or prompts.** Brand facts arrive from `brands/<brand>/`
   via `--brand`; a tool that needs one reads it off the run or stops.
2. **Every element label is a real library row** or an honest `none-fits`
   with a proposed row. An unknown id is refused and recorded, never guessed.
3. **Two gates hold a run:** *elements* after the labels; *copy* after the
   brief — no UNFILLED note, every price one the brand's offer bank sells today.
   A held run says why (`check.json`) and gets no brief id, so it never
   travels on to drafts. `--gates warn` records the verdict and carries on,
   only once a person has read the hold and overruled it.
4. **A changed prompt is a new version file** (`-vN-owner.md`, highest
   number wins), never an edit in place — and only on the owner's word.
5. **Never run a real teardown to "test" something.** The dry run is the test.

## What comes back

- Per block: the stage outputs, `elements.json`, `swaps.json`, `variations.json`, the brief, `run.json`
  and `check.json` — filed to `runs/image-teardown/<brand>/<label>/`. Pictures
  stay on Drive; media never enters the record.
- Then the drafts (three rolls per brief, judged) in
  `components/image-teardown/drafts/<brand>/vN/` (`flags.json` lists any that shipped flagged).

Report: how many blocks ran, how many briefs got ids, which were held and
why (one clause each), and the run folder.

Reply with the result and the folder it landed in (repo path or Drive folder name).
