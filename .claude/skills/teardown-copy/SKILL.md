---
name: teardown-copy
description: Run the copy teardown — a piece of words (ad primary text, a caption, an organic post, a headline set) goes in; its element labels and its brand-free construct come out. Use whenever someone says "tear down this copy for <brand>", "tear down this caption", "strip this post to its structure", "what's the construct of this ad copy", "tear down these headlines", "copy teardown", or pastes ad text and names a brand.
---

# Copy teardown

> **Not a component:** runs lab code in `lab/the owner/copy-teardown` — runs lab code.


External dependencies: `lab/the owner/copy-teardown/` (the machine), `brands/<brand>/` (must exist — names the run folder only), `components/elements` (the library the labels are checked against).

**One command. Words only.**

```
python3 lab/the owner/copy-teardown/tools/run.py <source.md or .txt> --brand <brand>
echo "<pasted text>" | python3 lab/the owner/copy-teardown/tools/run.py - --brand <brand>
python3 lab/the owner/copy-teardown/tools/run.py <source> --brand <brand> --dry-run
```

- The source is a `.md`/`.txt` file, or `-` for text piped in. A saved paid
  swipe card has only its `## Headline` / `## Primary text` parts taken.
- `--brand` is required and is only whose swipe it is: it names the run
  folder. Nothing of the brand is read into a prompt — a construct is for any
  brand; the brand enters later, at injection, in copy production.
- **`--dry-run` spends nothing** — resolves and fills every prompt, shows the
  model per step and where it would file, makes no model call, leaves no file.
- After a hold: fix the prompt (a new `-vN-` file) or the source, then
  `--rerun-from tear1|tear2|tear3`.

## What it does

Three steps: the read (the copy as read, source names and source defects
kept apart) → element labels (format, placement, framework, awareness,
register, humor) → the construct (the structure with the source's subject
stripped out). Every prompt is saved as sent.

## The rules the command enforces — do not work around any of them

1. **Words only.** A page, an email with pictures, a picture or a video is
   refused and told which teardown it belongs to.
2. **The strip is done in code, not asked for.** Every source name becomes a
   numbered marker before the labelling and construct steps see the text, so
   they cannot carry one.
3. **Every label is a real library row** or an honest `none-fits` with a
   proposed row. An unknown id is refused with the real ids named.
4. **Three gates hold a run** — inputs before any model; elements after the
   labels; copy twice (the record arrived in its parts; the construct carries
   no source name, no price, no handle, hashtag or web address, no UNFILLED
   note, and ends on its LEFT OUT line). A held run says why in `check.json`.
5. **No brand in code or prompts. No default brand.**

## What comes back

`runs/copy-teardown/<brand>/<label>/` — `source.md` (exactly what the steps
saw), `tear1--record.md`, `elements.json`, `tear3--construct.md`, every
prompt as sent, `run.json`, `check.json`.

Report: the labels it gave, the construct in one line, and whether it was
held and why.

Reply with the result and the folder it landed in (repo path or Drive folder name).
