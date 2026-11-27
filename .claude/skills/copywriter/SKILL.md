---
name: copywriter
description: Write the ad copy — a source (a teardown record, or a piece of raw copy to swipe) or a brief number, plus a brand and a product, go in; the words Meta shows beside the ad come out (primary text, headlines, descriptions, captions), one set per requested format, price-checked. Use whenever someone says "write the copy for brief 0221", "primary text and headlines for <brand>", "write the words for this ad", "copy for this teardown for <brand>", "swipe this copy for <brand>", "give me captions and headlines for <brand> <product>", "dry run the copywriter", "redo the copy from the render stage", or hands over a teardown record or a swipe and asks for copy.
---

# Copywriter

> **Activates component:** `components/copywriter` — `machine/copy_writer.py` runs the eleven-stage copy chain on one source; `machine/brief_words.py` runs it for one brief number.

External dependencies: `components/copywriter/` (`machine/` the runner, `prompts/` the stage prompts — highest `-vN-` wins, `bank/formats.json` the copy styles, `bank/format-bank.json` and `bank/channel-map.json` the surfaces), `components/marketing-chain-checks/` (the copy gate), `components/elements/` (the format check), `components/run-kit/` (the model tiers), `brands/<brand>/` (the brand's `variables/copy.md`, `products/<product>.md`, `products/offer-bank.md`, the avatar folders — read, never written).

Plain note: the copywriter writes to nothing but its own run folder, and it calls a paid model at every stage. The dry run is free; a real run is not, so show the person the dry run and get a yes before running it.

**One command.** Run from the repo root. There is no default brand.

```
python3 components/copywriter/machine/copy_writer.py <source.md> --brand <brand> --product brands/<brand>/products/<product>.md --dry-run
python3 components/copywriter/machine/copy_writer.py <source.md> --brand <brand> --product brands/<brand>/products/<product>.md [--write-as caption,short-form] [--channel "Meta (feed / Reels)"] [--hooks 5] [--label <name>] [--avatar <key>]
```

Starting from a brief number instead of a source file — it finds the source (the delivered ad's transcript, else the brief's writing run) and writes primary text, headlines and descriptions:

```
python3 components/copywriter/machine/brief_words.py --brand <brand> --brief brief-NNNN [--product <product>] --dry-run
python3 components/copywriter/machine/brief_words.py --brand <brand> --brief brief-NNNN [--product <product>] [--source <file.md>] [--formats short-form,caption]
```

Keep what is already written and redo from one stage on:

```
python3 components/copywriter/machine/copy_writer.py <source.md> --brand <brand> --product brands/<brand>/products/<product>.md --label <name> --rerun-from stage8
```

- `--brand` and `--product` are required. `source` is a teardown record or raw copy to swipe.
- `--dry-run` spends nothing and writes nothing: it prints OK or MISSING for the source, product, brand variable map, offer bank, every output format, each avatar's files, and every `{field}` each stage's prompt names. It exits non-zero when something a run needs is missing. Run it first, show the person the result.
- `--write-as` names the formats to write (default: every format in `bank/formats.json`); each is checked against the element library before anything runs, and an unknown one is refused with the real ids named. `--hooks` is how many variations beyond the control. `--avatar` names the avatar instead of letting triage pick. `--label` names the run (default: the source file name). `--video` and `--ad` give the board a clip and the finished ad's nuance.
- `--promo` marks a promotion or value ad; `--awareness <doctrine id>` writes at that awareness level. `--no-gate` skips the copy gate on purpose and says so in `run.json`.
- `--tier NAME=MODEL` or `--model <model>` repoint models; leave them alone unless asked.
- To run on the shared Mac mini instead, use the `mini-run` skill; the mini's door is `components/copywriter/machine/lab_entry.py` (`--source`, `--product`, `--avatar`, `--write_as`, `--dry_run`).
- There is no single command that takes only a sentence. A person says the brand and points at the source or the brief number; the session finds the product file under `brands/<brand>/products/` and runs the dry run, then the command above.

## The rules the command enforces — do not work around any of them

1. **Organic source: the creator's voice, never the brand's.** The copy is that person speaking, not brand copy with their name on it. This outranks house style.
2. **All hooks ship.** The machine writes a control (the source's own opening, swiped straight) plus variations and never picks, ranks or marks one recommended. Choosing is the owner's.
3. **Never improve version 0.** It is the control; an upgraded control measures nothing.
4. **Formats are checked first.** Every `--write-as` id must be on the element library's copy list; an unknown one is refused before any run folder is made.
5. **The copy gate, after stage 8, before the brief.** Every price in the copy must be one the brand's offer bank sells today, and no UNFILLED note may be left. A failure writes `check.json`, keeps every file made so far, holds the brief (stage 9) and exits 2.
6. **No price in a headline or description** unless the ad is a promotion (`--promo`, or the angle row says so). Separately, stage 6 (expansion) runs only when the source's lane is organic.
7. **Nothing is written into `brands/`.** Read-only, always. Brand context is read from the brand's own folder at run time.
8. **A usage limit stops the run with one line** (`USAGE LIMIT — …`) and is not retried; ordinary failures get three attempts.
9. **Never pass `--no-gate` unless the person says to skip the check.**

## What comes back, and where it lands

`runs/copywriter/<brand>/<label>/` — each stage's output (`stage0--triage.md`, `stage1--record.md`, `stage2--spec.md`, `stage3--injection.md`, `stage4--placement.md`, `stage5--hooks.md`, `stage7--close.md`, `stage8--render.md` the finished copy, and so on), each stage's prompt as actually sent (`stageN--sent.md`), `check.json` from the gates, and `run.json` (status, timing, the model each stage used, the picked elements). The brief stage writes `stage9` only if the gate passed.

From `brief_words.py` the run folder is `runs/copywriter/<brand>/<product>-<brief>-words/` (for example `…-brief-0137-words`).

To lift the finished copy out, `python3 components/copywriter/machine/publish.py [label]` writes it to `runs/copywriter/<brand>/<label>/deliverable/`; it says "nothing to publish" when no run has finished copy.

Report: the copy as pasteable text (primary text, headlines, descriptions per format), whether the gate passed or held (and why, one clause), and the model/credit cost noted in `run.json` if the person asked. Do not send the copy anywhere; sending is the person's act.

Reply with the result and the folder it landed in (repo path or Drive folder name).
