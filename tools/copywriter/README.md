# copy production

**copy-production** — takes **a source and a brief**, makes **the copy: primary
text, captions, headlines**. Does not **make pictures**.

(Formerly the copy machine / copywriter. The folder keeps the name
`tools/copywriter/`; its runs are filed under `runs/copywriter/`.)

A source is a teardown record (video or image, ad or organic) or a piece of raw
copy to swipe. The brief is what you pass with it: the brand, the product, the
formats to write, the channel, how many hooks.

## The three commands

Run from the repo root. `<brand>` is a folder under `brands/` — there is no
default brand.

**1. Dry run — check everything, spend nothing**

```
python3 tools/copywriter/machine/copy.py <source.md> --brand <brand> \
  --product brands/<brand>/products/<product>.md --dry-run
```

Prints OK / MISSING with character counts for: the source, the product, the
brand's variable map, the offer bank, every doctrine slice, every output
format (checked against the element library), each avatar's profile, language
rules and language rows per stage, and — stage by stage — every `{field}` the
prompt names against what the stage is handed, plus the model each stage would
use. No model is called and no file is written. Exits non-zero when something
a run needs is missing. Add `--avatar <key>` to check one avatar instead of
the whole roster.

**2. The run**

```
python3 tools/copywriter/machine/copy.py <source.md> --brand <brand> \
  --product brands/<brand>/products/<product>.md \
  [--write-as caption,short-form] [--channel "Meta (feed / Reels)"] [--hooks 5] \
  [--label <name>] [--source-reference "…"] [--video source.mp4] [--avatar <key>] \
  [--ad <finished-ad.md>]
```

`--ad` hands in the finished ad the copy runs beside (its story, person, what is
seen and said, its openings): the source stays the proven framework, the ad
supplies the nuance, and stage 8 adds thumbnail lines for its openings.

Files to `runs/copywriter/<brand>/<label>/`: each stage's output, the prompt
as sent, `run.json`, `check.json`. Each stage runs on the model its tier names
(`reads` / `checks` / `designs`); `--tier reads=<model>` repoints a tier,
`--model <model>` forces one model for everything.

After the copy is written (stage 8) the **copy gate** checks it: every price
must be one the brand's offer bank sells today, and no UNFILLED note may be
left in it. A held run keeps everything it made, says why, and does not write
the brief. `--no-gate` skips the gate on purpose.

Then the copy is **read back** (stage 8b) and **checked** (stage 8c). 8b
rewrites each body for the one person reading it: full sentences, one picture
she can see, on this product only, the spice the video scripts get, every
claim and the offer kept word for word. 8c is a reader who never saw 8b's
reasoning: she reads the finished words cold and passes or fails each text. A
fail gets one more 8b with her notes. On the second read, what she passed ships
when at least three texts, a headline and a description survive; otherwise the
run is HELD. The checked copy is written to `final--copy.md`, and that is the
copy every later step reads. Each stage's output is also reviewed by the
creative QC loop (`components/quality-checks`, filed in the run's `qc-log/`);
that review never stops a run.

The avatar's culture map (`brands/<brand>/core-avatars/<avatar>/culture-map.md`)
reaches every writing stage: a straight source stays straight unless the
culture map gives a receipt for a planted joke.

**3. Rerun from a stage — keep what is already written**

```
python3 tools/copywriter/machine/copy.py <source.md> --brand <brand> \
  --product brands/<brand>/products/<product>.md --label <name> --rerun-from stage8
```

Every saved stage before the named one is read back, not bought again
(`stage8`, `8` and `render` all mean the same stage). An older run that still
sits in `results/<label>/` is carried over to `runs/copywriter/` once.

## Around it

| | |
|---|---|
| `machine/serve.py` | the board, live on :8778 — every run from both run homes |
| `machine/publish.py [label]` | lifts finished copy into that run's own `deliverable/` |
| `machine/rerender.py [label …]` | re-runs stage 8 against each run's own brand, avatar and product |
| `machine/batch.sh <brand> <product-file>` | the list inside it, a few at a time |
| `machine/test_rollout.py` | the tests — no model, no network, no real brand |

The video chain's writing prompts (audience, injection, the stage-4 loop, the
brief, the page concept, the profile) live here too, under `prompts/video/`,
one current version per stage folder. The teardown prompts stay with the video
teardown.

Rules, the stage table and the gates: `CLAUDE.md`.
