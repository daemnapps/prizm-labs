# Running the image chain on a brand

Every brand, every swipe, same four facts. Nothing here names a brand.

## 1 · Check it can run

```
tools/preflight.py --brand <brand> --product <product> --avatar <avatar> --swipe <swipe>
```

Three checks, exits non-zero if any fail. **AGNOSTIC** — no brand or swipe
named in the code or prompts that drive a run. **PROMPTS** — every
`{placeholder}` a prompt asks for is supplied. **INPUTS** — every file the six
stages will want, resolved before starting rather than nine minutes into
stage 3. **BASELINE** — the cast and product this brand's drafts use.

### Dry run — see everything resolve, spend nothing

```
chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe> --dry-run
chain.py fill  --brand <brand> --product <product> --avatar <avatar> --dry-run
tools/run.py <run> all --brand <brand> --product <product> --avatar <avatar> --dry-run
```

Names the runs it would open, then for every stage prints the prompt file, the
model, and each file and variable the stage would be handed — **OK** or
**MISSING**. No model is called, no run is opened, nothing is written. Exits
non-zero if anything is MISSING.

## 2 · Pin the cast, once

```
chain.py baseline --brand <brand> --product <product> --avatar <avatar> --cast <roster id>
```

Writes `drafts/<brand>/baseline.json`: brand, product, lane, core avatar,
sub-avatar, the cast and the product Element. **Omit `--cast` and it chooses
by fewest uses, biased by `--problem`. Give `--cast` and he is pinned** — a
later run keeps him, because a tool that re-picks the cast on every run is
how a batch loses its man halfway through. `--recast` to choose again.

A brand with no roster casts nobody. That is an answer, not a missing file.

## 3 · Run the chain

```
chain.py start --brand <brand> --product <product> --avatar <avatar> --swipe <swipe> --count 3
```

Picks the most-duplicated angles in that swipe library — one block per angle,
because several records often share one title — pulls a still for each off
Drive, runs all six stages on every run **in parallel**, gives each finished
brief an id out of `briefs.json`, and rebuilds the pages.

Stage one ends at a brief. It never writes a production spec: that step is a
person's.

### What every run now records (2026-09-20)

**Element labels (stage 2b).** After the format is written, the run is labelled:
which `format/image`, `style/image`, `framework/all` and `doctrine/awareness`
row of the element library the swipe IS. The ids are checked against
`components/elements`; one the library does not hold is refused and written
down, never guessed, and `none-fits` comes with a one-line proposed row. The
result is `out/elements.json`. `chain.py fill ... --labels` labels older runs.

**Two gates.** *elements* after 2b; *copy* after the brief (no UNFILLED note;
every price in the part that gets built is one the brand's offer bank sells for
that product). A run that fails is **held**: it says why on screen and in
`check.json`, and gets no brief id. `tools/gates.py <run>` prints the verdict.
`--gates warn` records the verdict and carries on.

**The record.** Every run — not only variants — files to
`runs/image-teardown/<brand>/<run>/` at the repo root: stage text,
`elements.json`, `source.json`, `run.json`, `check.json`. Never pictures.

## 4 · Look at them

`http://127.0.0.1:8792` — every brief with its swipe, its injected frame, its
headlines, its pictures and every note the chain resolved. Always on; it
survives a reboot.

## 5 · Drafts

A draft is the whole ad in one image, for review — words included, so the
idea can be judged. It is **not** the shipping ad, which composites type at
full precision.

Prompts are assembled from thirteen slots, never written as prose, so a
regeneration can only move what you moved:

```
../image-production/tools/prompt.py render --slots drafts/<brand>/slots/<id>.json
../image-production/tools/prompt.py diff --a before.json --b after.json
```

Slot files name no person. `@cast` and `@product` resolve from the baseline,
so **running the same batch on a different man is one flag**:

```
prompt.py render --slots <f> --cast <roster id>
```

His Element and his own roster lines come with him. A cross-lane swap is
refused.

The register — shot, light, grade, style, texture, negatives — comes from a
style pack in `../image-production/style-packs.json`, so the same subject
renders as candid UGC or flat vector by changing one word.

## What a new brand needs

| | where | if it is missing |
|---|---|---|
| products | `brands/<brand>/products/<product>.md` | the run stops — this is the thing being sold |
| core avatar | `brands/<brand>/core-avatars/<avatar>/profile.md` | the run stops |
| offer bank | `brands/<brand>/offers/offer-bank.md` | the run stops |
| identity anchors, palette | `brands/<brand>/` | the run stops |
| angle bank | `brands/<brand>/strategy/angles.json` | stage 6 proposes angles instead of matching |
| casting roster | `brands/<brand>/core-avatars/casting/` | nobody is cast; formats without a person still run |
| swipe library | `swipe-paid/<swipe>/blocks/` | there is nothing to tear down |
| the swipe on Drive | `Shared Assets/swipe-paid/<swipe>/` | no stills to open a run on. Drive names this folder `blocks` for some brands and `angles` for others; both are read |

Brief ids come out of a per-brand block, allocated on first use. Nothing to
set up.

## The chain always ends the same way

Ruled 2026-09-14. A brief is not finished when stage 6 writes it. It is
finished when it is **ready for the designer**, and that means five things,
every time, for every brand:

| | |
|---|---|
| six stages | the teardown through to the brief |
| an id | `pNNN`, out of the brand's own block, for life |
| a draft picture | the swipe reproduced with our woman, our tube and our words — judged, best passing roll (`DRAFT-STANDARD.md`) |
| a page | on the briefs tool, under its brand |
| a folder on Drive | source, draft and brief together |

`chain.py start` does all of it and finishes by printing what is still
missing. `chain.py ready --brand <b>` answers the same question any time.

**The pages do not claim readiness they do not have.** A brief missing its
draft says *"Waiting on a draft picture"*, not *"Ready for the designer"* —
that claim was printed on every card regardless until 2026-09-14, which is
how nine <brand> briefs showed as ready while none of them had reached
Drive.

**The draft is made by the chain, not by a session** (Damon, 2026-09-17:
"put this in chain"). `start` ends by running the draft standard —
`chain.py draft --brand <brand>` on its own — which generates three rolls
per brief with the swipe as the reference, judges every roll, ships the best
passing one to Drive, the pack and the board, and names the briefs that got
nothing and why. `DRAFT-STANDARD.md` is the ruling; do not deviate from it.

## 6 · The work order — what the designer actually gets

```
chain.py worksheet --brand <brand>        every brief in that brand
chain.py worksheet --briefs p143,p144     named briefs
tools/deliver.py --brand <brand>          push it all to Drive
```

A finished brief is written for the person deciding what to make. The designer
is not that person — they are in Higgsfield, not in the repo, and they need a
job rather than an argument.

`worksheet` renders the brief's whole picture set as runnable prompts. Stage 5
names a control plus three or four variations, one variable moved each time,
but only the control ever had a prompt; the rest lived as prose. Every
variation now inherits the control's slots — same pack, same fidelity line,
same negatives, same references — and changes only its own subject, which is
what makes the set a test instead of four unrelated pictures.

It writes, per brief:

```
worksheets/<brand>/<brief>/work-order.md      the one page
worksheets/<brand>/<brief>/prompts/00-control.txt
worksheets/<brand>/<brief>/prompts/01-<name>.txt   …paste-ready
```

`deliver.py` puts those next to `source.jpg`, `draft.png` and `brief.md` in the
brief's own Drive folder, so the folder is the whole job and the designer never
opens anything else.

**A brief is not ready without one.** `chain.py ready` counts the work order
alongside the six stages, the draft, the page and the Drive folder — because a
brief that is finished for us and unstartable for them is not finished.
