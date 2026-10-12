# The variation batch — how a brief's variations become a loadable batch

**Ruled by the owner, 2026-09-23:** *"we need to just focus on this image editing
so we can get our batch of variations from the briefs, that's the whole point
of this stage specifically."* This file is that stage. It is the sibling of
`DRAFT-STANDARD.md`: that one turns a swipe into one judged picture, this one
turns that picture into the batch.

**Where it stops.** At named pictures and one list. **Not** at ad copy, not at
a Meta import sheet — taken out of this stage on his word the same day
(*"don't worry about primary text yet, remove that from the chain"*). A stage
that waits on copy is a stage that does not ship pictures.

```
chain.py variations --brand brand-a --product glow-body-scrub
chain.py variations --brand brand-a --product … --briefs p158,p159
chain.py variations --brand brand-a --product … --dry-run      spends nothing
chain.py variations --brand brand-a --product … --no-name      stop after the judge
```

(`tools/variations.py` is the same thing; `chain.py variations` just calls it.)

## What goes in

Two things the chain already made, and nothing else:

| | |
|---|---|
| **the baseline** | the brief's judged draft — the winner, made by the draft standard |
| **the variations** | what stage 4 wrote for that brief: five headlines, each already measured against that layout's own character ceiling |

A brief with no judged draft, or whose stage 4 wrote no variations (a
text-free ad), is **listed as skipped and nothing is invented for it**. Its
variations are pictures, which is a generation, not an edit — a different
stage.

## The seven steps

| # | Step | What it does |
|---|---|---|
| 1 | **read** | each brief's written variations (`tools/headline_sets.py`). Stage 4 is a writing prompt, so twenty-one briefs wrote the same thing six ways; they are read in order of how much each shape can be trusted, and the line table wins because that is the one stage 4 counts characters against |
| 2 | **generate** | one call per variation, through the image-edit engine, with the brief's own draft as the reference. The instruction carries the delta and nothing else |
| 3 | **judge** | the two-picture judge — change present · nothing else moved. Anything that moved more is held with its reason |
| 4 | **stage** | baseline first, then its variations, one folder per brief — the order the asset ids follow |
| 5 | **name** | the convention, one ad unit per brief, assets `a01…aNN`. The format comes off the run's own element labels (stage 2b), never guessed |
| 6 | **list** | `drop.csv` — every asset, its ad name, and the headline it carries. The headline also goes into each manifest, because the headline is exactly what the name leaves out |
| 7 | **mirror** | Drive, at the mirrored runs path |

Output lands at `runs/image-teardown/<brand>/<label>/` on both planes since
2026-10-08 (SI-48 (teardown drops home): a drop is image-teardown's run, and
the run index counts it there). Before that it landed under **image-edit**,
the name said out loud since 2026-09-23 (the owner, reading a
finished drop: *"why did this go into reference edit? … image edit instead,
since it's a final run for this chain"*) and, since 2026-09-30, the engine's
own folder name too (`tools/image-edit/`, was `reference-edit`).

## The five rules this stage enforces

1. **One delta per picture.** The baseline carries the composition; the
   instruction carries the one thing that moves. A difference in the account
   can then only be that thing.
2. **One call per variation, never one call with five.** The engine names a
   result's folder after the row it ran, so five `headline` rows in one call
   land on top of each other.
3. **A refusal is retried before it is believed.** The image provider
   rate-limits a burst — six at once refused fifty-four of sixty on
   2026-09-23, and every one of them succeeded alone.
4. **The picture on disk is the truth.** A state file can be overwritten by a
   dry run and its paths rewritten by a move; a delivered picture cannot. The
   stage reads what is on disk before it believes any record.
5. **A partial run never shrinks the batch.** A `--briefs p158` re-run is
   normal — a retry, one more ad — and the record and the list accumulate
   rather than being replaced. Both were rewritten down to six rows before
   this was fixed (2026-09-23).

## What comes back

- `runs/image-teardown/<brand>/<label>/drop.json` — every variation attempted,
  its state, and the ad unit each brief was named as.
- `.../deliverable/<brief>/` — the named assets and their manifest.
- `.../deliverable/drop.csv` — the whole batch in one list, which is what a
  person loads from.
- The same deliverable on Drive.

Report to the owner: how many ads, how many assets, which variations were held
and why (one clause each), and a contact sheet — baseline left, its
variations beside it. No paths, no commands.

## The run that set the standard

Brand A body scrub, 2026-09-23, batch `260923a`. Twelve ads carried written
headline variations; sixty were attempted and forty-three made. Ten ads named.
Nine ads carry no headline at all, so they were skipped by rule rather than
invented for.
