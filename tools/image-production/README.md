# Stage two — brief to finished ad

> The short version — what it takes, the steps, the gates, where a run files,
> the dry run — is `CLAUDE.md`. This file is the long version: the eight steps
> of a build and the failure each one was written after.

Stage one ends at a brief. This is everything after it.

**It is not one generation call.** Eight steps, each with its own output and its
own way of failing. Written out because the failures below were all found the
hard way, by doing it by hand, and every one of them is invisible if you think
of this as "generate the image".

**The brief is the only input.** Not the run folder, not the stage outputs, not
somebody's memory of what we decided. If a fact is not in the brief, it does not
reach the ad — that is what a brief is *for*, and it is the whole reason stage
one exists as a separate thing.

---

## 1 · Read the brief

Take from it, and nothing else:

- **the plates to make** — the control, then each picture variation
- **the layout data** — every text element with its position, weight, size,
  colour, tracking, measure and line count, and per-fragment colours where a
  line carries two
- **what is composited rather than generated**, and the file each comes from
- **the accept tests** — the three to five checkable things
- **the negative constraints** — what must not appear

If the brief names no plates, stop. A missing plate list is a stage-one defect
and it is cheaper to fix there.

## 2 · Make the plate

The photograph, **with no words in it at all**.

**The source ad is attached as the layout reference.** Measured across six
rebuilds, 2026-08-26: subject, wardrobe, props, action, environment, light,
grade, texture, shot size, height, angle and lens all survive being described in
words. **Where the camera stands does not** — it came back wrong every time,
including when stated plainly and repeated in the negatives. The reference is
how the frame is held; the words carry everything inside it.

One plate per picture the brief names. The control first — it is the baseline
every variation is a bet against.

**On Higgsfield, and nowhere else** (ruled 2026-09-05, restated 2026-09-13).
It is the only place that holds the roster identities and `flex-360-true`, the
product built from seven real turntable angles — and a picture is only as good
as its references. Generated at 4:5 and padded to 9:16 afterwards; the cast and
the product go in as Element ids, never as words.

**Two models, not one** (2026-09-14). Generating a photoreal PERSON and
painting everything else are different jobs, so they route to different models:

| The frame | Model | Why |
|---|---|---|
| has a person in it (`cast` is set on the ad) | `gpt_image_2` | built for human realism |
| has no person — product, surface, scene | `nano_banana_pro` | quality, text and diagrams |

`plates.py prepare` decides this per job and writes the reason into
`jobs.json` beside it. An ad that names its own `model` still wins, and so
does a batch that names one — a measured exception outranks a default.

**Every batch.json written before today carries `"model": "nano_banana_pro"`
at batch level, which suppresses the routing.** Drop that line from a spec to
let it route, or run the split as a test first:

```bash
# every plate both ways, slug@model, same prompt and same refs
python3 tools/plates.py prepare --run runs/<brand>/<batch> --ab nano_banana_pro
```

The only thing a side-by-side off that can be showing you is the model.

The fal path is retired. `generate.py`, `iterate.py` and `batch.py` all stop on
their first line, and the client is parked under `tools/superseded/fal/` so an
old run's records still read.

## 3 · Judge the plate before anything is built on it

The brief wrote three to five checkable things. Run them now, on the plate
alone, before a single character of type goes near it.

- Does the load-bearing action read correctly?
- Are hands and anatomy coherent?
- Is every band the brief declared empty actually empty?
- **A legible third-party brand anywhere in frame is an automatic reject.**
  Always. Every time.
- **Is the result believable?** If the frame shows an after state, a treated
  area or a transformation, it has a **credibility budget** and blowing it is a
  reject: the improvement is partial (~60-70%, never cleared), 3-5 of the
  original marks survive, freckles and texture are preserved, the same person
  in the same light, no glow and no plastic skin. *If the treated area looks
  like a brochure, that is a fail.*

  The budget lives once, in `style-packs.json` under `_result_budget`:
  `prompt.py` appends it to `anchors` and `negatives` for any slot file with
  `"result": true`, and `judge.py` checks the same list off the picture that
  comes back. A brief can tighten it with a `**Result budget**` block.

  Added 2026-09-14. Our texture slot already held skin truth; nothing held the
  CLAIM, so a plate that cleared the skin completely passed every test we ran.
  That is a believable machine shipping an unbelievable ad.

A plate that fails gets regenerated or killed. It never gets composited "to see
how it looks" — that is how a bad picture acquires enough sunk cost to ship.

## 4 · Measure the plate that actually came back

**The step everyone skips, and the one that broke the first finished ad.**

The source's black band began at 60% of frame height. The generated plate's
began at 63.9%, and its product inset sat lower than the source's. Carrying the
source's percentages across verbatim put the headline underneath the product
circle.

So: measure the real plate. Where does the empty band actually start? Where did
the inset ring actually land? Then **adapt the positions to this plate while
holding the layout's shape** — same axis, same order, same block proportions,
same gutters. The shape is the format. The numbers belong to the picture that
got made.

## 4b · What gets generated, and what gets drawn

**The plate is a photograph and nothing else.** Every graphic element on top of
it is drawn by the compositor, at full precision, from real assets. Getting
this line wrong is what makes an ad look almost-right in a way nobody can name.

**Generate** — the things a camera would have captured:
subject · skin, texture, condition · wardrobe · setting · lighting · grade ·
depth of field · the whole photographic feel.

**Draw or composite** — the things a designer would have made:

| Element | Why never generated |
|---|---|
| **Type** | Exact characters, real typeface, real weight. A model approximates letterforms. |
| **The logo** | A wordmark is either right or it is wrong. There is no close. |
| **The product** | It carries printing and a crest. Composited from the packshot. |
| **Boxes, squares, rules, frames** | A generated rectangle has soft, wandering edges and an off-square corner. A drawn one is crisp at any size. |
| **Stickers and their outlines** | The white stroke around a cut-out product is a uniform offset. Generated, it varies in width and eats the edges. |
| **Badges, bars, price blocks** | Flat fills with exact hex values. |

**The tell is edges.** Anything with a hard edge, an exact colour or a
character in it belongs to the compositor. Anything with light falling across
it belongs to the camera. A format that reads as sharp — a stroked square over
a soft macro, a flat white box against skin — is exactly that contrast, and it
only works if the sharp half is genuinely sharp.

**And the joins are the craft.** In the format we swiped, the headline box is
*flush* against the bottom edge of the target square and shares its left edge —
one shape reading as two. A half-pixel gap or a misaligned edge is the
difference between designed and assembled.

## 5 · Composite the product

From the brand's own packshot, cut out, into its container.

**Never generated.** The tube carries a wordmark and a crest; a model
approximates both, and a near-miss on a brand mark is worse than no product in
frame. Same reasoning as the type.

Match the container fill to the packshot's own backdrop and feather the join, or
cut the product out properly — a rectangle of one grey sitting inside a circle
of another grey reads as a mistake even when nobody can say why.

## 6 · Set the type

From the layout data, by the compositor, never by the image model.

Every character exact. Weights come from the data — **a weight is a different
typeface file, not a flag**, and a bold headline recorded as prose rebuilds in
regular with every word correct and the ad still wrong. Per-fragment colours and
panels where a line carries two: a two-tone badge is one line of two segments,
each with its own fill, never one box on the element.

The compositor reports every step-down it had to make. A headline that dropped
from 96pt to 61pt to fit is telling you the copy is too long for the space,
which is a copy decision and not a layout one.

## 7 · Prove it, and fix it before it leaves

**A known flaw is never delivered with a note attached.** Damon, 2026-08-31:
*"if you see the problem, then don't fucking deliver it."* Handing over a
broken ad and describing what's broken moves the work of noticing onto the
person who asked, which is the one thing this machine exists to take off them.

If a check fails, the fix happens here. If the fix needs a regeneration, it
gets regenerated. The ad leaves when it is right, not when it is explained.

Side by side with the source ad, at the same height.

Plus the compositor's notes: every size step-down, every keep-clear overlap,
every measure it had to fight. A finished ad with three warnings behind it is
not finished — it is a draft that rendered.

## 8 · Then multiply, cheaply

**A headline swap is a recomposite.** Same plate, words reset over it —
seconds, no generation, no spend. Six headlines over one approved plate is six
recomposites.

**A picture swap is a generation.** That is the expensive axis, and it is why
the brief prices the two separately and says which variations can be reached by
recompositing instead.

So the order is: approve one plate, spin every headline against it, and only
then spend on the pictures the brief argued for — cheapest and most-defensible
first, stopping wherever the returns stop.

---

## What runs each step

| Step | Runs on | Output |
|---|---|---|
| 1 · read the brief | — | the plate list and the layout data |
| 2 · make the plate | `tools/plates.py prepare` &rarr; a session on the Higgsfield MCP &rarr; `plates.py ingest` | `inbox/<slug>.png` |
| 3 · judge the plate | `tools/judge.py` (plates) · `tools/finish.py` (finished ads) — measured checks, then a vision model against the brief's tests; then the **media gate** (`tools/gates.py`) holds what failed | pass, or held with the reason in `check.json` |
| 4 · measure the plate | code | positions adapted to this plate |
| 5 · composite the product | ImageMagick | the plate with its product in |
| 6 · set the type | ImageMagick, from the layout data | the finished ad |
| 7 · prove it | ImageMagick | `finals/source-vs-output.jpg` |
| 8 · multiply | ImageMagick for headlines, `make_variations.py` + a session for pictures | the set |

**Three of the eight are a person's, and they are the three that matter**: which
plate is good enough (3), whether the finished ad is actually right (7), and
where to stop spending (8).

## The format is the swipe's, not the last one's

**Measured cause, 2026-08-31.** The compositor carried one hardcoded layout —
centred wordmark, white square framing the damage, headline in a box beneath,
product as a rotated sticker on the corner. That is angle 02's format. It was
drawn over angle 06 and angle 09, which share none of it, and both shipped.

The layout data was in each brief the whole time: margins, per-zone position,
measure, cap height, alignment, case, tracking, colour, max lines,
decorations, keep-clear rectangles. Nothing read it. The teardown had done its
job and the last step threw the answer away.

So, in `render.py`:

1. **Every element is drawn from the format's own layout data.** Position,
   measure, alignment, cap height, colour, tracking, case, line count.
2. **Nothing is drawn unless a zone names it.** A format with no wordmark zone
   gets no wordmark. Angle 02 has one; 06 and 09 do not, and both were being
   stamped with a logo their format never had.
3. **A chromatic colour that is not ours is refused, not painted.** Injection
   is meant to replace the swipe's accent. When it does not, the renderer
   draws the neutral and flags it — a headline shipped in the competitor's
   pink on 2026-08-31.
4. **The product fits its zone's box, not just its height.** Sizing to height
   alone pushed a tube off the frame edge.
5. **The product's zone is checked for content before the product lands on
   it.** Gross occupation only — calibrated against a real plate, and the
   limit is written where the check is.

The same failure has one shape every time: a measurement exists, and the step
that needed it guessed instead. When a stage produces data, the next stage
reads that data. Not a default, not the last run's, not a sentence describing
it.
