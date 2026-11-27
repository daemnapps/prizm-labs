---
name: image-edit
description: Fix one thing on a finished picture — the picture and ONE change (free words, or a named fix from the library: logo · text · product · layout · background · remove) go in; a new version comes out, judged against the original, the original never touched. Use whenever someone says "fix the logo on this one", "the tube is in the wrong hand", "the headline says SAALE, make it SALE", "swap the product for the real one", "move the badge to the top left", "take the watermark out", "change the background", "image edit", "what fixes are there", or names a picture and one thing wrong with it.
---

# Image edit

> **Activates component:** `components/image-edit` — `edit.py`, one change on a finished picture.


External dependencies: `components/image-edit/` (the engine; `library/fixes-vN-owner.json` the fixes, `splits.json` the keep/change split per kind, `prompts/compare-judge-vN-owner.md` the two-picture judge), `components/image-production/` (the image engine it edits through), `brands/<brand>/` (the real logo and product photo that ride along — read, never written).

**One command. One change.**

```
python3 components/image-edit/edit.py <picture> --brand <brand> --change "<the ONE thing to change>"
python3 components/image-edit/edit.py <picture> --brand <brand> --fix logo
python3 components/image-edit/edit.py <picture> --brand <brand> --fix text --arg was=SAALE --arg now=SALE
python3 components/image-edit/edit.py <picture> --brand <brand> --fix product --product <slug>
python3 components/image-edit/edit.py <picture> --brand <brand> --fix layout --arg element="the price badge" --arg where="the top left corner"
python3 components/image-edit/edit.py <picture> --brand <brand> --fix background --arg background="a plain white bathroom shelf"
python3 components/image-edit/edit.py <picture> --brand <brand> --fix remove --arg thing="the watermark"
python3 components/image-edit/edit.py <picture> --brand <brand> --fix … --dry-run
python3 components/image-edit/edit.py --fixes                      # the library, verbatim
```

- `--brand` is required. `--change` and `--fix` are exactly one.
- `--arg key=value` fills a fix's slots; a missing one is refused BY NAME.
- `--keep "…"` adds one more thing that must not move; `--ref <png>` attaches
  another reference (the real logo, the packshot) — reproduced exactly,
  never described; `--product <slug>` attaches the brand's product photo;
  `--kind picture|slide|frame-A|frame-B|frame-C` picks the keep/change split.
- **`--dry-run` spends nothing** — resolves everything, prints the
  instruction as it would be sent, writes `edit.json`.

## The rules the command enforces — do not work around any of them

1. **The instruction carries the delta and nothing else.** The reference
   carries the composition. A change past 400 characters has started
   describing the scene and is refused before anything is spent.
2. **One change per edit** (two at a push). Counted, and refused past that.
3. **The original is never written to.** The result is a new version,
   counted up per picture. A test enforces it.
4. **Two judges, both must pass:** the image engine's one-picture judge, then
   the two-picture judge — reference beside result — CHANGE PRESENT ·
   NOTHING ELSE MOVED · the fix's own test. A result that moved anything else
   is held under `rejected/` with its reason. The judge not running is a
   HOLD, never a pass.
5. **Refused, never guessed.** An unknown fix, kind or slot stops the work
   and names the real ones.
6. **9:16 only, content in the 4:5 zone.** A 4:5 or 9:16 reference leaves at
   9:16 — content edited at 4:5, finished with the strips painted.
7. **Every library row is `draft` until the owner marks it approved.** A changed
   row is a NEW file `-v<N+1>-owner.json`, never an edit in place.

## What comes back

`runs/image-edit/<brand>/<label>/` — `edit.json` (asked, the instruction
as sent, chars, changes, both verdicts, versions), the result as
`<stem>--<fix|edit>-v<N>.png`, `rejected/*-why.md`, `engine/` (the image
engine's own record); pictures mirrored to `Shared Assets/runs/image-edit/<brand>/<label>/`.

Report: pass or held (and why, one clause), and send the result beside the
original as images so the change is seen without opening anything.

Reply with the result and the folder it landed in (repo path or Drive folder name).
