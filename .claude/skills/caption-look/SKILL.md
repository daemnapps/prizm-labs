---
name: caption-look
description: Switch a finished (or in-progress) video's caption look — the run and the look go in; the captions come back in the new look as a new version of the cut sheet, the footage untouched. Use whenever someone says "switch this to the bold look", "put the clean lower captions on this", "one word at a time on the hook", "change the caption style", "the captions should look like the swipe's", "caption look", "what caption looks are there", or names a cut and a look.
---

# Caption look

> **Activates component:** `components/video-edit` — `machine/run.py change … captions`.


External dependencies: `components/video-edit/` (the machine; `looks/bank.json` is the list of looks, `machine/defaults.json` the dial, `machine/cutsheet.py` the gate that checks a look is on the list).

**A caption look is a SETTING, not an edit.** Switching it never re-edits
the footage. The looks on the list today (`looks/bank.json`, all `draft`
until the owner signs one):

| id | what |
|---|---|
| `bold-highlight` | Big white capitals with a black outline, 2–4 words at a time, the word being spoken turns yellow and pops. |
| `clean-lower` | Sentence-case white words on a soft dark plate, low in the frame. Reads like a subtitle, not a shout. |
| `one-word` | One huge word at a time, dead centre. For hooks and fast cuts. |

`match-swipe` (build a one-off look from the teardown's caption read) is
**not built yet** — say so plainly if it is asked for.

## The closest real step — there is no one-line "switch look" command yet

Switching a look on a run goes through the machine's own change step, the
same way any change at the captions stop does:

```
python3 components/video-edit/machine/run.py change <run-folder> captions "switch the captions to the <look id> look" --why "<his reason>"
```

That records the ask and the reason in `changes.jsonl`, copies the latest
cut sheet to a NEW version (`cutsheet-vN.json`) and reopens the captions
stop. Then the session sets `captions.look` in that new sheet to the look
id — the only edit made — and re-runs from the gate so the captioned cut is
rendered again:

```
python3 components/video-edit/machine/run.py start <kit-folder> --brand <brand> --label <label> --from gate
python3 components/video-edit/machine/run.py approve <run-folder> captions [--note "…"]
```

A run that has not started yet takes the look up front: a `controls.json`
with `caption_look` set, passed as `start … --controls <file>`. The default
is `bold-highlight`.

## The rules the machine enforces — do not work around any of them

1. **Text is a layer, never a generation.** The footage is not touched.
2. **A look must be on the list.** The gate refuses a `captions.look` that is
   not a row in `looks/bank.json` (or a match-swipe look, once that exists)
   and names the known ids. Nothing renders red.
3. **A change is a new version of the cut sheet with its reason kept** —
   never an edit in place, never a regeneration.
4. **Captions stay out of the safe zone**, 2–4 words, one highlight (the
   look's `y_pct` must clear the zone).
5. **Only the owner signs a look approved.** A new look is a new row in the bank;
   a changed row is a new version.

## What comes back

`runs/video-edit/<brand>/<label>/` — the new `cutsheet-vN.json`, the line in
`changes.jsonl`, the re-rendered captioned cut and `timeline.html` at the
captions stop.

Report: which look it is on now, the version number, and the timeline page
link.

Reply with the result and the folder it landed in (repo path or Drive folder name).
