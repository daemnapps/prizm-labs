---
name: image-sequence
description: Make a carousel or slideshow off one plate — slide one is the judged draft, every later slide is one change off it from the AI sequence brief's own slide-deltas, judged against slide one for the thread and finished to 9:16. Use whenever someone says "make the slides for p190", "build the carousel from that brief", "slides two onward", "run the sequence", "make the rest of the slideshow", or names an AI sequence brief and wants the pictures.
---

# Image sequence

> **Activates component:** `components/image-edit` — `sequence.py`, slides two onward off slide one.


External dependencies: `components/image-edit/` (the engine — `sequence.py`), `components/image-production/` (generation, the judge, the 9:16 finish), the AI sequence brief (`runs/image-teardown/<brand>/<label>/06-brief.md`, written by `image-teardown` with `--form sequence`), and slide one's draft (made by `image-draft`).

**One command. It runs the tool's own engine; nothing here adds logic.**

```
python3 components/image-edit/sequence.py <slide-one draft.png> --brand <brand> --deltas <the brief .md, or a .json list>
python3 components/image-edit/sequence.py <slide-one draft.png> --brand <brand> --deltas <brief> --dry-run
```

- `<slide-one draft>` is the judged draft of slide one — the plate. It is never written to.
- `--deltas` is the AI sequence brief itself: its slide-deltas block (a `json` list of `{slide, change, keep, type}`, slides two onward) is read out of it. A brief with no block is refused by name.
- `--count N` rolls N per slide; `--product <slug>` or `--ref <photo>` sends the real product photo along so the label holds; `--model` forces a declared image model.
- **`--dry-run` spends nothing** — every slide's instruction is resolved and written to its record, no model is called.

## What it does

For every slide from two onward: one edit off slide one carrying only that slide's `change` (the delta rule — under 400 characters, one or two changes, never a description of what slide one shows), with the slide's `keep` plus the thread (same person and face, same product held the same way, same palette, same framing) as what must not move. Two judges: the picture judge, then the two-picture judge with slide one beside the result — CHANGE PRESENT · NOTHING ELSE MOVED · still the same sequence. A passing slide is finished to 9:16 (content taped down, strips painted). Each slide's `type` from the brief is carried in the record for the compositor.

## The rules the command enforces — do not work around any of them

1. **Slide one is the plate.** Deltas start at slide two; a delta for slide one is refused.
2. **One change per slide.** A `change` that describes the scene, or asks for three things, is refused before anything is spent — narrow it in the brief, never here.
3. **The thread is judged, not assumed.** A slide that lost the person, the product, the palette or the framing is held under `rejected/` with the reason.
4. **Nothing is written over.** Slide one stays as it was; every slide is a new file under its own folder.
5. **Brand-agnostic.** No brand, product or person named in the engine; the brand's files come from `brands/<brand>/` by `--brand`.

## What comes back, and where it lands

`runs/image-edit/<brand>/<label>/` — `sequence.json` (the set: per slide its change, state, delivered and rejected files, its type block), and `slide-NN/` per slide with `edit.json`, the delivered 9:16 asset, `rejected/*-why.md`, and the engine's own record. The delivered assets mirror to `Shared Assets/runs/image-edit/<brand>/<label>/`.

Reply with the result and the folder it landed in (repo path or Drive folder name).
