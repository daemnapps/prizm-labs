# copy production

**copy-production** — takes **a source and a brief**, makes **the copy: primary
text, captions, headlines**. Does not **make pictures**.

(Formerly the copy machine / copywriter. The folder keeps the name
`components/copywriter/`; its runs keep the name `runs/copy-machine/`.)

A source is a teardown record (video or image, ad or organic) or a piece of raw
copy to swipe. The brief is what you pass with it: the brand, the product, the
formats to write, the channel, how many hooks.

## The three commands

Run from the repo root. `<brand>` is a folder under `brands/` — there is no
default brand.

**1. Dry run — check everything, spend nothing**

```
python3 components/copywriter/machine/copy.py <source.md> --brand <brand> \
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
python3 components/copywriter/machine/copy.py <source.md> --brand <brand> \
  --product brands/<brand>/products/<product>.md \
  [--write-as caption,short-form] [--channel "Meta (feed / Reels)"] [--hooks 5] \
  [--label <name>] [--source-reference "…"] [--video source.mp4] [--avatar <key>]
```

Files to `runs/copy-machine/<brand>/<label>/`: each stage's output, the prompt
as sent, `run.json`, `check.json`. Each stage runs on the model its tier names
(`reads` / `checks` / `designs`); `--tier reads=<model>` repoints a tier,
`--model <model>` forces one model for everything.

After the copy is written (stage 8) the **copy gate** checks it: every price
must be one the brand's offer bank sells today, and no UNFILLED note may be
left in it. A held run keeps everything it made, says why, and does not write
the brief. `--no-gate` skips the gate on purpose.

**3. Rerun from a stage — keep what is already written**

```
python3 components/copywriter/machine/copy.py <source.md> --brand <brand> \
  --product brands/<brand>/products/<product>.md --label <name> --rerun-from stage8
```

Every saved stage before the named one is read back, not bought again
(`stage8`, `8` and `render` all mean the same stage). An older run that still
sits in `results/<label>/` is carried over to `runs/copy-machine/` once.

## Around it

| | |
|---|---|
| `machine/serve.py` | the board, live on :8778 — every run from both run homes |
| `machine/publish.py [label]` | lifts finished copy into `output/` |
| `machine/rerender.py [label …]` | re-runs stage 8 against each run's own brand, avatar and product |
| `machine/batch.sh <brand> <product-file>` | the list inside it, a few at a time |
| `machine/test_rollout.py` | the tests — no model, no network, no real brand |

Rules, the stage table and the gates: `CLAUDE.md`.
