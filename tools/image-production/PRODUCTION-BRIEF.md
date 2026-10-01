# Production brief 001 — does format change the number?

**Brand** <brand> · **Product** Brilliance Body Scrub · **Avatar** spot-hider
**Problem** `darkspots` · **Angle** `pigmentmemory` (signed 2026-09-02)
**Written** 2026-09-02 · **Status** ready to run

## The question

We now have three formats and no idea whether the choice matters. Every
static shipped so far is `photostrip`. So the first extensive test holds
everything else still and moves one thing:

> With the same problem, the same angle and the same offer, does the
> **format** change cost per purchase?

Nothing else in this brief is interesting until that is answered, because
format is the cheapest thing to change and the most expensive to get wrong —
it decides what the picture has to be.

## What is held constant

Held so the answer means something. Any of these moving makes the read
worthless.

| | |
|---|---|
| brand · product | <brand> · bodyscrub |
| avatar | spothider |
| problem | darkspots |
| angle | pigmentmemory |
| source · talent | ai · none |
| ratio | 9x16, everything inside the 4x5 safe zone |
| offer | Save 25% · Free shipping · 60-day guarantee |
| picture model | Higgsfield `nano_banana_pro`, 4:5 then padded to 9:16 |

## What moves

One axis, three arms — so the report shows three groups of ads that differ in
exactly one field. Each picture is its own ad in Meta; the arm is the grouping,
read off the ad name.

| Arm | Format | Concept | Why this concept for this format |
|---|---|---|---|
| A | `photostrip` | `handsapplication` | The format's strength is a close-up doing the proving; the scrub going onto spotted skin is that. |
| B | `confession` | `triedeverything` | The format opens with an admission. Hers is "I've tried everything under the sun" — her sentence, answered. |
| C | `fullphoto` | `spotsuptheclose` | The format gives the picture the whole frame and one hard claim. The damage itself is the argument. |

Six assets per arm, six headlines already priced against the measure.

## How it is run

> Stale since 2026-09-13: `batch.py` is retired (it ran on fal). A batch is run
> with `run.py runs/<brand>/<batch>` — see `PIPELINE.md`. The command below is
> kept as the record of how this brief was written.

```
cd image-production
python3 batch.py runs/<batch> --plates 6 \
  --problem darkspots --angle pigmentmemory --brief p141 \
  --format <photostrip|confession|fullphoto> \
  --concept <handsapplication|triedeverything|spotsuptheclose>
```

Each run names and manifests itself. Paste the printed ad unit into Meta.

## What would make this readable

- **Same adset, same budget, same window.** Three ad units in one adset, let
  Meta split. Different adsets answer a different question.
- **Enough spend to separate them.** Below roughly 25 purchases an arm, the
  difference between arms is noise, and the honest answer is "not yet".

## What the answer changes

- **One format wins clearly** → it becomes the default, and the next brief
  moves `concept` inside it.
- **No format separates** → format is not the lever. Stop building templates
  and move to angle, which is the next-cheapest thing to vary.
- **All three underperform the existing account** → the problem is upstream
  of format — the avatar, the angle, or the offer — and no amount of
  template work fixes it.

## Recorded before the numbers land

So the result cannot be reinterpreted afterwards: **the expectation is that
`confession` wins**, because it is the only arm whose opening line is the
customer's own sentence rather than a claim about the product. If
`photostrip` wins instead, the lesson is that the picture is doing more work
than the copy, and production time should move to pictures.
