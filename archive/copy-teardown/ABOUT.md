# Copy teardown

Built 2026-09-20. Video teardown takes a video apart, image teardown a picture,
email teardown an email. **This takes apart words** — ad primary text, a
caption, an organic post, a headline set — and nothing else. Damon: *"copy
would just be literally copy."*

It does not write copy. What comes out is what the copy IS (its labels, from
the one element library) and how it argues (its construct — the structure with
the source's brand, product and subject stripped out, ready for any brand's
message to be put in).

## One command

```
python3 tools/run.py <source file, or "-" for piped text> --brand <brand> [--label L] [--dry-run] [--rerun-from tear1|tear2|tear3] [--model M]
```

Three steps: **read** (the copy, the source's own names and its defects, each
under its own heading) → **label** (format, placement, framework, awareness,
register, humor — asked of the element library, never invented) →
**construct** (built from the record with every source name withheld). The run
files to `runs/copy-teardown/<brand>/<label>/` at the repo root. `--dry-run`
spends nothing and writes nothing. A real run is three model calls at most:
one read, one check, one design.

`--brand` says whose swipe it is and whose run folder it files under. There is
no default, and no brand file is read into a prompt.

## What is in the folder

| | |
|---|---|
| `tools/run.py` | the one entry |
| `tools/source_text.py` | the source as words · the free scan · tolerant reading of a model's answer · withholding names · what a construct may not carry |
| `tools/elements_label.py` | the candidate rows, and checking the labels against the library |
| `tools/gates.py` | the three gates — inputs, elements, copy |
| `tools/paths.py` | where things live (walks up; honours `AI_WORKSPACE`) |
| `prompts/` | `tear1-copy-read`, `tear2-element-labels`, `tear3-construct` — `-vN-damon.md`, highest wins |
| `tests/` | `python3 tests/test_copy_teardown.py` — stubbed model, temp workspace |

Look at a held run: `python3 tools/gates.py runs/copy-teardown/<brand>/<label>`.
See what the code finds in a source for free: `python3 tools/source_text.py scan <source>`.

## Where it came from — copy production's steps 0–2

The prompts here are adapted from `components/copywriter/prompts/`
`stage0-triage-v2`, `stage1-read-v2` and `stage2-spec-v2`. Nothing in that
folder was edited, and copy production still runs its own three steps.

| Copy production | Here | What changed |
|---|---|---|
| stage 0 triage — lane, format, voice, **avatar, funnel** | folded into `tear1` (lane, speaker, about, doing) and `tear2` (format) | avatar and funnel are about OUR reader — they are briefing, not teardown, and stay in copy production. The format is now a checked label, not a line of text |
| stage 1 read — beats, opening, turn, proof, close, voice, absences, awareness | `tear1` | same read, plus two new labelled parts: SOURCE NAMES and SOURCE DEFECTS, and a data block the code checks later steps against |
| stage 2 spec — the construct | `tear3` | same construct, but it is written from a record with every source name swapped for a marker, and a gate holds it if a name, a price or a defect came through. "Medium-bound" became "placement-bound" — the source here is always words |
| — | `tear2` | new: six element labels checked against the library |

### What a side-by-side test needs before production is switched

1. The same source through both: `copy.py` to the end of stage 2, and this
   tool — then the two constructs read next to each other by Damon.
2. A way for copy production to START from a filed teardown (read
   `tear1--record.md` as its record and `tear3--construct.md` as its spec)
   while still running its own stage 0 for avatar and funnel. That is a new
   flag on `copy.py`, added beside the old path — not built here.
3. Copy production's stage 0 hands `triage` to stages 1 and 2 (lane and voice
   binding). This tool's record carries the lane and the speaker, but not the
   avatar or funnel — so production's later stages still need its own triage.
4. One check that the names being withheld does not cost the construct
   anything production's injection step relied on.

## Not built

- No page or board. The run folder is the record; the lead decides where it shows.
- No batch entry — one source per run. A loop over a folder of swipe cards is a
  few lines on top of `run.main()`, and is better added after the first real run.
- No words-only list exists for delivery style, pacing or reference world, so
  those three are not labelled (see `CLAUDE.md`).
